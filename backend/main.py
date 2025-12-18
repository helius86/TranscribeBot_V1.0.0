from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from sqlmodel import Session, select

from .database import get_session, init_db
from .models import Chapter, Project, TranscriptLine, utcnow
from .schemas import (
    ChapterListResponse,
    ChapterRead,
    ChapterRegenerateRequest,
    ChapterUpdate,
    ProjectCreate,
    ProjectCreateResponse,
    ProjectWithCounts,
    TranscriptLineRead,
)
from .services.llm_chapter_generator import (
    ChapterData,
    generate_chapters_from_transcript,
    regenerate_single_chapter,
)
from .utils.parser import parse_transcript_txt


app = FastAPI(title="Chapter Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def format_hms(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@app.post("/projects/from-transcript-txt", response_model=ProjectCreateResponse)
def create_project_from_transcript(
    payload: ProjectCreate, session: Session = Depends(get_session)
) -> ProjectCreateResponse:
    parsed_lines = parse_transcript_txt(payload.transcript_txt)
    if not parsed_lines:
        raise HTTPException(status_code=400, detail="No transcript lines found to import.")

    duration_sec = max((end if end is not None else start) for start, end, _ in parsed_lines)

    project = Project(
        title=payload.title,
        platform=payload.platform,
        duration_sec=duration_sec,
        max_chapters=payload.max_chapters or 10,
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    transcript_models = [
        TranscriptLine(
            project_id=project.id,
            start_sec=start,
            end_sec=end,
            text=text,
            source="asr",
        )
        for start, end, text in parsed_lines
    ]
    session.add_all(transcript_models)
    session.commit()

    project.updated_at = utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)

    return ProjectCreateResponse(project=project, transcript_line_count=len(parsed_lines))


@app.get("/projects/{project_id}", response_model=ProjectWithCounts)
def get_project(project_id: int, session: Session = Depends(get_session)) -> ProjectWithCounts:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    transcript_count = session.exec(
        select(func.count(TranscriptLine.id)).where(TranscriptLine.project_id == project_id)
    ).one()
    chapter_count = session.exec(
        select(func.count(Chapter.id)).where(Chapter.project_id == project_id)
    ).one()

    return ProjectWithCounts(
        **project.dict(),
        transcript_line_count=int(transcript_count),
        chapter_count=int(chapter_count),
    )


@app.get(
    "/projects/{project_id}/transcript",
    response_model=List[TranscriptLineRead],
)
def get_transcript_lines(
    project_id: int, session: Session = Depends(get_session)
) -> List[TranscriptLineRead]:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    result = session.exec(
        select(TranscriptLine).where(TranscriptLine.project_id == project_id).order_by(TranscriptLine.start_sec)
    ).all()
    return result


@app.get(
    "/projects/{project_id}/chapters",
    response_model=ChapterListResponse,
)
def get_chapters(
    project_id: int, session: Session = Depends(get_session)
) -> ChapterListResponse:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    chapters = session.exec(
        select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.order, Chapter.start_sec)
    ).all()
    return ChapterListResponse(chapters=chapters)


@app.post(
    "/projects/{project_id}/generate_chapters",
    response_model=ChapterListResponse,
)
def generate_chapters(
    project_id: int, session: Session = Depends(get_session)
) -> ChapterListResponse:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    transcript_lines = session.exec(
        select(TranscriptLine).where(TranscriptLine.project_id == project_id).order_by(TranscriptLine.start_sec)
    ).all()
    if not transcript_lines:
        raise HTTPException(status_code=400, detail="No transcript lines to generate chapters from.")

    stub_chapters: List[ChapterData] = generate_chapters_from_transcript(
        transcript_lines, max_chapters=project.max_chapters
    )

    existing = session.exec(select(Chapter).where(Chapter.project_id == project_id)).all()
    for ch in existing:
        session.delete(ch)
    session.commit()

    new_chapters = []
    for idx, ch_data in enumerate(stub_chapters):
        chapter = Chapter(
            project_id=project_id,
            title=ch_data.title,
            start_sec=ch_data.start_sec,
            end_sec=ch_data.end_sec,
            summary=ch_data.summary,
            tags=ch_data.tags,
            source=ch_data.source,
            confidence=ch_data.confidence,
            order=ch_data.order or idx + 1,
        )
        new_chapters.append(chapter)
        session.add(chapter)
    session.commit()

    refreshed = session.exec(
        select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.order, Chapter.start_sec)
    ).all()
    return ChapterListResponse(chapters=refreshed)


@app.put("/chapters/{chapter_id}", response_model=ChapterRead)
def update_chapter(
    chapter_id: int, payload: ChapterUpdate, session: Session = Depends(get_session)
) -> ChapterRead:
    chapter = session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found.")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(chapter, field, value)
    chapter.updated_at = datetime.utcnow()
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


@app.post("/chapters/{chapter_id}/regenerate", response_model=ChapterRead)
def regenerate_chapter(
    chapter_id: int, payload: ChapterRegenerateRequest, session: Session = Depends(get_session)
) -> ChapterRead:
    chapter = session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found.")

    transcript_lines = session.exec(
        select(TranscriptLine)
        .where(TranscriptLine.project_id == chapter.project_id)
        .order_by(TranscriptLine.start_sec)
    ).all()

    regenerated = regenerate_single_chapter(
        transcript_lines=transcript_lines,
        new_start_sec=payload.new_start_sec,
        existing_title=chapter.title,
        existing_summary=chapter.summary,
    )

    chapter.title = regenerated.title
    chapter.start_sec = regenerated.start_sec
    chapter.summary = regenerated.summary
    chapter.source = regenerated.source
    chapter.updated_at = datetime.utcnow()

    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


@app.get("/projects/{project_id}/export/bilibili", response_class=PlainTextResponse)
def export_bilibili(project_id: int, session: Session = Depends(get_session)) -> PlainTextResponse:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    chapters = session.exec(
        select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.order, Chapter.start_sec)
    ).all()
    lines = [f"{format_hms(ch.start_sec)} {ch.title}" for ch in chapters]
    return PlainTextResponse("\n".join(lines))


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}

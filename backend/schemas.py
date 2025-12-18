from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str
    platform: Optional[str] = None
    max_chapters: Optional[int] = Field(default=10)
    transcript_txt: str


class ProjectRead(BaseModel):
    id: int
    title: str
    platform: Optional[str]
    duration_sec: Optional[int]
    max_chapters: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ProjectWithCounts(ProjectRead):
    transcript_line_count: int
    chapter_count: int


class TranscriptLineRead(BaseModel):
    id: int
    project_id: int
    start_sec: int
    end_sec: Optional[int]
    text: str
    source: str

    class Config:
        orm_mode = True


class ChapterBase(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    start_sec: Optional[int] = None
    end_sec: Optional[int] = None
    tags: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    order: Optional[int] = None
    version: Optional[int] = None


class ChapterRead(ChapterBase):
    id: int
    project_id: int
    title: str
    start_sec: int
    order: int
    created_at: datetime
    updated_at: datetime
    source: str

    class Config:
        orm_mode = True


class ChapterUpdate(ChapterBase):
    title: Optional[str] = None
    summary: Optional[str] = None
    start_sec: Optional[int] = None
    end_sec: Optional[int] = None
    order: Optional[int] = None


class ChapterRegenerateRequest(BaseModel):
    new_start_sec: int


class ProjectCreateResponse(BaseModel):
    project: ProjectRead
    transcript_line_count: int


class ChapterListResponse(BaseModel):
    chapters: List[ChapterRead]

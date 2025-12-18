from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.utcnow()


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    platform: Optional[str] = Field(default=None)
    duration_sec: Optional[int] = Field(default=None)
    max_chapters: int = Field(default=10)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class TranscriptLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    start_sec: int
    end_sec: Optional[int] = Field(default=None)
    text: str
    source: str = Field(default="asr")
    created_at: datetime = Field(default_factory=utcnow)


class Chapter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    title: str
    start_sec: int
    end_sec: Optional[int] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    tags: Optional[str] = Field(default=None)  # comma-separated
    source: str = Field(default="auto")
    confidence: Optional[float] = Field(default=None)
    order: int = Field(default=1)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    version: int = Field(default=1)

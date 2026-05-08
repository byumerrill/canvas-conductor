"""Pydantic models for Canvas API responses.

Models accept extra fields so future Canvas additions don't break parsing.
Fields are conservative — only those documented in CANVAS-API-REFERENCE.md
and used by commands are included.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class _CanvasModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class Course(_CanvasModel):
    id: int
    name: str
    course_code: str | None = None
    workflow_state: str | None = None
    default_view: str | None = None
    term: dict[str, Any] | None = None
    start_at: str | None = None
    end_at: str | None = None


class Module(_CanvasModel):
    id: int
    name: str
    position: int | None = None
    published: bool | None = None
    items_count: int = 0
    unlock_at: str | None = None
    prerequisite_module_ids: list[int] = []


class ModuleItem(_CanvasModel):
    id: int
    title: str
    type: str
    position: int | None = None
    indent: int | None = None
    content_id: int | None = None
    page_url: str | None = None
    external_url: str | None = None
    published: bool | None = None
    module_id: int | None = None


class Page(_CanvasModel):
    page_id: int | None = None
    url: str
    title: str
    body: str | None = None
    published: bool | None = None
    front_page: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None


class Assignment(_CanvasModel):
    id: int
    name: str
    points_possible: float | None = None
    due_at: str | None = None
    unlock_at: str | None = None
    lock_at: str | None = None
    published: bool | None = None
    submission_types: list[str] = []
    grading_type: str | None = None
    assignment_group_id: int | None = None
    position: int | None = None


class AssignmentGroup(_CanvasModel):
    id: int
    name: str
    position: int | None = None
    group_weight: float | None = None


class CanvasFile(_CanvasModel):
    id: int
    display_name: str | None = None
    filename: str | None = None
    size: int | None = None
    content_type: str | None = None
    url: str | None = None
    folder_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class Submission(_CanvasModel):
    id: int | None = None
    user_id: int
    assignment_id: int | None = None
    score: float | None = None
    grade: str | None = None
    workflow_state: str | None = None
    submitted_at: str | None = None
    late: bool | None = None
    missing: bool | None = None
    submission_type: str | None = None


class User(_CanvasModel):
    id: int
    name: str | None = None
    email: str | None = None
    login_id: str | None = None


class Enrollment(_CanvasModel):
    id: int
    user_id: int
    type: str
    enrollment_state: str | None = None
    user: dict[str, Any] | None = None


class Tab(_CanvasModel):
    id: str
    label: str | None = None
    type: str | None = None
    position: int | None = None
    visibility: str | None = None
    hidden: bool | None = None


class DiscussionTopic(_CanvasModel):
    id: int
    title: str
    message: str | None = None
    published: bool | None = None
    pinned: bool | None = None
    discussion_type: str | None = None
    posted_at: str | None = None

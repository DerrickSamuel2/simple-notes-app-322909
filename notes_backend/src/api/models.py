"""Pydantic models for the notes API."""

from __future__ import annotations

from typing import Annotated, Optional

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Shared fields for creating/updating notes."""

    title: Annotated[
        str,
        Field(
            ...,
            min_length=1,
            max_length=200,
            description="Short title for the note (1-200 chars).",
            examples=["Grocery list"],
        ),
    ]
    content: Annotated[
        str,
        Field(
            ...,
            min_length=1,
            max_length=20_000,
            description="Full note content (1-20000 chars).",
            examples=["Milk\nEggs\nBread"],
        ),
    ]


class NoteCreateRequest(NoteBase):
    """Request body for creating a note."""


class NoteUpdateRequest(NoteBase):
    """Request body for updating a note."""


class NoteResponse(NoteBase):
    """Response model for a note."""

    id: Annotated[int, Field(..., description="Note identifier.", examples=[1])]
    created_at: Annotated[
        str,
        Field(
            ...,
            description="Creation timestamp (as stored by SQLite).",
            examples=["2026-02-17 10:11:12"],
        ),
    ]
    updated_at: Annotated[
        str,
        Field(
            ...,
            description="Last update timestamp (as stored by SQLite).",
            examples=["2026-02-17 10:20:00"],
        ),
    ]


class NotesListResponse(BaseModel):
    """Response model for listing notes."""

    items: Annotated[list[NoteResponse], Field(..., description="Notes collection.")]
    limit: Annotated[int, Field(..., ge=1, le=200, description="Applied limit.")]
    offset: Annotated[int, Field(..., ge=0, description="Applied offset.")]


class ErrorResponse(BaseModel):
    """Generic error response."""

    detail: Annotated[str, Field(..., description="Human-readable error message.")]


class DeleteResponse(BaseModel):
    """Response for delete operations."""

    deleted: Annotated[bool, Field(..., description="True if the note was deleted.")]
    id: Annotated[int, Field(..., description="Requested note id.")]
    message: Optional[str] = Field(
        default=None, description="Optional message providing more details."
    )

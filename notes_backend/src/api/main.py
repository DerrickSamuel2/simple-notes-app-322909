"""FastAPI app entrypoint for the Notes backend.

Provides a REST API for creating, listing, retrieving, updating, and deleting notes.
The API persists notes in a SQLite database configured by the SQLITE_DB environment
variable (provided by the database container).
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Path, Query
import os

from fastapi.middleware.cors import CORSMiddleware

from src.api import db
from src.api.models import (
    DeleteResponse,
    ErrorResponse,
    NoteCreateRequest,
    NoteResponse,
    NotesListResponse,
    NoteUpdateRequest,
)

openapi_tags = [
    {"name": "health", "description": "Service health and diagnostics."},
    {"name": "notes", "description": "CRUD operations for notes."},
]


def _csv_env(name: str) -> list[str]:
    """Parse a comma-separated env var into a list of trimmed, non-empty strings."""
    raw = os.getenv(name, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


app = FastAPI(
    title="Simple Notes API",
    description=(
        "Backend API for a simple notes application. "
        "Notes are stored in SQLite and exposed via CRUD endpoints."
    ),
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# If ALLOWED_ORIGINS is configured, use it; otherwise allow all (template-friendly).
_allowed_origins = _csv_env("ALLOWED_ORIGINS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=_csv_env("ALLOWED_METHODS") or ["*"],
    allow_headers=_csv_env("ALLOWED_HEADERS") or ["*"],
    max_age=int(os.getenv("CORS_MAX_AGE", "600")),
)


@app.get(
    "/",
    tags=["health"],
    summary="Health check",
    description="Simple health check endpoint to verify the service is running.",
    response_model=dict,
    operation_id="health_check",
)
# PUBLIC_INTERFACE
def health_check():
    """Health check endpoint.

    Returns:
        JSON with a 'message' key when the service is running.
    """
    return {"message": "Healthy"}


@app.get(
    "/notes",
    tags=["notes"],
    summary="List notes",
    description="List notes ordered by most recently updated first.",
    response_model=NotesListResponse,
    operation_id="list_notes",
    responses={500: {"model": ErrorResponse, "description": "Database error."}},
)
# PUBLIC_INTERFACE
def list_notes(
    limit: int = Query(
        default=100,
        ge=1,
        le=200,
        description="Max number of notes to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of notes to skip (pagination).",
    ),
) -> NotesListResponse:
    """List notes.

    Args:
        limit: Max number of notes to return.
        offset: Pagination offset.

    Returns:
        NotesListResponse with items, limit, and offset.
    """
    try:
        items = db.list_notes(limit=limit, offset=offset)
        return NotesListResponse(items=items, limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/notes/{note_id}",
    tags=["notes"],
    summary="Get note",
    description="Fetch a single note by its id.",
    response_model=NoteResponse,
    operation_id="get_note",
    responses={
        404: {"model": ErrorResponse, "description": "Note not found."},
        500: {"model": ErrorResponse, "description": "Database error."},
    },
)
# PUBLIC_INTERFACE
def get_note(
    note_id: int = Path(..., ge=1, description="The id of the note to retrieve.")
) -> NoteResponse:
    """Get a note by id.

    Args:
        note_id: Note identifier.

    Returns:
        The requested note.

    Raises:
        HTTPException: 404 if not found.
    """
    try:
        note = db.get_note(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found.")
        return NoteResponse(**note)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/notes",
    tags=["notes"],
    summary="Create note",
    description="Create a new note with a title and content.",
    response_model=NoteResponse,
    status_code=201,
    operation_id="create_note",
    responses={500: {"model": ErrorResponse, "description": "Database error."}},
)
# PUBLIC_INTERFACE
def create_note(payload: NoteCreateRequest) -> NoteResponse:
    """Create a note.

    Args:
        payload: NoteCreateRequest with title and content.

    Returns:
        The created note.
    """
    try:
        created = db.create_note(title=payload.title, content=payload.content)
        return NoteResponse(**created)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.put(
    "/notes/{note_id}",
    tags=["notes"],
    summary="Update note",
    description="Replace a note's title and content by id.",
    response_model=NoteResponse,
    operation_id="update_note",
    responses={
        404: {"model": ErrorResponse, "description": "Note not found."},
        500: {"model": ErrorResponse, "description": "Database error."},
    },
)
# PUBLIC_INTERFACE
def update_note(
    payload: NoteUpdateRequest,
    note_id: int = Path(..., ge=1, description="The id of the note to update."),
) -> NoteResponse:
    """Update an existing note.

    Args:
        note_id: Note identifier.
        payload: NoteUpdateRequest with updated title and content.

    Returns:
        The updated note.

    Raises:
        HTTPException: 404 if not found.
    """
    try:
        updated = db.update_note(note_id=note_id, title=payload.title, content=payload.content)
        if not updated:
            raise HTTPException(status_code=404, detail="Note not found.")
        return NoteResponse(**updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete(
    "/notes/{note_id}",
    tags=["notes"],
    summary="Delete note",
    description="Delete a note by id.",
    response_model=DeleteResponse,
    operation_id="delete_note",
    responses={
        404: {"model": ErrorResponse, "description": "Note not found."},
        500: {"model": ErrorResponse, "description": "Database error."},
    },
)
# PUBLIC_INTERFACE
def delete_note(
    note_id: int = Path(..., ge=1, description="The id of the note to delete.")
) -> DeleteResponse:
    """Delete a note.

    Args:
        note_id: Note identifier.

    Returns:
        DeleteResponse indicating deletion outcome.

    Raises:
        HTTPException: 404 if not found.
    """
    try:
        deleted = db.delete_note(note_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Note not found.")
        return DeleteResponse(deleted=True, id=note_id, message="Note deleted.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

"""
API router for tag management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from config.db import get_db
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag_schema import TagCreate, TagUpdate, TagResponse
from app.api.dependencies import require_ta, require_authenticated

router = APIRouter()


@router.post(
    "/",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tag (TA/Admin only)",
)
def create_tag(
    tag_in: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    """
    Create a new tag. Accessible by TAs, Instructors, and Admins.
    """
    existing_tag = db.query(Tag).filter(Tag.name == tag_in.name.lower()).first()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with this name already exists.",
        )

    db_tag = Tag(name=tag_in.name.lower(), created_by_id=current_user.id)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


@router.get("/", response_model=List[TagResponse], summary="List all tags or search by name")
def get_all_tags(
    search: Optional[str] = Query(None, description="Search for tags by name (case-insensitive)."),
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated),
):
    """
    Retrieve a list of all tags. Supports searching by name.
    Accessible by any authenticated user.
    """
    query = db.query(Tag)
    if search:
        query = query.filter(Tag.name.ilike(f"%{search}%"))
    tags = query.order_by(Tag.name).all()
    return tags


@router.get("/{tag_id}", response_model=TagResponse, summary="Get a tag by ID")
def get_tag_by_id(
    tag_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated),
):
    """
    Retrieve the details of a specific tag by its ID.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag


@router.put("/{tag_id}", response_model=TagResponse, summary="Update a tag (TA/Admin only)")
def update_tag(
    tag_id: int,
    tag_in: TagUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_ta),
):
    """
    Update an existing tag's name. Accessible by TAs, Instructors, and Admins.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    tag.name = tag_in.name.lower()
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a tag (TA/Admin only)")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_ta),
):
    """
    Delete a tag from the database. Accessible by TAs, Instructors, and Admins.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    db.delete(tag)
    db.commit()
    return
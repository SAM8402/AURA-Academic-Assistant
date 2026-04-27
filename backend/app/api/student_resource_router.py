"""
Student Resource Router - Personal resource management for students.

This module provides endpoints for students to manage their personal resources
(documents, images, links) separate from course materials.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import shutil
import uuid

from config.db import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.resource import Resource
from app.schemas.resource_schema import ResourceType, ResourceVisibility

router = APIRouter(prefix="/student-resources", tags=["Student Resources"])

# Configuration
UPLOAD_DIR = "uploads/student_resources"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ============================================================================
# Schemas
# ============================================================================

from pydantic import BaseModel, HttpUrl


class StudentResourceCreate(BaseModel):
    """Schema for creating a student resource."""
    title: Optional[str] = None
    resource_type: str  # "document", "image", "link"
    url: Optional[str] = None
    file_name: Optional[str] = None


class StudentResourceResponse(BaseModel):
    """Schema for student resource response."""
    id: int
    title: str
    resource_type: str
    url: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    is_pinned: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/my-resources", response_model=List[StudentResourceResponse])
async def get_my_resources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all personal resources for the current student.
    
    Returns:
        List of student resources
    """
    resources = db.query(Resource).filter(
        Resource.created_by_id == current_user.id,
        Resource.visibility == ResourceVisibility.PRIVATE,
        Resource.is_active == True
    ).order_by(Resource.created_at.desc()).all()
    
    result = []
    for res in resources:
        result.append({
            "id": res.id,
            "title": res.title,
            "resource_type": res.resource_type.value,
            "url": res.url,
            "file_path": res.file_path,
            "file_name": res.description,  # We store filename in description
            "is_pinned": res.is_pinned,
            "created_at": res.created_at
        })
    
    return result


@router.post("/upload-document", response_model=StudentResourceResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document (PDF, DOC, DOCX) as a personal resource.
    
    Args:
        file: Document file to upload
        title: Optional title for the resource
        
    Returns:
        Created resource details
    """
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to start
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024)}MB"
        )
    
    # Validate file type
    allowed_extensions = [".pdf", ".doc", ".docx", ".txt"]
    file_ext = os.path.splitext(file.filename or 'file')[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Create resource record
    resource = Resource(
        title=title or file.filename,
        description=file.filename,  # Store original filename
        resource_type=ResourceType.DOCUMENT,
        file_path=file_path,
        visibility=ResourceVisibility.PRIVATE,
        created_by_id=current_user.id,
        is_active=True
    )
    
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    return {
        "id": resource.id,
        "title": resource.title,
        "resource_type": resource.resource_type.value,
        "url": None,
        "file_path": resource.file_path,
        "file_name": resource.description,
        "created_at": resource.created_at
    }


@router.post("/upload-image", response_model=StudentResourceResponse)
async def upload_image(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an image as a personal resource.
    
    Args:
        file: Image file to upload
        title: Optional title for the resource
        
    Returns:
        Created resource details
    """
    # Validate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024)}MB"
        )
    
    # Validate file type
    allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    file_ext = os.path.splitext(file.filename or 'file')[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Create resource record
    resource = Resource(
        title=title or file.filename,
        description=file.filename,
        resource_type=ResourceType.DOCUMENT,  # Using DOCUMENT for images too
        file_path=file_path,
        visibility=ResourceVisibility.PRIVATE,
        created_by_id=current_user.id,
        is_active=True
    )
    
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    return {
        "id": resource.id,
        "title": resource.title,
        "resource_type": "image",
        "url": None,
        "file_path": resource.file_path,
        "file_name": resource.description,
        "created_at": resource.created_at
    }


@router.post("/add-link", response_model=StudentResourceResponse)
async def add_link(
    url: str = Form(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a link as a personal resource.
    
    Args:
        url: URL to add
        title: Optional title for the resource
        
    Returns:
        Created resource details
    """
    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://"
        )
    
    # Create resource record
    resource = Resource(
        title=title or url,
        description=None,
        resource_type=ResourceType.LINK,
        url=url,
        visibility=ResourceVisibility.PRIVATE,
        created_by_id=current_user.id,
        is_active=True
    )
    
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    return {
        "id": resource.id,
        "title": resource.title,
        "resource_type": resource.resource_type.value,
        "url": resource.url,
        "file_path": None,
        "file_name": None,
        "created_at": resource.created_at
    }


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a personal resource.
    
    Args:
        resource_id: ID of resource to delete
        
    Returns:
        204 No Content on success
    """
    resource = db.query(Resource).filter(
        Resource.id == resource_id,
        Resource.created_by_id == current_user.id,
        Resource.visibility == ResourceVisibility.PRIVATE
    ).first()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found or access denied"
        )
    
    # Delete file if exists
    if resource.file_path and os.path.exists(resource.file_path):
        try:
            os.remove(resource.file_path)
        except Exception as e:
            print(f"Warning: Failed to delete file {resource.file_path}: {e}")
    
    # Soft delete
    resource.is_active = False
    db.commit()
    
    return None


@router.patch("/{resource_id}/pin", response_model=StudentResourceResponse)
async def toggle_pin_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Toggle pin status of a personal resource.
    
    Args:
        resource_id: ID of resource to pin/unpin
        
    Returns:
        Updated resource details
    """
    resource = db.query(Resource).filter(
        Resource.id == resource_id,
        Resource.created_by_id == current_user.id,
        Resource.visibility == ResourceVisibility.PRIVATE,
        Resource.is_active == True
    ).first()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found or access denied"
        )
    
    # Toggle pin status
    resource.is_pinned = not resource.is_pinned
    db.commit()
    db.refresh(resource)
    
    return {
        "id": resource.id,
        "title": resource.title,
        "resource_type": resource.resource_type.value,
        "url": resource.url,
        "file_path": resource.file_path,
        "file_name": resource.description,
        "is_pinned": resource.is_pinned,
        "created_at": resource.created_at
    }


@router.get("/download/{resource_id}")
async def download_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download a personal resource file.
    
    Args:
        resource_id: ID of resource to download
        
    Returns:
        File download response
    """
    from fastapi.responses import FileResponse
    
    resource = db.query(Resource).filter(
        Resource.id == resource_id,
        Resource.created_by_id == current_user.id,
        Resource.visibility == ResourceVisibility.PRIVATE,
        Resource.is_active == True
    ).first()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found or access denied"
        )
    
    if not resource.file_path or not os.path.exists(resource.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Increment download count
    resource.download_count += 1
    db.commit()
    
    # Return file
    filename = resource.description or "download"
    return FileResponse(
        path=resource.file_path,
        filename=filename,
        media_type="application/octet-stream"
    )

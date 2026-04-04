"""
API router for course management.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.course import Course
from app.models.user import User
from app.schemas.course_schema import CourseCreate, CourseUpdate, CourseResponse
from app.api.dependencies import require_admin, require_authenticated

router = APIRouter()


@router.post(
    "/",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course (Admin only)",
)
def create_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new course in the database. Only accessible by administrators.
    """
    # Check if a course with the same name already exists
    existing_course = db.query(Course).filter(Course.name == course_in.name).first()
    if existing_course:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A course with this name already exists.",
        )

    db_course = Course(**course_in.model_dump(), created_by_id=current_user.id)
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/public", response_model=List[CourseResponse], summary="List all available courses (Public)")
def get_all_courses_public(
    db: Session = Depends(get_db),
):
    """
    Retrieve a list of all available courses. Public endpoint for registration form.
    Accessible without authentication.
    """
    courses = db.query(Course).order_by(Course.name).all()
    return courses


@router.get("/my-courses", response_model=List[CourseResponse], summary="Get current user's assigned courses")
def get_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Retrieve the list of courses assigned to the current user.
    - For Students: Returns courses assigned by admin/instructor
    - For TAs/Instructors: Returns courses selected during registration
    """
    courses = db.query(Course).join(
        Course.assigned_users
    ).filter(
        Course.assigned_users.any(user_id=current_user.id)
    ).order_by(Course.name).all()
    return courses


@router.get("/", response_model=List[CourseResponse], summary="List all available courses")
def get_all_courses(
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated),
):
    """
    Retrieve a list of all available courses. Accessible by any authenticated user.
    """
    courses = db.query(Course).order_by(Course.name).all()
    return courses


@router.get("/{course_id}", response_model=CourseResponse, summary="Get a course by ID")
def get_course_by_id(
    course_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated),
):
    """
    Retrieve the details of a specific course by its ID.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


@router.put("/{course_id}", response_model=CourseResponse, summary="Update a course (Admin only)")
def update_course(
    course_id: int,
    course_in: CourseUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Update an existing course's details. Only accessible by administrators.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    update_data = course_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a course (Admin only)")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Delete a course from the database. Only accessible by administrators.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    db.delete(course)
    db.commit()
    return
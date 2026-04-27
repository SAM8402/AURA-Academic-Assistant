"""
API router for slide deck generation and management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.db import get_db
from app.models.user import User
from app.models.course import Course
from app.models.slide_deck import SlideDeck
from app.schemas.slide_deck_schema import (
    SlideDeckGenerationRequest, SlideDeckUpdateRequest, SlideDeckResponse, SlideDeckPreview
)
from app.api.dependencies import require_ta, require_authenticated
from app.services.slides.deck_generator_service import slide_deck_service
from app.services.slides.pptx_export_service import export_to_pptx
from app.services.slides.pdf_export_service import export_to_pdf

router = APIRouter()


@router.post(
    "/preview",
    response_model=SlideDeckPreview,
    summary="Generate a preview of the slide deck (TA/Instructor only)",
)
async def generate_slide_deck_preview(
    request: SlideDeckGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    """
    Generates a preview outline of the slide deck before actual generation.
    """
    course = db.query(Course).filter(Course.id == request.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Generate preview using the AI service
    preview_content = await slide_deck_service.generate_preview(
        course_name=course.name,
        topics=request.topics,
        num_slides=request.num_slides,
        description=request.description or "",
        format=getattr(request, 'format', 'presentation'),
    )

    if "error" in preview_content:
        raise HTTPException(
            status_code=500,
            detail=f"AI service error: {preview_content['error']}"
        )

    return preview_content


@router.post(
    "/",
    response_model=SlideDeckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new slide deck (TA/Instructor only)",
)
async def generate_slide_deck(
    request: SlideDeckGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    """
    Generates a new slide deck using the AI service based on specified topics
    and saves it to the database.
    """
    course = db.query(Course).filter(Course.id == request.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Generate slide content using the AI service
    generated_content = await slide_deck_service.generate_slides(
        course_name=course.name,
        topics=request.topics,
        num_slides=request.num_slides,
        description=request.description or "",
        format=getattr(request, 'format', 'presentation'),
        include_graphs=getattr(request, 'include_graphs', False),
        graph_types=getattr(request, 'graph_types', None),
    )

    if "error" in generated_content or "slides" not in generated_content:
        raise HTTPException(
            status_code=500,
            detail=f"AI service error: {generated_content.get('error', 'Invalid content received')}"
        )

    # Save the generated slide deck to the database
    db_slide_deck = SlideDeck(
        title=request.title,
        description=request.description,
        course_id=request.course_id,
        created_by_id=current_user.id,
        slides=generated_content["slides"],
    )
    db.add(db_slide_deck)
    db.commit()
    db.refresh(db_slide_deck)
    return db_slide_deck


@router.get("/", response_model=List[SlideDeckResponse], summary="List all slide decks")
def get_all_slide_decks(
    search: Optional[str] = Query(None, description="Search slide decks by title."),
    course_id: Optional[int] = Query(None, description="Filter slide decks by course ID."),
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated),
):
    """
    Retrieves a list of all available slide decks, accessible to any authenticated user.
    """
    query = db.query(SlideDeck)
    if search:
        query = query.filter(SlideDeck.title.ilike(f"%{search}%"))
    if course_id:
        query = query.filter(SlideDeck.course_id == course_id)
    return query.order_by(SlideDeck.created_at.desc()).all()


@router.get("/{deck_id}", response_model=SlideDeckResponse, summary="Get a single slide deck")
def get_slide_deck(deck_id: int, db: Session = Depends(get_db), _: User = Depends(require_authenticated)):
    """
    Retrieves a single slide deck by its ID.
    """
    db_deck = db.query(SlideDeck).filter(SlideDeck.id == deck_id).first()
    if not db_deck:
        raise HTTPException(status_code=404, detail="Slide deck not found")
    return db_deck


@router.put("/{deck_id}", response_model=SlideDeckResponse, summary="Update a slide deck (Creator only)")
def update_slide_deck(
    deck_id: int,
    request: SlideDeckUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    """
    Updates a slide deck's title, description, or slide content.
    Only the original creator can perform this action.
    """
    db_deck = db.query(SlideDeck).filter(SlideDeck.id == deck_id).first()
    if not db_deck:
        raise HTTPException(status_code=404, detail="Slide deck not found")
    if db_deck.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update slide decks you have created.")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_deck, key, value)

    db.commit()
    db.refresh(db_deck)
    return db_deck


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a slide deck (Creator only)")
def delete_slide_deck(deck_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_ta)):
    """
    Deletes a slide deck. Only the original creator can perform this action.
    """
    db_deck = db.query(SlideDeck).filter(SlideDeck.id == deck_id).first()
    if not db_deck:
        raise HTTPException(status_code=404, detail="Slide deck not found")
    if db_deck.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete slide decks you have created.")

    db.delete(db_deck)
    db.commit()
    return


@router.get("/{deck_id}/export", summary="Export a slide deck to PPTX or PDF (Creator only)")
def export_slide_deck(
    deck_id: int,
    format: str = Query("pptx", description="Export format: 'pptx' or 'pdf'"),
    theme: str = Query("professional", description="Theme: 'professional', 'modern', 'colorful', 'dark', or 'minimalist'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    """
    Exports a slide deck to PPTX or PDF format with professional styling.
    Only the original creator can perform this action.
    
    Available themes:
    - professional: Navy blue and white, Calibri font
    - modern: Bright blue and light gray, Arial font
    - colorful: Red and peach, Georgia/Verdana fonts
    - dark: Yellow on dark gray, Segoe UI font
    - minimalist: Black and white, Arial font
    """
    # Fetch the deck
    db_deck = db.query(SlideDeck).filter(SlideDeck.id == deck_id).first()
    if not db_deck:
        raise HTTPException(status_code=404, detail="Slide deck not found")
    
    # Check authorization
    if db_deck.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only export slide decks you have created.")

    # Validate format
    if format not in ["pptx", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid export format. Use 'pptx' or 'pdf'.")
    
    # Validate theme
    valid_themes = ["professional", "modern", "colorful", "dark", "minimalist"]
    if theme not in valid_themes:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid theme. Choose from: {', '.join(valid_themes)}"
        )
    
    # Prepare slide data
    slides_data = []
    for slide in db_deck.slides:
        slides_data.append({
            'title': slide['title'],
            'content': slide['content'],
            'graph_image': slide.get('graph_image')
        })
    
    # Generate the file
    try:
        if format == "pptx":
            file_buffer = export_to_pptx(
                deck_title=db_deck.title,
                deck_description=db_deck.description,
                slides=slides_data,
                theme=theme
            )
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            filename = f"{db_deck.title.replace(' ', '_')}.pptx"
        else:  # pdf
            file_buffer = export_to_pdf(
                deck_title=db_deck.title,
                deck_description=db_deck.description,
                slides=slides_data,
                theme=theme
            )
            media_type = "application/pdf"
            filename = f"{db_deck.title.replace(' ', '_')}.pdf"
        
        # Return as streaming response
        return StreamingResponse(
            file_buffer,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate {format.upper()} file: {str(e)}"
        )

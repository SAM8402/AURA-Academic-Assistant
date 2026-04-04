from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
try:
    from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
    FASTAPI_MAIL_AVAILABLE = True
except ImportError:
    FASTAPI_MAIL_AVAILABLE = False
    FastMail = MessageSchema = ConnectionConfig = MessageType = None
import tempfile
import os
import logging

# Import database session dependency
from app.core.db import get_db
from app.api.dependencies import get_current_user
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Import schemas
from app.schemas.doubts import DoubtUploadCreate, WeeklySummaryResponse

# Import the service
from app.services.doubt_summarizer_service import doubt_summarizer_service
from app.services.doubt_export_service import doubt_export_service

# Email Configuration
def get_mail_config():
    """Get email configuration, return None if not configured"""
    if not FASTAPI_MAIL_AVAILABLE:
        return None
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return None
    
    try:
        return ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USER,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.EMAILS_FROM_EMAIL,
            MAIL_PORT=settings.SMTP_PORT,
            MAIL_SERVER=settings.SMTP_HOST,
            MAIL_FROM_NAME=settings.EMAILS_FROM_NAME,
            MAIL_STARTTLS=settings.SMTP_TLS,
            MAIL_SSL_TLS=settings.SMTP_SSL,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
    except Exception as e:
        logger.error(f"Failed to create email configuration: {e}")
        return None

# Background task for sending email
async def send_email_background(recipient_email: str, course_code: str, period: str, pdf_bytes: bytes, stats: dict):
    """
    Background task to send email asynchronously.
    This prevents blocking the API response.
    """
    if not FASTAPI_MAIL_AVAILABLE:
        logger.error("fastapi-mail not installed. Cannot send email.")
        return
    temp_path = None
    try:
        conf = get_mail_config()
        if not conf:
            logger.error("Email configuration not available")
            return
        
        # Save PDF to temporary file
        period_display = period or "all-time"
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_bytes)
            temp_path = temp_file.name
        
        subject = f"Doubt Summary Report - {course_code} ({period_display.title()})"
        
        # Email body
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2563eb;">AURA - Doubt Summary Report</h2>
                <p>Dear Instructor,</p>
                
                <p>Please find attached the doubt summary report for course <strong>{course_code}</strong>.</p>
                
                <h3 style="color: #1e40af;">Summary Statistics</h3>
                <ul>
                    <li><strong>Period:</strong> {period_display.title()}</li>
                    <li><strong>Total Messages:</strong> {stats['total_messages']}</li>
                    <li><strong>Unique Uploads:</strong> {stats['unique_uploads']}</li>
                    <li><strong>Topic Clusters:</strong> {stats['topic_clusters']}</li>
                    <li><strong>Learning Gaps:</strong> {stats['learning_gaps']}</li>
                    <li><strong>Recurring Issues:</strong> {stats['recurring_issues']}</li>
                </ul>
                
                <p>The attached PDF contains detailed analysis including:</p>
                <ul>
                    <li>Topic clusters with student confusion counts</li>
                    <li>Learning gaps identified</li>
                    <li>Actionable insights for instructors</li>
                </ul>
                
                <p style="margin-top: 20px;">
                    <em>This report was generated automatically by AURA (Academic Unified Response Assistant).</em>
                </p>
                
                <p>Best regards,<br>
                <strong>AURA Team</strong></p>
            </body>
        </html>
        """
        
        message = MessageSchema(
            subject=subject,
            recipients=[recipient_email],
            body=body,
            subtype=MessageType.html,
            attachments=[temp_path]
        )
        
        # Send email
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"Email sent successfully to {recipient_email}")
        
    except Exception as e:
        error_str = str(e)
        # Log detailed error for debugging
        if "BadCredentials" in error_str or "Username and Password not accepted" in error_str:
            logger.error(f"SMTP Authentication failed for {recipient_email}: Invalid credentials. Please check SMTP_USER and SMTP_PASSWORD in .env file.")
        elif "Connection" in error_str or "timeout" in error_str.lower():
            logger.error(f"Failed to connect to SMTP server for {recipient_email}: {error_str}")
        else:
            logger.error(f"Failed to send email to {recipient_email}: {error_str}")
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass

# Create FastAPI router
router = APIRouter(
    prefix="/doubts",
    tags=["Doubt Summarizer"]
)

# Upload Doubt Messages
@router.post("/upload", response_model=dict)
def upload_doubts(payload: DoubtUploadCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Upload student doubts for a course with metadata.
    user_id can be replaced with authentication dependency.
    """
    try:
        return doubt_summarizer_service.create_doubt_upload(db, payload, user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Get Summary + Insights
@router.get("/summary/{course_code}")
async def get_doubt_summary(
    course_code: str,
    db: Session = Depends(get_db),
    period: Optional[str] = None,
    source: str = None
):
    """
    Generate summary + insights for a course with optional filters.
    Returns enhanced response with statistics and source breakdown.
    
    Args:
        course_code: Course identifier
        period: 'daily', 'weekly', 'monthly', or omit for all time
        source: 'forum', 'email', 'chat', or omit for all sources
    """
    try:
        # Fetch messages with filters
        messages = doubt_summarizer_service.get_recent_messages_for_course(
            db, course_code, period=period, source=source
        )
        
        # Generate AI summary
        summary = await doubt_summarizer_service.generate_summary_topics_insights(messages, course_code)
        
        # Compute enhanced statistics
        stats_data = doubt_summarizer_service.compute_summary_stats(db, course_code, period, source)
        breakdown_data = doubt_summarizer_service.get_source_breakdown(db, course_code, period)
        
        # Add computed stats to response
        topics = summary.get('topics', [])
        learning_gaps = summary.get('learning_gaps', [])
        recurring_count = summary.get('recurring_issues_count', 
                                     sum(1 for gap in learning_gaps if isinstance(gap, dict) and gap.get('student_count', 0) > 1))
        
        summary['stats'] = {
            'total_messages': stats_data['total_messages'],
            'unique_uploads': stats_data['unique_uploads'],
            'topic_clusters': len(topics),
            'learning_gaps': len(learning_gaps),
            'recurring_issues': recurring_count
        }
        summary['source_breakdown'] = breakdown_data.get('breakdown', {})
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Get Topic Clusters + Confusion Counts
@router.get("/topics/{course_code}", response_model=List[dict])
async def get_topic_clusters(
    course_code: str,
    db: Session = Depends(get_db),
    period: Optional[str] = None,
    source: str = None
):
    """
    Get topic clusters with confusion counts.
    """
    try:
        messages = doubt_summarizer_service.get_recent_messages_for_course(
            db, course_code, period=period, source=source
        )
        summary = await doubt_summarizer_service.generate_summary_topics_insights(messages, course_code)
        return summary.get("topics", [])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Get Teacher Insights Only
@router.get("/insights/{course_code}", response_model=List[str])
async def get_teacher_insights(
    course_code: str,
    db: Session = Depends(get_db),
    period: Optional[str] = None,
    source: str = None
):
    """
    Get only teacher insights for a course.
    """
    try:
        messages = doubt_summarizer_service.get_recent_messages_for_course(
            db, course_code, period=period, source=source
        )
        summary = await doubt_summarizer_service.generate_summary_topics_insights(messages, course_code)
        return summary.get("insights", [])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Get Source Breakdown
@router.get("/source-breakdown/{course_code}", response_model=dict)
def get_source_breakdown(
    course_code: str,
    db: Session = Depends(get_db),
    period: Optional[str] = None
):
    """
    Get breakdown of doubts by source (forum, email, chat) with counts and percentages.
    
    Args:
        course_code: Course identifier
        period: 'daily', 'weekly', 'monthly', or omit for all time
    """
    try:
        return doubt_summarizer_service.get_source_breakdown(db, course_code, period=period)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# Export Endpoints
# ============================================================================

class EmailReportRequest(BaseModel):
    course_code: str
    period: str = "weekly"
    source: str = None
    recipient_email: EmailStr

# Export as PDF
@router.get("/export/pdf")
async def export_summary_pdf(
    course_code: str,
    db: Session = Depends(get_db),
    period: Optional[str] = None,
    source: str = None
):
    """
    Export doubt summary as PDF.
    """
    try:
        # Fetch summary data
        messages = doubt_summarizer_service.get_recent_messages_for_course(
            db, course_code, period=period, source=source
        )
        summary = await doubt_summarizer_service.generate_summary_topics_insights(messages, course_code)
        
        # Add stats
        stats_data = doubt_summarizer_service.compute_summary_stats(db, course_code, period, source)
        breakdown_data = doubt_summarizer_service.get_source_breakdown(db, course_code, period)
        
        topics = summary.get('topics', [])
        learning_gaps = summary.get('learning_gaps', [])
        recurring_count = summary.get('recurring_issues_count', 0)
        
        summary['stats'] = {
            'total_messages': stats_data['total_messages'],
            'unique_uploads': stats_data['unique_uploads'],
            'topic_clusters': len(topics),
            'learning_gaps': len(learning_gaps),
            'recurring_issues': recurring_count
        }
        
        # Generate PDF
        pdf_buffer = doubt_export_service.generate_pdf(summary, course_code, period or "all-time")
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=doubt-summary-{course_code}-{period or 'all'}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Export as CSV
@router.get("/export/csv")
async def export_summary_csv(
    course_code: str,
    db: Session = Depends(get_db),
    period: Optional[str] = None,
    source: str = None
):
    """
    Export doubt summary as CSV.
    """
    try:
        # Fetch summary data
        messages = doubt_summarizer_service.get_recent_messages_for_course(
            db, course_code, period=period, source=source
        )
        summary = await doubt_summarizer_service.generate_summary_topics_insights(messages, course_code)
        
        # Add stats
        stats_data = doubt_summarizer_service.compute_summary_stats(db, course_code, period, source)
        breakdown_data = doubt_summarizer_service.get_source_breakdown(db, course_code, period)
        
        topics = summary.get('topics', [])
        learning_gaps = summary.get('learning_gaps', [])
        recurring_count = summary.get('recurring_issues_count', 0)
        
        summary['stats'] = {
            'total_messages': stats_data['total_messages'],
            'unique_uploads': stats_data['unique_uploads'],
            'topic_clusters': len(topics),
            'learning_gaps': len(learning_gaps),
            'recurring_issues': recurring_count
        }
        
        # Generate CSV
        csv_buffer = doubt_export_service.generate_csv(summary, course_code, period or "all-time")
        
        return StreamingResponse(
            csv_buffer,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=doubt-summary-{course_code}-{period or 'all'}.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Email Report
@router.post("/export/email")
async def email_summary_report(
    request: EmailReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Queue email report to be sent in the background.
    Returns immediately while email is sent asynchronously.
    Requires SMTP configuration in environment variables.
    """
    try:
        # Check if SMTP is configured
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            raise HTTPException(
                status_code=503,
                detail="Email service is not configured. Please contact your administrator to set up SMTP credentials."
            )
        
        # Validate email configuration before queuing
        test_conf = get_mail_config()
        if not test_conf:
            raise HTTPException(
                status_code=503,
                detail="Email service configuration is invalid. Please contact your administrator."
            )
        
        # Fetch summary data
        messages = doubt_summarizer_service.get_recent_messages_for_course(
            db, request.course_code, period=request.period, source=request.source
        )
        summary = await doubt_summarizer_service.generate_summary_topics_insights(messages, request.course_code)
        
        # Add stats
        stats_data = doubt_summarizer_service.compute_summary_stats(db, request.course_code, request.period, request.source)
        
        topics = summary.get('topics', [])
        learning_gaps = summary.get('learning_gaps', [])
        recurring_count = summary.get('recurring_issues_count', 0)
        
        summary['stats'] = {
            'total_messages': stats_data['total_messages'],
            'unique_uploads': stats_data['unique_uploads'],
            'topic_clusters': len(topics),
            'learning_gaps': len(learning_gaps),
            'recurring_issues': recurring_count
        }
        
        # Generate PDF for background task
        pdf_buffer = doubt_export_service.generate_pdf(summary, request.course_code, request.period)
        pdf_bytes = pdf_buffer.getvalue()
        
        # Queue email to be sent in background
        background_tasks.add_task(
            send_email_background,
            request.recipient_email,
            request.course_code,
            request.period,
            pdf_bytes,
            summary['stats']
        )
        
        return {
            "message": f"Email report is being sent to {request.recipient_email}. You will receive it shortly.",
            "status": "queued",
            "recipient": request.recipient_email,
            "course_code": request.course_code,
            "period": request.period,
            "stats": summary['stats']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue email: {str(e)}")
        # Provide user-friendly error messages
        error_msg = str(e)
        if "BadCredentials" in error_msg or "Username and Password not accepted" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Email credentials are invalid. Please contact your administrator to update SMTP settings."
            )
        elif "Connection" in error_msg or "timeout" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Unable to connect to email server. Please check your network connection or contact support."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to process email request. Please try again or contact support if the issue persists."
            )

"""
AURA - Academic Unified Response Assistant API

Main FastAPI application entry point.

This module initializes the FastAPI application with:
- CORS middleware for frontend integration
- Database initialization on startup
- API route registration
- Comprehensive API documentation
"""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from app.api.doubt_summarizer_router import router as doubt_router

logger = logging.getLogger(__name__)

# Try to import LangChain (optional dependency)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatGoogleGenerativeAI = None

from config.settings import settings
from config.db import init_db
from app.api.auth import auth_router
from app.api.chatbot import chatbot_router
from app.api.knowledge import router as knowledge_router
from app.api.dashboard import router as dashboard_router
from app.api.tasks import router as tasks_router
from app.api.seed import router as seed_router
from app.api.seed_enhanced import router as seed_enhanced_router
from app.api.queries import router as queries_router
from app.api.course_router import router as course_router
from app.api.tag_router import router as tag_router
from app.api.quiz_router import router as quiz_router
from app.api.slide_deck_router import router as slide_deck_router
from app.api.analytics import router as analytics_router
from app.api.instructor_analytics import router as instructor_analytics_router
from app.api import video_router
from app.api.student_resource_router import router as student_resource_router

# ============================================================================
# Application Lifecycle Management
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize database tables
    - Shutdown: Cleanup resources (if needed)
    """
    # Startup: Initialize database
    logger.info("Starting AURA API...")
    logger.info("Database: %s", settings.DATABASE_URL)
    init_db()
    logger.info("Database initialized")

    # Auto-ingest any files in uploads/knowledge/ that haven't been processed yet
    try:
        from app.services.rag.ingest_pipeline import auto_ingest_uploads
        ingest_result = await auto_ingest_uploads()
        logger.info("Auto-ingest result: %s", ingest_result)
    except Exception as e:
        logger.warning("Auto-ingest skipped (non-fatal): %s", e)

    yield

    # Shutdown: Cleanup (if needed)
    logger.info("Shutting down AURA API...")


# ============================================================================
# FastAPI Application Instance
# ============================================================================


# Create description dynamically
environment_name = "Development" if settings.DEBUG else "Production"
api_description = f"""
## AURA - Academic Unified Response Assistant

A comprehensive educational platform API supporting:
- **Multi-role authentication** (Students, TAs, Instructors, Admins)
- **Query/Doubt management** system
- **Resource sharing** and management
- **Announcements** and notifications
- **User profiles** with statistics
- **Role-based access control** (RBAC)

### Authentication

Most endpoints require authentication using JWT Bearer tokens.

**How to authenticate:**
1. Register: `POST /api/auth/signup`
2. Login: `POST /api/auth/login`
3. Use the `access_token` in Authorization header: `Bearer <token>`

### User Roles

- **student**: Regular students - can post queries, view resources
- **ta**: Teaching assistants - can respond to queries, manage resources
- **instructor**: Course instructors - full course management
- **admin**: System administrators - full system access

### Features

#### Authentication & Authorization
- JWT-based authentication with refresh tokens
- Role-based access control
- Secure password hashing with Argon2

#### Query Management
- Students can post doubts/questions
- TAs/Instructors can respond and resolve queries
- Priority levels and status tracking
- Query analytics and statistics

#### Resource Management
- Upload and share educational materials
- Multiple resource types (videos, PDFs, links, etc.)
- Access control (public, course-specific, private)
- Download and view tracking

#### Announcements
- Institution-wide and course-specific announcements
- Target specific user roles
- Urgent/deadline notifications
- Pin important announcements

#### User Profiles
- Extended user information
- Academic details and interests
- Activity statistics
- Reputation scoring

### Rate Limiting

API rate limit: 60 requests per minute per user (configurable)

### Support

For issues or questions, please contact the development team.

---
**Version:** {settings.APP_VERSION}
**Environment:** {environment_name}
"""

load_dotenv()


app = FastAPI(
    title=settings.APP_NAME,
    description=api_description,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json",
    contact={
        "name": "AURA Development Team",
        "email": "support@aura.edu",
    },
    license_info={
        "name": "MIT License",
    },
)


# ============================================================================
# CORS Middleware Configuration
# ============================================================================


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# ============================================================================
# API Router Registration
# ============================================================================


# Authentication routes
app.include_router(
    auth_router,
    prefix=settings.API_PREFIX,
    tags=["Authentication"]
)

# Doubt Summarizer routes
app.include_router(
    doubt_router,
    prefix=f"{settings.API_PREFIX}/ta",
    tags=["Doubt Summarizer"]
)


# Chatbot routes
app.include_router(
    chatbot_router,
    prefix=f"{settings.API_PREFIX}/chatbot",
    tags=["Chatbot"]
)

# Knowledge Base routes
app.include_router(
    knowledge_router,
    prefix=settings.API_PREFIX
)

# Dashboard & Analytics routes
app.include_router(
    dashboard_router,
    prefix=settings.API_PREFIX
)

# Background Tasks routes
app.include_router(
    tasks_router,
    prefix=settings.API_PREFIX
)

# Seed Data routes (development/testing only - disabled in production)
if settings.DEBUG:
    app.include_router(
        seed_router,
        prefix=settings.API_PREFIX
    )
    app.include_router(
        seed_enhanced_router,
        prefix=settings.API_PREFIX
    )

# Queries routes
app.include_router(
    queries_router,
    prefix=settings.API_PREFIX
)

# Analytics routes (Admin dashboard)
app.include_router(
    analytics_router,
    prefix=settings.API_PREFIX
)

# Instructor Analytics routes (Discussion summaries, sentiment)
app.include_router(
    instructor_analytics_router,
    prefix=settings.API_PREFIX
)

# Course routes
app.include_router(
    course_router,
    prefix=f"{settings.API_PREFIX}/courses",
    tags=["Courses"]
)

# Tag routes
app.include_router(
    tag_router,
    prefix=f"{settings.API_PREFIX}/tags",
    tags=["Tags"]
)

# Quiz routes
app.include_router(
    quiz_router,
    prefix=f"{settings.API_PREFIX}/quizzes",
    tags=["Quizzes"]
)

# Slide Deck routes
app.include_router(
    slide_deck_router,
    prefix=f"{settings.API_PREFIX}/slide-decks",
    tags=["Slide Decks"]
)
# Video Summary routes
app.include_router(
    video_router.router,
    prefix=f"{settings.API_PREFIX}/video",
    tags=["Video"]
)

# Student Resource routes
app.include_router(
    student_resource_router,
    prefix=settings.API_PREFIX,
    tags=["Student Resources"]
)

# TODO: Add more routers as they are implemented
# from app.api.resources import resources_router
# from app.api.announcements import announcements_router
# from app.api.profiles import profiles_router
#
# app.include_router(resources_router, prefix=settings.API_PREFIX, tags=["Resources"])
# app.include_router(announcements_router, prefix=settings.API_PREFIX, tags=["Announcements"])
# app.include_router(profiles_router, prefix=settings.API_PREFIX, tags=["Profiles"])


# ============================================================================
# Root and Health Check Endpoints
# ============================================================================


@app.get(
    "/",
    include_in_schema=False,
    summary="Root endpoint"
)
async def root():
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check endpoint",
    description="Check if the API is running and database is accessible."
)
async def health_check():
    """
    Health check endpoint.

    Returns API status and basic system information.
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get(
    "/api",
    tags=["Info"],
    summary="API information",
    description="Get API version and available endpoints."
)
async def api_info():
    """
    API information endpoint.

    Returns API metadata and available route groups.
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Academic Unified Response Assistant API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "endpoints": {
            "authentication": f"{settings.API_PREFIX}/auth",
            "health": "/health",
            "documentation": "/docs"
        }
    }


# ============================================================================
# Application Entry Point (for development)
# ============================================================================


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(
        "Starting AURA v%s (%s)",
        settings.APP_VERSION,
        "development" if settings.DEBUG else "production",
    )
    logger.info("API docs: http://localhost:8000/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
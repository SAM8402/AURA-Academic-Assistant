"""
Authentication API endpoints.

This module provides endpoints for:
- User registration
- User login with JWT token generation
- Token refresh
- Password management
- User profile retrieval
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError

from config.db import get_db
from config.security import create_tokens, decode_token
from app.models.user import User
from app.models.profile import Profile
from app.models.course import Course
from app.models.user_course import UserCourse
from app.schemas.user_schema import (
    UserRole,
    UserCreate,
    UserResponse,
    UserLogin,
    UserUpdate,
    TokenResponse,
    RefreshTokenRequest,
)
from app.api.dependencies import get_current_user, get_current_active_user


# Initialize router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Registration and Login Endpoints
# ============================================================================


@auth_router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Register a new user account with email and password.

    **Authentication:** Not required (public endpoint)

    **Process:**
    1. Validates email format and password strength
    2. Checks if email is already registered
    3. Creates user account with hashed password
    4. Creates empty user profile
    5. Generates JWT access and refresh tokens
    6. Returns tokens and user information

    **Password Requirements:**
    - Minimum 8 characters
    - Recommended: Mix of uppercase, lowercase, numbers, special characters

    **Roles:**
    - student (default)
    - ta (teaching assistant)
    - instructor
    - admin (requires manual approval or separate admin creation endpoint)
    """,
    responses={
        201: {
            "description": "User created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 3600,
                        "user": {
                            "id": 1,
                            "email": "student@example.com",
                            "role": "student",
                            "full_name": "John Doe",
                            "is_active": True,
                            "created_at": "2025-01-15T10:30:00Z"
                        }
                    }
                }
            }
        },
        400: {"description": "Email already registered or invalid input"},
    }
)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Creates a new user with hashed password, assigns role, and returns JWT tokens.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please use a different email or login."
        )

    # Validate password strength
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    # Validate course IDs for TA and Instructor roles
    if user_data.role in [UserRole.TA, UserRole.INSTRUCTOR]:
        if not user_data.course_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Course IDs are required for {user_data.role} role"
            )
        
        # Verify all course IDs exist
        courses = db.query(Course).filter(Course.id.in_(user_data.course_ids)).all()
        if len(courses) != len(user_data.course_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more course IDs are invalid"
            )

    # Create user with role and full name
    user = User(
        email=user_data.email,
        role=user_data.role,
        full_name=user_data.full_name
    )
    user.set_password(user_data.password)

    # Add user to database
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign courses to TA/Instructor
    if user_data.role in [UserRole.TA, UserRole.INSTRUCTOR] and user_data.course_ids:
        for course_id in user_data.course_ids:
            user_course = UserCourse(user_id=user.id, course_id=course_id)
            db.add(user_course)
        db.commit()

    # Create user profile
    profile = Profile(
        user_id=user.id,
        full_name=user_data.full_name or user.email.split('@')[0]
    )
    db.add(profile)
    db.commit()

    # Generate JWT tokens
    tokens = create_tokens(user.id, user.email, user.role)

    # Return tokens with user data
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user=UserResponse.model_validate(user)
    )


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain tokens",
    description="""
    Authenticate user and obtain JWT access and refresh tokens.

    **Authentication:** Not required (public endpoint)

    **Process:**
    1. Validates email and password
    2. Checks if account is active
    3. Generates JWT access token (expires in 60 minutes)
    4. Generates JWT refresh token (expires in 7 days)
    5. Returns tokens and user information

    **Token Usage:**
    - Access Token: Use for API authentication (include in Authorization header)
    - Refresh Token: Use to obtain new access tokens without re-login

    **Example Request:**
    ```bash
    curl -X POST http://localhost:8000/api/auth/login \\
      -H "Content-Type: application/json" \\
      -d '{"email": "student@example.com", "password": "SecurePass123"}'
    ```

    **Example Authorization Header:**
    ```
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```
    """,
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"description": "Invalid email or password"},
        403: {"description": "Account is inactive"},
    }
)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT tokens.

    Validates credentials and returns access/refresh tokens for API authentication.
    """
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()

    # Verify user exists and password is correct
    if not user or not user.verify_password(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )

    # Generate JWT tokens
    tokens = create_tokens(user.id, user.email, user.role)

    # Return tokens with user data
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user=UserResponse.model_validate(user)
    )


# ============================================================================
# Token Management Endpoints
# ============================================================================


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="""
    Obtain a new access token using a refresh token.

    **Authentication:** Requires valid refresh token

    **Process:**
    1. Validates refresh token
    2. Checks if user still exists and is active
    3. Generates new access token
    4. Generates new refresh token (token rotation)
    5. Returns new tokens

    **Token Rotation:**
    For security, a new refresh token is issued with each refresh request.
    The old refresh token should be discarded.

    **Example Request:**
    ```bash
    curl -X POST http://localhost:8000/api/auth/refresh \\
      -H "Content-Type: application/json" \\
      -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
    ```
    """,
    responses={
        200: {"description": "New tokens generated successfully"},
        401: {"description": "Invalid or expired refresh token"},
        403: {"description": "User account inactive"},
    }
)
def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.

    Issues new access and refresh tokens for continued API access.
    """
    try:
        # Decode and validate refresh token
        token_data = decode_token(refresh_data.refresh_token, token_type="refresh")

        # Find user
        user = db.query(User).filter(User.id == token_data.user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )

        # Generate new tokens
        tokens = create_tokens(user.id, user.email, user.role)

        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"],
            user=UserResponse.model_validate(user)
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}"
        )


# ============================================================================
# User Profile Endpoints
# ============================================================================


@auth_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="""
    Retrieve the currently authenticated user's profile information.

    **Authentication:** Required (Bearer token)

    **Returns:**
    - User ID
    - Email address
    - Role
    - Full name
    - Account status
    - Creation date

    **Example Request:**
    ```bash
    curl -X GET http://localhost:8000/api/auth/me \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    ```
    """,
    responses={
        200: {"description": "User profile retrieved successfully"},
        401: {"description": "Not authenticated or invalid token"},
    }
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user's profile.

    Returns user information for the currently authenticated user.
    """
    return UserResponse.model_validate(current_user)


@auth_router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="""
    Update the currently authenticated user's profile information.

    **Authentication:** Required (Bearer token)

    **Updatable Fields:**
    - Full name
    - Email address (must be unique)
    - Password (requires current password for verification)

    **Password Change:**
    To change password, provide both `current_password` and `new_password`.

    **Example Request:**
    ```bash
    curl -X PUT http://localhost:8000/api/auth/me \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
      -H "Content-Type: application/json" \\
      -d '{"full_name": "Jane Doe", "email": "newemail@example.com"}'
    ```
    """,
    responses={
        200: {"description": "Profile updated successfully"},
        400: {"description": "Invalid input or email already exists"},
        401: {"description": "Not authenticated or incorrect current password"},
    }
)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information.

    Allows users to update their profile details including password change.
    """
    # Update full name if provided
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
        # Also update profile
        if current_user.profile:
            current_user.profile.full_name = user_update.full_name

    # Update email if provided
    if user_update.email is not None and user_update.email != current_user.email:
        # Check if new email already exists
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = user_update.email

    # Update password if provided
    if user_update.new_password is not None:
        # Verify current password
        if not user_update.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to change password"
            )

        if not current_user.verify_password(user_update.current_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect current password"
            )

        # Set new password
        current_user.set_password(user_update.new_password)

    # Commit changes
    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)

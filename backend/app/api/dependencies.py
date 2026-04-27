"""
API dependencies for authentication and authorization.

This module provides FastAPI dependency functions for:
- Extracting and validating JWT tokens
- Identifying current users
- Role-based access control
- Database session management
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from config.db import get_db
from config.security import decode_token
from app.models.user import User
from app.schemas.user_schema import UserRole, TokenData


# Security scheme for Bearer token authentication
security = HTTPBearer()


# ============================================================================
# Authentication Dependencies
# ============================================================================


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> TokenData:
    """
    Extract and validate JWT token from Authorization header.

    This dependency extracts the Bearer token from the Authorization header,
    validates it, and returns the decoded token data.

    Args:
        credentials: HTTP Authorization credentials containing the token
        db: Database session (for future token blacklist checking)

    Returns:
        TokenData: Decoded token data containing user information

    Raises:
        HTTPException: 401 if token is invalid or expired

    Usage:
        @app.get("/protected")
        async def protected_route(token: TokenData = Depends(get_current_user_token)):
            return {"user_id": token.user_id}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        token_data = decode_token(token, token_type="access")
        return token_data
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token_data: TokenData = Depends(get_current_user_token),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the database.

    This dependency validates the token and retrieves the full user object
    from the database.

    Args:
        token_data: Decoded token data
        db: Database session

    Returns:
        User: Current authenticated user object

    Raises:
        HTTPException: 401 if user not found or inactive

    Usage:
        @app.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return {"email": current_user.email}
    """
    user = db.query(User).filter(User.id == token_data.user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure the current user is active.

    This is an alias for get_current_user for semantic clarity.

    Args:
        current_user: Current user from token

    Returns:
        User: Active user object

    Usage:
        @app.get("/dashboard")
        async def dashboard(user: User = Depends(get_current_active_user)):
            return {"message": f"Welcome {user.email}"}
    """
    return current_user


# ============================================================================
# Optional Authentication (for public endpoints with optional auth)
# ============================================================================


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if token is provided, otherwise return None.

    Useful for endpoints that work differently for authenticated vs
    unauthenticated users.

    Args:
        credentials: Optional HTTP Authorization credentials
        db: Database session

    Returns:
        Optional[User]: User object if authenticated, None otherwise

    Usage:
        @app.get("/resources")
        async def get_resources(user: Optional[User] = Depends(get_current_user_optional)):
            if user:
                # Show private resources
                pass
            else:
                # Show only public resources
                pass
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        token_data = decode_token(token, token_type="access")
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user and user.is_active:
            return user
    except JWTError:
        return None

    return None


# ============================================================================
# Role-Based Access Control Dependencies
# ============================================================================


class RoleChecker:
    """
    Dependency class for role-based access control.

    This class creates dependencies that check if the current user
    has one of the required roles.

    Usage:
        admin_only = RoleChecker([UserRole.ADMIN])
        instructor_or_admin = RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN])

        @app.get("/admin/users")
        async def get_users(current_user: User = Depends(admin_only)):
            return {"users": [...]}
    """

    def __init__(self, allowed_roles: list[UserRole]):
        """
        Initialize role checker with allowed roles.

        Args:
            allowed_roles: List of roles that are allowed access
        """
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """
        Check if current user has required role.

        Args:
            current_user: Current authenticated user

        Returns:
            User: Current user if authorized

        Raises:
            HTTPException: 403 if user doesn't have required role
        """
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in self.allowed_roles]}",
            )
        return current_user


# ============================================================================
# Pre-configured Role Dependencies
# ============================================================================


# Admin only
require_admin = RoleChecker([UserRole.ADMIN])

# Instructor or Admin
require_instructor = RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN])

# TA, Instructor, or Admin
require_ta = RoleChecker([UserRole.TA, UserRole.INSTRUCTOR, UserRole.ADMIN])

# All authenticated users
require_authenticated = get_current_active_user


def require_role(allowed_roles: list[UserRole]):
    """
    Create a role-based access control dependency.

    This function creates a dependency that checks if the current user
    has one of the required roles.

    Args:
        allowed_roles: List of roles that are allowed access

    Returns:
        Callable: Dependency function that checks user role

    Usage:
        @app.get("/admin/analytics")
        async def get_analytics(current_user: User = Depends(require_role([UserRole.ADMIN]))):
            return {"data": [...]}
    """
    return RoleChecker(allowed_roles)


# ============================================================================
# Custom Permission Dependencies
# ============================================================================


async def can_modify_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Check if user can modify a specific query.

    Students can only modify their own queries.
    TAs and instructors can modify queries assigned to them.
    Admins can modify any query.

    Args:
        query_id: ID of the query to modify
        current_user: Current authenticated user
        db: Database session

    Returns:
        User: Current user if authorized

    Raises:
        HTTPException: 403 if user cannot modify the query
    """
    from app.models.query import Query

    query = db.query(Query).filter(Query.id == query_id).first()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )

    # Admin can modify any query
    if current_user.role == UserRole.ADMIN:
        return current_user

    # Student can only modify their own queries
    if current_user.role == UserRole.STUDENT:
        if query.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only modify your own queries"
            )
        return current_user

    # TA/Instructor can modify queries assigned to them
    if current_user.role in [UserRole.TA, UserRole.INSTRUCTOR]:
        if query.assigned_to_id != current_user.id and query.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only modify queries assigned to you"
            )
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )


async def can_modify_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Check if user can modify a specific resource.

    Users can only modify resources they created.
    Admins can modify any resource.

    Args:
        resource_id: ID of the resource to modify
        current_user: Current authenticated user
        db: Database session

    Returns:
        User: Current user if authorized

    Raises:
        HTTPException: 403 if user cannot modify the resource
    """
    from app.models.resource import Resource

    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Admin can modify any resource
    if current_user.role == UserRole.ADMIN:
        return current_user

    # Creator can modify their own resource
    if resource.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify resources you created"
        )

    return current_user


# ============================================================================
# Pagination Dependency
# ============================================================================


async def get_pagination_params(
    page: int = 1,
    page_size: int = 10
) -> dict:
    """
    Get pagination parameters with validation.

    Args:
        page: Page number (starts from 1)
        page_size: Number of items per page (max 100)

    Returns:
        dict: Dictionary with validated pagination parameters

    Raises:
        HTTPException: 400 if parameters are invalid

    Usage:
        @app.get("/items")
        async def get_items(pagination: dict = Depends(get_pagination_params)):
            skip = (pagination["page"] - 1) * pagination["page_size"]
            limit = pagination["page_size"]
            items = db.query(Item).offset(skip).limit(limit).all()
            return items
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be >= 1"
        )

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be between 1 and 100"
        )

    skip = (page - 1) * page_size
    return {
        "page": page,
        "page_size": page_size,
        "skip": skip,
        "limit": page_size
    }

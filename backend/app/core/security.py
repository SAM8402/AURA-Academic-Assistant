"""
Security utilities for authentication and authorization.

This module provides JWT token generation, validation, and password hashing utilities.
"""

from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.user_schema import TokenData, UserRole

# Password hashing context using Argon2
# Argon2 is recommended over bcrypt for modern applications
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ============================================================================
# Password Hashing Functions
# ============================================================================


def hash_password(password: str) -> str:
    """
    Hash a plain text password using Argon2.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password

    Example:
        >>> hashed = hash_password("SecurePass123")
        >>> print(hashed)
        '$argon2id$v=19$m=65536,t=3,p=4$...'
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        bool: True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("SecurePass123")
        >>> verify_password("SecurePass123", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT Token Functions
# ============================================================================


def create_access_token(
    user_id: int,
    email: str,
    role: UserRole,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's unique identifier
        email: User's email address
        role: User's role (student, ta, instructor, admin)
        expires_delta: Optional custom expiration time

    Returns:
        str: Encoded JWT token

    Example:
        >>> from datetime import timedelta
        >>> token = create_access_token(
        ...     user_id=1,
        ...     email="user@example.com",
        ...     role=UserRole.STUDENT
        ... )
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(UTC) + expires_delta

    to_encode: Dict[str, Any] = {
        "sub": str(user_id),  # Subject (user ID)
        "email": email,
        "role": role.value if isinstance(role, UserRole) else role,
        "exp": expire,  # Expiration time
        "iat": datetime.now(UTC),  # Issued at
        "type": "access"  # Token type
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(
    user_id: int,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Refresh tokens are used to obtain new access tokens without re-authentication.
    They have a longer expiration time and contain minimal information.

    Args:
        user_id: User's unique identifier
        email: User's email address
        expires_delta: Optional custom expiration time

    Returns:
        str: Encoded JWT refresh token

    Example:
        >>> token = create_refresh_token(
        ...     user_id=1,
        ...     email="user@example.com"
        ... )
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    expire = datetime.now(UTC) + expires_delta

    to_encode: Dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh"  # Token type
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str, token_type: str = "access") -> TokenData:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        TokenData: Decoded token data

    Raises:
        JWTError: If token is invalid or expired

    Example:
        >>> token = create_access_token(1, "user@example.com", UserRole.STUDENT)
        >>> data = decode_token(token)
        >>> print(data.user_id)
        1
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != token_type:
            raise JWTError(f"Invalid token type. Expected {token_type}")

        sub = payload.get("sub")
        email: str = payload.get("email")
        role_str: str = payload.get("role")
        exp_timestamp = payload.get("exp")

        if sub is None or email is None:
            raise JWTError("Invalid token payload")

        user_id: int = int(sub)

        # Convert role string to UserRole enum (only for access tokens)
        if token_type == "access" and role_str:
            try:
                role = UserRole(role_str)
            except ValueError:
                raise JWTError(f"Invalid role: {role_str}")
        else:
            role = None

        # Convert expiration timestamp to datetime
        exp = datetime.fromtimestamp(exp_timestamp) if exp_timestamp is not None else None

        return TokenData(
            user_id=user_id,
            email=email,
            role=role if role is not None else UserRole.STUDENT,
            exp=exp
        )

    except JWTError as e:
        raise JWTError(f"Could not validate token: {str(e)}")


def verify_token(token: str, token_type: str = "access") -> bool:
    """
    Verify if a JWT token is valid.

    Args:
        token: JWT token string
        token_type: Expected token type

    Returns:
        bool: True if token is valid, False otherwise

    Example:
        >>> token = create_access_token(1, "user@example.com", UserRole.STUDENT)
        >>> verify_token(token)
        True
        >>> verify_token("invalid_token")
        False
    """
    try:
        decode_token(token, token_type)
        return True
    except JWTError:
        return False


# ============================================================================
# Role-Based Access Control Helpers
# ============================================================================


def has_permission(user_role: UserRole, required_roles: list[UserRole]) -> bool:
    """
    Check if a user's role has permission to access a resource.

    Args:
        user_role: User's current role
        required_roles: List of roles that have access

    Returns:
        bool: True if user has permission, False otherwise

    Example:
        >>> has_permission(UserRole.ADMIN, [UserRole.ADMIN, UserRole.INSTRUCTOR])
        True
        >>> has_permission(UserRole.STUDENT, [UserRole.ADMIN])
        False
    """
    return user_role in required_roles


def is_admin(user_role: UserRole) -> bool:
    """
    Check if user is an administrator.

    Args:
        user_role: User's role

    Returns:
        bool: True if user is admin

    Example:
        >>> is_admin(UserRole.ADMIN)
        True
        >>> is_admin(UserRole.STUDENT)
        False
    """
    return user_role == UserRole.ADMIN


def is_instructor_or_above(user_role: UserRole) -> bool:
    """
    Check if user is instructor or administrator.

    Args:
        user_role: User's role

    Returns:
        bool: True if user is instructor or admin

    Example:
        >>> is_instructor_or_above(UserRole.INSTRUCTOR)
        True
        >>> is_instructor_or_above(UserRole.STUDENT)
        False
    """
    return user_role in [UserRole.INSTRUCTOR, UserRole.ADMIN]


def is_ta_or_above(user_role: UserRole) -> bool:
    """
    Check if user is TA, instructor, or administrator.

    Args:
        user_role: User's role

    Returns:
        bool: True if user is TA or above

    Example:
        >>> is_ta_or_above(UserRole.TA)
        True
        >>> is_ta_or_above(UserRole.STUDENT)
        False
    """
    return user_role in [UserRole.TA, UserRole.INSTRUCTOR, UserRole.ADMIN]


# ============================================================================
# Token Generation Helper
# ============================================================================


def create_tokens(user_id: int, email: str, role: UserRole) -> Dict[str, Any]:
    """
    Create both access and refresh tokens for a user.

    This is a convenience function for login/registration endpoints.

    Args:
        user_id: User's unique identifier
        email: User's email address
        role: User's role

    Returns:
        dict: Dictionary containing access_token, refresh_token, and metadata

    Example:
        >>> tokens = create_tokens(1, "user@example.com", UserRole.STUDENT)
        >>> print(tokens.keys())
        dict_keys(['access_token', 'refresh_token', 'token_type', 'expires_in'])
    """
    access_token = create_access_token(user_id, email, role)
    refresh_token = create_refresh_token(user_id, email)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
    }

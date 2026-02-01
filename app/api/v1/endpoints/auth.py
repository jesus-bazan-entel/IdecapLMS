"""
Authentication endpoints
JWT + Google OAuth
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import timedelta

from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    get_current_user,
)
from app.core.firebase_admin import get_firestore, get_document, create_document, update_document
from app.config import settings

router = APIRouter()


# Request/Response schemas
class LoginRequest(BaseModel):
    """Email/password login request"""
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Google OAuth login request"""
    id_token: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    """User information response"""
    id: str
    email: str
    name: str
    image_url: Optional[str] = None
    role: List[str] = []


class RegisterRequest(BaseModel):
    """New user registration request"""
    email: EmailStr
    password: str
    name: str


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    email: EmailStr
    new_password: str
    secret_key: str  # Simple protection


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login with email and password
    Returns JWT access token
    """
    db = get_firestore()

    # Find user by email
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", request.email).limit(1)
    docs = list(query.stream())

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user_doc = docs[0]
    user_data = user_doc.to_dict()
    user_id = user_doc.id

    # Verify password
    stored_password = user_data.get("password_hash") or user_data.get("passwordHash")
    if not stored_password or not verify_password(request.password, stored_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user is disabled
    if user_data.get("isDisbaled") or user_data.get("is_disabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Get user role
    role = user_data.get("role", [])
    if isinstance(role, str):
        role = [role]

    # Create JWT token
    token_data = {
        "sub": user_id,
        "email": user_data.get("email"),
        "role": role,
    }
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user={
            "id": user_id,
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "imageUrl": user_data.get("imageUrl") or user_data.get("image_url"),
            "role": role,
        }
    )


@router.post("/google", response_model=TokenResponse)
async def google_auth(request: GoogleAuthRequest):
    """
    Login/Register with Google OAuth
    Verifies Google ID token and creates/returns user
    """
    from firebase_admin import auth as firebase_auth

    try:
        # Verify Google ID token with Firebase
        decoded_token = firebase_auth.verify_id_token(request.id_token)
        uid = decoded_token["uid"]
        email = decoded_token.get("email")
        name = decoded_token.get("name", "")
        picture = decoded_token.get("picture")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )

    db = get_firestore()

    # Check if user exists
    user_doc = db.collection("users").document(uid).get()

    if user_doc.exists:
        user_data = user_doc.to_dict()

        # Check if disabled
        if user_data.get("isDisbaled") or user_data.get("is_disabled"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )

        role = user_data.get("role", ["student"])
        if isinstance(role, str):
            role = [role]
    else:
        # Create new user
        from datetime import datetime

        user_data = {
            "email": email,
            "name": name,
            "imageUrl": picture,
            "role": ["student"],
            "createdAt": datetime.utcnow(),
            "platform": "web",
            "isDisbaled": False,
        }
        db.collection("users").document(uid).set(user_data)
        role = ["student"]

    # Create JWT token
    token_data = {
        "sub": uid,
        "email": email,
        "role": role,
    }
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user={
            "id": uid,
            "email": email,
            "name": user_data.get("name", name),
            "imageUrl": user_data.get("imageUrl") or picture,
            "role": role,
        }
    )


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """
    Register a new user with email and password
    """
    db = get_firestore()

    # Check if email already exists
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", request.email).limit(1)
    docs = list(query.stream())

    if docs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Create user document
    from datetime import datetime
    import uuid

    user_id = str(uuid.uuid4())
    password_hash = get_password_hash(request.password)

    user_data = {
        "email": request.email,
        "name": request.name,
        "passwordHash": password_hash,
        "role": ["student"],
        "createdAt": datetime.utcnow(),
        "platform": "web",
        "isDisbaled": False,
    }

    db.collection("users").document(user_id).set(user_data)

    # Create JWT token
    token_data = {
        "sub": user_id,
        "email": request.email,
        "role": ["student"],
    }
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user={
            "id": user_id,
            "email": request.email,
            "name": request.name,
            "imageUrl": None,
            "role": ["student"],
        }
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    user_id = current_user["id"]
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    role = user_data.get("role", [])
    if isinstance(role, str):
        role = [role]

    return UserResponse(
        id=user_id,
        email=user_data.get("email"),
        name=user_data.get("name"),
        image_url=user_data.get("imageUrl") or user_data.get("image_url"),
        role=role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Refresh JWT access token
    """
    user_id = current_user["id"]
    user_data = await get_document("users", user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    role = user_data.get("role", [])
    if isinstance(role, str):
        role = [role]

    # Create new JWT token
    token_data = {
        "sub": user_id,
        "email": user_data.get("email"),
        "role": role,
    }
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user={
            "id": user_id,
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "imageUrl": user_data.get("imageUrl") or user_data.get("image_url"),
            "role": role,
        }
    )


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset user password (temporary endpoint)
    Requires secret key for protection
    """
    # Simple protection - remove this endpoint after use
    if request.secret_key != "apolo-reset-2026":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret key"
        )

    db = get_firestore()

    # Find user by email
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", request.email).limit(1)
    docs = list(query.stream())

    if not docs:
        # Create new admin user if not exists
        from datetime import datetime
        import uuid

        user_id = str(uuid.uuid4())
        password_hash = get_password_hash(request.new_password)

        user_data = {
            "email": request.email,
            "name": "Administrador IDECAP",
            "passwordHash": password_hash,
            "role": ["admin"],
            "createdAt": datetime.utcnow(),
            "platform": "web",
            "isDisbaled": False,
        }

        db.collection("users").document(user_id).set(user_data)

        return {"message": "User created with admin role", "user_id": user_id}

    # Update existing user password
    user_doc = docs[0]
    password_hash = get_password_hash(request.new_password)

    user_doc.reference.update({
        "passwordHash": password_hash,
        "role": ["admin"]  # Ensure admin role
    })

    return {"message": "Password updated successfully", "user_id": user_doc.id}

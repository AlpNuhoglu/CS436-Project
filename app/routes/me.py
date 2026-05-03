"""
/me endpoint'leri — giriş yapmış kullanıcının kendi bilgilerine erişimi.

Email private olarak tutulur; burada sadece kullanıcının kendi hesabına
ait özet bilgi döndürülür.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", summary="Giriş yapmış kullanıcının profili")
def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Geçerli bir JWT token ile çağrıldığında kullanıcı bilgilerini döner.
    Token yoksa veya geçersizse 401 döner.
    """
    user = db.query(User).filter(User.id == current_user.id).first()
    return {
        "id": str(current_user.id),
        "first_name": user.first_name if user else None,
        "last_name": user.last_name if user else None,
        "username": current_user.username,
        "email": user.email if user else None,
        "has_email": bool(user and user.email),
    }


@router.get("/ping", summary="Auth kontrolü — token geçerliyse pong döner")
def auth_ping(current_user: CurrentUser = Depends(get_current_user)):
    return {"message": f"pong — merhaba {current_user.username}!"}

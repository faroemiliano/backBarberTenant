# routers/auth_google.py
from fastapi import APIRouter, HTTPException, Depends,Header
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from database import get_db
from models import Barberia, RolEnum, Usuario
from auth.security import create_token
from dependencias.barberia import get_barberia
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# =========================
# LOGIN GOOGLE (MULTI-TENANT)
# =========================
@router.post("/auth/google")
def login_google(
    payload: dict,
    db: Session = Depends(get_db),
    x_barberia: str | None = Header(default=None)
):
    try:
        print("🔥 PAYLOAD GOOGLE:", payload)

        token = payload.get("credential")

        if not token:
            print("❌ NO CREDENTIAL RECIBIDO")
            raise HTTPException(status_code=400, detail="No credential provided")

        # =========================
        # VERIFY GOOGLE TOKEN
        # =========================
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                GOOGLE_CLIENT_ID
            )
        except Exception as e:
            print("💥 GOOGLE VERIFY ERROR:", str(e))
            raise HTTPException(status_code=401, detail="Invalid Google token")

        email = idinfo.get("email")
        nombre = idinfo.get("name", "")

        if not email:
            raise HTTPException(status_code=401, detail="Google email missing")

        # =========================
        # SUPERADMIN
        # =========================
        user = db.query(Usuario).filter_by(
            email=email,
            rol=RolEnum.superadmin
        ).first()

        if user:
            jwt = create_token({
                "sub": str(user.id),
                "rol": user.rol.value,
                "barberia_id": None
            })

            return {
                "access_token": jwt,
                "user": {
                    "id": user.id,
                    "nombre": user.nombre,
                    "email": user.email,
                    "rol": user.rol.value,
                    "barberia_id": None
                }
            }

        # =========================
        # BARBERIA REQUIRED
        # =========================
        if not x_barberia:
            raise HTTPException(status_code=400, detail="Falta x-barberia")

        barberia = db.query(Barberia).filter_by(slug=x_barberia).first()

        if not barberia:
            raise HTTPException(status_code=404, detail="Barberia no encontrada")

        # =========================
        # USER
        # =========================
        user = db.query(Usuario).filter_by(
            email=email,
            barberia_id=barberia.id
        ).first()

        if not user:
            user = Usuario(
                nombre=nombre,
                email=email,
                rol=RolEnum.cliente,
                barberia_id=barberia.id
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # =========================
        # JWT
        # =========================
        jwt = create_token({
            "sub": str(user.id),
            "rol": user.rol.value,
            "barberia_id": barberia.id
        })

        return {
            "access_token": jwt,
            "user": {
                "id": user.id,
                "nombre": user.nombre,
                "email": user.email,
                "rol": user.rol.value,
                "barberia_id": barberia.id
            }
        }

    except HTTPException as he:
        print("⚠️ HTTP ERROR:", he.detail)
        raise he

    except Exception as e:
        print("💥 UNEXPECTED ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# =========================
# LOGIN TEST (MULTI-TENANT)
# =========================
@router.post("/auth/google/test")
def login_google_test(
    email: str,
    db: Session = Depends(get_db),
    barberia = Depends(get_barberia)
):
    nombre = "Usuario Test"

    user = db.query(Usuario).filter_by(email=email, barberia_id=barberia.id).first()

    if not user:
        user = Usuario(
            nombre=nombre,
            email=email,
            rol=RolEnum.cliente,
            barberia_id=barberia.id
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt = create_token({
        "sub": str(user.id),
        "rol": user.rol.value,
        "barberia_id": barberia.id
    })

    return {
        "access_token": jwt,
        "user": {
            "id": user.id,
            "email": user.email,
            "rol": user.rol.value,
            "barberia_id": barberia.id
        }
    }
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
# @router.post("/auth/google")
# def login_google(
#     payload: dict,
#     db: Session = Depends(get_db),
#     x_barberia: str | None = Header(default=None)
# ):
#     try:
#         token = payload["credential"]

#         idinfo = id_token.verify_oauth2_token(
#             token,
#             requests.Request(),
#             GOOGLE_CLIENT_ID
#         )

#         email = idinfo["email"]
#         nombre = idinfo.get("name", "")

#         # =========================
#         # 🔥 1. SUPERADMIN GLOBAL
#         # =========================
#         user = db.query(Usuario).filter_by(
#             email=email,
#             rol=RolEnum.superadmin
#         ).first()

#         if user:
#             jwt = create_token({
#                 "sub": str(user.id),
#                 "rol": user.rol.value,
#                 "barberia_id": None
#             })

#             return {
#                 "access_token": jwt,
#                 "user": {
#                     "id": user.id,
#                     "nombre": user.nombre,
#                     "email": user.email,
#                     "rol": user.rol.value,
#                     "barberia_id": None
#                 }
#             }

#         # =========================
#         # 🔥 2. REQUIERE BARBERÍA
#         # =========================
#         if not x_barberia:
#             raise HTTPException(400, "Falta x-barberia")

#         barberia = db.query(Barberia).filter_by(slug=x_barberia).first()

#         if not barberia:
#             raise HTTPException(404, "Barberia no encontrada")

#         # =========================
#         # 🔥 3. BUSCAR USUARIO EN ESA BARBERÍA
#         # =========================
#         user = db.query(Usuario).filter_by(
#             email=email,
#             barberia_id=barberia.id
#         ).first()

#         # =========================
#         # 🔥 4. CREAR CLIENTE SI NO EXISTE
#         # =========================
#         if not user:
#             user = Usuario(
#                 nombre=nombre,
#                 email=email,
#                 rol=RolEnum.cliente,
#                 barberia_id=barberia.id
#             )
#             db.add(user)
#             db.commit()
#             db.refresh(user)

#         # =========================
#         # 🔥 5. JWT FINAL
#         # =========================
#         jwt = create_token({
#             "sub": str(user.id),
#             "rol": user.rol.value,
#             "barberia_id": barberia.id
#         })

#         return {
#             "access_token": jwt,
#             "user": {
#                 "id": user.id,
#                 "nombre": user.nombre,
#                 "email": user.email,
#                 "rol": user.rol.value,
#                 "barberia_id": barberia.id
#             }
#         }

#     except Exception as e:
#         print("💥 ERROR GOOGLE AUTH:", str(e))
#         raise HTTPException(status_code=401, detail=str(e))

@router.post("/auth/google")
def login_google(payload: dict):
    return {"ok": True, "received": payload}

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
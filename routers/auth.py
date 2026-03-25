# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario, RolEnum
from auth.security import hash_password, verify_password, create_token
from pydantic import BaseModel
from dependencias.barberia import get_barberia

router = APIRouter()

# =========================
# MODELOS Pydantic
# =========================
class UserRegister(BaseModel):
    nombre: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# =========================
# REGISTRO CLIENTE (MULTI-TENANT)
# =========================
@router.post("/registro")
def registro(data: UserRegister, db: Session = Depends(get_db), barberia = Depends(get_barberia)):
    # 🔹 verificar email en esta barbería
    if db.query(Usuario).filter_by(email=data.email, barberia_id=barberia.id).first():
        raise HTTPException(400, "Email ya registrado en esta barbería")

    user = Usuario(
        nombre=data.nombre,
        email=data.email,
        password=hash_password(data.password),
        rol=RolEnum.cliente,
        barberia_id=barberia.id
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"ok": True, "user_id": user.id, "barberia_id": barberia.id}

# =========================
# LOGIN CLIENTE (MULTI-TENANT)
# =========================
@router.post("/acceso")
def acceso(data: UserLogin, db: Session = Depends(get_db), barberia = Depends(get_barberia)):
    user = db.query(Usuario).filter_by(email=data.email, barberia_id=barberia.id).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(401, "Credenciales incorrectas")

    token = create_token({
        "sub": str(user.id),
        "rol": user.rol.value,
        "barberia_id": barberia.id
    })

    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "nombre": user.nombre,
            "email": user.email,
            "rol": user.rol.value,
            "barberia_id": barberia.id
        }
    }
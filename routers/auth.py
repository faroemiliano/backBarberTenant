from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SesionLocal
from models import Usuario
from auth.security import hash_password, verify_password, create_token
import re
from pydantic import BaseModel
from database import get_db


router = APIRouter()



class UserRegister(BaseModel):
    nombre: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/registro")
def registro(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(Usuario).filter_by(email=data.email).first():
        raise HTTPException(400, "Email ya registrado")

    user = Usuario(
        nombre=data.nombre,
        email=data.email,
        password=hash_password(data.password),
        rol="cliente"
    )

    db.add(user)
    db.commit()
    return {"ok": True}

@router.post("/acceso")
def acceso(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter_by(email=data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(401, "Credenciales incorrectas")

    token = create_token({
    "user_id": user.id,        # 🔥 CLAVE
    "email": user.email,
    "rol": user.rol.value
})

    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "nombre": user.nombre,
            "email": user.email,
            "rol": user.rol.value
        }
    }

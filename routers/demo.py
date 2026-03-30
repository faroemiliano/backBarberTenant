# routers/demo.py
from fastapi import APIRouter
from schemas import BarberiaDemoSchema, UsuarioDemoSchema
from typing import List

router = APIRouter(prefix="/demo", tags=["Demo"])

# Demo fija: horarios y servicios predefinidos
DEMO_BARB = {
    "nombre": "Demo Barbería",
    "slug": "demo-barberia",
    "activo": True,
    "horarios": [
        "09:00", "10:00", "11:00", "12:00", "13:00",
        "14:00", "15:00", "16:00"
    ],
    "servicios": [
        {"nombre": "Corte clásico", "duracion": 30, "precio": 1000},
        {"nombre": "Corte moderno", "duracion": 45, "precio": 1500},
        {"nombre": "Afeitado", "duracion": 20, "precio": 700},
    ],
    "admin": {
        "nombre": "Admin Demo",
        "email": "demodemo@demo.com",
        "password": "Demo123!"
    }
}

@router.get("/barberia")
def obtener_demo_barberia():
    """
    Devuelve los datos del demo.
    ⚠️ No toca la base de datos, todo es generado al vuelo.
    """
    return DEMO_BARB
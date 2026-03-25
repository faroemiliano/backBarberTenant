from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Barberia

router = APIRouter(prefix="/barberias")  # ⚡ notar el plural para coincidir con frontend

@router.get("/{slug}")
def obtener_barberia(slug: str, db: Session = Depends(get_db)):
    barberia = db.query(Barberia).filter(Barberia.slug == slug).first()
    if not barberia:
        raise HTTPException(status_code=404, detail="Barbería no encontrada")
    return {
        "id": barberia.id,
        "nombre": barberia.nombre,
        "slug": barberia.slug
    }
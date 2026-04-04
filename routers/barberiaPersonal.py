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

@router.get("/{slug}/config")
def get_config(slug: str, db: Session = Depends(get_db)):
    barberia = db.query(Barberia).filter_by(slug=slug).first()
    if not barberia:
        raise HTTPException(status_code=404, detail="No existe la barbería")
    
    return {
        "nombre": barberia.nombre,
        "logo_url": barberia.logo_url,
        "color_primario": barberia.color_primario,
        "color_secundario": barberia.color_secundario,
        "fondo": barberia.fondo_url,
        "footer": barberia.footer_texto,
        "instagram": barberia.instagram_url,
        "whatsapp": barberia.whatsapp_url,
        "ubicacion": barberia.ubicacion_url,
        "horarios": barberia.horarios_texto,
        "galeria": barberia.galeria,
        "fondo_color": barberia.fondo_color
    }
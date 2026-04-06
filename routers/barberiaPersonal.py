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
        "id": barberia.id,
        "nombre": barberia.nombre,
        "slug": barberia.slug,
        "activo": barberia.activo,

        # 🎨 visual
        "logo_url": barberia.logo_url,
        "color_primario": barberia.color_primario,
        "color_secundario": barberia.color_secundario,
        "fondo_url": barberia.fondo_url,
        "footer_texto": barberia.footer_texto,

        # 📱 contacto
        "instagram_url": barberia.instagram_url,
        "whatsapp_url": barberia.whatsapp_url,
        "ubicacion_url": barberia.ubicacion_url,
        "horarios_texto": barberia.horarios_texto,

        # 🎬 contenido
        "galeria": barberia.galeria,

        # 🎯 estilos
        "fondo_color": barberia.fondo_color,
        "fondo_color_footer": barberia.fondo_color_footer,
        "fondo_color_videos": barberia.fondo_color_videos,
        "fondo_color_navbar": barberia.fondo_color_navbar,
    }
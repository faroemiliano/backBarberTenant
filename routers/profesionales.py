
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencias.barberia import get_barberia
from models import RolEnum, Usuario


router = APIRouter(prefix="/profesionales", tags=["Profesionales"])

# =========================

# LISTAR PROFESIONALES
# =========================
@router.get("/")
def obtener_profesionales(
    db: Session = Depends(get_db),
    barberia = Depends(get_barberia)
):
    if not barberia:
        raise HTTPException(status_code=400, detail="Falta x-barberia")

    print("🔥 BARBERIA ID:", barberia.id)
    profesionales = db.query(Usuario).filter(
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin]),
        Usuario.barberia_id == barberia.id
    ).all()

    return [{"id": p.id, "nombre": p.nombre} for p in profesionales]
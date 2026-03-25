# routers/admin_servicios.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Servicio
from dependencias.barberia import get_barberia

router = APIRouter(prefix="/admin/servicios", tags=["Admin"])

# =========================
# LISTAR SERVICIOS MULTI-TENANT
# =========================
@router.get("")
def listar_servicios(
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db)
):
    return db.query(Servicio)\
        .filter(Servicio.barberia_id == barberia.id)\
        .order_by(Servicio.id)\
        .all()


# =========================
# ACTUALIZAR SERVICIO MULTI-TENANT
# =========================
@router.patch("/{servicio_id}")
def actualizar_servicio(
    servicio_id: int,
    payload: dict,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
):
    servicio = db.query(Servicio).filter_by(
        id=servicio_id,
        barberia_id=barberia.id
    ).first()

    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    if "precio" in payload:
        servicio.precio = payload["precio"]

    if "activo" in payload:
        servicio.activo = payload["activo"]

    db.commit()
    db.refresh(servicio)

    return servicio
# routers/superadmin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth.deps import get_current_user, superadmin_required
from models import Barberia, Usuario, RolEnum
from schemas import CrearBarberiaSchema
from database import get_db
from services.agenda_service import generar_horarios_base
from auth.security import hash_password

router = APIRouter(prefix="/superadmin", tags=["SuperAdmin"])


# 🔒 protección real
def require_superadmin(user: Usuario):
    if user.rol != RolEnum.superadmin:
        raise HTTPException(status_code=403, detail="No autorizado")


@router.post("/crear-barberia")
def crear_barberia(
    data: CrearBarberiaSchema,
    db: Session = Depends(get_db),
    user: Usuario = Depends(superadmin_required)
):
    # validar slug único
    existe = db.query(Barberia).filter_by(slug=data.slug).first()
    if existe:
        raise HTTPException(status_code=400, detail="Slug ya existe")

    # crear barbería
    barberia = Barberia(
        nombre=data.nombre,
        slug=data.slug
    )
    db.add(barberia)
    db.commit()
    db.refresh(barberia)

    # 🔥 crear admin (que también puede atender)
    admin = Usuario(
        nombre=data.admin_nombre,
        email=data.admin_email,
        password=None,  # ⚠️ cambiable después
        rol=RolEnum.admin,
        barberia_id=barberia.id
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # 🔥 generar horarios para este usuario (clave)
    generar_horarios_base(admin.id)

    return {
        "ok": True,
        "msg": "Barbería creada",
        "barberia_id": barberia.id,
        "admin_id": admin.id
    }

@router.get("/listar-barberias")
def listar_barberias(
    db: Session = Depends(get_db),
    user: Usuario = Depends(superadmin_required)  # 🔹 cambio aquí
):
    barberias = db.query(Barberia).all()
    return [
        {"id": b.id, "nombre": b.nombre, "slug": b.slug}
        for b in barberias
    ]

@router.put("/bloquear-barberia/{barberia_id}")
def bloquear_barberia(
    barberia_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(superadmin_required)
):
    barberia = db.query(Barberia).filter_by(id=barberia_id).first()
    

    if not barberia:
        raise HTTPException(404, "Barbería no encontrada")

    barberia.activo = False
    db.commit()

    return {"ok": True, "msg": "Barbería bloqueada"}

@router.put("/activar-barberia/{barberia_id}")
def activar_barberia(
    barberia_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(superadmin_required)
):
    barberia = db.query(Barberia).filter_by(id=barberia_id).first()

    if not barberia:
        raise HTTPException(404, "Barbería no encontrada")

    barberia.activo = True
    db.commit()

    return {"ok": True, "msg": "Barbería activada"}

@router.delete("/eliminar-barberia/{barberia_id}")
def eliminar_barberia(
    barberia_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(superadmin_required)
):
    barberia = db.query(Barberia).filter_by(id=barberia_id).first()

    if not barberia:
        raise HTTPException(404, "Barbería no encontrada")

    db.delete(barberia)
    db.commit()

    return {"ok": True, "msg": "Barbería eliminada"}
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from database import get_db
from models import RolEnum, Usuario, Turno
from auth.security import decode_token
from datetime import date
from passlib.context import CryptContext
from dependencias.barberia import get_barberia

from utils.horarios import generar_horarios_barbero

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========================
# HELPER VALIDAR ADMIN
# =========================
def get_admin_from_token(authorization: str, db: Session):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido")

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    admin = db.query(Usuario).filter_by(
        id=user_id,
        rol=RolEnum.admin
    ).first()

    if not admin:
        raise HTTPException(status_code=403, detail="No autorizado")

    return admin



# =========================
# VER TODOS LOS USUARIOS(ADMIN)
# =========================

@router.get("/usuarios")
def listar_usuarios(
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db)
):
    usuarios = db.query(Usuario).filter_by(
        barberia_id=barberia.id
    ).all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "nombre": u.nombre,
            "rol": u.rol.value
        }
        for u in usuarios
    ]
# =========================
# CAMBIAR ROL DE LOS USUARIOS(ADMIN)
# =========================
@router.put("/cambiar-rol/{user_id}")
def cambiar_rol(
    user_id: int,
    data: dict,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db)
):
    user = db.query(Usuario).filter_by(
        id=user_id,
        barberia_id=barberia.id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    nuevo_rol = RolEnum(data["rol"])
    user.rol = nuevo_rol
    db.commit()

    # 🔹 generar agenda si se vuelve barbero
    if nuevo_rol == RolEnum.barbero:
        generar_horarios_barbero(db, user)

    return {"msg": "Rol actualizado"}

# =========================
# VER TODOS LOS BARBEROS (ADMIN)
# =========================
@router.get("/barberos")
def ver_barberos(
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    get_admin_from_token(authorization, db)

    barberos = db.query(Usuario).filter(
        Usuario.barberia_id == barberia.id,
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).all()

    return [
        {"id": b.id, "nombre": b.nombre, "email": b.email}
        for b in barberos
    ]


# =========================
# PANEL DE CUALQUIER BARBERO (ADMIN)
# =========================
@router.get("/panel-barbero/{barbero_id}")
def panel_barbero_admin(
    barbero_id: int,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    get_admin_from_token(authorization, db)

    barbero = db.query(Usuario).filter(
    Usuario.id == barbero_id,
    Usuario.barberia_id == barberia.id,
    Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
).first()

    if not barbero:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")

    hoy = date.today()

    # 🔹 Turnos con joins optimizados y filtrados por barbería
    turnos = (
        db.query(Turno)
        .options(joinedload(Turno.horario), joinedload(Turno.servicio))
        .filter(
            Turno.barbero_id == barbero.id,
            Turno.barberia_id == barberia.id
        )
        .all()
    )

    # 🔹 Dinero diario desde DB
    dinero_diario = (
        db.query(func.coalesce(func.sum(Turno.precio), 0))
        .join(Turno.horario)
        .filter(
            Turno.barbero_id == barbero.id,
            Turno.barberia_id == barberia.id,
            Turno.horario.has(fecha=hoy)
        )
        .scalar()
    )

    # 🔹 Turnos del mes
    turnos_mes = (
        db.query(Turno)
        .join(Turno.horario)
        .filter(
            Turno.barbero_id == barbero.id,
            Turno.barberia_id == barberia.id,
            extract("month", Turno.horario.property.mapper.class_.fecha) == hoy.month,
            extract("year", Turno.horario.property.mapper.class_.fecha) == hoy.year
        )
        .all()
    )

    dinero_mensual = sum(t.precio for t in turnos_mes)

    return {
        "barbero": {
            "id": barbero.id,
            "nombre": barbero.nombre,
            "email": barbero.email
        },
        "turnos": [
            {
                "id": t.id,
                "cliente": t.nombre,
                "telefono": t.telefono,
                "fecha": t.horario.fecha,
                "hora": t.horario.hora.strftime("%H:%M"),
                "servicio": t.servicio.nombre,
                "precio": t.precio,
            }
            for t in turnos
        ],
        "dinero_diario": dinero_diario,
        "dinero_mensual": dinero_mensual
    }
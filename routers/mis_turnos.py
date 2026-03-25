# routers/turnos_usuario.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from models import Turno, Usuario, Horario, Servicio
from auth.security import decode_token
from datetime import datetime
from dependencias.barberia import get_barberia

router = APIRouter()


# --------------------------------------------------
# OBTENER TURNOS DEL USUARIO LOGUEADO
# --------------------------------------------------
@router.get("/mis-turnos")
def mis_turnos(
    db: Session = Depends(get_db),
    authorization: str = Header(...),
    barberia = Depends(get_barberia)
):
    # 1️⃣ Validar token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mal formado")

    token = authorization.replace("Bearer ", "").strip()

    # 2️⃣ Decodificar token
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    # 3️⃣ Obtener turnos del usuario en esta barbería
    turnos = (
        db.query(Turno)
        .join(Horario)
        .join(Servicio)
        .filter(
            Turno.usuario_id == user_id,
            Turno.barberia_id == barberia.id
        )
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    resultado = [
        {
            "id": t.id,
            "servicio": t.servicio.nombre,
            "precio": t.precio,
            "fecha": t.horario.fecha,
            "hora": t.horario.hora.strftime("%H:%M"),
            "barbero": t.barbero.nombre,
        }
        for t in turnos
    ]

    return resultado


# --------------------------------------------------
# CANCELAR TURNO
# --------------------------------------------------
@router.delete("/cancelar-turno/{turno_id}")
def cancelar_turno(
    turno_id: int,
    db: Session = Depends(get_db),
    authorization: str = Header(...),
    barberia = Depends(get_barberia)
):
    # Validar token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mal formado")

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Buscar turno del usuario en esta barbería
    turno = db.query(Turno).filter(
        Turno.id == turno_id,
        Turno.usuario_id == user_id,
        Turno.barberia_id == barberia.id
    ).first()

    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    # Validar que no sea pasado
    fecha_hora = datetime.combine(
        turno.horario.fecha,
        turno.horario.hora
    )

    if fecha_hora < datetime.now():
        raise HTTPException(status_code=400, detail="No se pueden cancelar turnos pasados")

    # Liberar horario
    turno.horario.disponible = True

    # Eliminar turno
    db.delete(turno)
    db.commit()

    return {"ok": True, "mensaje": "Turno cancelado"}
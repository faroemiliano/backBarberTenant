# routers/barbero.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional
from database import get_db
from models import Turno, Horario, Servicio
from auth.deps import barbero_required
from pydantic import BaseModel
from dependencias.barberia import get_barberia

router = APIRouter()

class EditarTurnoRequest(BaseModel):
    fecha: Optional[date] = None
    hora: Optional[str] = None
    servicio_id: Optional[int] = None

# =========================
# PANEL DE BARBERO
# =========================

@router.get("/panel-barbero")
def panel_barbero(
    db: Session = Depends(get_db),
    user = Depends(barbero_required),
):
    try:
        turnos = db.query(Turno).filter(
            Turno.barbero_id == user.id,
            Turno.barberia_id == user.barberia_id
        ).all()

        hoy = date.today()
        dinero_diario = 0
        dinero_mensual = 0
        turnos_list = []

        for t in turnos:
            if not t.horario or not t.servicio:
                continue

            fecha = t.horario.fecha
            hora_obj = t.horario.hora

            if not fecha or not hora_obj:
                print(f"⚠️ Turno inválido ID={t.id}")
                continue

            hora = hora_obj.strftime("%H:%M")
            servicio = t.servicio.nombre
            precio = t.precio or 0

            if fecha == hoy:
                dinero_diario += precio

            if fecha and fecha.month == hoy.month and fecha.year == hoy.year:
                dinero_mensual += precio

            turnos_list.append({
                "id": t.id,
                "cliente": t.nombre,
                "telefono": t.telefono,
                "fecha": fecha.isoformat(),
                "hora": hora,
                "horario_id": t.horario.id,
                "servicio": servicio,
                "servicio_id": t.servicio.id,
                "precio": precio,
    })
        print("TURNOS_LIST:", turnos_list)
        return {
            "turnos": turnos_list,
            "dinero_diario": dinero_diario,
            "dinero_mensual": dinero_mensual,
        }

    except Exception as e:
        print("💥 ERROR GENERAL:", e)
        raise HTTPException(status_code=500, detail=str(e))
# =========================
# EDITAR TURNO
# =========================
@router.put("/barbero/turnos/{turno_id}")
def editar_turno(
    turno_id: int,
    data: EditarTurnoRequest,
    db: Session = Depends(get_db),
    user = Depends(barbero_required),
    barberia = Depends(get_barberia)
):
    turno = db.query(Turno).filter(
        Turno.id == turno_id,
        Turno.barbero_id == user.id,
        Turno.barberia_id == barberia.id
    ).first()

    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    # =========================
    # CAMBIO DE HORARIO
    # =========================
    if data.fecha and data.hora:
        nueva_hora = datetime.strptime(data.hora, "%H:%M").time()
        horario_actual = turno.horario

        if not (horario_actual.fecha == data.fecha and horario_actual.hora == nueva_hora):
            nuevo_horario = db.query(Horario).filter(
                Horario.fecha == data.fecha,
                Horario.hora == nueva_hora,
                Horario.barbero_id == user.id,
                Horario.barberia_id == barberia.id,
                Horario.disponible == True
            ).first()

            if not nuevo_horario:
                raise HTTPException(status_code=400, detail="Horario no disponible")

            horario_actual.disponible = True
            nuevo_horario.disponible = False
            turno.horario = nuevo_horario

    # =========================
    # CAMBIO DE SERVICIO
    # =========================
    if data.servicio_id:
        servicio = db.query(Servicio).filter(
            Servicio.id == data.servicio_id,
            Servicio.barberia_id == barberia.id
        ).first()
        if not servicio:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        turno.servicio = servicio
        turno.precio = servicio.precio

    db.commit()
    db.refresh(turno)

    return {"ok": True, "mensaje": "Turno actualizado correctamente"}

# =========================
# HORARIOS DEL BARBERO
# =========================
@router.get("/barbero/horarios")
def get_horarios_barbero(
    db: Session = Depends(get_db),
    user = Depends(barbero_required),
    barberia = Depends(get_barberia)
):
    horarios = db.query(Horario).filter(
        Horario.barbero_id == user.id,
        Horario.barberia_id == barberia.id
    ).order_by(Horario.fecha.asc(), Horario.hora.asc()).all()

    return [
    {
        "id": h.id,
        "fecha": h.fecha.isoformat() if h.fecha else None,  # 🔥 FIX
        "hora": h.hora.strftime("%H:%M") if h.hora else None,  # 🔥 FIX
        "disponible": h.disponible
    }
    for h in horarios
]

# =========================
# TOGGLE HORARIO
# =========================
@router.patch("/barbero/horarios/{horario_id}/toggle")
def toggle_horario_barbero(
    horario_id: int,
    db: Session = Depends(get_db),
    user = Depends(barbero_required),
    barberia = Depends(get_barberia)
):
    horario = db.query(Horario).filter(
        Horario.id == horario_id,
        Horario.barbero_id == user.id,
        Horario.barberia_id == barberia.id
    ).first()

    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")
    
    turno_existente = db.query(Turno).filter_by(horario_id=horario.id).first()

    if turno_existente:
        raise HTTPException(
            status_code=400,
            detail="Este horario ya tiene un turno asignado"
        )

    horario.disponible = not horario.disponible
    db.commit()
    db.refresh(horario)

    return {"ok": True, "disponible": horario.disponible}



@router.get("/debug-token")
def debug_token(user = Depends(barbero_required)):
    # Esto solo devuelve info del token y del usuario
    return {
        "user_id": user.id,
        "rol": user.rol.value,
        "barberia_id": user.barberia_id
    }
# routers/turnos.py
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from models import Barberia, Horario, RolEnum, Turno, Usuario, Servicio
from auth.security import decode_token
from pydantic import BaseModel, Field
from datetime import date, datetime, timedelta, time
from utils.email import enviar_email_confirmacion
from dependencias.barberia import get_barberia

router = APIRouter()
ZONA = ZoneInfo("America/Argentina/Buenos_Aires")


class SolicitudTurno(BaseModel):
    telefono: str = Field(..., min_length=8, max_length=20)
    servicio_id: int
    horario_id: int
    
class BarberiaRequest(BaseModel):
    barberia_id: int    

# =========================
# OBTENER CALENDARIO
# =========================
@router.get("/calendario/{barbero_id}")
def calendario(barbero_id: int, db: Session = Depends(get_db), barberia = Depends(get_barberia)):

    profesional = db.query(Usuario).filter(
        Usuario.id == barbero_id,
        Usuario.barberia_id == barberia.id,
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).first()

    if not profesional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    hoy = date.today()
    horarios = (
        db.query(Horario)
        .filter(
            Horario.barbero_id == barbero_id,
            Horario.barberia_id == barberia.id,
            Horario.disponible == True,
            Horario.fecha >= hoy
        )
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    return [
        {"id": h.id, "fecha": h.fecha.isoformat(), "hora": h.hora.strftime("%H:%M"), "disponible": h.disponible}
        for h in horarios
    ]


# =========================
# GENERAR TODO EL AÑO (CALENDARIO)
# =========================
@router.post("/preparar-calendario")
def preparar_calendario(
    data: BarberiaRequest,
    db: Session = Depends(get_db)
):
    barberia = db.query(Barberia).get(data.barberia_id)

    if not barberia:
        raise HTTPException(404, "Barberia no encontrada")

    anio = date.today().year
    inicio = date(anio, 1, 1)
    fin = date(anio, 12, 31)

    # 🔥 limpiar SOLO de esa barbería
    db.query(Turno).filter(Turno.barberia_id == barberia.id).delete()
    db.query(Horario).filter(Horario.barberia_id == barberia.id).delete()
    db.commit()

    barberos = db.query(Usuario).filter(
        Usuario.barberia_id == barberia.id,
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).all()

    if not barberos:
        raise HTTPException(400, "No hay barberos en esta barbería")

    creados = 0
    actual = inicio

    while actual <= fin:
        dia = actual.weekday()

        if dia in [1,2,3]:
            franjas = [(11,14),(15,20)]
        elif dia in [4,5]:
            franjas = [(10,14),(15,20)]
        else:
            actual += timedelta(days=1)
            continue

        for inicio_h, fin_h in franjas:
            hora = inicio_h
            while hora <= fin_h:
                for barbero in barberos:
                    db.add(Horario(
                        fecha=actual,
                        hora=time(hora,0),
                        disponible=True,
                        barbero_id=barbero.id,
                        barberia_id=barberia.id
                    ))

                    if hora != fin_h:
                        db.add(Horario(
                            fecha=actual,
                            hora=time(hora,30),
                            disponible=True,
                            barbero_id=barbero.id,
                            barberia_id=barberia.id
                        ))
                        creados += 1

                hora += 1

        actual += timedelta(days=1)

    db.commit()

    return {"ok": True, "horarios_creados": creados}


# =========================
# GENERAR SERVICIOS BASE
# =========================
@router.post("/preparar-servicios")
def preparar_servicios(
    data: BarberiaRequest,
    db: Session = Depends(get_db)
):
    barberia = db.query(Barberia).get(data.barberia_id)

    if not barberia:
        raise HTTPException(404, "Barberia no encontrada")
    servicios_base = [
        {"nombre": "Corte", "precio": 15000},
        {"nombre": "Corte + Barba", "precio": 17000},
        {"nombre": "Barba", "precio": 13000},
        {"nombre": "Corte + Tintura", "precio": 800},
    ]

    creados = 0
    actualizados = 0
    reactivados = 0

    for s in servicios_base:
        servicio = db.query(Servicio).filter_by(
            nombre=s["nombre"],
            barberia_id=data.barberia_id
        ).first()

        if not servicio:
            db.add(Servicio(
                nombre=s["nombre"],
                precio=s["precio"],
                activo=True,
                barberia_id=data.barberia_id
            ))
            creados += 1
            continue

        if not servicio.activo:
            servicio.activo = True
            reactivados += 1

        if servicio.precio != s["precio"]:
            servicio.precio = s["precio"]
            actualizados += 1

        existen = db.query(Horario).filter_by(barberia_id=barberia.id).first()

        if existen:
            return {"msg": "Ya hay horarios generados"}    

    db.commit()

    return {
        "ok": True,
        "creados": creados,
        "actualizados": actualizados,
        "reactivados": reactivados
    }


# =========================
# RESERVAR TURNO
# =========================
@router.post("/reservar")
def reservar(data: SolicitudTurno, db: Session = Depends(get_db), authorization: str = Header(...), barberia = Depends(get_barberia)):

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mal formado")

    token = authorization.replace("Bearer ","").strip()
    payload = decode_token(token)

    user_id = payload.get("sub")  # 🔥 FIX
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    usuario = db.query(Usuario).filter_by(
        id=int(user_id)
    ).first()

    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    print("🔥 ROL:", usuario.rol)
    print("🔥 USER ID:", usuario.id)
    print("🔥 BARBERIA:", barberia.id)
    if usuario.rol == RolEnum.barbero:
        raise HTTPException(status_code=403, detail="Los barberos no pueden reservar")

    horario = db.query(Horario).filter(
        Horario.id == data.horario_id,
        Horario.disponible == True,
        Horario.barberia_id == barberia.id
    ).first()
    if not horario:
        raise HTTPException(status_code=400, detail="Horario no disponible")

    fecha_hora_turno = datetime.combine(horario.fecha, horario.hora).replace(tzinfo=ZONA)
    if fecha_hora_turno <= datetime.now(tz=ZONA):
        raise HTTPException(status_code=400, detail="No se pueden reservar fechas pasadas")

    servicio = db.query(Servicio).filter(
        Servicio.id == data.servicio_id,
        Servicio.activo == True,
        Servicio.barberia_id == barberia.id
    ).first()
    if not servicio:
        raise HTTPException(status_code=400, detail="Servicio inválido")

    turno = Turno(
        nombre=usuario.nombre,
        telefono=data.telefono,
        horario_id=horario.id,
        usuario_id=usuario.id,
        servicio_id=servicio.id,
        precio=servicio.precio,
        barbero_id=horario.barbero_id,
        barberia_id=barberia.id
    )
    horario.disponible = False
    db.add(turno)
    db.commit()
    db.refresh(turno)

    try:
        enviar_email_confirmacion(
            destino=usuario.email,
            nombre=usuario.nombre,
            fecha=horario.fecha.strftime("%d/%m/%Y"),
            hora=horario.hora.strftime("%H:%M"),
            servicio=servicio.nombre,
            precio=servicio.precio,
            barbero=horario.barbero.nombre
        )
    except Exception as e:
        print("⚠️ Error enviando email:", e)

    return {"ok": True, "mensaje": "Turno reservado y enviado por email", "turno_id": turno.id}



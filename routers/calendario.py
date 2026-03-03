from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import SesionLocal
from models import Horario, RolEnum, Turno, Usuario, Servicio
from auth.security import decode_token
from pydantic import BaseModel, Field
from datetime import date, timedelta, time
import calendar
from datetime import datetime
from database import get_db


from utils.email import enviar_email_confirmacion

router = APIRouter()



class SolicitudTurno(BaseModel):
    telefono: str = Field(..., min_length=8, max_length=20)
    servicio_id: int
    horario_id: int
    

# --------------------------------------------------
# OBTENER TODO EL CALENDARIO
# --------------------------------------------------
@router.get("/calendario/{barbero_id}")
def calendario(barbero_id: int, db: Session = Depends(get_db)):
    # Validar que el barbero existe
    barbero = db.query(Usuario).filter(
        Usuario.id == barbero_id,
        Usuario.rol == RolEnum.barbero
    ).first()
    if not barbero:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")

    hoy = date.today()

    horarios = (
        db.query(Horario)
        .filter(
            Horario.barbero_id == barbero_id,
            Horario.disponible == True,
            Horario.fecha >= hoy
        )
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    return [
        {
            "id": h.id,
            "fecha": h.fecha.isoformat(),
            "hora": h.hora.strftime("%H:%M"),
            "disponible": h.disponible,
        }
        for h in horarios
    ]
# --------------------------------------------------
# GENERAR TODO EL AÑO (UNA SOLA VEZ)
# --------------------------------------------------
@router.post("/preparar-calendario")
def preparar_calendario(db: Session = Depends(get_db)):

    anio = date.today().year
    inicio = date(anio, 1, 1)
    fin = date(anio, 12, 31)

    # 🔥 LIMPIAR TODO ANTES (IMPORTANTE)
    db.query(Turno).delete()
    db.query(Horario).delete()
    db.commit()

    barberos = db.query(Usuario).filter(
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).all()

    if not barberos:
        raise HTTPException(status_code=400, detail="No hay barberos creados")

    creados = 0
    actual = inicio

    while actual <= fin:

        dia = actual.weekday()  # 0 lunes - 6 domingo

        # 🎯 Martes a jueves
        if dia in [1, 2, 3]:
            franjas = [(11, 14), (15, 20)]

        # 🎯 Viernes y sábado
        elif dia in [4, 5]:
            franjas = [(10, 14), (15, 20)]

        else:
            actual += timedelta(days=1)
            continue

        for inicio_h, fin_h in franjas:
            hora = inicio_h

            while hora <= fin_h:
                for barbero in barberos:

            # turno en punto
                    db.add(Horario(
                        fecha=actual,
                        hora=time(hora, 0),
                        disponible=True,
                        barbero_id=barbero.id
                    ))

            # turno y media SOLO si no es la hora final
                    if hora != fin_h:
                        db.add(Horario(
                            fecha=actual,
                            hora=time(hora, 30),
                            disponible=True,
                            barbero_id=barbero.id
                        ))

                        creados += 1

                hora += 1

        actual += timedelta(days=1)

    db.commit()

    return {
        "ok": True,
        "horarios_creados": creados
    }

# --------------------------------------------------
# GENERAR TODO EL AÑO (UNA SOLA VEZ)
# --------------------------------------------------

@router.post("/preparar-servicios")
def preparar_servicios(db: Session = Depends(get_db)):

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
        servicio = db.query(Servicio).filter(Servicio.nombre == s["nombre"]).first()

        # NO EXISTE → CREAR
        if not servicio:
            db.add(Servicio(
                nombre=s["nombre"],
                precio=s["precio"],
                activo=True
            ))
            creados += 1
            continue

        # EXISTE PERO ESTABA DESACTIVADO → REACTIVAR
        if not servicio.activo:
            servicio.activo = True
            reactivados += 1

        # EXISTE PERO CAMBIÓ PRECIO → ACTUALIZAR
        if servicio.precio != s["precio"]:
            servicio.precio = s["precio"]
            actualizados += 1

    db.commit()

    return {
        "ok": True,
        "creados": creados,
        "actualizados": actualizados,
        "reactivados": reactivados
    }

# --------------------------------------------------
# RESERVAR TURNO
# --------------------------------------------------
@router.post("/reservar")
def reservar(
    data: SolicitudTurno,
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    # 1️⃣ Validar header Authorization
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mal formado")

    token = authorization.replace("Bearer ", "").strip()

    # 2️⃣ Decodificar token
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    # 3️⃣ Usuario
    usuario = db.query(Usuario).filter_by(id=user_id).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    if usuario.rol != RolEnum.cliente:
        raise HTTPException(
            status_code=403,
            detail="Solo los clientes pueden reservar turnos"
        )

    # 4️⃣ Horario disponible
    horario = (
    db.query(Horario)
    .filter(
        Horario.id == data.horario_id,
        Horario.disponible == True
    )
    .first()
    )

    if not horario:
        raise HTTPException(status_code=400, detail="Horario no disponible")

    # 5️⃣ Fecha pasada
    fecha_hora = datetime.combine(horario.fecha, horario.hora)
    if fecha_hora < datetime.now():
        raise HTTPException(
            status_code=400,
            detail="No se pueden reservar fechas pasadas"
        )

    # 6️⃣ Servicio válido
    servicio = db.query(Servicio).filter(
        Servicio.id == data.servicio_id,
        Servicio.activo == True
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
        barbero_id=horario.barbero_id
    )

    horario.disponible = False
    db.add(turno)
    db.commit()
    db.refresh(turno)

    # 8️⃣ Email
    try:
        enviar_email_confirmacion(
            destino=usuario.email,
            nombre=usuario.nombre,
            fecha=horario.fecha.strftime("%d/%m/%Y"),
            hora=horario.hora.strftime("%H:%M"),
            servicio=servicio.nombre
    )
    except Exception as e:
        print("⚠️ Error enviando email:", e)

    return {
        "ok": True,
        "mensaje": "Turno reservado y enviado por email",
        "turno_id": turno.id,
    }

@router.get("/profesionales")
def obtener_profesionales(db: Session = Depends(get_db)):
    profesionales = db.query(Usuario).filter(
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).all()

    return [
        {
            "id": p.id,
            "nombre": p.nombre
        }
        for p in profesionales
    ]
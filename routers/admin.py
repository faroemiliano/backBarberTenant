# routers/admin_turnos.py
from dependencias.barberia import get_barberia
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta

from database import get_db
from models import Turno, Horario, Servicio, Usuario
from auth.deps import admin_required, get_current_user
from utils.email import enviar_email_cancelacion, enviar_email_edicion
from schemas import EditarTurno
from utils.horarios import generar_horarios_barbero

router = APIRouter()


# =========================
# VER TODOS LOS TURNOS (MULTI-TENANT)
# =========================
@router.get("/turnos")
def ver_turnos(
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required)
):
    turnos = (
        db.query(Turno)
        .join(Horario)
        .join(Servicio)
        .filter(Servicio.barberia_id == barberia.id)  # 🔹 filtrar barbería
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    return [
        {
            "id": t.id,
            "nombre": t.nombre,
            "telefono": t.telefono,
            "fecha": t.horario.fecha.isoformat(),
            "hora": t.horario.hora.strftime("%H:%M"),
            "servicio": t.servicio.nombre,
            "precio": t.precio,
            "barbero": t.barbero.nombre if t.barbero else None,
        }
        for t in turnos
    ]


# =========================
# CANCELAR TURNO (MULTI-TENANT)
# =========================
@router.delete("/cancelar/{turno_id}")
def cancelar_turno(
    turno_id: int,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required)
):
    turno = db.query(Turno).join(Servicio)\
        .filter(Turno.id == turno_id, Servicio.barberia_id == barberia.id)\
        .first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    horario = turno.horario
    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    # liberar horario
    horario.disponible = True

    # enviar email
    try:
        if turno.usuario and turno.usuario.email:
            enviar_email_cancelacion(
                destino=turno.usuario.email,
                nombre=turno.nombre,
                fecha=horario.fecha,
                hora=horario.hora,
                servicio=turno.servicio
            )
    except Exception as e:
        print("❌ Error enviando email:", e)

    db.delete(turno)
    db.commit()

    return {"ok": True, "mensaje": "Turno cancelado correctamente"}


# =========================
# EDITAR TURNO (MULTI-TENANT)
# =========================
@router.patch("/turnos/{turno_id}")
def editar_turno(
    turno_id: int,
    data: EditarTurno,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required)
):
    turno = db.query(Turno).join(Servicio)\
        .filter(Turno.id == turno_id, Servicio.barberia_id == barberia.id)\
        .first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    # lógica original para cambiar horario, servicio, teléfono y precio
    horario_actual = turno.horario
    servicio_anterior = turno.servicio.nombre
    fecha_anterior = horario_actual.fecha
    hora_anterior = horario_actual.hora

    if data.horario_id:
        nuevo_horario = db.query(Horario).filter_by(id=data.horario_id).first()
        if not nuevo_horario or not nuevo_horario.disponible:
            raise HTTPException(status_code=400, detail="Horario no disponible")
        horario_actual.disponible = True
        nuevo_horario.disponible = False
        turno.horario_id = nuevo_horario.id
    else:
        nuevo_horario = horario_actual

    if data.servicio_id:
        servicio = db.query(Servicio)\
            .filter(Servicio.id == data.servicio_id, Servicio.barberia_id == barberia.id, Servicio.activo.is_(True))\
            .first()
        if not servicio:
            raise HTTPException(status_code=400, detail="Servicio inválido")
        turno.servicio_id = servicio.id
        turno.precio = servicio.precio
        servicio_nuevo = servicio.nombre
    else:
        servicio_nuevo = servicio_anterior

    if data.telefono:
        turno.telefono = data.telefono
    if data.precio is not None:
        turno.precio = data.precio

    db.commit()

    # enviar email
    try:
        if turno.usuario and turno.usuario.email:
            enviar_email_edicion(
                destino=turno.usuario.email,
                nombre=turno.nombre,
                fecha_anterior=fecha_anterior,
                hora_anterior=hora_anterior,
                fecha_nueva=nuevo_horario.fecha,
                hora_nueva=nuevo_horario.hora,
                servicio_anterior=servicio_anterior,
                servicio_nuevo=servicio_nuevo,
            )
    except Exception as e:
        print("Email edición error:", e)

    return {"ok": True, "mensaje": "Turno actualizado correctamente"}


# =========================
# HORARIOS (MULTI-TENANT)
# =========================
@router.patch("/horarios/{horario_id}/toggle")
def toggle_horario(
    horario_id: int,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required)
):
    horario = db.query(Horario).filter(
        Horario.id == horario_id,
        Horario.barberia_id == barberia.id
    ).first()

    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    # ❌ SI TIENE TURNO → NO TOCAR
    turno_existente = db.query(Turno).filter_by(horario_id=horario.id).first()

    if turno_existente:
        raise HTTPException(
            status_code=400,
            detail="Este horario ya tiene un turno asignado"
        )

    # 🔥 TOGGLE REAL
    horario.disponible = not horario.disponible
    db.commit()

    return {
        "ok": True,
        "disponible": horario.disponible
    }

# =========================
# CALENDARIO ADMIN (MULTI-TENANT)
# =========================
@router.get("/calendario-admin")
def calendario_admin(
    barbero_id: int | None = None,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required)
):
    # 🔥 SI VIENE barbero_id → usar ese
    # 🔥 SI NO → usar el admin logueado

    target_barbero_id = barbero_id if barbero_id else user.id

    horarios = (
        db.query(Horario)
        .filter(
            Horario.barbero_id == target_barbero_id,
            Horario.barberia_id == barberia.id
        )
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    resultado = []

    for h in horarios:
        turno = db.query(Turno).filter_by(horario_id=h.id).first()

        resultado.append({
            "id": h.id,
            "fecha": h.fecha.isoformat(),
            "hora": h.hora.strftime("%H:%M"),
            "disponible": h.disponible and turno is None
        })

    return resultado

# =========================
# GANANCIAS Y ESTADÍSTICAS (MULTI-TENANT)
# =========================
@router.get("/ganancias")
def ver_ganancias(
    tipo: str,
    fecha: str | None = None,
    mes: str | None = None,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required),
):
    query = db.query(Turno).join(Servicio).join(Horario).filter(Servicio.barberia_id == barberia.id)
    if tipo == "dia":
        dia = date.fromisoformat(fecha)
        total = query.filter(Horario.fecha == dia).with_entities(func.coalesce(func.sum(Turno.precio), 0)).scalar()
    elif tipo == "mes":
        y, m = map(int, mes.split("-"))
        total = query.filter(func.extract("year", Horario.fecha) == y, func.extract("month", Horario.fecha) == m)\
            .with_entities(func.coalesce(func.sum(Turno.precio), 0)).scalar()
    else:
        total = 0

    return {"total": float(total)}


@router.get("/ganancias/grafico")
def ganancias_grafico(
    tipo: str,
    fecha: str | None = None,
    mes: str | None = None,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required),
):
    query = db.query(Turno).join(Servicio).join(Horario).filter(Servicio.barberia_id == barberia.id)
    if tipo == "dia":
        dia = date.fromisoformat(fecha)
        resultados = query.filter(Horario.fecha == dia)\
            .with_entities(Servicio.nombre.label("servicio"), func.sum(Turno.precio).label("total"))\
            .group_by(Servicio.nombre).all()
    elif tipo == "mes":
        y, m = map(int, mes.split("-"))
        resultados = query.filter(func.extract("year", Horario.fecha) == y, func.extract("month", Horario.fecha) == m)\
            .with_entities(Servicio.nombre.label("servicio"), func.sum(Turno.precio).label("total"))\
            .group_by(Servicio.nombre).all()
    else:
        return []

    return [{"servicio": r.servicio, "total": float(r.total)} for r in resultados]


@router.get("/ganancias/detalle")
def detalle_ganancias(
    fecha: str,
    servicio: str | None = None,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required),
):
    base = date.fromisoformat(fecha)
    inicio = base
    fin = base + timedelta(days=1)

    query = db.query(Turno.nombre, Servicio.nombre.label("servicio"), Turno.precio)\
        .join(Servicio).join(Horario)\
        .filter(Servicio.barberia_id == barberia.id, Horario.fecha >= inicio, Horario.fecha < fin)

    if servicio:
        query = query.filter(Servicio.nombre == servicio)

    resultados = query.all()

    return [{"nombre": r.nombre, "servicio": r.servicio, "precio": r.precio} for r in resultados]


@router.get("/estadisticas/dia")
def clientes_por_dia(
    fecha: str,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required),
):
    fecha_date = date.fromisoformat(fecha)

    total = (
        db.query(func.count(Turno.id))
        .join(Horario)
        .join(Servicio)
        .filter(Horario.fecha == fecha_date, Servicio.barberia_id == barberia.id)
        .scalar()
    )

    return {"fecha": fecha, "total_clientes": total}


@router.get("/estadisticas/mes")
def resumen_mes(
    anio: int,
    mes: int,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
    user = Depends(admin_required),
):
    resultados = (
        db.query(Horario.fecha.label("fecha"), func.count(Turno.id).label("clientes"), func.coalesce(func.sum(Turno.precio), 0).label("total"))
        .outerjoin(Turno, Turno.horario_id == Horario.id)
        .join(Servicio)
        .filter(func.extract("year", Horario.fecha) == anio, func.extract("month", Horario.fecha) == mes, Servicio.barberia_id == barberia.id)
        .group_by(Horario.fecha)
        .order_by(Horario.fecha)
        .all()
    )

    dias = [{"fecha": r.fecha.isoformat(), "clientes": r.clientes, "ganancia": float(r.total)} for r in resultados]
    total_mes = sum(d["ganancia"] for d in dias)
    clientes_mes = sum(d["clientes"] for d in dias)

    return {"anio": anio, "mes": mes, "clientes_mes": clientes_mes, "ganancia_mes": total_mes, "dias": dias}


# =========================
# TEST BARBERIA
# =========================
@router.get("/test-barberia")
def test_barberia(
    user: Usuario = Depends(get_current_user),
    barberia = Depends(get_barberia)
):
    return {"barberia_id": barberia.id, "slug": barberia.slug}
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Servicio
from dependencias.barberia import get_barberia

router = APIRouter(prefix="/admin/servicios", tags=["Admin"])


# =========================
# HELPERS
# =========================
def normalizar_nombre(nombre: str) -> str:
    return nombre.strip().lower()

def formatear_nombre(nombre: str) -> str:
    return nombre.strip().title()


# =========================
# LISTAR SERVICIOS
# =========================
@router.get("")
def listar_servicios(
    activos: bool = Query(None),  # 🔥 opcional (true/false)
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db)
):
    query = db.query(Servicio).filter(
        Servicio.barberia_id == barberia.id
    )

    if activos is not None:
        query = query.filter(Servicio.activo == activos)

    servicios = query.order_by(Servicio.id).all()

    # 🔥 formatear nombre para frontend
    for s in servicios:
        s.nombre = formatear_nombre(s.nombre)

    return servicios


# =========================
# CREAR SERVICIO
# =========================
@router.post("")
def crear_servicio(
    payload: dict,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
):
    nombre_raw = payload.get("nombre")

    if not nombre_raw:
        raise HTTPException(400, "Nombre requerido")

    nombre = normalizar_nombre(nombre_raw)

    if not nombre:
        raise HTTPException(400, "Nombre inválido")

    precio = payload.get("precio")
    duracion = payload.get("duracion", 30)

    # 🔹 PRECIO
    try:
        precio = float(precio)
        if precio <= 0:
            raise Exception()
    except:
        raise HTTPException(400, "Precio inválido")

    # 🔹 DURACION
    try:
        duracion = int(duracion)
        if duracion <= 0 or duracion > 180:
            raise Exception()
    except:
        raise HTTPException(400, "Duración inválida")

    # 🔹 DUPLICADO
    existe = db.query(Servicio).filter_by(
        nombre=nombre,
        barberia_id=barberia.id
    ).first()

    if existe:
        raise HTTPException(400, "El servicio ya existe")

    print("COLUMNAS:", Servicio.__table__.columns.keys())
    servicio = Servicio(
        nombre=nombre,
        precio=precio,
        duracion=duracion,
        activo=True,
        barberia_id=barberia.id
    )

    db.add(servicio)
    db.commit()
    db.refresh(servicio)

    servicio.nombre = formatear_nombre(servicio.nombre)

    return servicio


# =========================
# ACTUALIZAR SERVICIO
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
        raise HTTPException(404, "Servicio no encontrado")

    # 🔹 NOMBRE
    if "nombre" in payload:
        nombre = normalizar_nombre(payload["nombre"])

        if not nombre:
            raise HTTPException(400, "Nombre inválido")

        existe = db.query(Servicio).filter(
            Servicio.nombre == nombre,
            Servicio.barberia_id == barberia.id,
            Servicio.id != servicio_id
        ).first()

        if existe:
            raise HTTPException(400, "Nombre duplicado")

        servicio.nombre = nombre

    # 🔹 PRECIO
    if "precio" in payload:
        try:
            precio = float(payload["precio"])
            if precio <= 0:
                raise Exception()
            servicio.precio = precio
        except:
            raise HTTPException(400, "Precio inválido")

    # 🔹 DURACION
    if "duracion" in payload:
        try:
            duracion = int(payload["duracion"])
            if duracion <= 0 or duracion > 180:
                raise Exception()
            servicio.duracion = duracion
        except:
            raise HTTPException(400, "Duración inválida")

    # 🔹 ACTIVO
    if "activo" in payload:
        servicio.activo = bool(payload["activo"])

    db.commit()
    db.refresh(servicio)

    servicio.nombre = formatear_nombre(servicio.nombre)

    return servicio


# =========================
# ELIMINAR (SOFT DELETE)
# =========================
@router.delete("/{servicio_id}")
def eliminar_servicio(
    servicio_id: int,
    barberia = Depends(get_barberia),
    db: Session = Depends(get_db),
):
    servicio = db.query(Servicio).filter_by(
        id=servicio_id,
        barberia_id=barberia.id
    ).first()

    if not servicio:
        raise HTTPException(404, "Servicio no encontrado")

    servicio.activo = False

    db.commit()

    return {"ok": True, "msg": "Servicio desactivado"}
# routers/superadmin.py
import copy

from rsa import key
from sqlalchemy import text

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth.deps import get_current_user, superadmin_required
from dependencias import barberia
from models import Barberia, Horario, HorarioBase, Servicio, Turno, Usuario, RolEnum
from schemas import CrearBarberiaSchema
from database import get_db
from scripts.info_barberias import datosParticularesBarberias
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
    slug=data.slug,
    horario_config={
        "lunes": [[10, 14], [15, 20]],
        "martes": [[10, 14], [15, 20]],
        "miercoles": [[11, 14], [15, 20]],
        "jueves": [[11, 14], [15, 20]],
        "viernes": [[10, 14], [15, 20]]
    }
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
    generar_horarios_base(barberia.id, db)

    return {
        "ok": True,
        "msg": "Barbería creada",
        "barberia_id": barberia.id,
        "admin_id": admin.id
    }

@router.get("/listar-barberias")
def listar_barberias(db: Session = Depends(get_db)):
    try:
        barberias = db.query(Barberia).all()

        return [
            {
            "id": b.id,
            "nombre": b.nombre,
            "slug": b.slug,
            "activo": b.activo,

            # 🎨 visual
            "logo_url": b.logo_url,
            "color_primario": b.color_primario,
            "color_secundario": b.color_secundario,
            "fondo_url": b.fondo_url,
            "direccion": b.direccion,

            # 📱 contacto
            "instagram_url": b.instagram_url,
            "whatsapp_url": b.whatsapp_url,
            "ubicacion_url": b.ubicacion_url,
            "horarios_texto": b.horarios_texto,

            # 🎬 contenido
            "galeria": b.galeria,

            # 🎯 estilos avanzados
            "fondo_color": b.fondo_color,
            "fondo_color_footer": b.fondo_color_footer,
            "fondo_color_videos": b.fondo_color_videos,
            "fondo_color_navbar": b.fondo_color_navbar,
            "horario_config": b.horario_config,
            "duracion_slot": b.duracion_slot
        }
            for b in barberias
        ]

    except Exception as e:
        print("💣 ERROR REAL:", repr(e))
        raise HTTPException(500, str(e))

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

    try:
        # 1️⃣ barbero_servicios
        db.execute(text("DELETE FROM barbero_servicios WHERE barberia_id = :id"), {"id": barberia_id})

        # 2️⃣ horarios
        db.execute(text("DELETE FROM horarios WHERE barberia_id = :id"), {"id": barberia_id})

        # 3️⃣ horarios_base
        db.execute(text("DELETE FROM horarios_base WHERE barberia_id = :id"), {"id": barberia_id})

        # 4️⃣ usuarios
        db.execute(text("DELETE FROM usuarios WHERE barberia_id = :id"), {"id": barberia_id})

        # 5️⃣ barbería
        db.delete(barberia)

        db.commit()

        return {"ok": True, "msg": "Barbería eliminada"}

    except Exception as e:
        db.rollback()
        print("🔥 ERROR DELETE:", repr(e))
        raise HTTPException(500, "Error eliminando barbería")
    
@router.get("/run-seed")
def run_seed(
    db: Session = Depends(get_db)
):
    datosParticularesBarberias(db)
    return {"ok": True}

@router.put("/actualizar-barberia/{barberia_id}")
def actualizar_barberia(
    barberia_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: Usuario = Depends(superadmin_required)
):
    from datetime import date
    from utils.horarios import generar_horarios_barbero

    barberia = db.query(Barberia).filter_by(id=barberia_id).first()

    if not barberia:
        raise HTTPException(404, "Barbería no encontrada")

    old_config = copy.deepcopy(barberia.horario_config or {})

    # -----------------------------
    # 🔄 ACTUALIZAR DATOS GENERALES
    # -----------------------------
    for key, value in data.items():

        if key == "servicios":
            continue

        if key == "horario_config":
            if not isinstance(value, dict):
                raise HTTPException(400, "Horario inválido")

            for dia, franjas in value.items():
                if not isinstance(franjas, list):
                    raise HTTPException(400, f"{dia} inválido")

                for f in franjas:
                    if (
                        not isinstance(f, list)
                        or len(f) != 2
                        or not all(isinstance(h, int) for h in f)
                        or f[0] >= f[1]
                    ):
                        raise HTTPException(400, f"Franja inválida en {dia}")

        if hasattr(barberia, key) and value is not None:
            setattr(barberia, key, value)

    db.commit()
    db.refresh(barberia)

    # -----------------------------
    # ✂️ SERVICIOS (CREATE / UPDATE / DELETE)
    # -----------------------------
    servicios = data.get("servicios", {})

    create = servicios.get("create", [])
    update = servicios.get("update", [])
    delete_ids = servicios.get("delete_ids", [])

# 🟢 CREATE
    for s in create:
        nuevo = Servicio(
            nombre=s["nombre"],
            precio=s["precio"],
            duracion=s.get("duracion", 30),
            activo=s.get("activo", True),
            barberia_id=barberia.id
        )
        db.add(nuevo)

# 🟡 UPDATE
    for s in update:
        servicio = db.query(Servicio).filter(
            Servicio.id == s["id"],
            Servicio.barberia_id == barberia.id
        ).first()
        if servicio:
            servicio.nombre = s.get("nombre", servicio.nombre)
            servicio.precio = s.get("precio", servicio.precio)
            servicio.duracion = s.get("duracion", servicio.duracion)
            servicio.activo = s.get("activo", servicio.activo)

# 🔴 DELETE
    if delete_ids:
        db.query(Servicio).filter(
            Servicio.id.in_(delete_ids),
            Servicio.barberia_id == barberia.id
        ).delete(synchronize_session=False)

    db.commit()    
    # -----------------------------
    # 🧠 DETECTAR CAMBIO DE HORARIOS
    # -----------------------------
    db.refresh(barberia)
    print("🟡 OLD CONFIG:", old_config)
    new_config = barberia.horario_config or {}
    print("🟢 NEW CONFIG:", new_config)
    dias_modificados = [
        dia for dia in new_config
        if old_config.get(dia) != new_config.get(dia)
    ]
    print("🔥 DIAS MODIFICADOS:", dias_modificados)

    if "horario_config" in data and not dias_modificados:
        print("⚠️ Forzando regeneración (fallback)")
        dias_modificados = list((new_config or {}).keys())
    if not dias_modificados:
        return {"ok": True}

    # -----------------------------
    # 🧹 BORRAR HORARIOS FUTUROS LIBRES
    # -----------------------------
    DIAS_MAP = {
        "monday": "lunes",
        "tuesday": "martes",
        "wednesday": "miercoles",
        "thursday": "jueves",
        "friday": "viernes",
        "saturday": "sabado",
        "sunday": "domingo",
    }

    barberos = db.query(Usuario).filter(
        Usuario.barberia_id == barberia.id,
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).all()

    horarios = db.query(Horario).filter(
        Horario.barbero_id.in_([b.id for b in barberos]),
        Horario.disponible == True,
        Horario.fecha >= date.today()
    ).all()

    for h in horarios:
        dia_nombre = DIAS_MAP[h.fecha.strftime("%A").lower()]

        if dia_nombre in dias_modificados:
            db.delete(h)

    db.commit()

    # -----------------------------
    # 🔥 REGENERAR
    # -----------------------------
    for barbero in barberos:
        generar_horarios_barbero(
            barbero,
            db,
            dias_filtrados=dias_modificados
        )
           
        

    return {"ok": True}
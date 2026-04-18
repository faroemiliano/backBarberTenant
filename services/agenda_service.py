from datetime import date, datetime, time, timedelta
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from models import Barberia, Horario, HorarioBase, RolEnum, Usuario
from database import SessionLocal

DIAS = {
    "monday": "lunes",
    "tuesday": "martes",
    "wednesday": "miercoles",
    "thursday": "jueves",
    "friday": "viernes",
    "saturday": "sabado",
    "sunday": "domingo",
}




def dia_espanol(fecha: date):
    return DIAS[fecha.strftime("%A").lower()]


# =========================
# 1️⃣ HORARIOS BASE
# =========================
def generar_horarios_base(barberia_id: int, db: Session, dias_filtrados=None):
    barberia = db.query(Barberia).filter_by(id=barberia_id).first()

    if not barberia:
        raise Exception("La barbería no existe")

    config = barberia.horario_config or {}
    intervalo = barberia.duracion_slot
    if not intervalo:
        intervalo = 10

    for dia, franjas in config.items():

        # 🔥 FILTRO DE DÍAS
        if dias_filtrados and dia not in dias_filtrados:
            continue

        for franja in franjas:
            inicio_h, fin_h = franja

            hora_actual = time(inicio_h, 0)
            hora_fin = time(fin_h, 0)

            while hora_actual < hora_fin:

                exists = db.query(HorarioBase).filter_by(
                    dia_semana=dia,
                    hora=hora_actual,
                    barberia_id=barberia_id
                ).first()

                if not exists:
                    db.add(HorarioBase(
                        dia_semana=dia,
                        hora=hora_actual,
                        barberia_id=barberia_id
                    ))

                # 🔥 usar duración real
                hora_actual = (
                    datetime.combine(date.today(), hora_actual)
                    + timedelta(minutes=intervalo)
                ).time()

    db.commit()


# =========================
# 2️⃣ AGENDA POR BARBERO
# =========================
def generar_agenda_barbero(barbero_id: int, barberia_id: int):
    db = SessionLocal()

    hoy = date.today()

    bases = db.query(HorarioBase).filter_by(
        barberia_id=barberia_id
    ).all()

    bases_por_dia = {}
    for base in bases:
        bases_por_dia.setdefault(base.dia_semana, []).append(base)

    nuevos = []

    for i in range(365):
        fecha = hoy + timedelta(days=i)
        dia = dia_espanol(fecha)

        for base in bases_por_dia.get(dia, []):
            nuevos.append({
                "fecha": fecha,
                "hora": base.hora,
                "disponible": True,
                "barbero_id": barbero_id,
                "barberia_id": barberia_id
            })

    if nuevos:
        stmt = insert(Horario).values(nuevos)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["fecha", "hora", "barbero_id"]
        )

        db.execute(stmt)
        db.commit()

    db.close()


# =========================
# 3️⃣ AGENDA PARA TODA LA BARBERÍA
# =========================
def generar_agenda_barberia(barberia_id: int):
    db = SessionLocal()

    barberos = db.query(Usuario).filter(
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin]),
        Usuario.barberia_id == barberia_id
    ).all()

    db.close()

    for barbero in barberos:
        generar_agenda_barbero(barbero.id, barberia_id)
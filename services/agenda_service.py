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

FRANJAS = {
    "martes":   [(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "miercoles":[(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "jueves":   [(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "viernes":  [(time(10,0), time(14,0)), (time(15,0), time(20,0))],
    "sabado":   [(time(10,0), time(14,0)), (time(15,0), time(20,0))],
}

INTERVALO = 30


def dia_espanol(fecha: date):
    return DIAS[fecha.strftime("%A").lower()]


# =========================
# 1️⃣ HORARIOS BASE
# =========================
def generar_horarios_base(barberia_id: int, db: Session):
    barberia = db.query(Barberia).filter_by(id=barberia_id).first()
    if not barberia:
        raise Exception("La barbería no existe")

    for dia, franjas in FRANJAS.items():
        for inicio, fin in franjas:
            hora_actual = inicio

            while hora_actual < fin:
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

                hora_actual = (
                    datetime.combine(date.today(), hora_actual)
                    + timedelta(minutes=INTERVALO)
                ).time()

    db.commit()  # ✔ usar la misma sesión


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
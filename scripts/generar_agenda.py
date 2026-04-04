import sys
import os
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from datetime import date, datetime, time, timedelta
from database import SessionLocal
from models import Horario, HorarioBase, RolEnum, Usuario

# ========================
# CONFIG
# ========================

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

FRANJAS = {
    "martes":   [(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "miercoles":[(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "jueves":   [(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "viernes":  [(time(10,0), time(14,0)), (time(15,0), time(20,0))],
    "sabado":   [(time(10,0), time(14,0)), (time(15,0), time(20,0))],
}

INTERVALO = 30  # minutos

db = SessionLocal()

# ========================
# 1️⃣ Generar horarios base si no existen
# ========================

for dia, franjas in FRANJAS.items():
    for inicio, fin in franjas:
        hora_actual = inicio
        while hora_actual < fin:
            exists = db.query(HorarioBase).filter_by(dia_semana=dia, hora=hora_actual).first()
            if not exists:
                db.add(HorarioBase(dia_semana=dia, hora=hora_actual))
            hora_actual = (datetime.combine(date.today(), hora_actual) + timedelta(minutes=INTERVALO)).time()

db.commit()
print("✅ Horarios base generados/validados")

# ========================
# 2️⃣ Generar horarios reales para cada barbero (1 año)
# ========================

hoy = date.today()

barberos = db.query(Usuario).filter(
    Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
).all()

print("🔢 Cantidad barberos:", len(barberos))

# 🔥 Traemos todos los horarios base UNA sola vez
bases_por_dia = {}

todas_bases = db.query(HorarioBase).all()
for base in todas_bases:
    bases_por_dia.setdefault(base.dia_semana, []).append(base)

nuevos = []

for barbero in barberos:
    for i in range(365):
        fecha = hoy + timedelta(days=i)
        dia = dia_espanol(fecha)

        bases = bases_por_dia.get(dia, [])

        for base in bases:
            nuevos.append(
                Horario(
                    fecha=fecha,
                    hora=base.hora,
                    disponible=True,
                    barbero_id=barbero.id
                )
            )

print("🧮 Cantidad de horarios a insertar:", len(nuevos))

stmt = insert(Horario).values([
    {
        "fecha": h.fecha,
        "hora": h.hora,
        "disponible": h.disponible,
        "barbero_id": h.barbero_id,
    }
    for h in nuevos
])

stmt = stmt.on_conflict_do_nothing(
    index_elements=["fecha", "hora", "barbero_id"]
)

db.execute(stmt)
db.commit()
db.close()

print("✅ Horarios generados para todos los barberos actuales")
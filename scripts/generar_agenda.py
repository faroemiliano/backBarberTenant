import sys
import os
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from datetime import date, datetime, time, timedelta
from database import SesionLocal
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

db = SesionLocal()

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
barberos = db.query(Usuario).filter(Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])).all()

for barbero in barberos:
    for i in range(365):
        fecha = hoy + timedelta(days=i)
        dia = dia_espanol(fecha)

        bases = db.query(HorarioBase).filter_by(dia_semana=dia).all()
        for base in bases:
            exists = db.query(Horario).filter_by(
                fecha=fecha, hora=base.hora, barbero_id=barbero.id
            ).first()
            if not exists:
                db.add(Horario(
                    fecha=fecha,
                    hora=base.hora,
                    disponible=True,
                    barbero_id=barbero.id
                ))

db.commit()
db.close()
print("✅ Horarios generados para todos los barberos actuales")
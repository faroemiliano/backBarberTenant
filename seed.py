import os
from datetime import datetime, timedelta
import random

from database import SessionLocal
from models import Usuario, Servicio, Turno

# =====================
# CONFIG
# =====================
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "faroemiliano@gmail.com")
ADMIN_NAME = "Administrador"
SERVICIOS_PREDEFINIDOS = [
    {"nombre": "Corte de cabello", "precio": 1500},
    {"nombre": "Barba", "precio": 1000},
    {"nombre": "Corte + Barba", "precio": 2300},
    {"nombre": "Peinados especiales", "precio": 2000},
]

HORAS_DISPONIBLES = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]

# =====================
# INICIAR SESIÓN DB
# =====================
db = SessionLocal()

# =====================
# CREAR ADMIN SI NO EXISTE
# =====================
admin = db.query(Usuario).filter_by(email=ADMIN_EMAIL).first()
if not admin:
    admin = Usuario(nombre=ADMIN_NAME, email=ADMIN_EMAIL, is_admin=True)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    print("✅ Usuario admin creado")
else:
    print("⚠️ Admin ya existe")

# =====================
# CREAR SERVICIOS
# =====================
for s in SERVICIOS_PREDEFINIDOS:
    servicio = db.query(Servicio).filter_by(nombre=s["nombre"]).first()
    if not servicio:
        servicio = Servicio(nombre=s["nombre"], precio=s["precio"])
        db.add(servicio)
db.commit()
print("✅ Servicios creados o confirmados")

# =====================
# GENERAR TURNOS PARA EL MES ACTUAL
# =====================
hoy = datetime.now()
inicio_mes = hoy.replace(day=1)
fin_mes = (inicio_mes.replace(month=inicio_mes.month % 12 + 1, day=1) - timedelta(days=1))

servicios = db.query(Servicio).all()

fecha = inicio_mes
while fecha <= fin_mes:
    # 2-3 turnos por día
    for _ in range(random.randint(2, 3)):
        hora = random.choice(HORAS_DISPONIBLES)
        servicio = random.choice(servicios)
        turno = Turno(
            nombre_cliente=f"Cliente {random.randint(1,100)}",
            fecha=fecha.date(),
            hora=hora,
            servicio_id=servicio.id
        )
        db.add(turno)
    fecha += timedelta(days=1)

db.commit()
db.close()
print("✅ Turnos generados para todo el mes")

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Usuario
from werkzeug.security import generate_password_hash
import os

# ---------------------
# Configuración
# ---------------------
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")  # Email del dueño real
ADMIN_NOMBRE = os.getenv("ADMIN_NOMBRE", "Dueño")  # Nombre opcional
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "cambiar123")  # Solo si hay login local

# Email del usuario que ya estaba como admin y queremos desactivar
MI_EMAIL = os.getenv("MI_EMAIL", "tu_email@ejemplo.com")

# ---------------------
# Conexión DB
# ---------------------
db: Session = SessionLocal()

try:
    # 1️⃣ Desactivar tu usuario si existe
    mi_usuario = db.query(Usuario).filter_by(email=MI_EMAIL).first()
    if mi_usuario:
        mi_usuario.is_admin = False
        db.commit()
        print(f"{MI_EMAIL} ya no es admin.")

    # 2️⃣ Verificar si el dueño ya existe
    admin_usuario = db.query(Usuario).filter_by(email=ADMIN_EMAIL).first()
    if admin_usuario:
        admin_usuario.is_admin = True
        db.commit()
        print(f"{ADMIN_EMAIL} ahora es admin.")
    else:
        # 3️⃣ Crear nuevo usuario dueño
        nuevo = Usuario(
            nombre=ADMIN_NOMBRE,
            email=ADMIN_EMAIL,
            password=generate_password_hash(ADMIN_PASSWORD),  # útil solo si hay login local
            is_admin=True
        )
        db.add(nuevo)
        db.commit()
        print(f"Cuenta de dueño creada: {ADMIN_EMAIL}")

finally:
    db.close()

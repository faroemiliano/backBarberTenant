import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
print("ENV:", os.environ.get("DATABASE_URL"))
# 🔥 cargar variables del .env (LOCAL)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

print("🔹 Database URL:", DATABASE_URL)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está configurada")

# 🔥 FIX para Render (a veces usa postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SesionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()
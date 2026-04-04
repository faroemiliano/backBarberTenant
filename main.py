from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()
print(os.getenv("ADMIN_EMAIL"))
from database import engine
from models import Base

# Routers
from routers import admin_barberos, auth, barberiaPersonal, barbero_solo, calendario, admin,profesionales, auth_google, admin_servicios, mis_turnos, superadmin

app = FastAPI(title="Barbería API")

# =====================
# RESET SOLO EN DESARROLLO
# =====================
RESET_DB = False
  # ⚠️ poner False en producción

if RESET_DB:
    print("⚠️ Borrando tablas...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tablas eliminadas")

print("📦 Creando tablas...")
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas")




# =====================
# OPENAPI / JWT
# =====================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Barberia API",
        version="1.0",
        description="API de turnos",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# =====================
# CORS
# =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://frontbarberiatenant.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# ROUTERS
# =====================
# 🔥 SUPERADMIN (SaaS control)
app.include_router(barberiaPersonal.router)
app.include_router(superadmin.router)

# Auth / Google / Registro
app.include_router(auth.router, prefix="", tags=["Auth"])
app.include_router(auth_google.router, prefix="", tags=["Auth Google"])

# Calendario y mis turnos (usuario normal)
app.include_router(calendario.router, prefix="", tags=["Calendario"])
app.include_router(mis_turnos.router, prefix="", tags=["Turnos Usuario"])
app.include_router(admin_servicios.router)
app.include_router(profesionales.router)
# =====================
# ADMIN ROUTER
# =====================
# Todas las rutas que usan admin_required o admin.is_admin
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(admin_barberos.router, prefix="/admin", tags=["Admin"])

# =====================
# BARBERO ROUTER
# =====================
# Solo rutas de barbero (ej: /panel-barbero)
app.include_router(barbero_solo.router, prefix="", tags=["Barbero"])
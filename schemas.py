from pydantic import BaseModel
from typing import Optional

class EditarTurno(BaseModel):
    horario_id: Optional[int] = None
    servicio_id: Optional[int] = None
    telefono: Optional[str] = None
    precio: Optional[float] = None

class HorarioOut(BaseModel):
    id: int
    fecha: str  # ISO format
    hora: str   # HH:MM
    disponible: bool

    class Config:
        orm_mode = True     


class CrearBarberiaSchema(BaseModel):
    nombre: str
    slug: str
    admin_email: str
    admin_nombre: str
    
    class Config:
        extra = "forbid"
    
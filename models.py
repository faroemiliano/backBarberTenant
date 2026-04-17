from sqlalchemy import (
    JSON, Column, Integer, String, Boolean, Date, Time, ForeignKey, UniqueConstraint, Index, Float, Enum, text
)
import enum
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# ======================
# ENUM ROL
# ======================
class RolEnum(enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    barbero = "barbero"
    cliente = "cliente"

# ======================
# USUARIO
# ======================
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, index=True )
    password = Column(String, nullable=True)
    rol = Column(Enum(RolEnum),
    nullable=False,
    server_default=text("'cliente'")
)

    barberia_id = Column(Integer, ForeignKey("barberias.id"), nullable=True)
    barberia = relationship("Barberia", back_populates="usuarios")

    # Turnos como cliente
    turnos = relationship("Turno", back_populates="usuario", cascade="all, delete-orphan", foreign_keys="Turno.usuario_id")
    # Turnos como barbero
    turnos_barbero = relationship("Turno", back_populates="barbero", cascade="all, delete-orphan", foreign_keys="Turno.barbero_id")

    __table_args__ = (
        UniqueConstraint("email", "barberia_id", name="uq_email_barberia"),
    )

    def __repr__(self):
        return f"<Usuario {self.id} {self.email} {self.rol}>"

# ======================
# HORARIOS BASE
# ======================
class HorarioBase(Base):
    __tablename__ = "horarios_base"

    id = Column(Integer, primary_key=True)
    dia_semana = Column(String(15), nullable=False)
    hora = Column(Time, nullable=False)

    barberia_id = Column(Integer, ForeignKey("barberias.id"), nullable=False)

    __table_args__ = (UniqueConstraint("dia_semana", "hora", "barberia_id", name="uq_dia_hora_base_barberia"),)

    def __repr__(self):
        return f"<HorarioBase {self.dia_semana} {self.hora}>"

# ======================
# HORARIOS (CALENDARIO)
# ======================
class Horario(Base):
    __tablename__ = "horarios"

    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False, index=True)
    hora = Column(Time, nullable=False)
    disponible = Column(Boolean, nullable=False, default=True)

    barbero_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    barberia_id = Column(Integer, ForeignKey("barberias.id"), nullable=False)
    turno = relationship(
        "Turno",
        back_populates="horario",
        uselist=False,
        cascade="all, delete-orphan",
    )

    barbero = relationship("Usuario")

    __table_args__ = (
        UniqueConstraint("fecha", "hora", "barbero_id", name="uq_fecha_hora_barbero"),
        Index("ix_fecha_disponible", "fecha", "disponible"),
    )

# ======================
# SERVICIOS
# ======================
class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    precio = Column(Float, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

    barberia_id = Column(Integer, ForeignKey("barberias.id"), nullable=False)
    barberia = relationship("Barberia", back_populates="servicios")
    duracion = Column(Integer, nullable=False, default=30)
    turnos = relationship("Turno", back_populates="servicio")

    __table_args__ = (
    UniqueConstraint("nombre", "barberia_id", name="uq_servicio_barberia"),
)
    def __repr__(self):
        return f"<Servicio {self.nombre} ${self.precio}>"

# ======================
# TURNOS
# ======================
class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(30), nullable=False)

    horario_id = Column(Integer, ForeignKey("horarios.id", ondelete="CASCADE"), nullable=False, unique=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    barbero_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False)
    barberia_id = Column(Integer, ForeignKey("barberias.id"), nullable=False)
    precio = Column(Float, nullable=False)

    horario = relationship("Horario", back_populates="turno")
    usuario = relationship("Usuario", back_populates="turnos", foreign_keys=[usuario_id])
    barbero = relationship("Usuario", back_populates="turnos_barbero", foreign_keys=[barbero_id])
    servicio = relationship("Servicio", back_populates="turnos")

    def __repr__(self):
        return f"<Turno {self.id} horario={self.horario_id} usuario={self.usuario_id} barbero={self.barbero_id}>"
    
class Barberia(Base):
    __tablename__ = "barberias"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    activo = Column(Boolean, default=True)

    usuarios = relationship("Usuario", back_populates="barberia", cascade="all, delete-orphan")
    servicios = relationship("Servicio", back_populates="barberia", cascade="all, delete-orphan")

    # Configuración visual
    logo_url = Column(String, nullable=True)
    color_primario = Column(String, default="#000000")
    color_secundario = Column(String, default="#ffffff")
    fondo_url = Column(String, nullable=True)
    footer_texto = Column(String, nullable=True)
    direccion = Column(String, nullable=True)

    # Redes y contacto
    instagram_url = Column(String, nullable=True)
    whatsapp_url = Column(String, nullable=True)
    ubicacion_url = Column(String, nullable=True)  # google maps link
    horarios_texto = Column(String, default="")
    galeria = Column(JSON, default=[])
    fondo_color = Column(String, nullable=True)
    fondo_color_footer = Column(String, nullable=True)
    fondo_color_videos = Column(String, nullable=True)
    fondo_color_navbar = Column(String, nullable=True)

    # cada barberia puede configurar su horario 
    horario_config = Column(JSON, nullable=True)
    duracion = Column(Integer)


class BarberoServicio(Base):
    __tablename__ = "barbero_servicios"

    id = Column(Integer, primary_key=True, index=True)
    barbero_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False)
    barberia_id = Column(Integer, ForeignKey("barberias.id"), nullable=False)
    barbero = relationship("Usuario")
    servicio = relationship("Servicio")
    barberia = relationship("Barberia")
    __table_args__ = (
        UniqueConstraint("barbero_id", "servicio_id", name="uq_barbero_servicio"),
    )
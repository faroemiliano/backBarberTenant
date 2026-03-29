from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import BarberoServicio, Servicio, Usuario, Horario, HorarioBase, RolEnum

INTERVALO = 30  # minutos

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


def generar_horarios_barbero(db: Session, barbero: Usuario, dias_a_generar: int = 365):

    """
    Genera horarios disponibles para un barbero usando HorarioBase.
    """
    hoy = date.today()
    for i in range(dias_a_generar):
        fecha = hoy + timedelta(days=i)
        dia = dia_espanol(fecha)

        bases = db.query(HorarioBase).filter_by(dia_semana=dia,
        barberia_id=barbero.barberia_id  # 🔥 IMPORTANTE
        ).all()

        for base in bases:
            exists = db.query(Horario).filter_by(
                fecha=fecha, hora=base.hora, barbero_id=barbero.id
            ).first()
            if not exists:
                db.add(Horario(
                    fecha=fecha,
                    hora=base.hora,
                    disponible=True,
                    barbero_id=barbero.id,
                    barberia_id=barbero.barberia_id
                ))
    db.commit()

def asignar_servicios_a_barbero(db: Session, barbero: Usuario):
    if not barbero.barberia_id:
        raise Exception("Barbero sin barbería")

    servicios = db.query(Servicio).filter_by(
        barberia_id=barbero.barberia_id
    ).all()

    for s in servicios:
        existe = db.query(BarberoServicio).filter_by(
            barbero_id=barbero.id,
            servicio_id=s.id
        ).first()

        if not existe:
            db.add(BarberoServicio(
                barbero_id=barbero.id,
                servicio_id=s.id
            ))

    db.commit()
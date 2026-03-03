from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import Usuario, Horario, HorarioBase, RolEnum

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
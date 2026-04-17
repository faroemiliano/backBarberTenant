
from datetime import date, datetime, time, timedelta
from sqlalchemy.orm import Session
from models import BarberoServicio, Servicio, Usuario, Horario, HorarioBase, RolEnum

def generar_horarios_barbero(
    db: Session,
    barbero: Usuario,
    dias_filtrados: list[str] = None,
    dias_a_generar: int = 60
):

    hoy = date.today()
    config = barbero.barberia.horario_config or {}
    duracion = barbero.barberia.duracion or 40

    dias_map = {
        0: "lunes",
        1: "martes",
        2: "miercoles",
        3: "jueves",
        4: "viernes",
        5: "sabado",
        6: "domingo",
    }

    for i in range(dias_a_generar):
        fecha = hoy + timedelta(days=i)
        dia_nombre = dias_map[fecha.weekday()]

        # 🔥 ESTA ES LA MAGIA
        if dias_filtrados and dia_nombre not in dias_filtrados:
            continue
        franjas = config.get(dia_nombre, [])
        horas_validas = set()
        # 🔹 CREAR HORAS NUEVAS
        for franja in franjas:
            inicio_h, fin_h = franja

            inicio_dt = datetime.combine(fecha, time(inicio_h, 0))
            fin_dt = datetime.combine(fecha, time(fin_h, 0))

            while inicio_dt < fin_dt:
                hora_actual = inicio_dt.time()

                # 🚫 regla opcional
                if fecha.weekday() in [4, 5] and hora_actual == time(13, 40):
                    inicio_dt += timedelta(minutes=duracion)
                    continue

                horas_validas.add(hora_actual)

                exists = db.query(Horario).filter_by(
                    fecha=fecha,
                    hora=hora_actual,
                    barbero_id=barbero.id
                ).first()

                if not exists:
                    db.add(Horario(
                        fecha=fecha,
                        hora=hora_actual,
                        disponible=True,
                        barbero_id=barbero.id,
                        barberia_id=barbero.barberia_id
                    ))

                inicio_dt += timedelta(minutes=duracion)

        # 🔥 ELIMINAR HORARIOS QUE YA NO EXISTEN (SOLO LIBRES)
        horarios_db = db.query(Horario).filter(
            Horario.fecha == fecha,
            Horario.barbero_id == barbero.id,
            Horario.disponible == True
        ).all()

        for h in horarios_db:
            if h.hora not in horas_validas:
                db.delete(h)

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
                servicio_id=s.id,
                barberia_id=barbero.barberia_id  # 🔹 obligatorio
            ))

    db.commit()
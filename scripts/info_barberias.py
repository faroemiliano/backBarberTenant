import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Barberia

db: Session = SessionLocal()

def upsert_barberia(db: Session,data):
    barberia = db.query(Barberia).filter_by(slug=data["slug"]).first()

    if not barberia:
        barberia = Barberia(slug=data["slug"])
        db.add(barberia)

    # 🔥 SOLO ACTUALIZA LO QUE VAS AGREGANDO
    if "nombre" in data:
        barberia.nombre = data["nombre"]

    if "footer_texto" in data:
        barberia.footer_texto = data["footer_texto"]

    if "ubicacion_url" in data:
        barberia.ubicacion_url = data["ubicacion_url"]

    if "horarios_texto" in data:
        barberia.horarios_texto = data["horarios_texto"]

    if "logo_url" in data:
        barberia.logo_url = data["logo_url"]

    if "color_primario" in data:
        barberia.color_primario = data["color_primario"]

    if "color_secundario" in data:
        barberia.color_secundario = data["color_secundario"]

    if "fondo_url" in data:
        barberia.fondo_url = data["fondo_url"]

    if "instagram_url" in data:
        barberia.instagram_url = data["instagram_url"]

    if "whatsapp_url" in data:
        barberia.whatsapp_url = data["whatsapp_url"]

    if "galeria" in data:
        barberia.galeria = data["galeria"]     
   
    if "fondo_color" in data:
        barberia.fondo_color = data["fondo_color"]    


def datosParticularesBarberias(db: Session):
    # 🔥 YA NO BORRAMOS NADA

    upsert_barberia(db,{
    "slug": "prueba2",
    "nombre": "Demo Barbería",
    "footer_texto": "direccion!!",
    "horarios_texto": "Martes a Jueves: 11-20\nViernes: 10-18",
    "instagram_url": "https://instagram.com/test_prueba2",
    "whatsapp_url": "https://wa.me/222222222",
    "ubicacion_url": "https://maps.google.com/?q=Palermo+Buenos+Aires",
    "fondo_url": "#0f172a",
    "fondo_color": "#ececec",
    "logo_url": "https://res.cloudinary.com/dnsxvwfoc/image/upload/v1775089980/logoBarberPrueba1-Photoroom_rkt1r3.png",
    "galeria": [
        {"tipo": "video", "url": "https://res.cloudinary.com/dnsxvwfoc/video/upload/v1770838550/corte1_nztjrt.mp4", "titulo": "Corte random 1"},
        {"tipo": "video", "url": "https://res.cloudinary.com/dnsxvwfoc/video/upload/v1770838550/corte4_a9vtbk.mp4", "titulo": "Corte random 2"},
        {"tipo": "foto", "url": "https://res.cloudinary.com/.../foto1.jpg", "titulo": "Foto random 1"},
        {"tipo": "video", "url": "https://res.cloudinary.com/dnsxvwfoc/video/upload/v1770838550/corte4_a9vtbk.mp4", "titulo": "Foto random 2"},
    ]
})

    upsert_barberia(db,{
        "slug": "prueba2",
        "nombre": "Prueba 2",
        "footer_texto": "© 2026 Prueba 2",
        "ubicacion_url": "Direccion Prueba 2",
        "horarios_texto": "Lunes a Viernes: 09-18\nSabados: 10-14"
    })

    db.commit()
    print("✅ Barberías creadas / actualizadas")


if __name__ == "__main__":
    datosParticularesBarberias(db)
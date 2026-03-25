from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Barberia

def get_barberia(
    x_barberia: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    print("🔥 x_barberia:", x_barberia)

    if not x_barberia:
        raise HTTPException(status_code=400, detail="Falta x-barberia")

    barberia = db.query(Barberia).filter_by(slug=x_barberia).first()

    if not barberia:
        raise HTTPException(status_code=404, detail="Barberia no encontrada")

    if not barberia.activo:
        raise HTTPException(403, "Barbería bloqueada por falta de pago")

    return barberia
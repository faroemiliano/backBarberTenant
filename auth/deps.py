from dependencias import barberia as barberia_dep
from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from auth.security import SECRET_KEY, ALGORITHM, decode_token
from database import get_db
from models import RolEnum, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# 🔐 Obtener usuario actual
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user_email = payload.get("email")

        if not user_id and not user_email:
            raise HTTPException(status_code=401, detail="Token inválido")

        SUPERADMIN_EMAIL = "faroemiliano@gmail.com"

        # 🔥 SUPERADMIN
        if user_email == SUPERADMIN_EMAIL:
            user = db.query(Usuario).filter_by(email=user_email).first()

            if not user:
                user = Usuario(
                    nombre="SuperAdmin",
                    email=user_email,
                    rol=RolEnum.superadmin,
                    barberia_id=None
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            return user

        # 🔥 USUARIOS NORMALES
        user = db.query(Usuario).filter_by(
            id=int(user_id)
        ).first()

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return user

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 👑 Admin
def admin_required(
    user: Usuario = Depends(get_current_user)
):
    if user.rol != RolEnum.admin:
        raise HTTPException(status_code=403, detail="No autorizado")
    return user


# 💈 Barbero
def barbero_required(
    user: Usuario = Depends(get_current_user)
):
    if user.rol != RolEnum.barbero:
        raise HTTPException(status_code=403, detail="No autorizado")

    return user

def superadmin_required(user: Usuario = Depends(get_current_user)):
    if user.rol != RolEnum.superadmin:
        raise HTTPException(status_code=403, detail="No autorizado")
    return user
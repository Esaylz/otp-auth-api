import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlmodel import SQLModel, Field, Session, create_engine, select


OTP_LIFETIME_MINUTES = 5

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, echo=False)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OTPCode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    code: str
    expires_at: datetime
    is_used: bool = Field(default=False)

class EmailRequest(BaseModel):
    email: EmailStr

class VerifyRequest(BaseModel):
    email: EmailStr
    code: str

class MessageResponse(BaseModel):
    message: str


app = FastAPI(title="Авторизация через email OTP-коды и JWT-токены")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def generate_otp_code() -> str:
    return "".join(random.choices(string.digits, k=6))

def issue_new_otp(user_id: int, session: Session) -> str:
    old_codes = session.exec(
        select(OTPCode).where(OTPCode.user_id == user_id, OTPCode.is_used == False)  
    ).all()
    for old in old_codes:
        old.is_used = True
        session.add(old)

    code = generate_otp_code()
    otp = OTPCode(
        user_id=user_id,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_LIFETIME_MINUTES),
        is_used=False,
    )
    session.add(otp)
    session.commit()

    print(f"[OTP] Код для user_id={user_id}: {code} (действителен {OTP_LIFETIME_MINUTES} мин.)")
    return code

def verify_otp(user_id: int, code: str, session: Session) -> OTPCode:
    otp = session.exec(
        select(OTPCode)
        .where(OTPCode.user_id == user_id, OTPCode.code == code)
        .order_by(OTPCode.id.desc())
    ).first()

    if not otp:
        raise HTTPException(status_code=400, detail="Неверный код")
    if otp.is_used:
        raise HTTPException(status_code=400, detail="Код уже использован")

    expires_at = otp.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Срок действия кода истёк")

    otp.is_used = True
    session.add(otp)
    session.commit()
    return otp


@app.post("/auth/register", response_model=MessageResponse)
def register(data: EmailRequest, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    user = User(email=data.email, is_verified=False)
    session.add(user)
    session.commit()
    session.refresh(user)

    issue_new_otp(user.id, session)
    return MessageResponse(message="Код подтверждения отправлен на email")


@app.post("/auth/verify", response_model=MessageResponse)
def verify(data: VerifyRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    verify_otp(user.id, data.code, session)

    user.is_verified = True
    session.add(user)
    session.commit()
    return MessageResponse(message="Email успешно подтверждён")


@app.post("/auth/login", response_model=MessageResponse)
def login(data: EmailRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not user.is_verified:
        raise HTTPException(status_code=400, detail="Email ещё не подтверждён")

    issue_new_otp(user.id, session)
    return MessageResponse(message="Код для входа отправлен на email")


@app.post("/auth/confirm", response_model=MessageResponse)
def confirm(data: VerifyRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    verify_otp(user.id, data.code, session)

    return MessageResponse(message="Вход подтверждён")


@app.get("/auth/me", response_model=MessageResponse)
def me():
    return MessageResponse(message="")


@app.post("/auth/logout", response_model=MessageResponse)
def logout():
    return MessageResponse(message="")

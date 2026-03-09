"""
╔══════════════════════════════════════════════════════╗
║        VitaCore — Backend FastAPI (fichier unique)   ║
║  Démarrage : uvicorn backend:app --reload --port 8040║
╚══════════════════════════════════════════════════════╝

Dépendances (pip install) :
  fastapi uvicorn[standard] sqlalchemy psycopg2-binary
  python-jose[cryptography] passlib[bcrypt] pydantic[email]
  python-multipart python-dotenv
"""

import os
import enum
from datetime import datetime, timedelta
from typing import Optional, List, Any

# ─── FastAPI ──────────────────────────────────────────
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ─── SQLAlchemy ───────────────────────────────────────
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.sql import func

# ─── Auth & Validation ────────────────────────────────
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field


from anthropic import Anthropic
# En haut de backend.py ajoutez ces deux lignes
from dotenv import load_dotenv
load_dotenv()  

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ══════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════
DATABASE_URL  = os.getenv("DATABASE_URL",  "postgresql://postgres:beauty@localhost:5432/vitacore_db")
SECRET_KEY    = os.getenv("SECRET_KEY",    "vitacore-secret-key-changez-en-production-2024!")
ALGORITHM     = "HS256"
TOKEN_EXPIRE  = 24 * 7   # heures

# ══════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════
engine       = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ══════════════════════════════════════════════════════
#  MODELS (SQLAlchemy)
# ══════════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    first_name      = Column(String(100), nullable=False)
    last_name       = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    health_profile = relationship("HealthProfile", back_populates="user",  uselist=False, cascade="all, delete-orphan")
    diseases       = relationship("Disease",       back_populates="user",  cascade="all, delete-orphan")
    medications    = relationship("Medication",    back_populates="user",  cascade="all, delete-orphan")
    appointments   = relationship("Appointment",   back_populates="user",  cascade="all, delete-orphan")
    health_history = relationship("HealthHistory", back_populates="user",  cascade="all, delete-orphan")


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Identité
    date_of_birth   = Column(String(20))
    gender          = Column(String(20))
    blood_type      = Column(String(5))
    nationality     = Column(String(100))
    occupation      = Column(String(150))
    marital_status  = Column(String(30))

    # Contact d'urgence
    emergency_name     = Column(String(150))
    emergency_relation = Column(String(100))
    emergency_phone    = Column(String(30))

    # Médecin traitant
    doctor_name    = Column(String(150))
    doctor_phone   = Column(String(30))
    doctor_address = Column(String(255))

    # Mensurations
    weight              = Column(Float)
    height              = Column(Float)
    waist_circumference = Column(Float)
    hip_circumference   = Column(Float)

    # Cardiovasculaire
    blood_pressure_systolic  = Column(Integer)
    blood_pressure_diastolic = Column(Integer)
    heart_rate               = Column(Integer)

    # Bilan biologique
    blood_sugar       = Column(Float)
    cholesterol_total = Column(Float)
    cholesterol_hdl   = Column(Float)
    cholesterol_ldl   = Column(Float)
    triglycerides     = Column(Float)
    hemoglobin        = Column(Float)
    creatinine        = Column(Float)
    temperature       = Column(Float)
    last_blood_test   = Column(String(20))

    # Allergies & antécédents
    allergies       = Column(JSON)
    allergy_notes   = Column(Text)
    family_history  = Column(JSON)

    # Santé mentale
    mental_health_history = Column(JSON)
    stress_level          = Column(Integer)

    # Hospitalisations
    hospitalized          = Column(String(5))
    hospitalization_notes = Column(Text)
    last_checkup          = Column(String(20))

    # Mode de vie — Tabac/Alcool
    smoking_status      = Column(String(30))
    cigarettes_per_day  = Column(Integer)
    smoking_years       = Column(Integer)
    alcohol_consumption = Column(String(30))

    # Mode de vie — Sport
    physical_activity  = Column(String(30))
    exercise_frequency = Column(Integer)
    exercise_duration  = Column(Integer)
    sports             = Column(JSON)

    # Alimentation
    diet_types    = Column(JSON)
    diet_quality  = Column(String(20))
    water_intake  = Column(Float)
    coffee_per_day = Column(Integer)

    # Sommeil
    sleep_hours          = Column(Float)
    sleep_quality        = Column(String(20))
    sleep_disorder_types = Column(JSON)

    # Suppléments, objectifs, notes
    supplements      = Column(JSON)
    health_goals     = Column(JSON)
    additional_notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="health_profile")


class Disease(Base):
    __tablename__ = "diseases"

    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name              = Column(String(200), nullable=False)
    severity          = Column(String(30), default="mild")
    diagnosed_year    = Column(Integer)
    current_treatment = Column(String(500))
    is_active         = Column(Boolean, default=True)
    notes             = Column(Text)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="diseases")


class Medication(Base):
    __tablename__ = "medications"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name         = Column(String(200), nullable=False)
    dosage       = Column(String(100))
    frequency    = Column(String(50))
    prescribed_by = Column(String(150))
    start_date   = Column(String(20))
    end_date     = Column(String(20))
    is_active    = Column(Boolean, default=True)
    notes        = Column(Text)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="medications")


class Appointment(Base):
    __tablename__ = "appointments"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title            = Column(String(200), nullable=False)
    doctor_name      = Column(String(150))
    specialty        = Column(String(100))
    appointment_date = Column(DateTime(timezone=True))
    location         = Column(String(255))
    notes            = Column(Text)
    status           = Column(String(30), default="scheduled")
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="appointments")


class HealthHistory(Base):
    __tablename__ = "health_history"

    id                       = Column(Integer, primary_key=True, index=True)
    user_id                  = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    health_score             = Column(Integer)
    weight                   = Column(Float)
    blood_pressure_systolic  = Column(Integer)
    blood_pressure_diastolic = Column(Integer)
    heart_rate               = Column(Integer)
    blood_sugar              = Column(Float)
    recorded_at              = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="health_history")


# ══════════════════════════════════════════════════════
#  SCHEMAS (Pydantic)
# ══════════════════════════════════════════════════════

# ── Auth ──────────────────────────────────────────────
class UserRegister(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name:  str = Field(..., min_length=1, max_length=100)
    email:      EmailStr
    password:   str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email:    EmailStr
    password: str

class UserOut(BaseModel):
    id:         int
    email:      str
    first_name: str
    last_name:  str
    is_active:  bool
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserOut

# ── Health ────────────────────────────────────────────
class HealthProfileCreate(BaseModel):
    date_of_birth:    Optional[str]   = None
    gender:           Optional[str]   = None
    blood_type:       Optional[str]   = None
    nationality:      Optional[str]   = None
    occupation:       Optional[str]   = None
    marital_status:   Optional[str]   = None
    emergency_name:   Optional[str]   = None
    emergency_relation: Optional[str] = None
    emergency_phone:  Optional[str]   = None
    doctor_name:      Optional[str]   = None
    doctor_phone:     Optional[str]   = None
    doctor_address:   Optional[str]   = None
    weight:           Optional[float] = None
    height:           Optional[float] = None
    waist_circumference: Optional[float] = None
    hip_circumference:   Optional[float] = None
    blood_pressure_systolic:  Optional[int]   = None
    blood_pressure_diastolic: Optional[int]   = None
    heart_rate:       Optional[int]   = None
    blood_sugar:      Optional[float] = None
    cholesterol_total: Optional[float] = None
    cholesterol_hdl:  Optional[float] = None
    cholesterol_ldl:  Optional[float] = None
    triglycerides:    Optional[float] = None
    hemoglobin:       Optional[float] = None
    creatinine:       Optional[float] = None
    temperature:      Optional[float] = None
    last_blood_test:  Optional[str]   = None
    allergies:        Optional[List[str]] = None
    allergy_notes:    Optional[str]   = None
    family_history:   Optional[List[str]] = None
    mental_health_history: Optional[List[str]] = None
    stress_level:     Optional[int]   = Field(None, ge=1, le=5)
    hospitalized:     Optional[str]   = None
    hospitalization_notes: Optional[str] = None
    last_checkup:     Optional[str]   = None
    smoking_status:   Optional[str]   = None
    cigarettes_per_day: Optional[int] = None
    smoking_years:    Optional[int]   = None
    alcohol_consumption: Optional[str] = None
    physical_activity:   Optional[str] = None
    exercise_frequency:  Optional[int] = None
    exercise_duration:   Optional[int] = None
    sports:           Optional[List[str]] = None
    diet_types:       Optional[List[str]] = None
    diet_quality:     Optional[str]   = None
    water_intake:     Optional[float] = None
    coffee_per_day:   Optional[int]   = None
    sleep_hours:      Optional[float] = None
    sleep_quality:    Optional[str]   = None
    sleep_disorder_types: Optional[List[str]] = None
    supplements:      Optional[List[str]] = None
    health_goals:     Optional[List[str]] = None
    additional_notes: Optional[str]   = None
    diseases:         Optional[List[Any]] = None
    medications:      Optional[List[Any]] = None

class DiseaseCreate(BaseModel):
    name:              str  = Field(..., min_length=1, max_length=200)
    severity:          Optional[str]  = "mild"
    diagnosed_year:    Optional[int]  = None
    current_treatment: Optional[str]  = None
    notes:             Optional[str]  = None

class DiseaseOut(DiseaseCreate):
    id:         int
    user_id:    int
    is_active:  bool
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class MedicationCreate(BaseModel):
    name:          str = Field(..., min_length=1, max_length=200)
    dosage:        Optional[str] = None
    frequency:     Optional[str] = None
    prescribed_by: Optional[str] = None
    start_date:    Optional[str] = None
    end_date:      Optional[str] = None
    notes:         Optional[str] = None

class MedicationOut(MedicationCreate):
    id:         int
    user_id:    int
    is_active:  bool
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class AppointmentCreate(BaseModel):
    title:            str = Field(..., min_length=1)
    doctor_name:      Optional[str]      = None
    specialty:        Optional[str]      = None
    appointment_date: Optional[datetime] = None
    location:         Optional[str]      = None
    notes:            Optional[str]      = None

class AppointmentOut(AppointmentCreate):
    id:         int
    user_id:    int
    status:     str
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# ══════════════════════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════════════════════
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security    = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db:    Session                       = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user

# ══════════════════════════════════════════════════════
#  SCORE DE SANTÉ
# ══════════════════════════════════════════════════════
def calculate_health_score(profile: HealthProfile, diseases: list) -> int:
    """Calcule un score de santé sur 100."""
    score = 0

    # IMC (20 pts)
    if profile.weight and profile.height:
        bmi = profile.weight / ((profile.height / 100) ** 2)
        if 18.5 <= bmi < 25:   score += 20
        elif 17 <= bmi < 27:   score += 14
        elif bmi < 17 or 27 <= bmi < 30: score += 8
        else:                   score += 3

    # Tension artérielle (20 pts)
    if profile.blood_pressure_systolic and profile.blood_pressure_diastolic:
        s, d = profile.blood_pressure_systolic, profile.blood_pressure_diastolic
        if s < 120 and d < 80:     score += 20
        elif s < 130 and d < 85:   score += 15
        elif s < 140 and d < 90:   score += 10
        else:                       score += 4

    # Glycémie (15 pts)
    if profile.blood_sugar:
        bs = profile.blood_sugar
        if bs < 100:   score += 15
        elif bs < 110: score += 10
        elif bs < 126: score += 6
        else:           score += 2

    # Fréquence cardiaque (10 pts)
    if profile.heart_rate:
        hr = profile.heart_rate
        if 60 <= hr <= 80:   score += 10
        elif 55 <= hr <= 95: score += 7
        else:                 score += 3

    # Cholestérol (10 pts)
    if profile.cholesterol_total:
        ch = profile.cholesterol_total
        if ch < 180:   score += 10
        elif ch < 200: score += 7
        elif ch < 240: score += 4
        else:           score += 1

    # Mode de vie (15 pts)
    lpts = 0
    if profile.smoking_status in ("never", None): lpts += 4
    elif profile.smoking_status == "ex":           lpts += 3
    elif profile.smoking_status == "occasional":   lpts += 2
    if profile.physical_activity in ("active", "very_active"): lpts += 4
    elif profile.physical_activity == "moderate":              lpts += 3
    elif profile.physical_activity == "light":                 lpts += 2
    if profile.sleep_hours and 7 <= profile.sleep_hours <= 9: lpts += 4
    elif profile.sleep_hours and 6 <= profile.sleep_hours < 7: lpts += 2
    if profile.diet_quality in ("good", "excellent"):  lpts += 3
    elif profile.diet_quality == "average":            lpts += 1
    score += min(lpts, 15)

    # Pathologies (malus, 10 pts)
    pts = 10
    for d in diseases:
        if d.severity == "severe":   pts -= 4
        elif d.severity == "chronic": pts -= 3
        elif d.severity == "moderate": pts -= 2
        else:                          pts -= 1
    score += max(pts, 0)

    return min(score, 100)

# ══════════════════════════════════════════════════════
#  APPLICATION FASTAPI
# ══════════════════════════════════════════════════════
app = FastAPI(
    title="VitaCore API",
    description="API backend de la plateforme de santé VitaCore",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Créer les tables au démarrage
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/", include_in_schema=False)
def root():
    return {"message": "VitaCore API v1.0", "docs": "/api/docs"}

@app.get("/api/health-check")
def health_check():
    return {"status": "ok"}

# ══════════════════════════════════════════════════════
#  ROUTES — AUTHENTIFICATION
# ══════════════════════════════════════════════════════

@app.post("/api/v1/auth/register", response_model=TokenResponse, status_code=201, tags=["Auth"])
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Inscription d'un nouvel utilisateur."""
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(400, "Cet email est déjà utilisé")
    user = User(
        email=data.email.lower(),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        hashed_password=hash_password(data.password),
    )
    db.add(user); db.commit(); db.refresh(user)
    return TokenResponse(access_token=create_token(user.id), user=UserOut.from_orm(user))


@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Connexion utilisateur."""
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(403, "Compte désactivé")
    return TokenResponse(access_token=create_token(user.id), user=UserOut.from_orm(user))


@app.get("/api/v1/auth/me", response_model=UserOut, tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    """Profil de l'utilisateur connecté."""
    return current_user


@app.put("/api/v1/auth/me", response_model=UserOut, tags=["Auth"])
def update_me(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mettre à jour prénom/nom."""
    for k in ("first_name", "last_name"):
        if data.get(k):
            setattr(current_user, k, data[k])
    db.commit(); db.refresh(current_user)
    return current_user


@app.post("/api/v1/auth/change-password", tags=["Auth"])
def change_password(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Changer le mot de passe."""
    if not verify_password(data.get("current_password", ""), current_user.hashed_password):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    if len(data.get("new_password", "")) < 8:
        raise HTTPException(400, "Le nouveau mot de passe doit faire au moins 8 caractères")
    current_user.hashed_password = hash_password(data["new_password"])
    db.commit()
    return {"message": "Mot de passe modifié"}

# ══════════════════════════════════════════════════════
#  ROUTES — SANTÉ
# ══════════════════════════════════════════════════════

@app.post("/api/v1/health/profile", tags=["Santé"])
def save_profile(
    data: HealthProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Créer ou mettre à jour le bilan de santé complet."""
    diseases_data = data.diseases or []
    meds_data     = data.medications or []
    profile_dict  = data.dict(exclude={"diseases", "medications"}, exclude_none=True)

    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if profile:
        for k, v in profile_dict.items():
            setattr(profile, k, v)
        profile.updated_at = datetime.utcnow()
    else:
        profile = HealthProfile(user_id=current_user.id, **profile_dict)
        db.add(profile)
    db.flush()

    # Remplacer les maladies
    db.query(Disease).filter(Disease.user_id == current_user.id).delete()
    for d in diseases_data:
        if d.get("name"):
            db.add(Disease(
                user_id=current_user.id, name=d["name"],
                severity=d.get("severity", "mild"),
                diagnosed_year=d.get("diagnosed_year"),
                current_treatment=d.get("current_treatment"),
            ))

    # Remplacer les médicaments
    db.query(Medication).filter(Medication.user_id == current_user.id).delete()
    for m in meds_data:
        if m.get("name"):
            db.add(Medication(
                user_id=current_user.id, name=m["name"],
                dosage=m.get("dosage"), frequency=m.get("frequency"),
                prescribed_by=m.get("prescribed_by"),
            ))

    db.commit(); db.refresh(profile)

    # Enregistrer snapshot historique
    diseases = db.query(Disease).filter(Disease.user_id == current_user.id).all()
    score = calculate_health_score(profile, diseases)
    db.add(HealthHistory(
        user_id=current_user.id, health_score=score,
        weight=profile.weight, blood_pressure_systolic=profile.blood_pressure_systolic,
        blood_pressure_diastolic=profile.blood_pressure_diastolic,
        heart_rate=profile.heart_rate, blood_sugar=profile.blood_sugar,
    ))
    db.commit()
    return {"message": "Bilan enregistré", "health_score": score}


@app.put("/api/v1/health/profile", tags=["Santé"])
def update_profile(data: HealthProfileCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return save_profile(data, current_user, db)


@app.get("/api/v1/health/profile", tags=["Santé"])
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obtenir le bilan de santé."""
    return db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()


@app.get("/api/v1/health/dashboard", tags=["Santé"])
def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Dashboard complet : profil, maladies, médicaments, score, tendance."""
    profile     = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    diseases    = db.query(Disease).filter(Disease.user_id == current_user.id, Disease.is_active == True).all()
    medications = db.query(Medication).filter(Medication.user_id == current_user.id, Medication.is_active == True).all()
    appointments = db.query(Appointment).filter(
        Appointment.user_id == current_user.id, Appointment.status == "scheduled"
    ).order_by(Appointment.appointment_date).limit(5).all()

    health_score = calculate_health_score(profile, diseases) if profile else 0

    history = db.query(HealthHistory).filter(HealthHistory.user_id == current_user.id
        ).order_by(HealthHistory.recorded_at.desc()).limit(6).all()
    score_trend = None
    if len(history) > 1:
        history.reverse()
        score_trend = {
            "labels": [h.recorded_at.strftime("%b") for h in history],
            "values": [h.health_score for h in history],
        }

    return {
        "profile": profile, "diseases": diseases, "medications": medications,
        "appointments": appointments, "health_score": health_score, "score_trend": score_trend,
    }


# ── Maladies ──────────────────────────────────────────
@app.get("/api/v1/health/diseases",     response_model=List[DiseaseOut], tags=["Santé"])
def get_diseases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Disease).filter(Disease.user_id == current_user.id).all()

@app.post("/api/v1/health/diseases",    response_model=DiseaseOut, status_code=201, tags=["Santé"])
def add_disease(data: DiseaseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = Disease(user_id=current_user.id, **data.dict()); db.add(d); db.commit(); db.refresh(d); return d

@app.put("/api/v1/health/diseases/{did}", response_model=DiseaseOut, tags=["Santé"])
def update_disease(did: int, data: DiseaseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = db.query(Disease).filter(Disease.id == did, Disease.user_id == current_user.id).first()
    if not d: raise HTTPException(404, "Introuvable")
    for k, v in data.dict(exclude_none=True).items(): setattr(d, k, v)
    db.commit(); db.refresh(d); return d

@app.delete("/api/v1/health/diseases/{did}", tags=["Santé"])
def delete_disease(did: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = db.query(Disease).filter(Disease.id == did, Disease.user_id == current_user.id).first()
    if not d: raise HTTPException(404, "Introuvable")
    db.delete(d); db.commit(); return {"message": "Supprimée"}


# ── Médicaments ───────────────────────────────────────
@app.get("/api/v1/health/medications",     response_model=List[MedicationOut], tags=["Santé"])
def get_medications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Medication).filter(Medication.user_id == current_user.id).all()

@app.post("/api/v1/health/medications",    response_model=MedicationOut, status_code=201, tags=["Santé"])
def add_medication(data: MedicationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = Medication(user_id=current_user.id, **data.dict()); db.add(m); db.commit(); db.refresh(m); return m

@app.delete("/api/v1/health/medications/{mid}", tags=["Santé"])
def delete_medication(mid: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Medication).filter(Medication.id == mid, Medication.user_id == current_user.id).first()
    if not m: raise HTTPException(404, "Introuvable")
    db.delete(m); db.commit(); return {"message": "Supprimé"}


# ── Rendez-vous ───────────────────────────────────────
@app.get("/api/v1/health/appointments",     response_model=List[AppointmentOut], tags=["Santé"])
def get_appointments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Appointment).filter(Appointment.user_id == current_user.id
        ).order_by(Appointment.appointment_date).all()

@app.post("/api/v1/health/appointments",    response_model=AppointmentOut, status_code=201, tags=["Santé"])
def add_appointment(data: AppointmentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = Appointment(user_id=current_user.id, **data.dict()); db.add(a); db.commit(); db.refresh(a); return a

@app.put("/api/v1/health/appointments/{aid}/status", tags=["Santé"])
def update_appointment(aid: int, data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(Appointment).filter(Appointment.id == aid, Appointment.user_id == current_user.id).first()
    if not a: raise HTTPException(404, "Introuvable")
    if data.get("status") in ("scheduled", "completed", "cancelled"):
        a.status = data["status"]
    db.commit(); return {"message": "Mis à jour"}


# ── Historique ────────────────────────────────────────
@app.get("/api/v1/health/history", tags=["Santé"])
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(HealthHistory).filter(HealthHistory.user_id == current_user.id
        ).order_by(HealthHistory.recorded_at.desc()).limit(50).all()





import httpx
import os
from fastapi import Request, Depends
from fastapi.responses import StreamingResponse

@app.post("/api/v1/ai/chat")
async def ai_proxy(request: Request, current_user = Depends(get_current_user)):
    body = await request.json()
    
    # Forcer stream: true
    body["stream"] = True

    async def stream():
        async with httpx.AsyncClient(timeout=120) as http:
            async with http.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": os.environ.get("ANTHROPIC_API_KEY"),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=body,
            ) as resp:
                print("STATUS ANTHROPIC:", resp.status_code)  # ← debug
                async for line in resp.aiter_lines():
                    print("CHUNK:", line[:80])  # ← debug, voir ce qui arrive
                    if line:
                        yield f"{line}\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )
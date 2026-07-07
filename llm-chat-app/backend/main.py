"""
Backend FastAPI : authentification (inscription / connexion) + chat LLM
propulsé par Gemma (modèle open source de Google) exécuté localement via Ollama.

Prérequis (une seule fois) :
    1. Installer Ollama : https://ollama.com/download
    2. Télécharger le modèle :  ollama pull gemma3:1b

Lancement :
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

import logging

logging.basicConfig(
    filename="security.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
security_logger = logging.getLogger("security")

from datetime import datetime, timedelta

# Stocke les tentatives ratées par email : { email: {"count": int, "blocked_until": datetime|None} }
LOGIN_ATTEMPTS = {}

def check_login_bloque(email: str):
    """Vérifie si cet email est actuellement bloqué. Lève une exception si oui."""
    entry = LOGIN_ATTEMPTS.get(email)
    if entry and entry["blocked_until"] and datetime.now() < entry["blocked_until"]:
        minutes_restantes = int((entry["blocked_until"] - datetime.now()).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Trop de tentatives échouées. Réessayez dans {minutes_restantes} minute(s).",
        )

def enregistrer_echec(email: str):
    """Incrémente le compteur d'échecs et bloque si le seuil est atteint."""
    entry = LOGIN_ATTEMPTS.setdefault(email, {"count": 0, "blocked_until": None})
    entry["count"] += 1

    if entry["count"] >= 10:
        entry["blocked_until"] = datetime.now() + timedelta(hours=1)
    elif entry["count"] >= 5:
        entry["blocked_until"] = datetime.now() + timedelta(minutes=10)

def reset_tentatives(email: str):
    """Remet le compteur à zéro après une connexion réussie."""
    LOGIN_ATTEMPTS.pop(email, None)

# ─────────────────────────── Configuration ───────────────────────────

DB_PATH = os.getenv("DB_PATH", "app.db")
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))  # fixez-le en prod !
JWT_ALGO = "HS256"
TOKEN_TTL_SECONDS = 60 * 60 * 24  # 24 h

# ── Choix du fournisseur LLM ──
# LLM_PROVIDER = "ollama" (local, défaut) ou "gemini" (cloud Google)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# Option locale : Ollama — aucun compte ni clé API nécessaire
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")  # ex. gemma3:1b, gemma3:4b, gemma3:12b

# Option cloud : API Gemini — clé gratuite sur https://aistudio.google.com/apikey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

app = FastAPI(title="LLM Chat API")

# CORS : autorise le frontend React en développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ─────────────────────────── Base de données ───────────────────────────


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )


init_db()

# ─────────────────────────── Mots de passe ───────────────────────────


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 200_000
    ).hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), expected_hash)


# ─────────────────────────── JWT ───────────────────────────


def create_token(user_id: int, name: str) -> str:
    payload = {"sub": str(user_id), "name": name, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        return {"id": int(payload["sub"]), "name": payload["name"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée, reconnectez-vous.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Jeton invalide.")


# ─────────────────────────── Schémas ───────────────────────────

import re
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)

    @field_validator("password")
    @classmethod
    def valider_complexite(cls, value: str) -> str:
        erreurs = []
        if not re.search(r"[A-Z]", value):
            erreurs.append("une majuscule")
        if not re.search(r"[a-z]", value):
            erreurs.append("une minuscule")
        if not re.search(r"[0-9]", value):
            erreurs.append("un chiffre")

        if erreurs:
            raise ValueError(
                "Le mot de passe doit contenir au moins " + ", ".join(erreurs) + "."
            )
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str


from typing import Literal

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatIn(BaseModel):
    messages: list[ChatMessage]


# ─────────────────────────── Routes : auth ───────────────────────────


@app.post("/api/register")
def register(data: RegisterIn):
    salt = secrets.token_hex(16)
    pwd_hash = hash_password(data.password, salt)
    try:
        with get_db() as db:
            cur = db.execute(
                "INSERT INTO users (name, email, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
                (data.name, data.email.lower(), pwd_hash, salt, int(time.time())),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        # On ne confirme JAMAIS que l'email existe déjà
        raise HTTPException(
            status_code=400,
            detail="Impossible de créer le compte avec ces informations. Si vous avez déjà un compte, essayez de vous connecter.",
        )
    return {"token": create_token(user_id, data.name), "name": data.name}


from fastapi import Request

@app.post("/api/login")
def login(request: Request, data: LoginIn):
    email = data.email.lower()

    check_login_bloque(email)

    with get_db() as db:
        row = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

    if not row or not verify_password(data.password, row["salt"], row["password_hash"]):
        enregistrer_echec(email)
        security_logger.warning(
            f"Échec de connexion - email tenté: {email} - IP: {request.client.host}"
        )
        raise HTTPException(status_code=401, detail="E-mail ou mot de passe incorrect.")

    reset_tentatives(email)
    return {"token": create_token(row["id"], row["name"]), "name": row["name"]}


@app.get("/api/me")
def me(user: dict = Depends(get_current_user)):
    return user


# ─────────── Route : chat LLM (Ollama en local OU Gemini dans le cloud) ───────────


async def ask_ollama(system_prompt: str, messages: list[dict]) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "options": {"num_predict": 1024},
    }
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama est injoignable. Installez-le (https://ollama.com/download), "
                f"puis lancez :  ollama pull {OLLAMA_MODEL}"
            ),
        )
    if resp.status_code == 404:
        raise HTTPException(
            status_code=502,
            detail=f"Modèle « {OLLAMA_MODEL} » introuvable. Téléchargez-le :  ollama pull {OLLAMA_MODEL}",
        )
    if resp.status_code != 200:
        security_logger.warning(f"Erreur Ollama interne : {resp.text[:300]}")
        raise HTTPException(status_code=502, detail="Le service d'IA a rencontré un problème. Réessayez plus tard.")
    return (resp.json().get("message") or {}).get("content", "").strip()


async def ask_gemini(system_prompt: str, messages: list[dict]) -> str:
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "Clé Gemini manquante : créez-en une (gratuit) sur "
                "https://aistudio.google.com/apikey puis définissez GEMINI_API_KEY."
            ),
        )
    # Format Gemini : rôles "user" / "model", system prompt à part
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, params={"key": GEMINI_API_KEY}, json=payload)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="API Gemini injoignable (vérifiez la connexion internet du serveur).")
    if resp.status_code == 429:
        raise HTTPException(status_code=429, detail="Quota Gemini dépassé, réessayez dans une minute.")
    if resp.status_code != 200:
        security_logger.warning(f"Erreur Gemini interne : {resp.text[:300]}")
        raise HTTPException(status_code=502, detail="Le service d'IA a rencontré un problème. Réessayez plus tard.")
    try:
        parts = resp.json()["candidates"][0]["content"]["parts"]
        return "\n".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError):
        return ""
    

SUSPICIOUS_PATTERNS = [
    "ignore les instructions",
    "ignore previous instructions",
    "ignore tes instructions",
    "system override",
    "tu es maintenant",
    "nouvelles instructions",
    "oublie tes instructions",
]

def contient_injection_suspecte(texte: str) -> bool:
    texte_lower = texte.lower()
    return any(pattern in texte_lower for pattern in SUSPICIOUS_PATTERNS)



@app.post("/api/chat")
async def chat(data: ChatIn, user: dict = Depends(get_current_user)):
    if not data.messages:
        raise HTTPException(status_code=400, detail="Aucun message fourni.")

    #  AJOUTE CES 6 LIGNES ICI (juste après le "if not data.messages") 
    for m in data.messages:
        if contient_injection_suspecte(m.content):
            security_logger.warning(
                f"Tentative de prompt injection détectée - user_id: {user['id']}"
            )
            raise HTTPException(
                status_code=400,
                detail="Votre message contient un contenu non autorisé.",
            )

    system_prompt = (
        "Tu es un assistant IA francophone, chaleureux et concis. "
        f"L'utilisateur s'appelle {user['name']}. "
        "Réponds en français sauf s'il écrit dans une autre langue."
    )
    messages = [m.model_dump() for m in data.messages]

    if LLM_PROVIDER == "gemini":
        text = await ask_gemini(system_prompt, messages)
    else:
        text = await ask_ollama(system_prompt, messages)

    return {"reply": text or "Je n'ai pas pu générer de réponse."}

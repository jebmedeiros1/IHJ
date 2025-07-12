from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import text
from .database import engine
import yaml
from yaml.loader import SafeLoader

app = FastAPI(title="IHJ API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.load(f, Loader=SafeLoader)


def authenticate_user(username: str, password: str) -> bool:
    users = config.get("credentials", {}).get("usernames", {})
    if username in users and password == users[username].get("password"):
        return True
    return False


class Equipamento(BaseModel):
    equipamento: str


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if authenticate_user(form_data.username, form_data.password):
        return {"access_token": form_data.username, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/classes")
def get_classes():
    query = "SELECT DISTINCT classe FROM tb_caract"
    with engine.connect() as conn:
        df = conn.execute(text(query)).fetchall()
    return [row[0] for row in df]


@app.get("/equipamentos")
def get_equipamentos(classe: str):
    query = text("SELECT DISTINCT equipamento FROM tb_caract WHERE classe=:classe")
    with engine.connect() as conn:
        rows = conn.execute(query, {"classe": classe}).fetchall()
    return [row[0] for row in rows]


@app.post("/similaridade")
def similaridade(data: Equipamento):
    query = text(
        "SELECT * FROM tb_caract WHERE classe IN (SELECT classe FROM tb_caract WHERE equipamento=:equip)"
    )
    with engine.connect() as conn:
        df = conn.execute(query, {"equip": data.equipamento}).fetchall()
    # TODO: implementar lógica real de similaridade
    return {"result": [dict(row) for row in df]}

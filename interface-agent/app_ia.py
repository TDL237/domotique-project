from fastapi import FastAPI, HTTPException
import redis
import json
import os
import uuid
from pydantic import BaseModel

app = FastAPI(title="Interface Agent")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
TOPIC = os.getenv("TOPIC_COMMANDS", "commands")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

class Command(BaseModel):
    objet: str  # lampe, prise, thermostat
    action: str  # on, off, get_state, set_temp
    valeur: float = None

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/command")
def send_command(cmd: Command):
    """Envoie une commande structurée au coordinateur"""
    trace_id = str(uuid.uuid4())
    
    message = {
        "objet": cmd.objet,
        "action": cmd.action,
        "valeur": cmd.valeur,
        "trace_id": trace_id
    }
    
    # Envoyer au stream Redis
    r.xadd(TOPIC, {"command": json.dumps(message)})
    
    return {
        "status": "command_sent",
        "trace_id": trace_id,
        "message": f"Commande {cmd.action} envoyée à {cmd.objet}"
    }

@app.get("/response/{trace_id}")
def get_response(trace_id: str):
    """Récupère une réponse depuis Redis (optionnel)"""
    responses = r.xread({"responses": "0"}, block=1000, count=10)
    for stream, msgs in responses:
        for msg_id, data in msgs:
            if data.get("trace_id") == trace_id:
                return json.loads(data.get("result", "{}"))
    return {"status": "pending", "trace_id": trace_id}

    from fastapi import FastAPI
import redis
import json
import os
import uuid
import httpx
from pydantic import BaseModel

app = FastAPI(title="Interface Agent IA")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
TOPIC = os.getenv("TOPIC_COMMANDS", "commands")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

class Command(BaseModel):
    texte: str

def ask_ollama(prompt):
    """Interroge Ollama pour interpréter la demande"""
    try:
        # Utiliser le modèle qwen2.5:1.5b-instruct
        response = httpx.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "qwen2.5:1.5b-instruct",
                "prompt": f"""Tu es un assistant domotique. Convertit cette demande en JSON.
Réponds UNIQUEMENT avec du JSON valide, rien d'autre.

Format attendu: {{"objet": "lampe|prise|thermostat", "action": "on|off|get_state|set_temp", "valeur": nombre (si action=set_temp)}}

Demande: {prompt}""",
                "stream": False
            },
            timeout=15.0
        )
        result = response.json()
        
        # Extraire le JSON de la réponse
        import re
        json_match = re.search(r'\{.*\}', result["response"], re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"error": "Format JSON invalide"}
    except Exception as e:
        return {"error": str(e)}

def parse_simple(text):
    """Parsing simple de secours"""
    text = text.lower()
    
    if "lampe" in text:
        objet = "lampe"
    elif "prise" in text:
        objet = "prise"
    elif "thermostat" in text:
        objet = "thermostat"
    else:
        return None, None, None
    
    if "allume" in text or "allumer" in text:
        action = "on"
    elif "eteins" in text or "eteindre" in text or "éteins" in text:
        action = "off"
    elif "état" in text or "status" in text or "température" in text:
        action = "get_state"
    else:
        action = None
    
    import re
    nombres = re.findall(r'\d+[,.]?\d*', text)
    valeur = None
    if nombres and ("température" in text or "degré" in text):
        valeur = float(nombres[0].replace(',', '.'))
        action = "set_temp"
    
    return objet, action, valeur

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/ollama/status")
async def ollama_status():
    """Vérifie la connexion à Ollama"""
    try:
        response = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
        return {
            "status": "connected",
            "host": OLLAMA_HOST,
            "models": [m["name"] for m in response.json().get("models", [])]
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "host": OLLAMA_HOST}

@app.post("/command")
async def send_command(cmd: Command):
    """Reçoit une commande en langage naturel"""
    trace_id = str(uuid.uuid4())
    
    # Essayer Ollama d'abord
    parsed = ask_ollama(cmd.texte)
    
    if "error" in parsed:
        # Fallback parsing simple
        objet, action, valeur = parse_simple(cmd.texte)
        if not objet or not action:
            return {
                "status": "error",
                "message": f"Je n'ai pas compris: {cmd.texte}",
                "suggestion": "Exemples: 'allume la lampe', 'éteins la prise', 'état du thermostat'"
            }
    else:
        objet = parsed.get("objet")
        action = parsed.get("action")
        valeur = parsed.get("valeur")
    
    if not objet or not action:
        return {"status": "error", "message": "Impossible de comprendre la commande"}
    
    message = {
        "objet": objet,
        "action": action,
        "valeur": valeur,
        "trace_id": trace_id
    }
    
    r.xadd(TOPIC, {"command": json.dumps(message)})
    
    return {
        "status": "command_sent",
        "trace_id": trace_id,
        "message": f"✅ Commande comprise: {action} sur {objet}" + (f" à {valeur}°C" if valeur else ""),
        "commande_parsee": message
    }

@app.get("/response/{trace_id}")
def get_response(trace_id: str):
    responses = r.xread({"responses": "0"}, block=1000, count=10)
    for stream, msgs in responses:
        for msg_id, data in msgs:
            if data.get("trace_id") == trace_id:
                return json.loads(data.get("result", "{}"))
    return {"status": "pending", "trace_id": trace_id}

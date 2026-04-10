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

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

class Command(BaseModel):
    objet: str
    action: str
    valeur: float = None

class TextCommand(BaseModel):
    texte: str

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/command")
def send_command(cmd: Command):
    trace_id = str(uuid.uuid4())
    message = {
        "objet": cmd.objet,
        "action": cmd.action,
        "valeur": cmd.valeur,
        "trace_id": trace_id
    }
    r.xadd(TOPIC, {"command": json.dumps(message)})
    return {
        "status": "command_sent",
        "trace_id": trace_id,
        "message": f"Commande {cmd.action} envoyée à {cmd.objet}"
    }

def parse_simple(text):
    """Parsing simple et rapide (fallback)"""
    text = text.lower()
    
    if "lampe" in text:
        objet = "lampe"
    elif "prise" in text:
        objet = "prise"
    elif "thermostat" in text:
        objet = "thermostat"
    else:
        return None, None, None
    
    if "allume" in text:
        action = "on"
    elif "eteins" in text or "éteins" in text:
        action = "off"
    elif "état" in text or "status" in text:
        action = "get_state"
    elif "température" in text or "degré" in text:
        import re
        nombres = re.findall(r'\d+[,.]?\d*', text)
        if nombres:
            action = "set_temp"
            valeur = float(nombres[0].replace(',', '.'))
            return objet, action, valeur
        action = "get_state"
    else:
        action = "get_state"
    
    return objet, action, None

def ask_ollama(prompt):
    """Interroge Ollama avec timeout plus long"""
    try:
        response = httpx.post(
            "http://host.docker.internal:11434/api/generate",
            json={
                "model": "qwen2.5:1.5b-instruct",
                "prompt": f"""Convertit cette demande domotique en JSON.
Format: {{"objet": "lampe|prise|thermostat", "action": "on|off|get_state|set_temp", "valeur": (nombre si set_temp)}}
Demande: {prompt}
JSON:""",
                "stream": False,
                "options": {
                    "num_predict": 50,
                    "temperature": 0
                }
            },
            timeout=30.0
        )
        result = response.json()
        
        import re
        json_match = re.search(r'\{.*\}', result["response"], re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

@app.post("/command_ia")
async def send_command_ia(cmd: TextCommand):
    """Commande en langage naturel (avec IA)"""
    trace_id = str(uuid.uuid4())
    
    # Essayer Ollama d'abord (30 secondes max)
    parsed = ask_ollama(cmd.texte)
    
    # Fallback sur parsing simple si Ollama échoue
    if not parsed:
        objet, action, valeur = parse_simple(cmd.texte)
        if objet and action:
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
                "message": f"✅ (mode simple) Commande: {action} sur {objet}",
                "commande_parsee": message,
                "mode": "fallback"
            }
        else:
            return {
                "status": "error",
                "message": f"Je n'ai pas compris: {cmd.texte}",
                "suggestion": "Exemples: 'allume la lampe', 'éteins la prise', 'état du thermostat'"
            }
    
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
        "message": f"✅ IA: {action} sur {objet}" + (f" à {valeur}°C" if valeur else ""),
        "commande_parsee": message,
        "mode": "ollama"
    }

@app.get("/response/{trace_id}")
def get_response(trace_id: str):
    responses = r.xread({"responses": "0"}, block=1000, count=10)
    for stream, msgs in responses:
        for msg_id, data in msgs:
            if data.get("trace_id") == trace_id:
                return json.loads(data.get("result", "{}"))
    return {"status": "pending", "trace_id": trace_id}

@app.get("/ollama/status")
async def ollama_status():
    try:
        response = httpx.get("http://host.docker.internal:11434/api/tags", timeout=5.0)
        return {
            "status": "connected",
            "models": [m["name"] for m in response.json().get("models", [])]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

import redis
import json
import os
import httpx
import uuid
import time

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
TOPIC = os.getenv("TOPIC_COMMANDS", "commands")

# Mapping des objets vers leurs URLs
SERVICES = {
    "lampe": f"http://lamp-agent:8000",
    "prise": f"http://prise-agent:8000",
    "thermostat": f"http://thermostat-agent:8000"
}

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def process_command(command_msg):
    """Traite une commande venue de Redis"""
    try:
        data = json.loads(command_msg)
        objet = data.get("objet")
        action = data.get("action")
        valeur = data.get("valeur")
        trace_id = data.get("trace_id", str(uuid.uuid4()))

        if objet not in SERVICES:
            return {"error": f"Objet inconnu: {objet}"}

        url = SERVICES[objet]
        
        # Router l'action
        if action == "on":
            response = httpx.post(f"{url}/on", timeout=2.0)
        elif action == "off":
            response = httpx.post(f"{url}/off", timeout=2.0)
        elif action == "get_state":
            response = httpx.get(f"{url}/state", timeout=2.0)
        elif action == "set_temp" and valeur is not None:
            response = httpx.post(f"{url}/set_temp/{valeur}", timeout=2.0)
        else:
            return {"error": f"Action inconnue: {action}"}

        return response.json()
    
    except Exception as e:
        return {"error": str(e)}

def main():
    print(f"Coordinateur démarré, écoute sur Redis topic: {TOPIC}")
    
    while True:
        try:
            # Lire les messages Redis Stream
            messages = r.xread({TOPIC: '0'}, block=5000, count=1)
            
            for stream, msg_list in messages:
                for msg_id, msg_data in msg_list:
                    command_json = msg_data.get("command", "{}")
                    result = process_command(command_json)
                    
                    # Envoyer la réponse sur un stream de réponses
                    r.xadd("responses", {
                        "trace_id": json.loads(command_json).get("trace_id", ""),
                        "result": json.dumps(result)
                    })
                    
                    # Supprimer le message traité
                    r.xdel(TOPIC, msg_id)
                    
        except KeyboardInterrupt:
            print("Arrêt du coordinateur")
            break
        except Exception as e:
            print(f"Erreur: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()

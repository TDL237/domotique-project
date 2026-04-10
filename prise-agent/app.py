from fastapi import FastAPI

app = FastAPI(title="Prise Agent")

state = {
    "power": False,
    "type": "prise"
}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/state")
def get_state():
    return state

@app.post("/on")
def turn_on():
    state["power"] = True
    return {"status": "ok", "power": True}

@app.post("/off")
def turn_off():
    state["power"] = False
    return {"status": "ok", "power": False}

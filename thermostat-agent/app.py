from fastapi import FastAPI

app = FastAPI(title="Thermostat Agent")

state = {
    "power": False,
    "target_temp": 19.0,
    "current_temp": 18.5,
    "type": "thermostat"
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

@app.post("/set_temp/{temp}")
def set_temperature(temp: float):
    state["target_temp"] = temp
    return {"status": "ok", "target_temp": temp}

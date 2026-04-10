from fastapi import FastAPI

app = FastAPI()

state = {
    "power": False
}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/state")
def get_state():
    return state
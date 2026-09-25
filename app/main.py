from fastapi import FastAPI

app = FastAPI(title="Painel B3")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}

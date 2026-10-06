from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.local_routes import router as local_router
from app.patient_store import init_db

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

app = FastAPI(
    title="QSafeRx / Qure",
    description="Quantum-assisted candidate regimen selection research prototype",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(local_router)
init_db()

if WEB.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB)), name="assets")


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(WEB / "index.html")


@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "QSafeRx", "version": app.version}

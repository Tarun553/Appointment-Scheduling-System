from fastapi import FastAPI
from app.api.v1 import auth, appointments, availability
from app.db.session import init_db
from app.core.config import settings
from app.core.scheduler import start_scheduler, shutdown_scheduler

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    shutdown_scheduler()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Appointment Scheduling System API"}

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(appointments.router, prefix=f"{settings.API_V1_STR}/appointments", tags=["appointments"])
app.include_router(availability.router, prefix=f"{settings.API_V1_STR}/availability", tags=["availability"])

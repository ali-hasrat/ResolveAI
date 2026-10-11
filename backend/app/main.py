from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import Base, engine
from app.models import models

from app.api.routes.health import router as health_router
from app.api.routes.support import router as support_router
from app.api.routes.cases import router as cases_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.admin_cases import router as admin_cases_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-powered customer support resolution platform",
)

origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    health_router,
    prefix="/api",
)

app.include_router(
    support_router,
    prefix="/api",
)

app.include_router(
    cases_router,
    prefix="/api",
)

app.include_router(
    evidence_router,
    prefix="/api",
)

app.include_router(
    admin_cases_router,
    prefix="/api",
)


@app.get("/")
def root():
    return {
        "service": "ResolveAI",
        "status": "running",
        "docs": "/docs",
    }

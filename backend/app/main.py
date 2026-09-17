from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.cloudflare import router as cloudflare_router
from app.api.routes.google_analytics import router as google_analytics_router
from app.api.routes.google_search_console import router as google_search_console_router
from app.api.routes.health import router as health_router
from app.api.routes.normalization import router as normalization_router
from app.api.routes.sites import router as sites_router
from app.api.routes.workspaces import router as workspaces_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(workspaces_router, prefix="/api")
app.include_router(sites_router, prefix="/api")
app.include_router(google_analytics_router, prefix="/api")
app.include_router(google_search_console_router, prefix="/api")
app.include_router(cloudflare_router, prefix="/api")
app.include_router(normalization_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "TrafficVerdict API", "status": "running"}

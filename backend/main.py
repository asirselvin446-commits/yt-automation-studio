import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import system_logger
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    system_logger.info("Booting YT Automation Studio Backend...")
    settings.ensure_directories()
    await init_db()
    system_logger.info(f"Pipeline directories ready at: {settings.root_path}")
    yield
    # Shutdown
    system_logger.info("Shutting down YT Automation Studio Backend.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"] if settings.DEBUG else settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API
app.include_router(api_router)

# Mount Frontend static files if built
frontend_dist = Path("./frontend/dist").resolve()
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't hijack API routes
        if full_path.startswith("api"):
            return None
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "docs": "/docs",
            "api": "/api/v1"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=settings.DEBUG)

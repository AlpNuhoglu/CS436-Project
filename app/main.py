"""
FastAPI application entry point.

Ders Forumu - Sabancı Üniversitesi hoca & ders değerlendirme platformu.
"""
from fastapi import FastAPI, APIRouter

from app.routes import auth
from app.routes import health
from app.routes import me
from app.routes import professors
from app.routes import courses
from app.routes import reviews
from app.routes import search
from app.routes import stats

app = FastAPI(
    title="Ders Forumu API",
    description="Sabancı Üniversitesi hoca ve ders değerlendirme platformu",
    version="0.1.0",
)

# All routes are prefixed with /api so CloudFront's /api/* behavior
# forwards requests to ALB without any path rewriting needed.
api = APIRouter(prefix="/api")
api.include_router(health.router)
api.include_router(auth.router)
api.include_router(me.router)
api.include_router(professors.router)
api.include_router(courses.router)
api.include_router(reviews.router)
api.include_router(search.router)
api.include_router(stats.router)
app.include_router(api)


@app.get("/")
def root():
    return {
        "name": "Ders Forumu API",
        "version": "0.1.0",
        "docs": "/docs",
    }

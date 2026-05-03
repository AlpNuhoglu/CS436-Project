"""
FastAPI application entry point.

Ders Forumu - Sabancı Üniversitesi hoca & ders değerlendirme platformu.
"""
from fastapi import FastAPI

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

# Register route modules here as they are implemented.
# Week 1: /health
# Week 2: /me  (auth)
# Week 3: /professors, /courses
# Week 4: /reviews, /upvotes
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(professors.router)
app.include_router(courses.router)
app.include_router(reviews.router)
app.include_router(search.router)
app.include_router(stats.router)


@app.get("/")
def root():
    """Root endpoint - basic API info."""
    return {
        "name": "Ders Forumu API",
        "version": "0.1.0",
        "docs": "/docs",
    }

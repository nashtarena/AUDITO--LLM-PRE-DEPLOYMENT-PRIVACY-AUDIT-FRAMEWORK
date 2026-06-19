import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database.session import Base, engine
from api.routes import auth, projects, datasets, audits, notifications, analytics
import models  # noqa: F401 — ensures all models are registered

# Create tables
Base.metadata.create_all(bind=engine)

# Create required directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("faiss_indexes", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("reports_output", exist_ok=True)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Audito API",
    description="LLM Data Memorization & Privacy Leakage Auditing Platform",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # update with Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(audits.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

@app.get("/") 
def root():
    return {"Message" : "Backend is running!"}
    
@app.get("/health")
def health():
    return {"status": "ok"}

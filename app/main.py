from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_to_mongo, close_mongo_connection
from app.routes import videos, contacts

app = FastAPI(
    title="Women Safety App API",
    description="API for video tutorials and safety features",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection events
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Include routers
app.include_router(videos.router, prefix="/api")
app.include_router(contacts.router, prefix="/contact")

@app.get("/")
async def root():
    return {"message": "Women Safety App API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
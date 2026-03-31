from fastapi import FastAPI
from app.core.database import engine,Base
from app.models import users,regulation,rule
from app.api.regulation_api import router as regulation_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Aircraft Certification Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
app.include_router(regulation_router)
@app.get("/")
def root():
    return {"message": "Aircraft Certification Platform Backend Running"}
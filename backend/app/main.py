from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# Import your local files
from . import crud, models, schemas
from .database import SessionLocal, engine

# 1. Create the database tables automatically
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 2. Add CORS (So your Frontend can talk to this Backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency: Get the database session for each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTES ---

@app.get("/", tags=["Root"])
def read_root():
    return {"status": "Chemical Safety API is running"}

# POST: Add a new chemical
@app.post("/chemicals/", response_model=schemas.Chemical, tags=["Chemicals"])
def create_chemical(chemical: schemas.ChemicalCreate, db: Session = Depends(get_db)):
    return crud.create_chemical(db=db, chemical=chemical)

# GET: List all chemicals
@app.get("/chemicals/", response_model=List[schemas.Chemical], tags=["Chemicals"])
def read_chemicals(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    chemicals = crud.get_chemicals(db, skip=skip, limit=limit)
    return chemicals
    # Mount the React build folder
# Make sure this path points to where your 'frontend/build' folder is
# We use '..' to go up one level from 'backend/app' to 'backend', then '..' to root, then 'frontend/build'
build_path = os.path.join(os.path.dirname(__file__), "../../frontend/build")

if os.path.exists(build_path):
    app.mount("/static", StaticFiles(directory=f"{build_path}/static"), name="static")

    # Catch-all route to serve the React App
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # If the API path was not matched above, serve the index.html
        return FileResponse(f"{build_path}/index.html")
else:
    print("Warning: React build folder not found. Did you run 'npm run build'?")
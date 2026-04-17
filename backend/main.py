from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routes import auth, tasks, analyze, help, ratings

load_dotenv()

app = FastAPI(
    title="Workviser API",
    description="Smart team productivity with AI-powered stuck detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(analyze.router)
app.include_router(help.router)
app.include_router(ratings.router)

@app.get("/")
async def root():
    return {
        "message": "Workviser API is running",
        "version": "1.0.0",
        "docs": "http://localhost:8000/docs"
    }
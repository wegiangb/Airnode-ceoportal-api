from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/dashboard")
def dashboard():
    return [
        {
            "subject": "EV dealership partnership",
            "score": 18,
            "why": "Strong EV distribution channel opportunity"
        },
        {
            "subject": "SME ESG reporting request",
            "score": 15,
            "why": "Repeated SME demand signal"
        }
    ]

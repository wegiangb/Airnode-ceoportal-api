import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

app = FastAPI(title="AirNode CEO Portal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MOCK_EMAILS = [
    {
        "subject": "EV dealership partnership",
        "body": "We want to explore air quality data integration into EV dealership sales.",
        "sender": "partner@example.com"
    },
    {
        "subject": "SME ESG reporting request",
        "body": "We need help with air quality compliance and ESG reporting for our logistics fleet.",
        "sender": "sme@example.com"
    }
]

PRIORITIES = [
    "Expand EV partnerships",
    "Scale SME ESG SaaS",
    "Secure grants and funding",
    "Reduce CEO information overload"
]

def score_email(a):
    m = {"low": 1, "medium": 2, "high": 3}
    score = (
        m.get(a["revenue_potential"], 1) * 3 +
        m.get(a["strategic_value"], 1) * 3 +
        m.get(a["time_saving"], 1) * 2
    )
    if a.get("priority_aligned"):
        score += 5
    return score

def analyse_email(email):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
You are analysing emails for the CEO of AirNode.

CEO priorities:
{PRIORITIES}

Email:
Subject: {email['subject']}
Sender: {email['sender']}
Body: {email['body']}

Return JSON only with:
summary,
why,
revenue_potential: low|medium|high,
strategic_value: low|medium|high,
time_saving: low|medium|high,
urgency: low|medium|high,
priority_aligned: true|false
"""
    )

    text = response.output_text
    return json.loads(text)

@app.get("/")
def home():
    return {"status": "AirNode CEO Portal API is running"}

@app.get("/api/dashboard")
def dashboard():
    results = []

    for email in MOCK_EMAILS:
        analysis = analyse_email(email)
        score = score_email(analysis)

        results.append({
            "subject": email["subject"],
            "why": analysis["why"],
            "summary": analysis["summary"],
            "score": score,
            "revenue_potential": analysis["revenue_potential"],
            "strategic_value": analysis["strategic_value"],
            "urgency": analysis["urgency"]
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

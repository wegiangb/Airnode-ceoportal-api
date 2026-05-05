import os
import json
from datetime import datetime, timezone

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from supabase import create_client

from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")



app = FastAPI(title="AirNode CEO Portal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MOCK_EMAILS = [
    {
        "subject": "EV dealership partnership",
        "body": "We want to explore air quality data integration into EV dealership sales.",
        "sender": "partner@example.com",
        "sender_email": "partner@example.com",
    },
    {
        "subject": "SME ESG reporting request",
        "body": "We need help with air quality compliance and ESG reporting for our logistics fleet.",
        "sender": "sme@example.com",
        "sender_email": "sme@example.com",
    },
]

PRIORITIES = [
    "Expand EV partnerships",
    "Scale SME ESG SaaS",
    "Secure grants and funding",
    "Reduce CEO information overload",
]


def score_email(a):
    m = {"low": 1, "medium": 2, "high": 3}

    score = (
        m.get(a.get("revenue_potential", "low"), 1) * 3
        + m.get(a.get("strategic_value", "low"), 1) * 3
        + m.get(a.get("time_saving", "low"), 1) * 2
        + m.get(a.get("urgency", "low"), 1) * 2
    )

    if a.get("priority_aligned"):
        score += 5

    return min(score, 30)



def analyse_email(email):
    fallback = {
        "summary": email.get("subject", "No subject"),
        "value_to_reader": "Potentially relevant email, but AI JSON parsing failed.",
        "why": "The system could not parse the AI response, so this email has been given a safe default analysis.",
        "ceo_role": "Execution",
        "category": "Information",
        "revenue_potential": "low",
        "strategic_value": "medium",
        "time_saving": "low",
        "urgency": "low",
        "priority_aligned": False,
        "reply_needed": "Maybe",
        "reply_timing": "Later",
        "suggested_owner": "CEO",
        "owner_reason": "Fallback owner because AI parsing failed.",
        "score_explanation": [
            "AI response was not valid JSON",
            "Fallback scoring applied"
        ],
    }

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You are analysing emails for the CEO of AirNode.

CEO priorities:
{PRIORITIES}

Email:
Subject: {email.get('subject', '')}
Sender: {email.get('sender', '')}
Body: {email.get('body', '')}

Return ONLY valid JSON. No markdown. No explanation.

Required JSON shape:
{{
  "summary": "string",
  "value_to_reader": "string",
  "why": "string",
  "ceo_role": "Capital / Direction",
  "category": "Partnership",
  "revenue_potential": "high",
  "strategic_value": "high",
  "time_saving": "low",
  "urgency": "medium",
  "priority_aligned": true,
  "reply_needed": "Yes",
  "reply_timing": "24h",
  "suggested_owner": "CEO",
  "owner_reason": "string",
  "score_explanation": ["string"]
}}
""",
            text={
                "format": {
                    "type": "json_object"
                }
            },
        )

        text = response.output_text

        if not text:
            fallback["raw_error_text"] = "Empty OpenAI response"
            return fallback

        return json.loads(text)

    except Exception as e:
        fallback["raw_error"] = str(e)
        return fallback

def email_exists(subject, sender_email):
    existing = (
        supabase.table("emails")
        .select("id")
        .eq("subject", subject)
        .eq("sender_email", sender_email)
        .limit(1)
        .execute()
    )

    return existing.data[0] if existing.data else None


def save_email(email):
    existing = email_exists(email["subject"], email.get("sender_email", ""))

    if existing:
        return existing["id"]

    row = (
        supabase.table("emails")
        .insert(
            {
                "subject": email["subject"],
                "sender": email.get("sender"),
                "sender_email": email.get("sender_email"),
                "body": email["body"],
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
    )

    return row.data[0]["id"]


def save_analysis(email_id, analysis, score):
    existing = (
        supabase.table("email_analysis")
        .select("id")
        .eq("email_id", email_id)
        .limit(1)
        .execute()
    )

    payload = {
        "email_id": email_id,
        "summary": analysis.get("summary"),
        "value_to_reader": analysis.get("value_to_reader"),
        "why": analysis.get("why"),
        "ceo_role": analysis.get("ceo_role"),
        "category": analysis.get("category"),
        "score": score,
        "reply_needed": analysis.get("reply_needed"),
        "reply_timing": analysis.get("reply_timing"),
        "suggested_owner": analysis.get("suggested_owner"),
        "owner_reason": analysis.get("owner_reason"),
        "score_explanation": analysis.get("score_explanation", []),
        "raw_ai": analysis,
    }

    if existing.data:
        (
            supabase.table("email_analysis")
            .update(payload)
            .eq("email_id", email_id)
            .execute()
        )
    else:
        supabase.table("email_analysis").insert(payload).execute()


def ensure_decision_row(email_id):
    existing = (
        supabase.table("email_decisions")
        .select("id")
        .eq("email_id", email_id)
        .limit(1)
        .execute()
    )

    if not existing.data:
        (
            supabase.table("email_decisions")
            .insert({"email_id": email_id, "status": "not_reviewed"})
            .execute()
        )


@app.get("/")
def home():
    return {"status": "AirNode CEO Portal API is running"}


@app.post("/api/test-db")
def test_db():
    row = (
        supabase.table("emails")
        .insert(
            {
                "subject": "Database test email",
                "sender": "AirNode Test",
                "sender_email": "test@airnode.co.uk",
                "body": "Testing Supabase connection.",
            }
        )
        .execute()
    )

    return {"inserted": row.data}


@app.post("/api/ingest-demo")
def ingest_demo():
    processed = []

    for email in MOCK_EMAILS:
        email_id = save_email(email)
        analysis = analyse_email(email)
        score = score_email(analysis)

        save_analysis(email_id, analysis, score)
        ensure_decision_row(email_id)

        processed.append(
            {
                "email_id": email_id,
                "subject": email["subject"],
                "score": score,
            }
        )

    return {"processed": processed}


@app.post("/api/ingest-email")
def ingest_email(email: dict = Body(...)):
    email_id = save_email(email)
    analysis = analyse_email(email)
    score = score_email(analysis)

    save_analysis(email_id, analysis, score)
    ensure_decision_row(email_id)

    return {
        "email_id": email_id,
        "analysis": analysis,
        "score": score,
    }


@app.get("/api/dashboard")
def dashboard():
    emails = supabase.table("emails").select("*").execute().data
    analysis_rows = supabase.table("email_analysis").select("*").execute().data
    decision_rows = supabase.table("email_decisions").select("*").execute().data

    analysis_by_email = {row["email_id"]: row for row in analysis_rows}
    decision_by_email = {row["email_id"]: row for row in decision_rows}

    results = []

    for email in emails:
        a = analysis_by_email.get(email["id"])
        d = decision_by_email.get(email["id"], {})

        if not a:
            continue

        results.append(
            {
                "id": email["id"],
                "subject": email["subject"],
                "sender": email.get("sender"),
                "sender_email": email.get("sender_email"),
                "summary": a.get("summary"),
                "value_to_reader": a.get("value_to_reader"),
                "why": a.get("why"),
                "ceo_role": a.get("ceo_role"),
                "category": a.get("category"),
                "score": a.get("score"),
                "reply_needed": a.get("reply_needed"),
                "reply_timing": a.get("reply_timing"),
                "suggested_owner": a.get("suggested_owner"),
                "owner_reason": a.get("owner_reason"),
                "score_explanation": a.get("score_explanation") or [],
                "decision_status": d.get("status", "not_reviewed"),
                "assigned_owner": d.get("assigned_owner"),
                "decision_note": d.get("decision_note"),
                "deferred_until": d.get("deferred_until"),
            }
        )

    return sorted(results, key=lambda x: x.get("score") or 0, reverse=True)


@app.post("/api/email/{email_id}/decision")
def update_decision(email_id: str, payload: dict = Body(...)):
    status = payload.get("status", "reviewed")

    allowed = [
        "not_reviewed",
        "reviewed",
        "delegated",
        "ignored",
        "deferred",
        "replied",
    ]

    if status not in allowed:
        return {"error": f"Invalid status. Use one of: {allowed}"}

    existing = (
        supabase.table("email_decisions")
        .select("id")
        .eq("email_id", email_id)
        .limit(1)
        .execute()
    )

    decision_payload = {
        "email_id": email_id,
        "status": status,
        "assigned_owner": payload.get("assigned_owner"),
        "decision_note": payload.get("decision_note"),
        "deferred_until": payload.get("deferred_until"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if existing.data:
        row = (
            supabase.table("email_decisions")
            .update(decision_payload)
            .eq("email_id", email_id)
            .execute()
        )
    else:
        row = supabase.table("email_decisions").insert(decision_payload).execute()

    return {"updated": row.data}



@app.get("/api/gmail/connect")
def gmail_connect():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return RedirectResponse(auth_url)

@app.get("/api/gmail/callbak")
def gmail_callbak(code: str, state: str = None):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

    flow.fetch_token(code=code)
    creds = flow.credentials

    token_json = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }

    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    user_email = profile.get("emailAddress")

    supabase.table("gmail_tokens").insert({
        "user_email": user_email,
        "token_json": token_json
    }).execute()

    return {
        "status": "gmail_connected",
        "email": user_email
    }


def decode_body(payload):
    body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    else:
        data = payload.get("body", {}).get("data")
        if data:
            body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return body[:5000]


def header_value(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


@app.post("/api/gmail/sync")
def gmail_sync():
    token_rows = supabase.table("gmail_tokens").select("*").execute().data

    if not token_rows:
        return {"error": "No Gmail account connected"}

    token_json = token_rows[-1]["token_json"]

    creds = Credentials(
        token=token_json["token"],
        refresh_token=token_json.get("refresh_token"),
        token_uri=token_json["token_uri"],
        client_id=token_json["client_id"],
        client_secret=token_json["client_secret"],
        scopes=token_json["scopes"],
    )

    service = build("gmail", "v1", credentials=creds)

    messages = service.users().messages().list(
        userId="me",
        maxResults=10,
        q="newer_than:14d"
    ).execute().get("messages", [])

    processed = []

    for msg in messages:
        full = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        payload = full.get("payload", {})
        headers = payload.get("headers", [])

        subject = header_value(headers, "Subject") or "(No subject)"
        sender = header_value(headers, "From")
        body = decode_body(payload)

        email = {
            "subject": subject,
            "sender": sender,
            "sender_email": sender,
            "body": body or full.get("snippet", "")
        }

        email_id = save_email(email)
        analysis = analyse_email(email)
        score = score_email(analysis)

        save_analysis(email_id, analysis, score)
        ensure_decision_row(email_id)

        processed.append({
            "email_id": email_id,
            "subject": subject,
            "score": score
        })

    return {
        "synced": len(processed),
        "processed": processed
    }
import requests
from fastapi import Request

@app.get("/api/gmail/callback")
def gmail_callback(request: Request):
    try:
        code = request.query_params.get("code")
        error = request.query_params.get("error")

        if error:
            return {"success": False, "step": "google_error", "error": error}

        if not code:
            return {"success": False, "step": "missing_code"}

        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        token_json = token_response.json()

        if token_response.status_code != 200:
            return {
                "success": False,
                "step": "token_exchange_failed",
                "google_error": token_json,
            }

        creds = Credentials(
            token=token_json["access_token"],
            refresh_token=token_json.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=GMAIL_SCOPES,
        )

        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        user_email = profile.get("emailAddress")

        supabase.table("gmail_tokens").insert({
            "user_email": user_email,
            "token_json": {
                "token": token_json["access_token"],
                "refresh_token": token_json.get("refresh_token"),
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "scopes": GMAIL_SCOPES,
            }
        }).execute()

        return {
            "success": True,
            "status": "gmail_connected",
            "email": user_email,
        }

    except Exception as e:
        return {
            "success": False,
            "step": "exception",
            "error": str(e),
        }

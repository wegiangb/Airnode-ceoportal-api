import os
import json
import uuid
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


import urllib.parse
from fastapi.responses import RedirectResponse

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


CEO_PRIORITY_MODEL = {
    "strategy": {
        "title": "Strategy, Growth & External Leadership",
        "short": "Strategy & Growth",
        "subtopics": {
            "strategicLeadership": {"title": "Strategic Leadership", "priorities": ["Ports strategy", "India growth", "AQ SaaS positioning"]},
            "revenueGrowth": {"title": "Revenue & Growth", "priorities": ["Fleet optimisation", "EV advisory", "ESG consultancy"]},
            "financialLeadership": {"title": "Financial Leadership", "priorities": ["Secure grants", "Investor follow-up", "Project margins"]},
            "externalRepresentation": {"title": "External Representation", "priorities": ["Government meetings", "Conference follow-up", "Stakeholder briefings"]},
        },
    },
    "operations": {
        "title": "Operations, Delivery & Organisational Leadership",
        "short": "Operations & Delivery",
        "subtopics": {
            "operationsExecution": {"title": "Operations & Execution", "priorities": ["CEO Portal v2", "Dashboard delivery", "Proposal pipeline"]},
            "peopleLeadership": {"title": "People & Leadership", "priorities": ["Leader programme", "Advisor coordination", "Capability gaps"]},
            "riskGovernance": {"title": "Risk & Governance", "priorities": ["AI governance", "ESG evidence", "Cyber resilience"]},
        },
    },
    "intelligence": {
        "title": "Intelligence, Decision-Making & Coordination",
        "short": "Intelligence & Coordination",
        "subtopics": {
            "executiveIntelligence": {"title": "Executive Intelligence", "priorities": ["High value emails", "Strategic risks", "Opportunity scoring"]},
            "organisationalMemory": {"title": "Organisational Memory", "priorities": ["Relationship memory", "Proposal archive", "Decision history"]},
            "coordinationSystems": {"title": "Coordination Systems", "priorities": ["Reply backlog", "Delegated actions", "Blocked proposals"]},
        },
    },
    "technology": {
        "title": "Technology, Innovation & Platform Systems",
        "short": "Technology & Innovation",
        "subtopics": {
            "technologyAI": {"title": "Technology & AI", "priorities": ["GPT analysis", "AI scoring", "OpenAQ integration"]},
            "productInnovation": {"title": "Product & Innovation", "priorities": ["MyAirBubble", "AirNode SaaS", "Sonder"]},
            "airnodeDomainSystems": {"title": "AirNode Domain Systems", "priorities": ["AQ exposure analytics", "ESG dashboard", "Smart city systems"]},
        },
    },
}

CEO_INITIATIVES = [
    {"id": "fedex_fleet", "topic": "strategy", "subtopic": "revenueGrowth", "priority": "Fleet optimisation", "title": "FedEx fleet proposal", "organisation": "FedEx", "stage": "Proposal needed", "description": "Commercial process to sell AQ + AI fleet optimisation.", "next_action": "Prepare a short fleet optimisation proposal and follow-up email."},
    {"id": "dhl_fleet", "topic": "strategy", "subtopic": "revenueGrowth", "priority": "Fleet optimisation", "title": "DHL logistics opportunity", "organisation": "DHL", "stage": "Warm intro", "description": "Potential logistics partner for fleet emissions and AQ optimisation.", "next_action": "Identify warm intro and create a one-page use case."},
    {"id": "port_tyne_fleet", "topic": "strategy", "subtopic": "revenueGrowth", "priority": "Fleet optimisation", "title": "Port of Tyne fleet continuation", "organisation": "Port of Tyne", "stage": "Active relationship", "description": "Extend existing port work into vehicles, logistics and local AQ intelligence.", "next_action": "Create extension proposal options."},
    {"id": "ev_dealership_sales", "topic": "strategy", "subtopic": "revenueGrowth", "priority": "EV advisory", "title": "EV dealership advisory sales", "organisation": "UK dealerships", "stage": "Prospecting", "description": "Use local AQ and health evidence to help dealerships sell EVs.", "next_action": "Build a dealership demo and target first prospects."},
    {"id": "sme_esg_aq", "topic": "strategy", "subtopic": "revenueGrowth", "priority": "ESG consultancy", "title": "SME ESG + AQ audit offer", "organisation": "SMEs", "stage": "Offer design", "description": "Consultancy combining AI audit, air quality metrics and ESG reporting.", "next_action": "Define fixed-price packages."},
    {"id": "innovateuk_grant", "topic": "strategy", "subtopic": "financialLeadership", "priority": "Secure grants", "title": "InnovateUK AI / AQ feasibility grant", "organisation": "Innovate UK", "stage": "Opportunity scanning", "description": "Grant initiative for AI AQ prediction, fleet optimisation or executive intelligence tooling.", "next_action": "Match active calls to AirNode capabilities."},
    {"id": "esa_ideas", "topic": "strategy", "subtopic": "financialLeadership", "priority": "Secure grants", "title": "ESA environmental intelligence proposal", "organisation": "European Space Agency", "stage": "Concept", "description": "EO + AQ concept for environmental monitoring and ESG intelligence.", "next_action": "Create concise EO + AQ concept note."},
    {"id": "bergen_norway_setup", "topic": "strategy", "subtopic": "strategicLeadership", "priority": "Norway expansion", "title": "Bergen / Norway market setup", "organisation": "Norway ecosystem", "stage": "Exploration", "description": "Market entry process covering innovation hubs, customers and partners.", "next_action": "Create Norway target list and outreach actions."},
    {"id": "ceo_portal_initiatives", "topic": "operations", "subtopic": "operationsExecution", "priority": "CEO Portal v2", "title": "CEO Portal initiatives layer", "organisation": "AirNode internal", "stage": "Build", "description": "Track sales and collaboration initiatives beneath CEO priorities.", "next_action": "Deploy frontend and backend initiative updates."},
    {"id": "ai_initiative_classifier", "topic": "technology", "subtopic": "technologyAI", "priority": "AI scoring", "title": "AI initiative classifier", "organisation": "AirNode internal", "stage": "Prototype", "description": "Classify emails or documents to the most relevant initiative.", "next_action": "Connect classifier endpoint to the email detail panel."},
]


def normalise_initiative(row):
    """Map Supabase rows and static rows into the same frontend/classifier shape."""
    if not row:
        return row
    return {
        "id": row.get("id") or row.get("initiative_id"),
        "title": row.get("title"),
        "organisation": row.get("organisation") or row.get("stakeholder"),
        "stakeholder": row.get("stakeholder") or row.get("organisation"),
        "stakeholder_info": row.get("stakeholder_info"),
        "objective": row.get("objective"),
        "description": row.get("description"),
        "products": row.get("products") or [],
        "domain": row.get("domain"),
        "use_case": row.get("use_case"),
        "topic": row.get("topic") or row.get("ceo_topic"),
        "ceo_topic": row.get("ceo_topic") or row.get("topic"),
        "ceo_topic_label": row.get("ceo_topic_label"),
        "subtopic": row.get("subtopic") or row.get("ceo_subtopic"),
        "ceo_subtopic": row.get("ceo_subtopic") or row.get("subtopic"),
        "ceo_subtopic_label": row.get("ceo_subtopic_label"),
        "priority": row.get("priority"),
        "how_began": row.get("how_began"),
        "stage": row.get("stage"),
        "next_action": row.get("next_action"),
        "nextAction": row.get("next_action") or row.get("nextAction"),
        "source": row.get("source", "supabase"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def get_initiatives_from_supabase():
    """Return Supabase initiatives if the ceo_initiatives table exists; otherwise return [] without breaking the API."""
    try:
        rows = supabase.table("ceo_initiatives").select("*").order("created_at", desc=True).execute().data
        return [normalise_initiative(r) for r in (rows or [])]
    except Exception:
        return []


def get_all_initiatives_combined():
    """Use database initiatives first, then include static demo initiatives not already present."""
    db_rows = get_initiatives_from_supabase()
    seen = {r.get("id") for r in db_rows}
    static_rows = [normalise_initiative(r) for r in CEO_INITIATIVES if r.get("id") not in seen]
    return db_rows + static_rows


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


@app.get("/api/ceo/model")
def ceo_model():
    """Return the CEO hierarchy plus starter initiatives for the frontend."""
    return {
        "topics": CEO_PRIORITY_MODEL,
        "initiatives": CEO_INITIATIVES,
    }


@app.get("/api/ceo/initiatives")
def ceo_initiatives(priority: str = None, subtopic: str = None, topic: str = None, all: bool = True):
    """Return initiatives filtered by topic, subtopic or priority. Uses Supabase table ceo_initiatives when available."""
    rows = get_all_initiatives_combined()
    if topic:
        rows = [r for r in rows if r.get("topic") == topic or r.get("ceo_topic") == topic]
    if subtopic:
        rows = [r for r in rows if r.get("subtopic") == subtopic or r.get("ceo_subtopic") == subtopic]
    if priority:
        rows = [r for r in rows if r.get("priority") == priority]
    return rows


@app.post("/api/ceo/initiatives")
def create_ceo_initiative(payload: dict = Body(...)):
    """Create a CEO initiative and save it to Supabase.

    Requires a ceo_initiatives table. If the table is missing, returns the SQL needed to create it.
    """
    now = datetime.now(timezone.utc).isoformat()
    initiative_id = payload.get("id") or str(uuid.uuid4())
    row = {
        "id": initiative_id,
        "title": payload.get("title"),
        "stakeholder": payload.get("stakeholder"),
        "organisation": payload.get("organisation") or payload.get("stakeholder"),
        "stakeholder_info": payload.get("stakeholder_info"),
        "objective": payload.get("objective"),
        "description": payload.get("description"),
        "products": payload.get("products") or [],
        "domain": payload.get("domain"),
        "use_case": payload.get("use_case"),
        "ceo_topic": payload.get("ceo_topic") or payload.get("topic"),
        "ceo_topic_label": payload.get("ceo_topic_label"),
        "topic": payload.get("ceo_topic") or payload.get("topic"),
        "ceo_subtopic": payload.get("ceo_subtopic") or payload.get("subtopic"),
        "ceo_subtopic_label": payload.get("ceo_subtopic_label"),
        "subtopic": payload.get("ceo_subtopic") or payload.get("subtopic"),
        "priority": payload.get("priority"),
        "how_began": payload.get("how_began"),
        "stage": payload.get("stage"),
        "next_action": payload.get("next_action") or payload.get("nextAction"),
        "source": payload.get("source", "manual_ceo_input"),
        "created_at": now,
        "updated_at": now,
    }
    if not row["title"]:
        return {"error": "title is required"}
    try:
        result = supabase.table("ceo_initiatives").insert(row).execute()
        return {"saved": True, "initiative": normalise_initiative(result.data[0] if result.data else row)}
    except Exception as e:
        return {
            "saved": False,
            "error": str(e),
            "message": "Create the Supabase ceo_initiatives table, then retry.",
            "sql_hint": "See supabase_ceo_initiatives.sql in the ZIP."
        }


@app.post("/api/ceo/initiatives/classify")
def classify_to_initiative(payload: dict = Body(...)):
    """
    Classify an email/document to the most relevant CEO initiative.
    User can later confirm, change, or create a new initiative in the frontend.
    """
    text = payload.get("text") or payload.get("body") or ""
    subject = payload.get("subject", "")
    sender = payload.get("sender", "")

    fallback = {
        "initiative_id": CEO_INITIATIVES[0]["id"],
        "initiative_title": CEO_INITIATIVES[0]["title"],
        "topic": CEO_INITIATIVES[0]["topic"],
        "subtopic": CEO_INITIATIVES[0]["subtopic"],
        "priority": CEO_INITIATIVES[0]["priority"],
        "confidence": 0.35,
        "reason": "Fallback match used because AI classification failed.",
        "user_action_needed": True,
        "options": ["confirm", "change_initiative", "create_new_initiative"],
    }

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You classify emails and documents for the AirNode CEO Portal.

Available initiatives JSON:
{json.dumps(get_all_initiatives_combined())}

Content:
Subject: {subject}
Sender: {sender}
Text: {text[:5000]}

Return ONLY valid JSON with this shape:
{{
  "initiative_id": "one available id",
  "initiative_title": "title",
  "topic": "topic key",
  "subtopic": "subtopic key",
  "priority": "priority name",
  "confidence": 0.0,
  "reason": "short explanation",
  "user_action_needed": true,
  "options": ["confirm", "change_initiative", "create_new_initiative"]
}}
""",
            text={"format": {"type": "json_object"}},
        )
        result = json.loads(response.output_text)
        valid_ids = {i["id"] for i in get_all_initiatives_combined()}
        if result.get("initiative_id") not in valid_ids:
            return fallback
        result["user_action_needed"] = True
        result["options"] = ["confirm", "change_initiative", "create_new_initiative"]
        return result
    except Exception as e:
        fallback["raw_error"] = str(e)
        return fallback


@app.post("/api/ceo/initiatives/confirm")
def confirm_initiative_classification(payload: dict = Body(...)):
    """Save a user-confirmed link between an email/document and an initiative."""
    row = {
        "email_id": payload.get("email_id"),
        "document_id": payload.get("document_id"),
        "initiative_id": payload.get("initiative_id"),
        "suggested_initiative_id": payload.get("suggested_initiative_id"),
        "confidence": payload.get("confidence"),
        "reason": payload.get("reason"),
        "confirmed_by": payload.get("confirmed_by", "CEO"),
        "source": payload.get("source", "user_confirmed"),
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        result = supabase.table("initiative_email_links").insert(row).execute()
        return {"saved": True, "link": result.data}
    except Exception as e:
        return {"saved": False, "error": str(e), "message": "Create initiative_email_links table before using confirmations."}


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
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)





@app.get("/api/gmail/connet")
def gmail_connet():
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

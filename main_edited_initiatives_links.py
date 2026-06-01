"""
AirNode CEO Portal API
----------------------
Clean FastAPI backend for:
- CEO inbox and AI email analysis
- Gmail OAuth and sync
- Supabase persistence
- CEO topics / subtopics / priorities / initiatives
- Initiative creation and export support
- Email/document to initiative classification with user confirmation

Deploy:
1. Rename this file to main.py
2. Commit to https://github.com/wegiangb/Airnode-ceoportal-api
3. Let Render redeploy
4. Run the Supabase SQL table setup for ceo_initiatives + ceo_initiative_links
"""

import base64
import json
import os
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from openai import OpenAI
from supabase import create_client

# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------

app = FastAPI(title="AirNode CEO Portal API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Static CEO model fallback
# -----------------------------------------------------------------------------

CEO_TOPICS: Dict[str, Dict[str, Any]] = {
    "strategy": {
        "title": "Strategy, Growth & External Leadership",
        "short": "Strategy & Growth",
        "why": "Sets direction, chooses markets, secures growth and builds external influence.",
        "subtopics": {
            "strategicLeadership": {
                "title": "Strategic Leadership",
                "priorities": ["Ports strategy", "Norway expansion", "AQ SaaS positioning"],
            },
            "revenueGrowth": {
                "title": "Revenue & Growth",
                "priorities": ["Fleet optimisation", "EV advisory", "ESG consultancy"],
            },
            "financialLeadership": {
                "title": "Financial Leadership",
                "priorities": ["Secure grants", "Investor follow-up", "Project margins"],
            },
            "externalRepresentation": {
                "title": "External Representation",
                "priorities": ["Government meetings", "Conference follow-up", "Stakeholder briefings"],
            },
        },
    },
    "operations": {
        "title": "Operations, Delivery & Organisational Leadership",
        "short": "Operations & Delivery",
        "why": "Turns strategy into delivery, manages execution and reduces operational risk.",
        "subtopics": {
            "operationsExecution": {
                "title": "Operations & Execution",
                "priorities": ["CEO Portal v2", "Dashboard delivery", "Proposal pipeline"],
            },
            "peopleLeadership": {
                "title": "People & Leadership",
                "priorities": ["Advisor coordination", "Capability gaps", "Team workflows"],
            },
            "riskGovernance": {
                "title": "Risk & Governance",
                "priorities": ["AI governance", "ESG evidence", "Cyber resilience"],
            },
        },
    },
    "intelligence": {
        "title": "Intelligence, Decision-Making & Coordination",
        "short": "Intelligence & Coordination",
        "why": "Helps the CEO see what matters, coordinate action and preserve organisational memory.",
        "subtopics": {
            "executiveIntelligence": {
                "title": "Executive Intelligence",
                "priorities": ["High value emails", "Strategic risks", "Opportunity scoring"],
            },
            "organisationalMemory": {
                "title": "Organisational Memory",
                "priorities": ["Relationship memory", "Proposal archive", "Decision history"],
            },
            "coordinationSystems": {
                "title": "Coordination Systems",
                "priorities": ["Reply backlog", "Delegated actions", "Blocked proposals"],
            },
        },
    },
    "technology": {
        "title": "Technology, Innovation & Platform Systems",
        "short": "Technology & Innovation",
        "why": "Builds scalable AI, product and environmental intelligence capabilities.",
        "subtopics": {
            "technologyAI": {
                "title": "Technology & AI",
                "priorities": ["GPT analysis", "AI scoring", "OpenAQ integration"],
            },
            "productInnovation": {
                "title": "Product & Innovation",
                "priorities": ["MyAirBubble", "AirNode SaaS", "AirNode Sonder"],
            },
            "airnodeDomainSystems": {
                "title": "AirNode Domain Systems",
                "priorities": ["AQ exposure analytics", "ESG dashboard", "Smart city systems"],
            },
        },
    },
}

STATIC_INITIATIVES: List[Dict[str, Any]] = [
    {
        "id": "fedex_fleet",
        "title": "FedEx fleet proposal",
        "organisation": "FedEx",
        "objective": "Sell AQ + AI fleet optimisation to a parcel logistics operator.",
        "description": "Commercial process to position AirNode fleet exposure, routing and emissions intelligence.",
        "products": ["Fleet Optimisation", "Air Quality Analytics", "AI Analysis"],
        "domain": "Transport and logistics",
        "use_case": "Fleet routing and emissions intelligence",
        "topic": "strategy",
        "subtopic": "revenueGrowth",
        "priority": "Fleet optimisation",
        "how_began": "Warm intro",
        "stage": "Proposal needed",
        "next_action": "Prepare a short fleet optimisation proposal and follow-up email.",
        "source": "static",
    },
    {
        "id": "dhl_fleet",
        "title": "DHL logistics opportunity",
        "organisation": "DHL",
        "objective": "Develop logistics AQ and emissions optimisation opportunity.",
        "description": "Potential logistics partner for fleet emissions, route risk and AQ optimisation.",
        "products": ["Fleet Optimisation", "ESG Intelligence"],
        "domain": "Transport and logistics",
        "use_case": "Logistics AQ exposure and optimisation",
        "topic": "strategy",
        "subtopic": "revenueGrowth",
        "priority": "Fleet optimisation",
        "how_began": "Warm intro",
        "stage": "Warm intro",
        "next_action": "Identify warm intro and create a one-page use case.",
        "source": "static",
    },
    {
        "id": "port_tyne_continuation",
        "title": "Port of Tyne continuation",
        "organisation": "Port of Tyne",
        "objective": "Extend port work into vehicles, logistics, vessels and local AQ intelligence.",
        "description": "Collaboration/sales initiative around port emissions, fleet activity and AQ monitoring.",
        "products": ["Air Quality Analytics", "Sensors", "ESG Intelligence"],
        "domain": "Ports and maritime",
        "use_case": "Port authority emissions and AQ intelligence",
        "topic": "strategy",
        "subtopic": "revenueGrowth",
        "priority": "Fleet optimisation",
        "how_began": "Existing relationship",
        "stage": "Active relationship",
        "next_action": "Create extension proposal options.",
        "source": "static",
    },
    {
        "id": "innovateuk_grant",
        "title": "InnovateUK AI / AQ feasibility grant",
        "organisation": "Innovate UK",
        "objective": "Secure innovation funding for AI and air quality product development.",
        "description": "Grant initiative for AI AQ prediction, fleet optimisation or executive intelligence tooling.",
        "products": ["AI Analysis", "Air Quality Analytics", "CEO Portal"],
        "domain": "Innovation funding",
        "use_case": "Grant-funded AI and AQ feasibility",
        "topic": "strategy",
        "subtopic": "financialLeadership",
        "priority": "Secure grants",
        "how_began": "Grant scan",
        "stage": "Opportunity scanning",
        "next_action": "Match active calls to AirNode capabilities.",
        "source": "static",
    },
    {
        "id": "ceo_portal_initiatives",
        "title": "CEO Portal initiatives layer",
        "organisation": "AirNode internal",
        "objective": "Turn the CEO portal into an initiative-led executive management system.",
        "description": "Track sales, partnerships and collaborations beneath CEO topics and priorities.",
        "products": ["CEO Portal", "AI Analysis"],
        "domain": "Business management",
        "use_case": "Executive initiative coordination",
        "topic": "operations",
        "subtopic": "operationsExecution",
        "priority": "CEO Portal v2",
        "how_began": "Internal build",
        "stage": "Build",
        "next_action": "Deploy frontend and backend initiative updates.",
        "source": "static",
    },
    {
        "id": "ai_initiative_classifier",
        "title": "AI initiative classifier",
        "organisation": "AirNode internal",
        "objective": "Classify emails and documents to the most relevant initiative.",
        "description": "AI workflow where users confirm, change or create initiative links.",
        "products": ["CEO Portal", "AI Analysis"],
        "domain": "AI workflow automation",
        "use_case": "Email-to-initiative classification",
        "topic": "technology",
        "subtopic": "technologyAI",
        "priority": "AI scoring",
        "how_began": "Internal build",
        "stage": "Prototype",
        "next_action": "Connect classifier endpoint to email detail panel.",
        "source": "static",
    },
]

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
    "Fleet optimisation",
    "EV advisory",
    "ESG consultancy",
    "Secure grants",
    "CEO Portal v2",
    "AI scoring",
    "Reduce CEO information overload",
]


# Supabase table names used by the executive knowledge graph pages.
INITIATIVES_TABLE = "ceo_initiatives"
INITIATIVE_LINKS_TABLE = "ceo_initiative_links"

CEO_LOOKUP_TABLES = {
    "stakeholders": "ceo_stakeholders",
    "industries": "ceo_industries",
    "use_cases": "ceo_use_cases",
    "client_problems": "ceo_client_problems",
    "client_opportunities": "ceo_client_opportunities",
    "products": "ceo_products",
    "services": "ceo_services",
    "priorities": "ceo_priorities",
}

# Only these columns are inserted into ceo_initiatives.
# This avoids Supabase errors if the frontend sends extra UI-only fields.
INITIATIVE_COLUMNS = {
    "title", "objective", "description",
    "stakeholder_id", "industry_id", "use_case_id", "problem_id",
    "opportunity_id", "product_id", "service_id", "priority_id",
    "organisation", "contact_name", "contact_email", "contact_role",
    "origin", "stage", "estimated_value", "owner", "next_action",
    "status", "created_at", "updated_at",
}

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_supabase():
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY.")
    return supabase


def safe_supabase_table(table_name: str):
    db = require_supabase()
    return db.table(table_name)


def slugify(text: str) -> str:
    text = (text or "initiative").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "initiative"


def normalise_initiative(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map form/front-end/Supabase rows into one consistent shape."""
    return {
        "id": row.get("id") or row.get("initiative_id") or slugify(row.get("title", "initiative")),
        "title": row.get("title") or row.get("name"),
        "organisation": row.get("organisation") or row.get("stakeholder") or row.get("stakeholder_organisation"),
        "contact_name": row.get("contact_name"),
        "contact_email": row.get("contact_email"),
        "contact_role": row.get("contact_role"),
        "stakeholder_info": row.get("stakeholder_info"),
        "objective": row.get("objective"),
        "description": row.get("description"),
        "products": row.get("products") or row.get("airnode_products") or [],
        "domain": row.get("domain"),
        "use_case": row.get("use_case"),
        "topic": row.get("topic") or row.get("ceo_topic"),
        "ceo_topic": row.get("ceo_topic") or row.get("topic"),
        "ceo_topic_label": row.get("ceo_topic_label"),
        "subtopic": row.get("subtopic") or row.get("ceo_subtopic"),
        "ceo_subtopic": row.get("ceo_subtopic") or row.get("subtopic"),
        "ceo_subtopic_label": row.get("ceo_subtopic_label"),
        "priority": row.get("priority") or row.get("ceo_priority"),
        "how_began": row.get("how_began") or row.get("origin"),
        "stage": row.get("stage") or "Active",
        "estimated_value": row.get("estimated_value"),
        "owner": row.get("owner"),
        "target_date": row.get("target_date"),
        "next_action": row.get("next_action") or row.get("nextAction"),
        "source": row.get("source", "supabase"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def get_initiatives_from_supabase() -> List[Dict[str, Any]]:
    if not supabase:
        return []
    try:
        rows = supabase.table(INITIATIVES_TABLE).select("*").order("created_at", desc=True).execute().data
        return [normalise_initiative(r) for r in (rows or [])]
    except Exception:
        # Table may not exist yet. Return fallback rather than break dashboard.
        return []


def get_all_initiatives(include_static_if_empty: bool = True) -> List[Dict[str, Any]]:
    rows = get_initiatives_from_supabase()
    if rows:
        return rows
    return STATIC_INITIATIVES if include_static_if_empty else []



def initiative_db_payload(payload: Dict[str, Any], is_create: bool = True) -> Dict[str, Any]:
    """Return only columns that should be saved to ceo_initiatives.

    The UX can send extra fields such as products arrays, labels, or UI keys.
    Those are ignored here or stored separately in ceo_initiative_links.
    """
    mapped = {
        "title": payload.get("title") or payload.get("name") or payload.get("initiative_title"),
        "objective": payload.get("objective"),
        "description": payload.get("description"),
        "stakeholder_id": payload.get("stakeholder_id"),
        "industry_id": payload.get("industry_id"),
        "use_case_id": payload.get("use_case_id"),
        "problem_id": payload.get("problem_id"),
        "opportunity_id": payload.get("opportunity_id"),
        "product_id": payload.get("product_id"),
        "service_id": payload.get("service_id"),
        "priority_id": payload.get("priority_id"),
        "organisation": payload.get("organisation") or payload.get("stakeholder_organisation"),
        "contact_name": payload.get("contact_name"),
        "contact_email": payload.get("contact_email"),
        "contact_role": payload.get("contact_role"),
        "origin": payload.get("origin") or payload.get("how_began"),
        "stage": payload.get("stage") or ("Prospecting" if is_create else None),
        "estimated_value": payload.get("estimated_value"),
        "owner": payload.get("owner"),
        "next_action": payload.get("next_action") or payload.get("nextAction"),
        "status": payload.get("status") or ("Active" if is_create else None),
        "updated_at": now_iso(),
    }
    if is_create:
        mapped["created_at"] = payload.get("created_at") or now_iso()

    return {k: v for k, v in mapped.items() if k in INITIATIVE_COLUMNS and v not in (None, "")}


def extract_many(value: Any) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    if isinstance(value, str):
        # Accept JSON arrays or comma separated strings from simple forms.
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed if v not in (None, "")]
        except Exception:
            pass
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(value)]


def save_initiative_reference_links(initiative_id: Optional[str], payload: Dict[str, Any], replace_existing: bool = False):
    """Store optional many-to-many links in ceo_initiative_links.

    This is used when one initiative relates to multiple products, services,
    stakeholders, documents, emails or meetings.
    """
    if not initiative_id or not supabase:
        return

    link_inputs = {
        "stakeholder": extract_many(payload.get("stakeholder_ids")),
        "industry": extract_many(payload.get("industry_ids")),
        "use_case": extract_many(payload.get("use_case_ids")),
        "problem": extract_many(payload.get("problem_ids")),
        "opportunity": extract_many(payload.get("opportunity_ids")),
        "product": extract_many(payload.get("product_ids") or payload.get("products")),
        "service": extract_many(payload.get("service_ids") or payload.get("services")),
        "priority": extract_many(payload.get("priority_ids")),
        "email": extract_many(payload.get("email_ids")),
        "document": extract_many(payload.get("document_ids")),
        "meeting": extract_many(payload.get("meeting_ids")),
        "task": extract_many(payload.get("task_ids")),
    }

    try:
        if replace_existing:
            supabase.table(INITIATIVE_LINKS_TABLE).delete().eq("initiative_id", initiative_id).execute()

        rows = []
        for link_type, ids in link_inputs.items():
            for linked_id in ids:
                rows.append({
                    "initiative_id": initiative_id,
                    "link_type": link_type,
                    "linked_id": linked_id,
                    "source": "user_selected",
                    "created_at": now_iso(),
                })
        if rows:
            supabase.table(INITIATIVE_LINKS_TABLE).insert(rows).execute()
    except Exception:
        # Do not fail initiative creation if optional links table is missing.
        pass


def score_email(analysis: Dict[str, Any]) -> int:
    levels = {"low": 1, "medium": 2, "high": 3}
    score = (
        levels.get(analysis.get("revenue_potential", "low"), 1) * 3
        + levels.get(analysis.get("strategic_value", "low"), 1) * 3
        + levels.get(analysis.get("time_saving", "low"), 1) * 2
        + levels.get(analysis.get("urgency", "low"), 1) * 2
    )
    if analysis.get("priority_aligned"):
        score += 5
    return min(score, 30)


def keyword_classify(email_text: str, initiatives: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fallback classifier when OpenAI is not configured or fails."""
    text = (email_text or "").lower()
    best = None
    best_score = 0
    alternatives = []

    for init in initiatives:
        fields = [
            init.get("title", ""),
            init.get("organisation", ""),
            init.get("objective", ""),
            init.get("description", ""),
            init.get("domain", ""),
            init.get("use_case", ""),
            init.get("priority", ""),
            " ".join(init.get("products") or []),
        ]
        tokens = set(re.findall(r"[a-zA-Z0-9]{3,}", " ".join(fields).lower()))
        score = sum(1 for token in tokens if token in text)
        if score > best_score:
            best_score = score
            best = init
        alternatives.append({
            "initiative_id": init.get("id"),
            "initiative_title": init.get("title"),
            "confidence": min(score / 10, 0.75),
        })

    alternatives = sorted(alternatives, key=lambda x: x["confidence"], reverse=True)[:3]
    best = best or (initiatives[0] if initiatives else {})

    return {
        "suggested_initiative_id": best.get("id"),
        "suggested_initiative_title": best.get("title"),
        "confidence": min(0.45 + best_score / 20, 0.75) if best_score else 0.25,
        "reason": "Fallback keyword match based on initiative title, organisation, products, domain and description.",
        "alternatives": alternatives,
        "needs_user_confirmation": True,
        "classifier": "keyword_fallback",
    }

# -----------------------------------------------------------------------------
# Health / debug
# -----------------------------------------------------------------------------


@app.get("/")
def home():
    return {
        "status": "AirNode CEO Portal API is running",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "openai_configured": bool(client),
        "supabase_configured": bool(supabase),
        "gmail_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI),
        "time": now_iso(),
    }

# -----------------------------------------------------------------------------
# CEO model and initiatives
# -----------------------------------------------------------------------------


@app.get("/api/ceo/model")
def ceo_model():
    return {
        "topics": CEO_TOPICS,
        "initiatives": get_all_initiatives(),
    }


@app.get("/api/ceo/initiatives")
def list_initiatives():
    return get_all_initiatives()


@app.get("/api/ceo/initiatives/{initiative_id}")
def get_initiative(initiative_id: str):
    for initiative in get_all_initiatives():
        if str(initiative.get("id")) == str(initiative_id):
            return initiative
    raise HTTPException(status_code=404, detail="Initiative not found")


@app.post("/api/ceo/initiatives")
def create_initiative(payload: Dict[str, Any] = Body(...)):
    """Create an initiative in Supabase.

    The frontend may send rich UI fields. This endpoint stores only columns that
    exist in ceo_initiatives, then stores optional many-to-many links in
    ceo_initiative_links.
    """
    db = require_supabase()
    insert_payload = initiative_db_payload(payload, is_create=True)

    if not insert_payload.get("title"):
        raise HTTPException(status_code=400, detail="title is required")

    result = db.table(INITIATIVES_TABLE).insert(insert_payload).execute()
    created = result.data[0] if result.data else insert_payload
    initiative_id = created.get("id")

    # Optional generic links from the form, for many-to-many relationships.
    save_initiative_reference_links(initiative_id, payload)

    return {"created": True, "initiative": normalise_initiative(created)}


@app.patch("/api/ceo/initiatives/{initiative_id}")
def update_initiative(initiative_id: str, payload: Dict[str, Any] = Body(...)):
    db = require_supabase()
    update_payload = initiative_db_payload(payload, is_create=False)
    update_payload["updated_at"] = now_iso()

    if not update_payload:
        raise HTTPException(status_code=400, detail="No valid initiative fields supplied")

    result = db.table(INITIATIVES_TABLE).update(update_payload).eq("id", initiative_id).execute()
    save_initiative_reference_links(initiative_id, payload, replace_existing=True)

    return {"updated": True, "initiative": normalise_initiative(result.data[0]) if result.data else None}


@app.delete("/api/ceo/initiatives/{initiative_id}")
def delete_initiative(initiative_id: str):
    db = require_supabase()
    result = db.table(INITIATIVES_TABLE).delete().eq("id", initiative_id).execute()
    return {"deleted": True, "rows": result.data}


@app.post("/api/ceo/initiatives/classify")
def classify_to_initiative(payload: Dict[str, Any] = Body(...)):
    subject = payload.get("subject", "")
    sender = payload.get("sender", "")
    body = payload.get("body", "")
    document_text = payload.get("text", "")
    email_id = payload.get("email_id")
    initiatives = get_all_initiatives()

    combined_text = f"Subject: {subject}\nSender: {sender}\nBody/Text: {body or document_text}"

    if not initiatives:
        return {
            "suggested_initiative_id": None,
            "suggested_initiative_title": None,
            "confidence": 0,
            "reason": "No initiatives available to classify against.",
            "alternatives": [],
            "needs_user_confirmation": True,
        }

    if not client:
        result = keyword_classify(combined_text, initiatives)
    else:
        try:
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=f"""
You are classifying an email or document for the AirNode CEO Portal.

Choose the most relevant initiative from the available list.

Email or document:
{combined_text}

Available initiatives:
{json.dumps(initiatives, indent=2)}

Return ONLY valid JSON with this exact shape:
{{
  "suggested_initiative_id": "string",
  "suggested_initiative_title": "string",
  "confidence": 0.0,
  "reason": "string",
  "alternatives": [
    {{
      "initiative_id": "string",
      "initiative_title": "string",
      "confidence": 0.0
    }}
  ],
  "needs_user_confirmation": true
}}
""",
                text={"format": {"type": "json_object"}},
            )
            result = json.loads(response.output_text)
            result["classifier"] = "openai"
        except Exception as exc:
            result = keyword_classify(combined_text, initiatives)
            result["openai_error"] = str(exc)

    # Store AI suggestion if Supabase table exists.
    if supabase and email_id and result.get("suggested_initiative_id"):
        try:
            supabase.table(INITIATIVE_LINKS_TABLE).insert({
                "initiative_id": result.get("suggested_initiative_id"),
                "link_type": "email",
                "linked_id": str(email_id),
                "confidence": result.get("confidence"),
                "reason": result.get("reason"),
                "source": "ai_suggested",
                "created_at": now_iso(),
            }).execute()
        except Exception:
            pass

    return result


@app.post("/api/ceo/initiatives/confirm")
def confirm_initiative_link(payload: Dict[str, Any] = Body(...)):
    db = require_supabase()
    email_id = payload.get("email_id")
    initiative_id = payload.get("initiative_id")

    if not initiative_id:
        raise HTTPException(status_code=400, detail="initiative_id is required")

    row = {
        "initiative_id": initiative_id,
        "link_type": payload.get("link_type", "email"),
        "linked_id": str(email_id or payload.get("linked_id") or ""),
        "confidence": payload.get("confidence"),
        "reason": payload.get("reason"),
        "source": "user_confirmed",
        "created_at": now_iso(),
    }
    if not row["linked_id"]:
        raise HTTPException(status_code=400, detail="email_id or linked_id is required")
    result = db.table(INITIATIVE_LINKS_TABLE).insert(row).execute()
    return {"confirmed": True, "link": result.data[0] if result.data else row}


# -----------------------------------------------------------------------------
# Lookup / taxonomy tables for the extra UX pages
# -----------------------------------------------------------------------------


@app.get("/api/ceo/lookups/{record_type}")
def list_lookup_records(record_type: str):
    table = CEO_LOOKUP_TABLES.get(record_type)
    if not table:
        raise HTTPException(status_code=404, detail=f"Unknown record_type. Use one of: {list(CEO_LOOKUP_TABLES.keys())}")
    db = require_supabase()
    return db.table(table).select("*").order("created_at", desc=True).execute().data


@app.post("/api/ceo/lookups/{record_type}")
def create_lookup_record(record_type: str, payload: Dict[str, Any] = Body(...)):
    table = CEO_LOOKUP_TABLES.get(record_type)
    if not table:
        raise HTTPException(status_code=404, detail=f"Unknown record_type. Use one of: {list(CEO_LOOKUP_TABLES.keys())}")
    db = require_supabase()
    payload = dict(payload)
    payload.pop("id", None)
    payload["created_at"] = payload.get("created_at") or now_iso()
    if "updated_at" in payload:
        payload["updated_at"] = now_iso()
    return {"created": True, "record": db.table(table).insert(payload).execute().data[0]}


@app.patch("/api/ceo/lookups/{record_type}/{record_id}")
def update_lookup_record(record_type: str, record_id: str, payload: Dict[str, Any] = Body(...)):
    table = CEO_LOOKUP_TABLES.get(record_type)
    if not table:
        raise HTTPException(status_code=404, detail=f"Unknown record_type. Use one of: {list(CEO_LOOKUP_TABLES.keys())}")
    db = require_supabase()
    payload = dict(payload)
    payload.pop("id", None)
    payload["updated_at"] = now_iso()
    return {"updated": True, "record": db.table(table).update(payload).eq("id", record_id).execute().data}


@app.delete("/api/ceo/lookups/{record_type}/{record_id}")
def delete_lookup_record(record_type: str, record_id: str):
    table = CEO_LOOKUP_TABLES.get(record_type)
    if not table:
        raise HTTPException(status_code=404, detail=f"Unknown record_type. Use one of: {list(CEO_LOOKUP_TABLES.keys())}")
    db = require_supabase()
    return {"deleted": True, "rows": db.table(table).delete().eq("id", record_id).execute().data}


# -----------------------------------------------------------------------------
# Email analysis / dashboard
# -----------------------------------------------------------------------------


def analyse_email(email: Dict[str, Any]) -> Dict[str, Any]:
    fallback = {
        "summary": email.get("subject", "No subject"),
        "value_to_reader": "Potentially relevant email.",
        "why": "Fallback analysis used because OpenAI is unavailable or returned invalid JSON.",
        "ceo_role": "Intelligence, Decision-Making & Coordination",
        "category": "Information",
        "revenue_potential": "low",
        "strategic_value": "medium",
        "time_saving": "low",
        "urgency": "low",
        "priority_aligned": False,
        "reply_needed": "Maybe",
        "reply_timing": "Later",
        "suggested_owner": "CEO",
        "owner_reason": "Fallback owner.",
        "score_explanation": ["Fallback scoring applied"],
    }

    if not client:
        fallback["raw_error"] = "OpenAI is not configured"
        return fallback

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You are analysing emails for the CEO of AirNode.

CEO priorities:
{json.dumps(PRIORITIES)}

Email:
Subject: {email.get('subject', '')}
Sender: {email.get('sender', '')}
Body: {email.get('body', '')}

Return ONLY valid JSON. No markdown.

Required JSON shape:
{{
  "summary": "string",
  "value_to_reader": "string",
  "why": "string",
  "ceo_role": "Strategy / Growth / Operations / Intelligence / Technology",
  "category": "Partnership / Sales / Funding / Operations / Risk / Information",
  "revenue_potential": "low | medium | high",
  "strategic_value": "low | medium | high",
  "time_saving": "low | medium | high",
  "urgency": "low | medium | high",
  "priority_aligned": true,
  "reply_needed": "Yes | No | Maybe",
  "reply_timing": "24h | 48h | This week | Later",
  "suggested_owner": "CEO",
  "owner_reason": "string",
  "score_explanation": ["string"]
}}
""",
            text={"format": {"type": "json_object"}},
        )
        return json.loads(response.output_text) if response.output_text else fallback
    except Exception as exc:
        fallback["raw_error"] = str(exc)
        return fallback


def email_exists(subject: str, sender_email: str) -> Optional[Dict[str, Any]]:
    db = require_supabase()
    existing = db.table("emails").select("id").eq("subject", subject).eq("sender_email", sender_email).limit(1).execute()
    return existing.data[0] if existing.data else None


def save_email(email: Dict[str, Any]) -> str:
    db = require_supabase()
    subject = email.get("subject") or "(No subject)"
    sender_email = email.get("sender_email") or email.get("sender") or ""
    existing = email_exists(subject, sender_email)
    if existing:
        return existing["id"]

    row = db.table("emails").insert({
        "subject": subject,
        "sender": email.get("sender"),
        "sender_email": sender_email,
        "body": email.get("body") or "",
        "received_at": email.get("received_at") or now_iso(),
    }).execute()
    return row.data[0]["id"]


def save_analysis(email_id: str, analysis: Dict[str, Any], score: int):
    db = require_supabase()
    existing = db.table("email_analysis").select("id").eq("email_id", email_id).limit(1).execute()
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
        db.table("email_analysis").update(payload).eq("email_id", email_id).execute()
    else:
        db.table("email_analysis").insert(payload).execute()


def ensure_decision_row(email_id: str):
    db = require_supabase()
    existing = db.table("email_decisions").select("id").eq("email_id", email_id).limit(1).execute()
    if not existing.data:
        db.table("email_decisions").insert({"email_id": email_id, "status": "not_reviewed"}).execute()


@app.post("/api/test-db")
def test_db():
    db = require_supabase()
    row = db.table("emails").insert({
        "subject": "Database test email",
        "sender": "AirNode Test",
        "sender_email": "test@airnode.co.uk",
        "body": "Testing Supabase connection.",
        "received_at": now_iso(),
    }).execute()
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
        processed.append({"email_id": email_id, "subject": email["subject"], "score": score})
    return {"processed": processed}


@app.post("/api/ingest-email")
def ingest_email(email: Dict[str, Any] = Body(...)):
    email_id = save_email(email)
    analysis = analyse_email(email)
    score = score_email(analysis)
    save_analysis(email_id, analysis, score)
    ensure_decision_row(email_id)

    # Also suggest initiative so the frontend can ask user to confirm.
    classification = classify_to_initiative({
        "email_id": email_id,
        "subject": email.get("subject"),
        "sender": email.get("sender"),
        "body": email.get("body"),
    })

    return {"email_id": email_id, "analysis": analysis, "score": score, "initiative_suggestion": classification}


@app.get("/api/dashboard")
def dashboard():
    db = require_supabase()
    emails = db.table("emails").select("*").execute().data
    analysis_rows = db.table("email_analysis").select("*").execute().data
    decision_rows = db.table("email_decisions").select("*").execute().data

    analysis_by_email = {row["email_id"]: row for row in analysis_rows}
    decision_by_email = {row["email_id"]: row for row in decision_rows}

    # Optional initiative links.
    initiative_by_email: Dict[str, List[Dict[str, Any]]] = {}
    try:
        links = db.table(INITIATIVE_LINKS_TABLE).select("*").eq("link_type", "email").execute().data or []
        for link in links:
            if link.get("linked_id"):
                initiative_by_email.setdefault(str(link["linked_id"]), []).append(link)
    except Exception:
        pass

    results = []
    for email in emails:
        a = analysis_by_email.get(email["id"])
        d = decision_by_email.get(email["id"], {})
        if not a:
            continue
        results.append({
            "id": email["id"],
            "subject": email.get("subject"),
            "sender": email.get("sender"),
            "sender_email": email.get("sender_email"),
            "body": email.get("body"),
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
            "initiative_links": initiative_by_email.get(email["id"], []),
        })
    return sorted(results, key=lambda x: x.get("score") or 0, reverse=True)


@app.post("/api/email/{email_id}/decision")
def update_decision(email_id: str, payload: Dict[str, Any] = Body(...)):
    db = require_supabase()
    status = payload.get("status", "reviewed")
    allowed = ["not_reviewed", "reviewed", "delegated", "ignored", "deferred", "replied"]
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use one of: {allowed}")

    existing = db.table("email_decisions").select("id").eq("email_id", email_id).limit(1).execute()
    decision_payload = {
        "email_id": email_id,
        "status": status,
        "assigned_owner": payload.get("assigned_owner"),
        "decision_note": payload.get("decision_note"),
        "deferred_until": payload.get("deferred_until"),
        "updated_at": now_iso(),
    }
    if existing.data:
        row = db.table("email_decisions").update(decision_payload).eq("email_id", email_id).execute()
    else:
        row = db.table("email_decisions").insert(decision_payload).execute()
    return {"updated": row.data}

# -----------------------------------------------------------------------------
# Gmail integration
# -----------------------------------------------------------------------------


def decode_body(payload: Dict[str, Any]) -> str:
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


def header_value(headers: List[Dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


@app.get("/api/gmail/connect")
def gmail_connect():
    if not (GOOGLE_CLIENT_ID and GOOGLE_REDIRECT_URI):
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")
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


@app.get("/api/gmail/callback")
def gmail_callback(request: Request):
    db = require_supabase()
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
            timeout=30,
        )
        token_json = token_response.json()
        if token_response.status_code != 200:
            return {"success": False, "step": "token_exchange_failed", "google_error": token_json}

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

        db.table("gmail_tokens").insert({
            "user_email": user_email,
            "token_json": {
                "token": token_json["access_token"],
                "refresh_token": token_json.get("refresh_token"),
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "scopes": GMAIL_SCOPES,
            },
        }).execute()
        return {"success": True, "status": "gmail_connected", "email": user_email}
    except Exception as exc:
        return {"success": False, "step": "exception", "error": str(exc)}


@app.post("/api/gmail/sync")
def gmail_sync():
    db = require_supabase()
    token_rows = db.table("gmail_tokens").select("*").execute().data
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
    messages = service.users().messages().list(userId="me", maxResults=10, q="newer_than:14d").execute().get("messages", [])

    processed = []
    for msg in messages:
        full = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        payload = full.get("payload", {})
        headers = payload.get("headers", [])
        subject = header_value(headers, "Subject") or "(No subject)"
        sender = header_value(headers, "From")
        body = decode_body(payload) or full.get("snippet", "")
        email = {"subject": subject, "sender": sender, "sender_email": sender, "body": body}
        email_id = save_email(email)
        analysis = analyse_email(email)
        score = score_email(analysis)
        save_analysis(email_id, analysis, score)
        ensure_decision_row(email_id)

        # Save AI initiative suggestion if possible.
        classification = classify_to_initiative({"email_id": email_id, "subject": subject, "sender": sender, "body": body})
        processed.append({"email_id": email_id, "subject": subject, "score": score, "initiative_suggestion": classification})

    return {"synced": len(processed), "processed": processed}

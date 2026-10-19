"""
FastAPI Production Web Server & Webhook Handler for Render.com
Provides REST API, live Webhook handlers, interactive status dashboard,
and trigger endpoints for Render deployment.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pydantic

from src.cleaning.normalizer import DataNormalizer
from src.cleaning.deduplicator import DeduplicationEngine
from src.qualification.lead_scorer import LeadScoringEngine
from src.personalization.generator import PersonalizationGenerator
from src.state_machine.lead_lifecycle import LeadLifecycleManager
from src.reply_classifier.classifier import ReplyClassifier
from src.outreach.email_sender import EmailSender
from src.outreach.whatsapp_sender import WhatsAppSender
from src.outreach.linkedin_queue import LinkedInReviewQueue
from src.analytics.daily_reporter import DailyReporter

# Initialize FastAPI App
app = FastAPI(
    title="B2B Lead Generation & Outreach Automation API",
    description="Delhi NCR Production B2B Lead Gen, AI Qualification & Multi-channel Outreach System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory / File State Cache
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "sample_delhi_ncr_leads.json")
SUPPRESSION_FILE = os.path.join(os.path.dirname(__file__), "database", "google_sheets_crm", "templates", "suppression_list.csv")

# Load initial state
def load_leads():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

CURRENT_LEADS = load_leads()
ACTIVITY_LOGS = []
SUPPRESSED_EMAILS = {"optout@competitor.example.com"}

# -------------------------------------------------------------
# 1. Healthcheck Endpoint (Required for Render)
# -------------------------------------------------------------
@app.get("/health")
def healthcheck():
    return {
        "status": "HEALTHY",
        "timestamp": datetime.now().isoformat(),
        "total_leads_cached": len(CURRENT_LEADS),
        "environment": os.getenv("RENDER_ENV", "render-production"),
        "service": "b2b-outreach-engine"
    }

# -------------------------------------------------------------
# 2. Live Dashboard UI
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard_ui():
    cat_a = len([l for l in CURRENT_LEADS if l.get("lead_category") == "A"])
    cat_b = len([l for l in CURRENT_LEADS if l.get("lead_category") == "B"])
    contacted = len([l for l in CURRENT_LEADS if l.get("lead_state") == "CONTACTED"])
    suppressed = len(SUPPRESSED_EMAILS)

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>B2B Outreach Command Center - Delhi NCR</title>
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 min-h-screen p-6 font-sans">
      <div class="max-w-6xl mx-auto space-y-6">
        
        <!-- Header -->
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-xl">
          <div>
            <div class="flex items-center space-x-3">
              <span class="inline-block w-3 h-3 bg-emerald-400 rounded-full animate-pulse"></span>
              <h1 class="text-2xl font-bold text-white tracking-wide">B2B Outreach Automation System</h1>
            </div>
            <p class="text-slate-400 text-sm mt-1">Target Market: Delhi NCR (Real Estate, Healthcare, Education) | Render Live Server</p>
          </div>
          <div class="mt-4 md:mt-0 flex space-x-3">
            <button onclick="triggerPipeline(true)" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm transition shadow-md">
              Run Pilot Simulation
            </button>
            <a href="/docs" target="_blank" class="bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium px-4 py-2 rounded-lg text-sm transition border border-slate-600">
              API Docs
            </a>
          </div>
        </div>

        <!-- Metric Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-slate-800 p-5 rounded-xl border border-slate-700">
            <div class="text-slate-400 text-xs uppercase font-semibold">Total Leads</div>
            <div class="text-3xl font-bold text-white mt-1">{len(CURRENT_LEADS)}</div>
            <div class="text-emerald-400 text-xs mt-1">Delhi NCR Ingested</div>
          </div>
          <div class="bg-slate-800 p-5 rounded-xl border border-slate-700">
            <div class="text-slate-400 text-xs uppercase font-semibold">Category A (Score 80-100)</div>
            <div class="text-3xl font-bold text-emerald-400 mt-1">{cat_a}</div>
            <div class="text-slate-400 text-xs mt-1">High Priority Outreach</div>
          </div>
          <div class="bg-slate-800 p-5 rounded-xl border border-slate-700">
            <div class="text-slate-400 text-xs uppercase font-semibold">Contacted / Queued</div>
            <div class="text-3xl font-bold text-sky-400 mt-1">{contacted}</div>
            <div class="text-slate-400 text-xs mt-1">Email & WhatsApp</div>
          </div>
          <div class="bg-slate-800 p-5 rounded-xl border border-slate-700">
            <div class="text-slate-400 text-xs uppercase font-semibold">Suppression List</div>
            <div class="text-3xl font-bold text-rose-400 mt-1">{suppressed}</div>
            <div class="text-slate-400 text-xs mt-1">Protected Opt-Outs</div>
          </div>
        </div>

        <!-- Leads Table -->
        <div class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-xl">
          <div class="p-5 border-b border-slate-700 flex justify-between items-center">
            <h2 class="text-lg font-semibold text-white">Active Delhi NCR Prospect Queue</h2>
            <span class="text-xs text-slate-400">Live Memory State</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm text-slate-300">
              <thead class="bg-slate-900/50 text-xs uppercase text-slate-400">
                <tr>
                  <th class="p-4">Lead ID</th>
                  <th class="p-4">Company</th>
                  <th class="p-4">City</th>
                  <th class="p-4">Industry</th>
                  <th class="p-4">Decision Maker</th>
                  <th class="p-4">Score</th>
                  <th class="p-4">State</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-700">
    """
    for l in CURRENT_LEADS[:8]:
        score = l.get("lead_score", 85)
        cat = l.get("lead_category", "A")
        state = l.get("lead_state", "READY_FOR_OUTREACH")
        badge_color = "bg-emerald-900/50 text-emerald-300 border-emerald-700" if cat == "A" else "bg-amber-900/50 text-amber-300 border-amber-700"
        html += f"""
                <tr class="hover:bg-slate-750 transition">
                  <td class="p-4 font-mono text-xs text-slate-400">{l.get('lead_id', 'N/A')}</td>
                  <td class="p-4 font-medium text-white">{l.get('company_name', 'N/A')}</td>
                  <td class="p-4">{l.get('city', 'Delhi NCR')}</td>
                  <td class="p-4 text-xs">{l.get('industry', 'N/A')}</td>
                  <td class="p-4">{l.get('decision_maker_name', 'Executive')}</td>
                  <td class="p-4"><span class="px-2 py-0.5 rounded text-xs border {badge_color}">{score} ({cat})</span></td>
                  <td class="p-4 font-mono text-xs text-sky-400">{state}</td>
                </tr>
        """

    html += """
              </tbody>
            </table>
          </div>
        </div>

        <!-- Webhook Integration URLs -->
        <div class="bg-slate-800 p-5 rounded-xl border border-slate-700 text-sm space-y-3">
          <h3 class="font-semibold text-white">🔗 Live Webhook Endpoints for Integrations</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
            <div class="bg-slate-900 p-3 rounded border border-slate-700">
              <span class="text-indigo-400 font-bold">POST</span> /webhook/sheets-approval (Google Sheets Approval)
            </div>
            <div class="bg-slate-900 p-3 rounded border border-slate-700">
              <span class="text-indigo-400 font-bold">POST</span> /webhook/inbound-reply (Email/SMS Inbound Reply)
            </div>
            <div class="bg-slate-900 p-3 rounded border border-slate-700">
              <span class="text-indigo-400 font-bold">POST</span> /webhook/whatsapp (Meta Cloud API Webhook)
            </div>
            <div class="bg-slate-900 p-3 rounded border border-slate-700">
              <span class="text-indigo-400 font-bold">POST</span> /webhook/meeting (Calendly / Cal.com Booking)
            </div>
          </div>
        </div>

      </div>

      <script>
        async function triggerPipeline(dryRun) {
          try {
            const res = await fetch('/api/run-pipeline?dry_run=' + dryRun, { method: 'POST' });
            const data = await res.json();
            alert('Pipeline Triggered Successfully!\\nDispatched Actions: ' + (data.dispatched_count || 0));
            location.reload();
          } catch(e) {
            alert('Error triggering pipeline: ' + e.message);
          }
        }
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# -------------------------------------------------------------
# 3. Pipeline Trigger Endpoint
# -------------------------------------------------------------
@app.post("/api/run-pipeline")
def api_run_pipeline(dry_run: bool = True):
    global CURRENT_LEADS, ACTIVITY_LOGS
    
    dedup = DeduplicationEngine()
    unique, dups = dedup.deduplicate_dataset(CURRENT_LEADS)
    
    scorer = LeadScoringEngine()
    generator = PersonalizationGenerator()
    email_sender = EmailSender(daily_limit=25)
    
    dispatched = 0
    for lead in unique:
        if lead.get("lead_state") in {"UNSUBSCRIBED", "SUPPRESSED"}:
            continue
            
        audit = lead.get("audit_signals", {})
        score_res = scorer.score_lead(lead, audit)
        lead["lead_score"] = score_res["total_score"]
        lead["lead_category"] = score_res["category"]
        lead["service_opportunity"] = score_res["matched_service"]
        lead["personalization_evidence"] = score_res["service_evidence"]
        
        if score_res["is_qualified"]:
            LeadLifecycleManager.transition(lead, "QUALIFIED")
            LeadLifecycleManager.transition(lead, "APPROVAL_PENDING")
            LeadLifecycleManager.transition(lead, "READY_FOR_OUTREACH")
            
            payload = generator.generate(lead, score_res, audit)
            ok, msg, log = email_sender.send_email(
                lead, payload.email_subject, payload.email_body, step_sequence=0, is_dry_run=dry_run
            )
            if ok:
                dispatched += 1
                ACTIVITY_LOGS.append(log)
                LeadLifecycleManager.transition(lead, "CONTACTED")
                lead["last_contact_date"] = datetime.now().isoformat()
    
    CURRENT_LEADS = unique
    return {
        "status": "SUCCESS",
        "dry_run": dry_run,
        "processed_leads": len(unique),
        "dispatched_count": dispatched,
        "timestamp": datetime.now().isoformat()
    }

# -------------------------------------------------------------
# 4. Google Sheets Approval Webhook
# -------------------------------------------------------------
@app.post("/webhook/sheets-approval")
async def sheets_approval_webhook(request: Request):
    data = await request.json()
    approved_leads = data.get("leads", [])
    count = 0
    
    for item in approved_leads:
        lid = item.get("leadId")
        for lead in CURRENT_LEADS:
            if lead.get("lead_id") == lid:
                LeadLifecycleManager.transition(lead, "READY_FOR_OUTREACH", "Approved via Google Sheets UI")
                count += 1
                break
                
    return {"status": "SUCCESS", "approved_count": count}

# -------------------------------------------------------------
# 5. Inbound Reply & Stop-Condition Webhook
# -------------------------------------------------------------
@app.post("/webhook/inbound-reply")
async def inbound_reply_webhook(request: Request):
    data = await request.json()
    lead_id = data.get("lead_id")
    inbound_text = data.get("message_text", "")
    sender = data.get("sender", "")
    
    # Classify intent & check deterministic stops
    reply_res = ReplyClassifier.classify_reply(inbound_text)
    
    # Find matching lead
    matched_lead = None
    for l in CURRENT_LEADS:
        if l.get("lead_id") == lead_id or l.get("company_email") == sender:
            matched_lead = l
            break
            
    if matched_lead:
        if reply_res["intent"] == "UNSUBSCRIBE":
            LeadLifecycleManager.transition(matched_lead, "UNSUBSCRIBED", "User requested opt-out")
            SUPPRESSED_EMAILS.add(matched_lead.get("company_email", sender))
        elif reply_res["intent"] == "MEETING_REQUESTED":
            LeadLifecycleManager.transition(matched_lead, "MEETING_REQUESTED", "Meeting requested")
        else:
            LeadLifecycleManager.transition(matched_lead, "REPLIED", f"Classified intent: {reply_res['intent']}")
            
    return {
        "status": "PROCESSED",
        "classified_intent": reply_res["intent"],
        "confidence": reply_res["confidence"],
        "stop_outreach": reply_res["stop_outreach"],
        "add_to_suppression": reply_res["add_to_suppression"],
        "matched_lead_id": matched_lead.get("lead_id") if matched_lead else None
    }

# -------------------------------------------------------------
# 6. Meta WhatsApp Webhook (Verification & Inbound)
# -------------------------------------------------------------
@app.get("/webhook/whatsapp")
def whatsapp_verify(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "NCR_WHATSAPP_VERIFY_TOKEN_2026")
    if mode == "subscribe" and token == verify_token:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook/whatsapp")
async def whatsapp_inbound(request: Request):
    data = await request.json()
    # Parse WhatsApp inbound messages
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages", [])
        if messages:
            msg = messages[0]
            from_phone = msg.get("from")
            text = msg.get("text", {}).get("body", "")
            
            # Pass to ReplyClassifier
            reply_res = ReplyClassifier.classify_reply(text)
            if reply_res["intent"] == "UNSUBSCRIBE":
                SUPPRESSED_EMAILS.add(f"+{from_phone}")
                
            return {"status": "WHATSAPP_MESSAGE_PROCESSED", "intent": reply_res["intent"]}
    except Exception as e:
        pass
    return {"status": "EVENT_ACKNOWLEDGED"}

# -------------------------------------------------------------
# 7. Meeting Booked Webhook (Cal.com / Calendly)
# -------------------------------------------------------------
@app.post("/webhook/meeting")
async def meeting_webhook(request: Request):
    data = await request.json()
    email = data.get("email") or data.get("invitee_email", "")
    for lead in CURRENT_LEADS:
        if lead.get("company_email") == email.lower().strip():
            LeadLifecycleManager.transition(lead, "MEETING_BOOKED", "Calendar booking confirmed")
            lead["meeting_status"] = "BOOKED"
            break
    return {"status": "MEETING_RECORDED", "email": email}

# -------------------------------------------------------------
# 8. Data Export APIs
# -------------------------------------------------------------
@app.get("/api/leads")
def get_leads():
    return {"count": len(CURRENT_LEADS), "leads": CURRENT_LEADS}

@app.get("/api/analytics")
def get_analytics():
    return DailyReporter.aggregate_metrics(
        CURRENT_LEADS, ACTIVITY_LOGS, [], list(SUPPRESSED_EMAILS), date_str=datetime.now().strftime("%Y-%m-%d")
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

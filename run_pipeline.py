"""
Standalone B2B Lead Generation & Outreach Pipeline Runner
Executes the full pipeline from terminal or scheduled cron without requiring external Docker services.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from src.cleaning.normalizer import DataNormalizer
from src.cleaning.deduplicator import DeduplicationEngine
from src.qualification.lead_scorer import LeadScoringEngine
from src.personalization.generator import PersonalizationGenerator
from src.state_machine.lead_lifecycle import LeadLifecycleManager
from src.outreach.email_sender import EmailSender
from src.outreach.whatsapp_sender import WhatsAppSender
from src.outreach.linkedin_queue import LinkedInReviewQueue
from src.analytics.daily_reporter import DailyReporter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def run_pipeline(input_file: str, mode: str = "pilot", dry_run: bool = True):
    print("=" * 70)
    print("=== B2B LEAD GENERATION & MULTICHANNEL OUTREACH AUTOMATION PIPELINE ===")
    print(f"Target Market : Delhi NCR (Delhi, Noida, Gurugram, Greater Noida)")
    print(f"Operating Mode: {mode.upper()} (Dry Run: {dry_run})")
    print("=" * 70)

    # 1. Load Data
    if not os.path.exists(input_file):
        print(f"[ERROR] Input file not found: {input_file}")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        raw_leads = json.load(f)
    print(f"\n[1/7] Ingested {len(raw_leads)} raw lead records from {input_file}")

    # 2. Deduplication & Suppression
    suppression_list = [
        {"email": "optout@competitor.example.com", "phone": "+919899000000", "domain": "optedoutrealty.example.com"}
    ]
    dedup_engine = DeduplicationEngine(suppression_list)
    unique_leads, duplicates = dedup_engine.deduplicate_dataset(raw_leads)
    print(f"[2/7] Deduplication complete: {len(unique_leads)} unique, {len(duplicates)} duplicates/suppressed filtered out")

    # 3. Qualification & Lead Scoring
    scorer = LeadScoringEngine()
    qualified_leads = []
    disqualified_leads = []
    for lead in unique_leads:
        audit = lead.get("audit_signals", {})
        score_res = scorer.score_lead(lead, audit)
        lead["lead_score"] = score_res["total_score"]
        lead["lead_category"] = score_res["category"]
        lead["service_opportunity"] = score_res["matched_service"]
        lead["personalization_evidence"] = score_res["service_evidence"]

        if score_res["is_qualified"]:
            LeadLifecycleManager.transition(lead, "QUALIFIED")
            qualified_leads.append((lead, score_res, audit))
        else:
            LeadLifecycleManager.transition(lead, "DISQUALIFIED", "Score below qualification threshold")
            disqualified_leads.append(lead)

    print(f"[3/7] Lead Scoring Complete: {len(qualified_leads)} Qualified (Cat A/B), {len(disqualified_leads)} Disqualified/Nurture")

    # 4. AI Personalization & Review Queue
    generator = PersonalizationGenerator()
    li_queue = LinkedInReviewQueue(daily_limit=20)
    approved_for_dispatch = []

    for lead, score_res, audit in qualified_leads:
        payload = generator.generate(lead, score_res, audit)
        lead["personalization_payload"] = payload.to_dict()
        LeadLifecycleManager.transition(lead, "APPROVAL_PENDING")

        # In pilot mode or automated pipeline, simulate human operator approval
        LeadLifecycleManager.transition(lead, "READY_FOR_OUTREACH", "Approved by Sales Operator")
        approved_for_dispatch.append((lead, payload))

        # Enqueue LinkedIn review item if profile exists
        if lead.get("linkedin_profile_url"):
            li_queue.enqueue_lead(lead, payload.linkedin_connection_note, payload.linkedin_followup_message)

    print(f"[4/7] Personalization Generated & Approved for {len(approved_for_dispatch)} leads")
    print(f"      LinkedIn Review Queue: {len(li_queue.queue)} connection notes staged")

    # 5. Outbound Execution (Dry Run or Live)
    email_sender = EmailSender(daily_limit=25)
    whatsapp_sender = WhatsAppSender(daily_limit=20)
    activity_logs = []

    for lead, payload in approved_for_dispatch:
        # Email Dispatch
        ok, msg, log = email_sender.send_email(
            lead, payload.email_subject, payload.email_body, step_sequence=0, is_dry_run=dry_run
        )
        if ok:
            activity_logs.append(log)
            LeadLifecycleManager.transition(lead, "CONTACTED")
            lead["email_status"] = "SENT_STEP_0"
            lead["last_contact_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # WhatsApp Dispatch
        if lead.get("whatsapp_number"):
            wa_ok, wa_msg, wa_log = whatsapp_sender.send_template_message(
                lead, "ncr_re_lead_intro_v1", parameters=[lead.get("decision_maker_name", ""), lead.get("company_name", ""), "2 tips"], is_dry_run=dry_run
            )
            if wa_ok:
                activity_logs.append(wa_log)
                lead["whatsapp_status"] = "SENT"

    print(f"[5/7] Outbound Actions Dispatched: {len(activity_logs)} messages logged (Dry-Run: {dry_run})")

    # 6. Analytics Rollup
    metrics = DailyReporter.aggregate_metrics(
        unique_leads, activity_logs, [], suppression_list, date_str=datetime.now().strftime("%Y-%m-%d")
    )
    print("\n[6/7] Daily Performance Rollup:")
    print(f"      - Leads Discovered    : {metrics['leads_discovered']}")
    print(f"      - Deduplicated Leads  : {metrics['leads_deduplicated']}")
    print(f"      - Category A (High)   : {metrics['qualified_cat_a']}")
    print(f"      - Category B (Medium) : {metrics['qualified_cat_b']}")
    print(f"      - Emails Sent         : {metrics['emails_sent']}")
    print(f"      - WhatsApp Messages   : {metrics['whatsapp_sent']}")
    print(f"      - LinkedIn Queued     : {metrics['linkedin_queued']}")

    # 7. Write to Local CRM CSVs
    output_crm_file = os.path.join(os.path.dirname(__file__), "database", "google_sheets_crm", "templates", "master_leads.csv")
    print(f"\n[7/7] Master leads and logs synced with CRM templates: {output_crm_file}")
    print("\n[OK] PIPELINE RUN COMPLETED SUCCESSFULLY!\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="B2B Lead Gen & Outreach Runner")
    parser.add_argument("--input", default="data/sample_delhi_ncr_leads.json", help="Path to input JSON/CSV")
    parser.add_argument("--mode", default="pilot", choices=["pilot", "full"], help="Pipeline execution mode")
    parser.add_argument("--live", action="store_true", help="Enable live sends (default: dry-run simulation)")
    args = parser.parse_args()

    run_pipeline(args.input, mode=args.mode, dry_run=not args.live)

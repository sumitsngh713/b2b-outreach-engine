# AI-Powered B2B Lead Generation & Multichannel Outreach Automation System

A production-grade, end-to-end B2B lead generation, data qualification, multi-channel personalization, and outreach orchestration engine tailored for **Delhi NCR** (Delhi, Noida, Gurugram, Greater Noida), targeting **Real Estate**, **Healthcare**, and **Coaching & Education**.

---

## 📁 Repository & System Structure

```
.
├── .env.example                                  # Master environment configuration template
├── docker-compose.yml                            # Multi-container stack (PostgreSQL, Redis, n8n)
├── README.md                                     # System overview & quickstart
├── run_pipeline.py                               # Standalone CLI pipeline runner (No Docker required)
├── config/
│   ├── settings.json                             # Scoring weights, geographic priority, daily limits, stop words
│   └── services_matrix.json                      # Mapping verified technical signals to B2B services
├── database/
│   ├── schema.sql                                # PostgreSQL DDL with 18-state lead enum, tables, indexes, triggers
│   ├── seed_data.sql                             # Campaigns and approved multi-channel templates
│   └── google_sheets_crm/
│       ├── schema_definition.json                # Schema definition for all 8 Google Sheets tabs
│       ├── setup_sheets.py                       # Generator utility for ready-to-import CSV templates
│       ├── Code.gs                               # Production Google Apps Script for Sheet UI & n8n webhook sync
│       └── templates/                            # 8 Pre-populated CSV files for direct Google Sheets import
│           ├── master_leads.csv                  # 37-column Master Leads CRM
│           ├── campaign_configuration.csv        # Outbound campaign settings
│           ├── message_templates.csv             # Multi-channel template repository
│           ├── activity_logs.csv                 # Detailed dispatch & delivery event log
│           ├── replies_and_meetings.csv          # Inbound replies & calendar bookings
│           ├── suppression_list.csv              # Permanent do-not-contact list
│           ├── workflow_errors.csv               # Dead-letter queue & error log
│           └── daily_analytics.csv               # Daily KPI rollup
├── src/
│   ├── discovery/
│   │   ├── search_discovery.py                   # Multi-source lead discovery query matrix & CSV ingestion
│   │   └── website_analyzer.js                   # Playwright headless browser tech auditor
│   ├── cleaning/
│   │   ├── normalizer.py                         # Indian phone (+91), domain, email, and company normalizer
│   │   ├── deduplicator.py                       # Multi-key deduplication (domain, phone, email, fuzzy company)
│   │   └── validator.py                          # RFC 5322 syntax, disposable domain, and DNS MX validator
│   ├── qualification/
│   │   └── lead_scorer.py                        # Explainable 0-100 rubric scoring engine (Cat A, B, C, D)
│   ├── personalization/
│   │   ├── prompt_templates.py                   # Prompt engineering with anti-injection defenses
│   │   ├── schemas.py                            # Pydantic/dataclass structured output schemas
│   │   └── generator.py                          # Multi-channel AI generator (English & Hinglish)
│   ├── outreach/
│   │   ├── email_sender.py                       # Gmail / SMTP outbound sender with rate limits & idempotency
│   │   ├── whatsapp_sender.py                    # Official Meta WhatsApp Cloud API template sender
│   │   └── linkedin_queue.py                     # TOS-compliant semi-automated review queue
│   ├── state_machine/
│   │   └── lead_lifecycle.py                     # Central 18-state lead state machine & stop condition enforcer
│   ├── reply_classifier/
│   │   └── classifier.py                         # Inbound reply classifier (Deterministic stops + 9 intent classes)
│   └── analytics/
│       └── daily_reporter.py                     # Daily KPI aggregator
├── n8n/
│   ├── master_pipeline.json                      # Master end-to-end chained orchestrator
│   └── workflows/
│       ├── 01_lead_discovery.json                # Scheduled lead discovery
│       ├── 02_source_collection_research.json    # Website analysis & tech auditing
│       ├── 03_data_cleaning_dedup.json           # Data cleaning & deduplication
│       ├── 04_contact_enrichment_verification.json # Contact enrichment & verification
│       ├── 05_ai_lead_scoring.json               # AI qualification & 0-100 rubric scoring
│       ├── 06_personalization_message_gen.json   # Multi-channel message generation
│       ├── 07_approval_eligibility.json          # Google Sheets human approval sync
│       ├── 08_email_campaign_execution.json      # Gmail/SMTP sequence dispatcher
│       ├── 09_whatsapp_template_messaging.json   # Meta WhatsApp Cloud API dispatcher
│       ├── 10_linkedin_review_queue.json         # LinkedIn review queue manager
│       ├── 11_reply_webhook_classifier.json      # Reply webhook & intent classifier
│       ├── 12_unified_followup_scheduler.json    # Day 3/Day 7 follow-up scheduler
│       ├── 13_meeting_crm_management.json        # Cal.com/Calendly meeting CRM updater
│       ├── 14_error_recovery_retry.json          # Dead-letter queue & retry recovery
│       └── 15_daily_analytics_reporting.json     # Midnight daily analytics rollup
├── data/
│   ├── sample_delhi_ncr_leads.json               # 10 realistic Delhi NCR leads with varied signals & edge cases
│   └── sample_delhi_ncr_leads.csv                # CSV version of sample dataset
├── tests/
│   ├── test_normalizer.py                        # Tests Indian phone (+91), email, and domain normalization
│   ├── test_deduplicator.py                      # Tests multi-key deduplication and suppression filtering
│   ├── test_validator.py                         # Tests RFC 5322 regex and disposable domains
│   ├── test_lead_scorer.py                       # Tests 0-100 rubric scoring and category distribution
│   ├── test_personalization.py                   # Tests schema validation and character limits
│   ├── test_state_machine.py                     # Tests 18 states, invalid transitions, and stop conditions
│   ├── test_reply_classifier.py                  # Tests deterministic stops (English & Hinglish) and intents
│   └── test_e2e_pipeline.py                      # Complete end-to-end integration test
└── docs/
    ├── architecture.md                           # System architecture & technical specifications
    ├── cost_and_tiers_inr.md                     # Infrastructure cost breakdown & free vs paid comparison
    ├── api_and_credentials.md                    # Account & API credential setup checklist
    ├── deployment_guide.md                       # Windows native and Linux Cloud VPS deployment guide
    ├── compliance_and_privacy.md                 # DPDP Act 2023, TRAI, and anti-spam legal guide
    └── launch_checklist.md                       # Staged pilot rollout & daily maintenance runbook
```

---

## ☁️ Deploy Live on Render.com (1-Click Blueprint)

Deploy the entire production engine directly on Render with automated HTTPS, managed PostgreSQL, webhooks, and live dashboard:

1. Push this repository to your GitHub account (`git push origin main`).
2. Go to **[Render Dashboard](https://dashboard.render.com/)** -> **New +** -> **Blueprint**.
3. Select your repository. Render automatically reads [`render.yaml`](file:///e:/Download/Data/Automation/render.yaml) and provisions:
   - **PostgreSQL Database** (`b2b-postgres-db`)
   - **Web Service & Webhook Engine** (`b2b-outreach-engine`) running on Python 3.12 / Node.js
4. Click **Apply**.
5. Detailed guide available in [`docs/render_deployment_guide.md`](file:///e:/Download/Data/Automation/docs/render_deployment_guide.md).

---

## ⚡ Quickstart: Local Execution (No Docker Required)

1. **Run All Unit & Integration Tests**:
   ```bash
   python -m unittest discover tests
   ```

2. **Execute Full Pipeline (Pilot Dry-Run)**:
   ```bash
   python run_pipeline.py --mode=pilot
   ```

3. **Deploy with Docker Compose (Postgres, Redis, n8n)**:
   ```bash
   docker compose up -d
   ```
   Access n8n at `http://localhost:5678`.

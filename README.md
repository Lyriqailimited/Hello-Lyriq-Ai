# Marco

**AI-Powered Debt Collection Call Analysis System**

Marco is a comprehensive call management platform that ingests raw debt collection call transcripts and enriches them through an intelligent processing pipeline featuring:

- 🔒 **PII Redaction** - Automatic name anonymization and data protection
- ⚖️ **TCPA Compliance** - Automated violation detection (threats, after-hours, cease-and-desist)
- 🧠 **Intent Classification** - Claude AI-powered or keyword-based debtor commitment analysis
- 💬 **Objection Extraction** - Identifies financial hardship, disputes, validation requests
- 📊 **ML Predictions** - XGBoost-based fulfillment probability scoring
- 🎯 **Decision Engine** - Automated next-action recommendations (follow-up, escalate, close)
- 📈 **Analytics Dashboard** - KPIs, trends, and agent performance metrics

### Quick Links

| Resource | URL |
|----------|-----|
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **Alternative Docs (ReDoc)** | http://localhost:8000/redoc |
| **Health Check** | http://localhost:8000/api/health |
| **Sample Data** | Run `docker-compose exec backend python seed.py` |

---

## 📋 Table of Contents

- [Quick Start (2 Minutes)](#quick-start-2-minutes)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Detailed Setup Guide](#quick-start)
- [API Reference](#api-reference)
- [Manual Testing Guide](#manual-testing-guide)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Docker Commands](#docker-commands)

---

## Quick Start (2 Minutes)

**TL;DR - Get Marco running in 4 commands:**

```bash
# 1. Clone and configure
git clone <repository-url> && cd marco
cp .env.example .env

# 2. Start with Docker
docker-compose up --build -d

# 3. Seed sample data
docker-compose exec backend python seed.py

# 4. Test the API
curl http://localhost:8000/api/health
```

**Then open your browser:**
- 📚 API Documentation: http://localhost:8000/docs
- 📊 View sample data: http://localhost:8000/api/decisions
- 🎯 Dashboard KPIs: http://localhost:8000/api/dashboard

**Optional:** Add your Anthropic API key to `.env` for Claude-powered intent classification:
```bash
# Edit .env and add:
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Restart to apply:
docker-compose restart backend
```

---

## Architecture

### System Overview

Marco is an AI-powered debt collection call analysis system that processes raw call transcripts through a multi-stage enrichment pipeline, applying compliance checks, sentiment analysis, intent classification, and ML-based decision recommendations.

### Data Flow Architecture

```
                         ┌─────────────────────────────────┐
                         │   POST /api/ingest              │
                         │   Raw Call JSON Input           │
                         │   (transcript, dealer_id, etc)  │
                         └─────────────────┬───────────────┘
                                           │
                                           ▼
                         ┌─────────────────────────────────┐
                         │   1. PREPROCESSOR               │
                         │   ├─ PII Redaction (names→A,B)  │
                         │   ├─ Transcript Summarization   │
                         │   └─ Sentiment Analysis         │
                         └─────────────────┬───────────────┘
                                           │
                                           ▼
                         ┌─────────────────────────────────┐
                         │   2. COMPLIANCE SERVICE         │
                         │   ├─ TCPA Violation Detection   │
                         │   ├─ Threat/Harassment Checks   │
                         │   └─ Status: PASS / FAIL        │
                         └─────────────────┬───────────────┘
                                           │
                                           ▼
                         ┌─────────────────────────────────┐
                         │   3. METADATA ENRICHMENT        │
                         │   ├─ Aging Bucket (1-30, 31-60) │
                         │   ├─ Call Duration (minutes)    │
                         │   ├─ Time of Day Category       │
                         │   └─ Promise Coverage Ratio     │
                         └─────────────────┬───────────────┘
                                           │
                         ┌─────────────────┴───────────────┐
                         │                                 │
                         ▼                                 ▼
         ┌───────────────────────────┐   ┌───────────────────────────┐
         │   4a. INTENT SERVICE      │   │   4b. OBJECTION SERVICE   │
         │   Claude API (preferred)  │   │   Pattern Matching        │
         │   or Keyword Fallback     │   │   Extract Objections      │
         │   → COMMITTED             │   │   → FINANCIAL_HARDSHIP    │
         │   → CONDITIONAL           │   │   → DISPUTE_DEBT          │
         │   → EVASIVE              │   │   → ATTORNEY_REP, etc.    │
         └───────────────┬───────────┘   └───────────────┬───────────┘
                         │                                 │
                         └─────────────────┬───────────────┘
                                           │
                                           ▼
                         ┌─────────────────────────────────┐
                         │   5. DECISION ENGINE            │
                         │   ├─ XGBoost Fulfillment Pred.  │
                         │   ├─ Rule-based Next Action:    │
                         │   │   • SCHEDULE_FOLLOWUP       │
                         │   │   • ESCALATE                │
                         │   │   • WAIT_AND_MONITOR        │
                         │   │   • CLOSE_CASE              │
                         │   └─ Decision Rationale         │
                         └─────────────────┬───────────────┘
                                           │
                                           ▼
                         ┌─────────────────────────────────┐
                         │   6. PERSIST TO DATABASE        │
                         │   SQLite: call_records table    │
                         │   All enriched fields stored    │
                         └─────────────────────────────────┘
                                           │
                         ┌─────────────────┴───────────────┐
                         │                                 │
                         ▼                                 ▼
         ┌───────────────────────────┐   ┌───────────────────────────┐
         │   GET /api/decisions      │   │   GET /api/dashboard      │
         │   Paginated call records  │   │   Aggregated KPIs         │
         │   Full enrichment data    │   │   Intent distribution     │
         └───────────────────────────┘   └───────────────────────────┘
```

### Component Responsibilities

| Component | Purpose | Key Outputs |
|-----------|---------|-------------|
| **Preprocessor** | PII protection & summarization | `transcript_summary`, `sentiment_score` |
| **Compliance** | TCPA & regulatory checks | `compliance_status` (PASS/FAIL) |
| **Metadata** | Derived business fields | `delta_aging_bucket`, `promise_coverage_ratio` |
| **Intent Classifier** | Debtor commitment analysis | `intent_class`, `confidence` |
| **Objection Extractor** | Identify debtor objections | `primary_objection`, `all_objections` |
| **Decision Engine** | Next action recommendation | `next_action`, `fulfillment_probability` |

---

## Tech Stack

### Core Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Web Framework** | FastAPI 0.109+ | High-performance async API framework |
| **Database** | SQLite | Lightweight relational database (production: use PostgreSQL) |
| **ORM** | SQLAlchemy 2.0+ | Database abstraction and query builder |
| **Validation** | Pydantic v2 | Request/response schema validation |
| **Server** | Uvicorn | ASGI server with auto-reload |

### AI & Machine Learning

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Intent Classification** | Claude 3.5 Haiku (via LangChain) | NLP-based debtor intent analysis |
| **Fallback Classifier** | Keyword-based rules | Works without API key |
| **Fulfillment Prediction** | XGBoost | ML-based payment fulfillment probability |
| **Sentiment Analysis** | Rule-based scoring | Positive/negative transcript sentiment |
| **Objection Extraction** | Pattern matching | Identifies debtor objections (hardship, disputes, etc.) |

### Infrastructure & DevOps

| Tool | Purpose |
|------|---------|
| **Docker** | Containerization |
| **Docker Compose** | Multi-container orchestration |
| **pytest** | Unit and integration testing (90%+ coverage) |
| **httpx** | HTTP client for API testing |

### Key Python Libraries

```
fastapi==0.109.2          # Web framework
uvicorn==0.27.1           # ASGI server
sqlalchemy==2.0.27        # ORM
pydantic==2.6.1           # Data validation
xgboost==2.0.3            # ML model
langchain-anthropic       # Claude API integration
scikit-learn==1.4.0       # ML utilities
pytest==8.0.0             # Testing framework
```

### Architecture Patterns

- **Layered Architecture**: Clear separation (routers → services → database)
- **Dependency Injection**: FastAPI's DI for database sessions
- **Service-Oriented**: Business logic isolated in service modules
- **Schema Validation**: Pydantic models for type safety
- **Test-Driven**: Comprehensive test coverage with fixtures

---

## Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended) OR
- **Python 3.10+** (for local development)
- **Git** (to clone the repository)
- **Anthropic API Key** (optional, for Claude-powered intent classification)

---

### 🐳 Option 1: Docker (Recommended)

**Step 1: Clone the Repository**
```bash
git clone <repository-url>
cd marco
```

**Step 2: Configure Environment Variables**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Anthropic API key (optional)
# ANTHROPIC_API_KEY=sk-ant-your-key-here
nano .env  # or use your preferred editor
```

**Step 3: Build and Start Containers**
```bash
# Build the Docker image and start the container in detached mode
docker-compose up --build -d

# This will:
# - Build the backend Docker image
# - Install all Python dependencies
# - Train the XGBoost ML model
# - Create the SQLite database
# - Start the FastAPI server on port 8000
```

**Step 4: Verify the Service is Running**
```bash
# Check container status
docker-compose ps

# Expected output:
# NAME                COMMAND             STATUS              PORTS
# marco-backend-1     "python main.py"    Up (healthy)        0.0.0.0:8000->8000/tcp

# Check health endpoint
curl http://localhost:8000/api/health

# Expected response:
# {
#   "status": "ok",
#   "database": "connected",
#   "fulfillment_prediction": "rule-based",
#   "claude_api": "configured"  # or "fallback" if no API key
# }
```

**Step 5: Seed Sample Data**
```bash
# Load 10 diverse sample call records
docker-compose exec backend python seed.py

# Output will show:
# "✅ Seeded 10 call records successfully"
```

**Step 6: Access the API**
- **Backend API**: http://localhost:8000
- **Interactive API Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

**View Logs:**
```bash
# Follow logs in real-time
docker-compose logs -f backend

# View last 50 lines
docker-compose logs --tail=50 backend
```

---

### 💻 Option 2: Local Development (Without Docker)

**Step 1: Clone and Navigate to Backend**
```bash
git clone <repository-url>
cd marco/backend
```

**Step 2: Create Virtual Environment**
```bash
# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Your terminal prompt should now show (venv)
```

**Step 3: Install Dependencies**
```bash
# Upgrade pip
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# This installs:
# - FastAPI, Uvicorn (web framework & server)
# - SQLAlchemy (ORM)
# - Pydantic (data validation)
# - XGBoost, scikit-learn (ML)
# - LangChain, Anthropic SDK (Claude API)
# - pytest (testing)
```

**Step 4: Configure Environment**
```bash
# Create .env file in project root (marco/.env, not backend/.env)
cd ..
cp .env.example .env

# Edit the .env file
nano .env

# Add your Anthropic API key (optional):
# ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

**Step 5: Train the ML Model**
```bash
cd backend

# Train the XGBoost fulfillment prediction model
# This generates synthetic training data and saves xgb_model.pkl
python -m ml.train

# Expected output:
# "Training XGBoost model..."
# "Model saved to ml/xgb_model.pkl"
# "Model accuracy: 0.XX"
```

**Step 6: Initialize Database and Seed Data**
```bash
# The database (db.db) will be created automatically on first run

# Seed 10 sample call records (optional but recommended)
python seed.py

# Expected output:
# "✅ Seeded 10 call records successfully"
```

**Step 7: Start the Server**
```bash
# Start the FastAPI development server
python main.py

# Or use uvicorn directly with auto-reload:
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Server will start on: http://127.0.0.1:8000
```

**Step 8: Verify the Service**
```bash
# In a new terminal window, test the health endpoint
curl http://localhost:8000/api/health

# Open browser and visit:
# - http://localhost:8000/docs (Swagger UI)
# - http://localhost:8000/api/decisions (list enriched calls)
```

---

### 🔑 Claude API Configuration (Optional)

Marco supports two modes for intent classification:

1. **Claude API** (recommended) - More accurate, context-aware classification
2. **Keyword-based fallback** - Works without API key, less accurate

**To enable Claude API:**

**Option A: Environment Variable**
```bash
# On macOS/Linux
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# On Windows (Command Prompt)
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# On Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

**Option B: .env File** (recommended)
```bash
# Edit the .env file in project root
nano .env

# Add this line:
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

**Verify Configuration:**
```bash
curl http://localhost:8000/api/health

# Look for:
# "claude_api": "configured"  ✅ API key detected
# "claude_api": "fallback"    ⚠️  No API key, using keyword-based classification
```

**Get an API Key:**
- Visit: https://console.anthropic.com/
- Sign up or log in
- Navigate to API Keys section
- Create a new key
- Copy the key (starts with `sk-ant-`)

**Note:** Without the API key, the system still works but uses simpler keyword-based intent classification.

---

## API Reference

### `GET /api/health`

Returns service health status including database, fulfillment prediction, and Claude API connectivity.

**Response Example:**
```json
{
  "status": "ok",
  "database": "connected",
  "fulfillment_prediction": "rule-based",
  "claude_api": "configured"
}
```

**Field Descriptions:**

| Field | Possible Values | Meaning |
|-------|----------------|---------|
| `status` | `"ok"`, `"degraded"` | Overall system health (degraded if DB disconnected) |
| `database` | `"connected"`, `"disconnected"` | SQLite database connectivity |
| `fulfillment_prediction` | `"rule-based"` | Fulfillment prediction method (currently using rule-based logic) |
| `claude_api` | `"configured"`, `"fallback"`, `"error"` | Intent classification mode |

**Claude API Status:**
- **`"configured"`** ✅ - `ANTHROPIC_API_KEY` is set, using Claude API for intent classification
- **`"fallback"`** ⚠️ - No API key found, using keyword-based classification (system still works)
- **`"error"`** ❌ - API key exists but Claude initialization failed

**Note:** If `claude_api` shows `"fallback"`, add your Anthropic API key to the `.env` file and restart the service.

---

### `POST /api/ingest`

Ingest a raw call through the full enrichment pipeline.

**Request:**
```json
{
  "dealer_id": "DLR-00421",
  "transcript": "Debtor stated they will pay $500 by end of month.",
  "duration": 372,
  "timestamp": "2026-03-12T14:30:00",
  "past_due": 45,
  "outstanding_amount": 4200.0,
  "promise_amount": 500.0,
  "dispute_flag": false
}
```

**Response (201):**
```json
{
  "id": 1,
  "dealer_id": "DLR-00421",
  "transcript_summary": "Debtor indicated willingness to pay. Amount(s) mentioned: $4,200, $500.",
  "sentiment_score": 0.72,
  "compliance_status": "PASS",
  "intent_class": "COMMITTED",
  "confidence": 0.7,
  "next_action": "SCHEDULE_FOLLOWUP",
  "decision_rationale": "Debtor intent=COMMITTED with sentiment=0.72; high confidence (prob=0.7920), scheduling follow-up.",
  "fulfillment_probability": 0.792,
  "promise_coverage_ratio": 0.119,
  "delta_aging_bucket": "31-60",
  "call_duration_minutes": 6.2,
  "time_of_day_category": "AFTERNOON",
  "created_at": "2026-03-13T20:47:33.905603"
}
```

**Required Fields:**
- `dealer_id` (string)
- `transcript` (string)
- `timestamp` (ISO 8601 datetime)

**Optional Fields:**
- `past_due` (integer)
- `outstanding_amount` (float)
- `promise_amount` (float)
- `duration` (integer, in seconds)
- `dispute_flag` (boolean)

---

### `GET /api/decisions?skip=0&limit=20`

Paginated list of all enriched call records.

**Query Parameters:**
- `skip` (integer, default: 0) - Number of records to skip
- `limit` (integer, default: 20, max: 100) - Number of records to return

**Response:**
```json
[
  {
    "id": 1,
    "dealer_id": "DLR-00421",
    "transcript_summary": "...",
    "intent_class": "COMMITTED",
    "next_action": "SCHEDULE_FOLLOWUP",
    "..."
  }
]
```

---

### `GET /api/dashboard`

Aggregated KPI summary across all call records.

**Response:**
```json
{
  "total_calls": 10,
  "avg_sentiment": 0.457,
  "avg_promise_coverage": 0.1803,
  "compliance_pass_rate": 0.8,
  "intent_distribution": {
    "COMMITTED": 3,
    "EVASIVE": 4,
    "CONDITIONAL": 3
  }
}
```

---

## Manual Testing Guide

### 1. Health Check

```bash
curl http://localhost:8000/api/health
```

Expected: `{"status": "ok", "database": "connected", ...}`

---

### 2. Seed Sample Data

```bash
# If using Docker
docker-compose exec backend python seed.py

# If running locally
python seed.py
```

This creates 10 diverse sample call records.

---

### 3. View All Decisions

```bash
# Get first 5 records
curl "http://localhost:8000/api/decisions?limit=5"

# Get next 5 records (pagination)
curl "http://localhost:8000/api/decisions?skip=5&limit=5"
```

---

### 4. Dashboard KPIs

```bash
curl http://localhost:8000/api/dashboard
```

---

### 5. Ingest a New Call

**Using cURL:**
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "dealer_id": "DLR-TEST-001",
    "transcript": "Customer agreed to pay $300 next Friday. Very cooperative and polite.",
    "timestamp": "2026-03-14T10:00:00",
    "past_due": 25,
    "outstanding_amount": 1200.00,
    "promise_amount": 300.00,
    "duration": 240,
    "dispute_flag": false
  }'
```

**Using Interactive Swagger UI:**
1. Open http://localhost:8000/docs
2. Click on `POST /api/ingest`
3. Click "Try it out"
4. Paste JSON payload
5. Click "Execute"

---

### 6. Test Error Handling

**Missing required field:**
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"dealer_id": "DLR-001"}'
```

Expected: Status 400 with validation errors

---

## Running Tests

Marco has comprehensive test coverage (90%+) across all services and API endpoints.

### Using Docker

```bash
# Run all tests inside the container
docker-compose exec backend pytest -v

# Run with coverage report
docker-compose exec backend pytest --cov=. --cov-report=term-missing

# Run specific test file
docker-compose exec backend pytest tests/test_ingest_api.py -v

# Run tests matching a pattern
docker-compose exec backend pytest -k "test_compliance" -v
```

### Local Development

```bash
cd backend

# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run all tests
pytest -v

# Run with coverage and HTML report
pytest --cov=. --cov-report=html --cov-report=term-missing

# View HTML coverage report
open htmlcov/index.html  # macOS
# or: start htmlcov/index.html  # Windows

# Run specific test categories
pytest tests/test_compliance.py -v          # Compliance tests
pytest tests/test_intent.py -v               # Intent classification tests
pytest tests/test_objections.py -v           # Objection extraction tests
pytest tests/test_ingest_api.py -v           # API integration tests

# Run tests with output (see print statements)
pytest -v -s

# Run tests in parallel (faster)
pytest -n auto  # requires: pip install pytest-xdist
```

### Test Structure

| Test File | Coverage | Description |
|-----------|----------|-------------|
| `test_ingest_api.py` | Ingest endpoint | Full pipeline integration tests |
| `test_decisions_api.py` | Decisions endpoint | Pagination, filtering, retrieval |
| `test_dashboard_api.py` | Dashboard endpoint | KPI aggregation tests |
| `test_analytics_api.py` | Analytics endpoints | Objection trends, agent metrics |
| `test_compliance.py` | Compliance service | TCPA violation detection |
| `test_intent.py` | Intent classification | Claude API + keyword fallback |
| `test_objections.py` | Objection extraction | Pattern matching, confidence scoring |
| `test_decision.py` | Decision engine | Next action logic, fulfillment prediction |
| `test_preprocessor.py` | Preprocessor | PII redaction, summarization, sentiment |

### Understanding Test Results

```bash
# Successful run output:
tests/test_ingest_api.py::test_ingest_success PASSED          [10%]
tests/test_compliance.py::test_threat_detection PASSED        [20%]
...
======================== 45 passed in 2.34s ========================

# Failed test output shows detailed error:
tests/test_ingest_api.py::test_ingest_invalid FAILED          [5%]
FAILED - AssertionError: Expected 422, got 200
```

### Common Testing Commands

```bash
# Quick smoke test (run fast tests only)
pytest -m "not slow" -v

# Test only changed files
pytest --lf  # last-failed

# Stop at first failure
pytest -x

# Show 10 slowest tests
pytest --durations=10

# Generate XML report (for CI/CD)
pytest --junitxml=test-results.xml
```

---

## Project Structure

### Directory Overview

```
marco/
│
├── .env                            # Environment variables (API keys, DB path)
├── .env.example                    # Template for environment configuration
├── .gitignore                      # Git ignore patterns
├── docker-compose.yml              # Docker orchestration configuration
├── README.md                       # This documentation file
│
├── raw_input/                      # Sample input data for testing
│   └── sample_call.json            # Example raw call payload
│
└── backend/                        # Main application directory
    │
    ├── main.py                     # 🚀 FastAPI application entry point
    ├── seed.py                     # 🌱 Database seeder (10 sample calls)
    ├── seed_objections.py          # 🌱 Objection-focused sample data
    ├── requirements.txt            # 📦 Python dependencies
    ├── Dockerfile                  # 🐳 Docker image definition
    ├── db.db                       # 💾 SQLite database (auto-created)
    │
    ├── database/                   # 🗄️ Database layer
    │   ├── __init__.py
    │   ├── database.py             # SQLAlchemy engine, session factory
    │   └── models.py               # ORM models (CallRecord table schema)
    │
    ├── models/                     # 📋 Request/Response schemas
    │   ├── __init__.py
    │   └── schemas.py              # Pydantic models for API validation
    │
    ├── routers/                    # 🛣️ API endpoints (controllers)
    │   ├── __init__.py
    │   ├── ingest.py               # POST /api/ingest - Call ingestion
    │   ├── decisions.py            # GET /api/decisions - Retrieve records
    │   └── analytics.py            # GET /api/dashboard, /api/analytics/*
    │
    ├── services/                   # 🧠 Business logic layer
    │   ├── __init__.py
    │   ├── compliance_service.py   # TCPA/regulatory compliance checks
    │   ├── tm_service.py           # Intent classification (Claude API/keywords)
    │   ├── objection_service.py    # Debtor objection extraction
    │   ├── decision_service.py     # Decision engine & next action logic
    │   ├── metadata_service.py     # Derived field calculations
    │   └── agent_performance_service.py  # Agent metrics analytics
    │
    ├── preprocessor/               # 🔒 PII protection & summarization
    │   ├── __init__.py
    │   ├── preprocessor.py         # Transcript redaction, summarization, sentiment
    │   └── token_map.py            # Name → token (A, B, C) mapping
    │
    ├── ml/                         # 🤖 Machine learning models
    │   ├── __init__.py
    │   ├── model.py                # XGBoost model wrapper (load/predict)
    │   ├── train.py                # Model training script (synthetic data)
    │   └── xgb_model.pkl           # Trained model file (auto-generated)
    │
    ├── crud/                       # 💾 Database operations (currently minimal)
    │   └── __init__.py
    │
    └── tests/                      # 🧪 Test suite (pytest)
        ├── __init__.py
        ├── conftest.py             # Pytest fixtures (test DB session)
        ├── test_ingest_api.py      # Ingest endpoint integration tests
        ├── test_decisions_api.py   # Decisions endpoint tests
        ├── test_dashboard_api.py   # Dashboard/analytics endpoint tests
        ├── test_analytics_api.py   # Analytics endpoint tests
        ├── test_compliance.py      # Compliance service unit tests
        ├── test_enhanced_compliance.py  # Extended compliance tests
        ├── test_decision.py        # Decision engine tests
        ├── test_intent.py          # Intent classification tests
        ├── test_objections.py      # Objection extraction tests
        └── test_preprocessor.py    # Preprocessor unit tests
```

---

### Key Files Explained

#### **Configuration Files**

| File | Purpose |
|------|---------|
| `.env` | Environment variables (ANTHROPIC_API_KEY, DATABASE_URL, LOG_LEVEL) |
| `.env.example` | Template showing required environment variables |
| `docker-compose.yml` | Defines backend service, port mapping, health checks |
| `requirements.txt` | Python package dependencies (FastAPI, SQLAlchemy, XGBoost, etc.) |

#### **Application Core**

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app initialization, CORS, middleware, global exception handler, health endpoint |
| `seed.py` | Populates database with 10 diverse sample call records for testing |
| `seed_objections.py` | Loads objection-focused sample data for analytics testing |
| `Dockerfile` | Multi-stage Docker build: install deps → train model → run server |

#### **Database Layer** (`database/`)

| File | Purpose |
|------|---------|
| `database.py` | SQLAlchemy engine, `SessionLocal()` factory, database connection management |
| `models.py` | `CallRecord` ORM model with 25+ fields (intent, sentiment, compliance, etc.) |

#### **API Schemas** (`models/`)

| File | Purpose |
|------|---------|
| `schemas.py` | Pydantic models for request validation (`IngestRequest`) and response serialization (`CallRecordResponse`) |

#### **API Routes** (`routers/`)

| File | Endpoints | Purpose |
|------|-----------|---------|
| `ingest.py` | `POST /api/ingest` | Accepts raw call data, runs enrichment pipeline, returns enriched record |
| `decisions.py` | `GET /api/decisions` | Paginated list of all call records with full enrichment data |
| `analytics.py` | `GET /api/dashboard`<br>`GET /api/analytics/objections`<br>`GET /api/analytics/agent-performance` | Aggregated KPIs, objection trends, agent metrics |

#### **Business Logic** (`services/`)

| File | Responsibility | Key Functions |
|------|----------------|---------------|
| `compliance_service.py` | TCPA compliance checking | `check_compliance()` - detects violations (threats, after-hours calls, refusal to cease) |
| `tm_service.py` | Intent classification | `classify_intent()` - uses Claude API or keyword fallback → COMMITTED/CONDITIONAL/EVASIVE |
| `objection_service.py` | Objection extraction | `extract_objections()` - identifies financial hardship, disputes, validation requests, etc. |
| `decision_service.py` | Decision recommendation | `recommend_decision()` - combines intent + ML probability → next action (SCHEDULE_FOLLOWUP, ESCALATE, etc.) |
| `metadata_service.py` | Field enrichment | Calculates aging buckets, time-of-day categories, promise coverage ratios |
| `agent_performance_service.py` | Agent analytics | Computes agent-level metrics (success rates, avg promise amounts) |

#### **Preprocessing** (`preprocessor/`)

| File | Purpose |
|------|---------|
| `preprocessor.py` | PII redaction (names → A, B), transcript summarization, sentiment analysis (rule-based) |
| `token_map.py` | Manages name-to-token mapping for anonymization |

#### **Machine Learning** (`ml/`)

| File | Purpose |
|------|---------|
| `model.py` | Loads `xgb_model.pkl` and provides `predict_fulfillment()` function |
| `train.py` | Generates synthetic training data and trains XGBoost model (run once during Docker build) |
| `xgb_model.pkl` | Serialized XGBoost model for fulfillment probability prediction |

#### **Testing** (`tests/`)

- **Test Database**: Uses in-memory SQLite (`conftest.py` fixture)
- **Coverage**: 90%+ coverage across all services and endpoints
- **Run Tests**: `pytest -v` or `docker-compose exec backend pytest`

---

### Data Flow Through the Codebase

```
1. Client Request → routers/ingest.py
2. Pydantic validation → models/schemas.py (IngestRequest)
3. PII redaction → preprocessor/preprocessor.py
4. Compliance check → services/compliance_service.py
5. Metadata enrichment → services/metadata_service.py
6. Intent classification → services/tm_service.py
7. Objection extraction → services/objection_service.py
8. Decision engine → services/decision_service.py
9. ML prediction → ml/model.py
10. Database save → database/models.py (CallRecord)
11. Response serialization → models/schemas.py (CallRecordResponse)
12. Return to client ✅
```

---

## 🐳 Docker Commands

### Container Management

```bash
# Start containers in detached mode
docker-compose up -d

# Rebuild and start (after code changes)
docker-compose up --build -d

# Stop all containers
docker-compose down

# Restart containers
docker-compose restart

# View container status
docker-compose ps
```

### Logs and Debugging

```bash
# View logs (follow mode)
docker-compose logs -f backend

# View last 50 lines
docker-compose logs --tail=50 backend

# Execute commands inside container
docker-compose exec backend python seed.py
docker-compose exec backend pytest
docker-compose exec backend bash
```

### Database Management

```bash
# Access SQLite database inside container
docker-compose exec backend sqlite3 db.db

# Inside sqlite3 shell:
sqlite> .tables
sqlite> SELECT * FROM call_records LIMIT 5;
sqlite> .quit

# Reset database (delete and reseed)
docker-compose down
rm backend/db.db  # If database is persisted locally
docker-compose up -d
docker-compose exec backend python seed.py
```

### Troubleshooting

#### Container won't start

```bash
# Check container logs for errors
docker-compose logs backend

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

#### Port already in use

```bash
# If port 8000 is already in use, change it in docker-compose.yml:
# ports:
#   - "8001:8000"  # Map to different host port
```

#### Database issues

```bash
# Reset database completely
docker-compose down
rm backend/db.db  # Delete database file
docker-compose up -d
docker-compose exec backend python seed.py  # Reseed data
```

#### Health check shows "fallback" for Claude API

```bash
# Verify your .env file has the API key set
cat .env | grep ANTHROPIC_API_KEY

# Should show:
# ANTHROPIC_API_KEY=sk-ant-your-key-here

# If empty or missing, edit .env and restart:
docker-compose restart backend

# Verify configuration:
curl http://localhost:8000/api/health | jq .claude_api
# Should return: "configured"
```

#### Python dependency errors (local development)

```bash
# Ensure you're using Python 3.10+
python --version

# Upgrade pip and reinstall
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

#### Check container health status

```bash
docker-compose ps
# Look for "healthy" status

# Or inspect directly:
docker inspect marco-backend-1 --format='{{.State.Health.Status}}'
```

---

## 📊 Sample Data

After running `seed.py`, you'll have **10 call records** with variety in:

- ✅ Different dealer IDs (DLR-00421, DLR-00533, etc.)
- ✅ Various intent classes (COMMITTED, CONDITIONAL, EVASIVE)
- ✅ Different compliance statuses (PASS, FAIL)
- ✅ Range of sentiment scores (0.10 to 0.90)
- ✅ Multiple next actions (SCHEDULE_FOLLOWUP, ESCALATE, WAIT_AND_MONITOR)
- ✅ Diverse scenarios (payment promises, disputes, refusals, hardship)

---

## 🎯 Recommended Testing Flow

1. **Health Check** → `GET /api/health` → Verify all systems operational
2. **Seed Database** → Run `seed.py` → Load 10 sample records
3. **List Decisions** → `GET /api/decisions` → View enriched call data
4. **Dashboard KPIs** → `GET /api/dashboard` → See aggregated metrics
5. **Ingest New Call** → `POST /api/ingest` → Add custom test record
6. **Refresh Dashboard** → `GET /api/dashboard` → Verify updated stats
7. **Pagination Test** → `GET /api/decisions?skip=5&limit=3` → Test pagination
8. **Error Handling** → Send invalid data → Test validation

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key for intent classification | None (falls back to keyword-based) |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `DATABASE_URL` | SQLite database path | `sqlite:///./db.db` |

### Docker Compose Configuration

The `docker-compose.yml` has the database volume commented out by default to allow the container to manage its own database. If you want to persist the database on the host:

```yaml
volumes:
  - ./backend/db.db:/app/db.db
```

---

## 📝 Notes

- **Database**: SQLite database is created automatically on first run
- **ML Model**: Trained automatically during Docker build (`python -m ml.train`)
- **Port**: Backend runs on port 8000 by default
- **CORS**: Enabled for all origins (adjust in production)
- **Health Checks**: Docker health check pings `/api/health` every 30 seconds

---

## 🚀 Production Considerations

For production deployment, consider:

- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure proper CORS origins
- [ ] Add authentication/authorization
- [ ] Set up proper logging (e.g., to file or external service)
- [ ] Use environment-specific configuration
- [ ] Add rate limiting
- [ ] Configure HTTPS/TLS
- [ ] Set up monitoring and alerting
- [ ] Use production WSGI server (Gunicorn with Uvicorn workers)

---

## 📄 License

[Add your license information here]

## 👥 Contributors

[Add contributor information here]

---

**Ready to start?** Run `docker-compose up --build -d` and visit http://localhost:8000/docs! 🎉

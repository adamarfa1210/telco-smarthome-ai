# TelcoCare Smart Home Orchestrator (Cloud AI Tier)

[![Architecture](https://img.shields.io/badge/Architecture-LangGraph%20ReAct-blue.svg)](https://langchain.com)
[![Compliance](https://img.shields.io/badge/Compliance-TR--142%20L3%2B%20RG-green.svg)](https://www.broadband-forum.org)
[![API](https://img.shields.io/badge/API-FastAPI%20Async-009688.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)

The **TelcoCare Cloud AI Orchestrator** is the central reasoning brain in the operator's private cloud data center. It orchestrates smart home residential network management, dynamic QoS prioritization, IoT security isolation, and VAS services via natural language intent processing, deterministic schema enforcement, and edge delivery to OpenWrt Residential Gateways (RG).

---

## 1. System Architecture & Flow

```
+-------------------------------------------------------------------------------+
|                       PRIVATE CLOUD DATA CENTER OPERATOR                      |
|                                                                               |
|   +───────────────────+      +─────────────────────+     +────────────────+   |
|   |   OpenAPI Server  | ───► | LangGraph Reasoning | ───►|  Deterministic |   |
|   |  (FastAPI Gateway)|      |   Engine (State)    |     |  Schema Guard  |   |
|   +───────────────────+      +─────────────────────+     +────────────────+   |
+─────────────────────────────────────────┬─────────────────────────────────────+
                                          │
                                          │ Deterministic JSON (gRPC/HTTPS HMAC)
                                          ▼
+-------------------------------------------------------------------------------+
|                      RG ENTITY (Layer 3+ Router OpenWrt CPE)                   |
|                                                                               |
|   +───────────────────+      +─────────────────────+     +────────────────+   |
|   |  Local API Client | ───► |   Kernel Linux tc   | ───►| Firewall Rules |   |
|   | (Instruksi Parser)|      |  (QoS Queue Boost)  |     |   (nftables)   |   |
|   +───────────────────+      +─────────────────────+     +────────────────+   |
+-------------------------------------------------------------------------------+
```

### Key Principles:
1. **TR-142 Compliance**:
   - Strictly communicates only with the **Residential Gateway (RG) Entity** (Layer 3 and above).
   - Absolute isolation from the **ONU Entity** (Layer 2 physical fiber, OMCI, PON laser).
2. **Deterministic Schema Enforcement**:
   - Pydantic and Outlines-like structured extraction prevent hallucinations or unstructured outputs from reaching the edge.
3. **Defense-in-Depth Security**:
   - Zero OS command injection guardrails sanitizing all strings and arguments against shell exploits.
4. **Privacy-by-Design**:
   - Telemetry strictly accepts anonymized metrics (throughput, RSSI, load, ping) and ignores raw user packet payloads or browsing history.

---

## 2. Directory Structure

```text
.
├── api/                            # API Gateway Layer (FastAPI)
│   ├── main.py                     # App entrypoint, middleware & routing
│   ├── middleware/                 # Auth, security, and rate limiting
│   │   ├── auth.py
│   │   └── rate_limiter.py
│   └── routes/                     # Endpoints
│       ├── control.py              # Natural language reasoning endpoint
│       ├── telemetry.py            # Privacy-safe router telemetry ingestion
│       └── webhooks.py             # Billing & IoT Cloud webhooks
│
├── agent/                          # LangGraph Stateful Reasoning Engine
│   ├── state.py                    # Network state & device profile schemas
│   ├── prompt_templates.py         # System prompts & context injection
│   ├── nodes.py                    # ReAct decision & execution nodes
│   ├── graph.py                    # Compiled LangGraph StateGraph
│   └── tools/                      # Actionable Tools
│       ├── router_cmd.py           # Kernel Linux tc & nftables formatters
│       ├── iot_control.py          # Matter & Tuya device controllers
│       └── billing_vas.py          # Operator Core Billing integrators
│
├── core/                           # Security & LLMOps Layer
│   ├── config.py                   # Environment & Pydantic Settings
│   ├── schema.py                   # Deterministic action schemas & validation
│   └── security.py                 # TR-142 validator & Command Injection Guard
│
├── integrations/                   # External Operator & Edge Drivers
│   ├── billing_client.py           # Operator BSS/OSS connector
│   ├── tuya_client.py              # Matter/Tuya Cloud-to-Cloud client
│   └── router_client.py            # OpenWrt CPE edge dispatcher
│
├── docker/                         # Deployment
│   ├── docker-compose.yaml         # Orchestration (API, Postgres, Redis)
│   └── .env.example                # Config template
│
├── Dockerfile                      # Production container image
└── requirements.txt                # Python dependencies
```

---

## 3. Quickstart Guide

### Prerequisites
- Python 3.10+
- (Optional) Docker & Docker Compose

### Configuration & LLM Setup

Before running the server, copy the docker env example to `.env` in the root directory:
```bash
cp docker/.env.example .env
```

Open `.env` and configure the LLM settings:

#### Option A: Groq Cloud API (Default & Recommended)
This is the default configuration for fast, cloud-based inference:
```env
LLM_MODEL=qwen/qwen3.6-27b
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=your_groq_api_key_here
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=1024
LLM_TIMEOUT_SEC=30.0
```

#### Option B: Local Ollama
To run the orchestrator entirely locally using CPU/GPU via Ollama:
```env
LLM_MODEL=qwen2.5:3b
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=1024
LLM_TIMEOUT_SEC=300.0  # Set higher timeout for local CPU execution
```

#### Local Development Setup
1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run Server**:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

3. **Explore OpenAPI Docs**:
Navigate to `http://localhost:8000/docs`.

---

## 4. Running Tests
You can verify the entire suite of 32 tests (schema, security, agent reasoning, API gateways) by running:
```bash
pytest -v
```

---

## 5. API Endpoints Reference

### A. Natural Language Control
- **`POST /api/v1/control/command`**
  - **Body**:
    ```json
    {
      "user_input": "Tolong prioritaskan koneksi laptop kerja saya untuk meeting video sekarang.",
      "router_id": "RG-CPE-001"
    }
    ```
  - **Response**:
    ```json
    {
      "success": true,
      "action_type": "SET_TRAFFIC_PRIORITY",
      "command": {
        "target_action": "SET_TRAFFIC_PRIORITY",
        "payload": {
          "action": "SET_TRAFFIC_PRIORITY",
          "target_mac": "A4:C3:F0:12:89:AB",
          "priority_class": "WORK_EF",
          "duration_minutes": 60,
          "narrative_response": "Prioritas jaringan kelas WORK_EF berhasil diaktifkan untuk perangkat kerja (A4:C3:F0:12:89:AB) selama 60 menit."
        },
        "summary": "Prioritaskan lalu lintas kerja untuk MAC A4:C3:F0:12:89:AB",
        "requires_edge_dispatch": true
      },
      "user_message": "Prioritas jaringan kelas WORK_EF berhasil diaktifkan untuk perangkat kerja (A4:C3:F0:12:89:AB) selama 60 menit.",
      "edge_dispatched": true
    }
    ```

### B. Telemetry Ingestion (Privacy-by-Design)
- **`POST /api/v1/telemetry/report`**
  - Sends anonymized router telemetry and active client summary to update the orchestrator's working memory.

### C. Direct Administrative Execution
- **`POST /api/v1/control/direct-exec`**
  - Executes strictly validated and security-scanned JSON actions directly.

---

## 5. Security & TR-142 Verification

All actions undergo verification through `core/security.py`:
- **TR-142 Compliance**: Any payload targeting physical ONU keywords (`omci`, `pon_laser`, `optical_power`, etc.) is automatically blocked with `TR142ViolationError`.
- **Command Injection Guard**: All fields are scanned for shell tokens (`;`, `&`, `|`, `` ` ``, `$()`, `rm`, `mkfs`, etc.) before reaching the Edge CPE.

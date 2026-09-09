# Office Worker Agent

A comprehensive enterprise AI system for automating microfinance workflows with advanced RAG, LLM-powered planning, multi-agent coordination, and tool integration.

**🎯 Key Features**:

- ✅ Advanced RAG (hybrid search, re-ranking, decomposition, compression, self-RAG)
- ✅ LLM-agnostic adapters (OpenAI, Deepseek, HuggingFace, Gemini, generic HTTP)
- ✅ DAG-based reactive planning with async execution
- ✅ ChromaDB long-term memory (episodic, semantic, procedural)
- ✅ Multi-agent system (Supervisor + 5 Specialists)
- ✅ Multi-format document ingestion (PDF, Excel, Word, images with OCR)
- ✅ Tool cooldown & credential management
- ✅ FastAPI REST backend with semantic search & report generation

📖 **[For Detailed Architecture & File Reference → See README_DETAILED.md](README_DETAILED.md)**

---

## Quick Start (Windows)

### 1. Bootstrap Environment

```powershell
python start.py
```

This creates `.venv` and installs dependencies automatically.

### 2. Configure Credentials

```powershell
copy .env.example .env
```

Edit `.env` with your API keys (OpenAI, Deepseek, Google, etc.).

### 3. Start the Backend

```powershell
python -m uvicorn backend_api:app --reload --host 0.0.0.0 --port 8000
```

Backend is now at `http://localhost:8000`

### 4. Try It Out

```bash
# Upload a document
curl -X POST -F "file=@report.pdf" http://localhost:8000/upload

# Semantic search
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" \
  -d '{"prompt": "Which clients have payment delays?"}'

# Generate plan (dry-run)
curl -X POST http://localhost:8000/plan -H "Content-Type: application/json" \
  -d '{"goal": "Send payment reminders and log completion"}'
```

---

## Core Components

| File                      | Purpose                                                  |
| ------------------------- | -------------------------------------------------------- |
| **agent_orchestrator.py** | Central hub wiring all services                          |
| **embeddings_rag.py**     | Advanced RAG: hybrid search, re-ranking, decomposition   |
| **llm_interface.py**      | LLM adapters (OpenAI, Deepseek, HuggingFace, Gemini)     |
| **memory_manager.py**     | ChromaDB long-term memory (episodic/semantic/procedural) |
| **reactive_planner.py**   | DAG-based planner with parallel execution                |
| **document_manager.py**   | Multi-format document ingestion                          |
| **mcp_manager.py**        | Tool registry, validation, cooldown                      |
| **tools.py**              | Email, Google, microfinance tools                        |
| **backend_api.py**        | FastAPI REST endpoints                                   |
| **specialist_agents.py**  | Data, Report, Communication, Risk, Search agents         |
| **supervisor_agent.py**   | Multi-agent orchestrator                                 |

📖 **[Full documentation → README_DETAILED.md](README_DETAILED.md)**

---

## REST API Endpoints

| Endpoint        | Method | Purpose                 |
| --------------- | ------ | ----------------------- |
| `/query`        | POST   | Semantic search         |
| `/upload`       | POST   | Ingest documents        |
| `/documents`    | GET    | List documents          |
| `/status`       | GET    | System status           |
| `/plan`         | POST   | Generate plan (dry-run) |
| `/execute_plan` | POST   | Execute plan            |
| `/report`       | POST   | Generate report         |

---

## Environment Variables

```bash
# LLM (choose one provider)
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
HF_TOKEN=hf_...

# Email
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=admin@company.com
EMAIL_PASSWORD=***

# Google (optional)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
TEAMS_WEBHOOK_URL=https://outlook.webhook.office.com/...

# Supabase (optional, for remote vector storage)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
```

See `.env.example` for all variables.

---

## Python API Examples

### Semantic Search

```python
from agent_orchestrator import AgentOrchestrator

agent = AgentOrchestrator(config={"llm_provider": "deepseek"})
agent.ingest_file("loan_data.xlsx")
result = agent.query("Which clients have payment delays?")
print(result.answer)
```

### Planning & Execution

```python
plan = agent.plan("Send payment reminders to overdue clients", top_k=5)
if plan.needs_confirmation:
    confirmed = input("Confirm? ").lower() == "yes"
else:
    confirmed = True

result = agent.execute_plan(plan, confirmed=confirmed)
print(f"Goal achieved: {result.goal_achieved}")
```

### Report Generation

```python
report = agent.generate_report(
    goal="Create Q4 2024 risk assessment",
    query="high-risk clients, default rates",
    top_k=10
)
if report.ready_to_finalize:
    report.to_word("Q4_Assessment.docx")
```

---

## LLM Adapters

Supports 6 LLM providers:

```python
from llm_interface import LLMFactory

# OpenAI
llm = LLMFactory.create({"llm_provider": "openai", "model": "gpt-4"})

# Deepseek (OpenAI-compatible)
llm = LLMFactory.create({"llm_provider": "deepseek"})

# HuggingFace
llm = LLMFactory.create({"llm_provider": "huggingface"})

# Gemini
llm = LLMFactory.create({"llm_provider": "gemini"})

# Generic (any OpenAI-compatible)
llm = LLMFactory.create({"llm_provider": "generic", "api_base": "..."})

# Mock (testing)
llm = LLMFactory.create({"llm_provider": "mock"})
```

---

## Advanced RAG Features

- **Hybrid Search**: BM25 (keyword) + Vector (semantic)
- **Re-ranking**: Cross-encoder for relevance
- **Query Decomposition**: LLM breaks complex questions
- **Compression**: Reduce token consumption
- **Knowledge Graph**: Entity relationships
- **Self-RAG**: Decide when search needed

---

## Multi-Agent System

Supervisor coordinates 5 specialist agents:

1. **DataAgent** - Spreadsheets, aggregation
2. **ReportAgent** - Document generation
3. **CommunicationAgent** - Email, notifications
4. **RiskAgent** - Loan scoring, compliance
5. **SearchAgent** - RAG-based retrieval

---

## Document Support

- **PDF**: Text + OCR for scanned
- **Excel**: .xlsx, .xls
- **Word**: .docx
- **CSV**: Configurable
- **Images**: .png, .jpg, .tiff with OCR

For OCR, install Tesseract:

```powershell
scoop install tesseract
```

---

## Next.js Frontend

```bash
cd "C:\Users\hp\Pictures\Microfinince frontend"
npm install
npm run dev
```

Set `BACKEND_URL=http://localhost:8000` in `.env.local`

---

## Architecture Overview

```
┌──────────────────────────────────┐
│    Frontend (Next.js)            │
├──────────────────────────────────┤
│    Backend REST API (FastAPI)    │
├──────────────────────────────────┤
│    AgentOrchestrator (Hub)       │
├────────┬────────┬────────┬───────┤
│  RAG   │ Memory │Planner │Agents │
├────────┴────────┴────────┴───────┤
│     Tools (Email, Google, etc.)  │
└──────────────────────────────────┘
```

---

## Documentation

- **[README_DETAILED.md](README_DETAILED.md)** - Complete architecture & file reference
- **[DETAILED_FUNCTIONALITY_REPORT.md](DETAILED_FUNCTIONALITY_REPORT.md)** - System capabilities
- **[TOOL_CREDENTIALS_IMPLEMENTATION.md](TOOL_CREDENTIALS_IMPLEMENTATION.md)** - Tool setup

---

**Status**: Production Ready ✅  
**Version**: 2.0 (Advanced RAG + Multi-Agent)  
**Python**: 3.11+

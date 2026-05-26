# Property Agent UI

An AI-powered Malaysian property search agent that combines a conversational LLM interface with live scraping of [Mudah.my](https://www.mudah.my). Users describe what they're looking for, the agent profiles their needs, scrapes real listings, classifies them into match tiers, weights results dynamically, and walks the user through a ranked shortlist — all in a chat-style UI.

---

## Architecture Overview

```
property-agent-ui/   ← React 19 + TanStack Router frontend (Vite)
backend/             ← FastAPI Python backend
  main.py            ← All REST endpoints
  llm_client.py      ← Chutes AI integration (DeepSeek-V3, Llama, Qwen)
  search_pipeline.py ← Scrape → tier classify → weight → LLM remarks
  scraper/           ← Mudah.my async scraper (Playwright + BS4)
  session_manager.py ← In-memory session state
  topology.py        ← Malaysian district/region graph
  config.yaml        ← LLM model + scraper config
```

**LLM Provider:** [Chutes AI](https://chutes.ai) (OpenAI-compatible API, hosts DeepSeek-V3, Llama 3.1, Qwen 2.5)

**Scraper mode:** `realtime` (live Mudah.my scrape) or `demo` (bundled CSV fallback — no API key or internet needed for demo)

---

## Prerequisites

| Tool | Min version |
|------|-------------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |

---

## 1 — Get a Chutes AI API Key

1. Sign up at <https://chutes.ai>
2. Generate an API key from your dashboard
3. Keep it handy — you'll paste it into `.env` below

> **No key?** You can still run the backend in `demo` mode (see Step 3).

---

## 2 — Clone the repo

```bash
git clone --depth 1 https://github.com/MAXAJIE/wsdfc.git
cd wsdfc
```

---

## 3 — Backend setup

### macOS / Linux

```bash
cd backend

# Create and activate virtualenv
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r ../requirements.txt

# Install Playwright browsers (needed for live scraping)
playwright install chromium

# Create your .env
cp .env.example .env
```

Open `.env` and paste your API key:

```
CHUTES_AI_API_KEY=your-key-here
CHUTES_AI_BASE_URL=https://llm.chutes.ai/v1
APP_SECRET_KEY=change-me-in-production
```

### Windows

```cmd
cd backend

python -m venv venv
venv\Scripts\activate.bat

pip install -r ..\requirements.txt
playwright install chromium

copy .env.example .env
```

Then edit `.env` with your API key.

### Demo mode (no API key / no internet scraping)

In `backend/config.yaml`, set:

```yaml
scraper:
  mode: "demo"
```

The backend will serve bundled mock listings instead of live scrapes, and the UI will display a popup indicating demo mode is active.

---

## 4 — Run the backend

```bash
# Still inside backend/ with venv active
python startup.py
```

`startup.py` runs pre-flight checks (Python version, deps, `.env`, config, mock data) and then launches uvicorn on **http://localhost:8000**.

Alternatively, launch uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's up:

```
http://localhost:8000/docs      ← Swagger UI
http://localhost:8000/redoc     ← ReDoc
```

---

## 5 — Frontend setup

Open a **new terminal** from the repo root:

```bash
cd property-agent-ui

npm install

# Point the frontend at your local backend
# (the default dev proxy already targets http://localhost:8000)
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## 6 — Quick start scripts (optional)

The repo ships with convenience scripts that do Steps 3–4 in one go.

**macOS / Linux:**
```bash
cd wsdfc
bash backend/start.sh
```

**Windows:**
```cmd
cd wsdfc
backend\start.bat
```

After the backend is up, still run the frontend manually (Step 5).

---

## How it works — user flow

1. **Phase 1 form** — enter budget, target (e.g. "condo in Johor Bahru"), buyer identity, preferred agent style
2. **Semantic alignment** — LLM extracts structured tags from free-text input
3. **Conversation** — agent asks clarifying questions and detects preference conflicts
4. **Search** — pipeline scrapes Mudah.my for the matched districts, classifies listings into Tier 1 / 2 / 3, applies dynamic weighting, generates LLM remarks per property
5. **Results** — two batches of 5 listings shown; user can reject individual listings or all of them
6. **Resolution** — on full rejection the agent offers "refine search" (new prompt) or "keep memories" (soft reset)

---

## API reference (key endpoints)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/init_session` | Start a session with Phase 1 data |
| `GET`  | `/api/v1/session_ready/{id}` | Poll until semantic alignment finishes |
| `POST` | `/api/v1/chat` | Send a chat message |
| `GET`  | `/api/v1/search_status/{id}` | Poll search pipeline progress |
| `GET`  | `/api/v1/next_batch/{id}` | Fetch second batch of results |
| `POST` | `/api/v1/reject_single` | Reject one listing |
| `POST` | `/api/v1/reject_all` | Reject all, trigger NPP learning |
| `POST` | `/api/v1/resolve_action` | Choose next step after full rejection |
| `GET`  | `/api/v1/system_status` | Health check + demo mode flag |

**Example — init session:**
```bash
curl -X POST http://localhost:8000/api/v1/init_session \
  -H "Content-Type: application/json" \
  -d '{
    "budget": 500000,
    "agent_style": "Professional",
    "target": "condo in Johor Bahru",
    "identity": "first_time_buyer",
    "gender": "female"
  }'
```

---

## Configuration reference

`backend/config.yaml`:

```yaml
llm:
  model: deepseek-ai/DeepSeek-V3.2-TEE   # main dialogue model
  max_tokens: 2000
  concurrency: 3                           # max parallel LLM calls

scraper:
  mode: "realtime"          # "realtime" | "demo"
  retries: 3
  realtime_budget_seconds: 90   # abort slow scrapes after this many seconds
```

Per-phase models can be overridden via environment variables:

```
REMARKS_MODEL=chutesai/Llama-3.1-8B-Instruct
REASONING_MODEL=Qwen/Qwen2.5-7B-Instruct
REMARKS_MAX_TOKENS=512
REMARKS_CONCURRENCY=8
```

---

## Project structure

```
wsdfc/
├── requirements.txt                  # Python deps
├── backend/
│   ├── .env.example                  # copy → .env, add API key
│   ├── config.yaml                   # LLM + scraper settings
│   ├── main.py                       # FastAPI app + all endpoints
│   ├── llm_client.py                 # Chutes AI async client
│   ├── search_pipeline.py            # end-to-end search orchestration
│   ├── session_manager.py            # in-memory session store
│   ├── schemas.py                    # Pydantic models
│   ├── topology.py                   # Malaysian district graph
│   ├── weighting.py                  # dynamic property scoring
│   ├── mock_data.py                  # demo-mode fixture data
│   ├── npp_enum.py / positive_enum.py # preference tag enums
│   ├── startup.py                    # pre-flight checks + uvicorn launcher
│   ├── start.sh / start.bat          # convenience start scripts
│   └── scraper/
│       ├── mudah_scraper.py          # Playwright + BS4 scraper
│       ├── pipeline.py               # scrape orchestration
│       ├── seeder.py                 # district seed logic
│       ├── storage.py                # scraped data store
│       └── live_filter.py            # real-time listing filter
└── property-agent-ui/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── routes/                   # TanStack Router pages
        ├── components/               # React components by phase
        ├── hooks/                    # custom React hooks
        └── lib/                      # store (Zustand), API client, utils
```

---

## Troubleshooting

**Backend won't start — missing `.env`**
```bash
cp backend/.env.example backend/.env
# then add your CHUTES_AI_API_KEY
```

**Playwright browser not found**
```bash
playwright install chromium
```

**Live scrape always fails / falls back to demo**
Mudah.my may be rate-limiting or blocking headless requests. Either wait and retry, increase `realtime_budget_seconds` in `config.yaml`, or switch to `mode: "demo"` for development.

**CORS errors in the browser**
Make sure the backend is running on port 8000 and the frontend dev server is on port 5173. The FastAPI CORS middleware allows all origins by default in this build.

**`python` not found on macOS/Linux**
Use `python3` — the `start.sh` script already handles this.

---

## License

See repository for license details.

# Email Follow-Up Agent

An ambient AI agent that runs every Monday, reads your Gmail inbox for the past week, identifies emails that need a reply, and saves draft responses directly to your Gmail Drafts folder. Every run is fully traced in LangSmith.

---

## What it does

Every Monday at 8:00 AM the agent wakes up automatically and:

1. Reads all emails in your **Gmail Primary inbox** from the past 7 days
2. Analyzes each thread using an LLM to decide if a reply is needed
3. Writes a draft reply for every thread that needs follow-up
4. Saves the drafts to your **Gmail Drafts folder**
5. Detects meeting requests and creates **Google Calendar events** with a Meet link when you approve the draft

You review the drafts at your convenience and decide what to send.

---

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LangGraph Agent                          │
│                                                                 │
│   fetch_emails                                                  │
│       │  Gmail API — threads from last 7 days (Primary only)   │
│       ▼                                                         │
│   analyze_emails                                                │
│       │  LLM — parallel analysis of all threads (10 at a time) │
│       │  Decides: needs_followup? is_meeting_request?           │
│       ▼                                                         │
│   draft_followups                                               │
│       │  LLM — writes a draft reply for each flagged thread    │
│       ▼                                                         │
│   save_drafts                                                   │
│       │  Gmail API — saves drafts to Gmail Drafts folder       │
│       ▼                                                         │
│   summarize                                                     │
│       │  LLM — generates a run summary logged to LangSmith     │
│       ▼                                                         │
│      END                                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ (local run only)
                              ▼
                    Interactive Review CLI
                    ┌─────────────────────┐
                    │  [y] Send draft      │
                    │  [e] Edit then send  │  ──► Gmail API (send)
                    │  [n] Skip            │  ──► Calendar API (if meeting)
                    └─────────────────────┘
```

### Key design decisions

| Decision | Reason |
|---|---|
| Threads analyzed in parallel (10 workers) | ~10x faster than sequential LLM calls |
| Drafts saved, not auto-sent | You always review before anything is sent |
| Calendar event created only on approval | Prevents phantom invites for skipped drafts |
| LLM is swappable via env var | Works with Anthropic Claude or OpenAI GPT |
| Full LangSmith tracing | Every node, every run is observable |

---

## Stack

| Concern | Technology |
|---|---|
| Agent framework | [LangGraph](https://github.com/langchain-ai/langgraph) |
| Tracing & scheduling | [LangSmith](https://smith.langchain.com) + LangGraph Cloud cron |
| Email | Gmail API (OAuth 2.0) |
| Calendar | Google Calendar API (OAuth 2.0) |
| LLM | Configurable — Anthropic Claude or OpenAI GPT |
| Settings | pydantic-settings |

---

## Project Structure

```
email-agent/
├── agent/
│   ├── graph.py        # LangGraph StateGraph — wires all nodes together
│   ├── nodes.py        # Node functions: fetch, analyze, draft, save, summarize
│   ├── state.py        # AgentState and EmailThread schemas
│   └── prompts.py      # LLM system prompts
├── gmail/
│   ├── auth.py         # Gmail + Calendar OAuth2 flow with token refresh
│   └── client.py       # Gmail API: fetch threads, create/send/delete drafts
├── calendar_tool/
│   └── client.py       # Google Calendar API: create events with Meet link
├── config.py           # Settings loaded from .env, LLM factory
├── langgraph.json      # LangGraph Cloud deployment manifest
├── main.py             # Local runner with interactive review step
├── run.sh              # Shell wrapper (suppresses noise warnings)
└── .env.example        # Template for environment variables
```

---

## Setup from Scratch

### Prerequisites

- Python 3.9+
- A Google account (Gmail)
- An Anthropic or OpenAI API key
- A LangSmith account (free at [smith.langchain.com](https://smith.langchain.com))

---

### Step 1 — Clone and install

```bash
git clone https://github.com/francescoliso/email-agent.git
cd email-agent
pip3 install -r requirements.txt
```

---

### Step 2 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
MODEL_PROVIDER=anthropic          # or "openai"
MODEL_NAME=claude-sonnet-4-6      # or e.g. "gpt-4o"
ANTHROPIC_API_KEY=sk-ant-...      # get from console.anthropic.com
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=email-agent
LANGSMITH_API_KEY=lsv2_...        # get from smith.langchain.com → Settings → API Keys
```

---

### Step 3 — Set up Gmail & Calendar access

The agent needs permission to read your Gmail and create Calendar events. This is done once via OAuth.

#### 3a. Create Google Cloud credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Go to **API e servizi → Libreria**
4. Search and enable **Gmail API**
5. Search and enable **Google Calendar API**
6. Go to **API e servizi → Credenziali**
7. Click **Crea credenziali → ID client OAuth 2.0**
8. Application type: **App desktop**
9. Click **Scarica JSON** and save the file as:
   ```
   ~/Desktop/email-agent/credentials.json
   ```
10. Go to **API e servizi → Schermata consenso OAuth → Modifica app**
11. Set **Tipo utente** to **Esterno** and save

#### 3b. Authorize the agent (one-time)

```bash
cd ~/Desktop/email-agent
python3 -W ignore -m gmail.auth
```

A browser window will open. Sign in with your Google account and grant access. A `token.json` file is saved automatically — the agent uses it for all future runs without needing the browser again.

---

### Step 4 — Run locally

```bash
~/Desktop/email-agent/run.sh
```

The agent will:
- Fetch and analyze your inbox
- Print a summary
- Show each draft that needs review

For each draft you can:
- **`y`** → send it
- **`e`** → edit the body, then send
- **`n`** → skip (draft stays in Gmail for later)

If a meeting was detected, a Google Calendar event with a Meet link is created automatically when you send.

---

## Deploy to LangGraph Cloud (runs every Monday automatically)

### Step 1 — Push your code to GitHub

Make sure your latest code is on GitHub:
```bash
git push
```

### Step 2 — Create a deployment

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Left sidebar → **Deployments** → **+ New Deployment**
3. Connect your GitHub account and select `email-agent`
4. Fill in:
   - **Name**: `email-agent`
   - **Git Ref**: `main`
   - **Config file**: `langgraph.json`
5. Add environment variables:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `LANGCHAIN_TRACING_V2` | `true` |
| `LANGCHAIN_PROJECT` | `email-agent` |

6. Click **Deploy**

### Step 3 — Set the Monday cron

Once deployed, go to your deployment → **Crons** → **Add**:

```
0 8 * * 1
```

This runs every Monday at 8:00 AM UTC.

> ⚠️ **Gmail OAuth and cloud deployments**: The `token.json` file is generated locally and is not committed to GitHub (it's in `.gitignore`). For the cloud deployment to access Gmail, you need to either use a Google Service Account or handle token upload separately. The local `run.sh` script is the recommended way to use the agent until service account support is added.

---

## Development vs Production deployments

| | Development | Production |
|---|---|---|
| Infrastructure | Preemptible (shared) | Dedicated |
| Uptime | May sleep when idle | Always on |
| Reliability | Best-effort | Guaranteed |
| Cost | Lower | Higher |
| Upgrade path | Cannot upgrade — need new deployment | — |

For a weekly Monday agent, **Development is sufficient**.

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `MODEL_PROVIDER` | Yes | `anthropic` or `openai` |
| `MODEL_NAME` | Yes | e.g. `claude-sonnet-4-6` or `gpt-4o` |
| `ANTHROPIC_API_KEY` | If using Anthropic | From [console.anthropic.com](https://console.anthropic.com) |
| `OPENAI_API_KEY` | If using OpenAI | From [platform.openai.com](https://platform.openai.com) |
| `LANGCHAIN_TRACING_V2` | Yes | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | No | LangSmith project name (default: `email-agent`) |
| `GMAIL_CREDENTIALS_PATH` | No | Path to OAuth credentials (default: `~/Desktop/email-agent/credentials.json`) |
| `GMAIL_TOKEN_PATH` | No | Path to cached token (default: `~/Desktop/email-agent/token.json`) |

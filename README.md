# Email Follow-Up Agent

An ambient LangGraph agent that runs every Monday, reads your Gmail inbox for the past week, identifies threads that need a reply, and saves draft responses directly to your Gmail Drafts folder. Every run is fully traced in LangSmith.

## How it works

```
fetch_emails → analyze_emails → draft_followups → save_drafts → summarize
```

1. **fetch_emails** — pulls all threads from the last 7 days (excludes sent, drafts, spam, trash)
2. **analyze_emails** — LLM decides which threads need a follow-up and why
3. **draft_followups** — LLM writes a concise reply for each flagged thread
4. **save_drafts** — saves each draft to Gmail Drafts (you review and send manually)
5. **summarize** — generates a run summary logged to LangSmith

## Stack

| Concern | Technology |
|---|---|
| Agent framework | [LangGraph](https://github.com/langchain-ai/langgraph) |
| Tracing & scheduling | [LangSmith](https://smith.langchain.com) + LangGraph Platform cron |
| Email | Gmail API (OAuth 2.0) |
| LLM | Configurable — Anthropic Claude or OpenAI GPT |
| Settings | pydantic-settings |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Gmail credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → enable the **Gmail API**
3. Create an **OAuth 2.0 Desktop** credential → download `credentials.json`
4. Save it to `~/.email-agent/credentials.json`

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
MODEL_PROVIDER=anthropic          # or "openai"
MODEL_NAME=claude-sonnet-4-6      # or e.g. "gpt-4o"
ANTHROPIC_API_KEY=sk-ant-...      # or OPENAI_API_KEY
LANGSMITH_API_KEY=lsv2_...
```

### 4. Authorize Gmail (one-time)

```bash
python -m gmail.auth
```

This opens a browser window to grant Gmail access. The token is saved to `~/.email-agent/token.json` and auto-refreshes on subsequent runs.

### 5. Run locally

```bash
python main.py
```

Check [LangSmith](https://smith.langchain.com) for the full node-by-node trace.

## Deploy with LangGraph Cloud

```bash
pip install langgraph-cli
langgraph build
langgraph deploy
```

Then in the LangGraph Cloud UI go to **Crons → Add** and set the schedule:

```
0 8 * * 1
```

This runs the agent every Monday at 8:00 AM UTC.

## Project structure

```
email-agent/
├── agent/
│   ├── graph.py        # LangGraph StateGraph
│   ├── nodes.py        # Node functions
│   ├── state.py        # AgentState + EmailThread schemas
│   └── prompts.py      # LLM system prompts
├── gmail/
│   ├── auth.py         # OAuth2 flow + token refresh
│   └── client.py       # Gmail API wrapper
├── config.py           # Settings + LLM factory
├── langgraph.json      # LangGraph deployment manifest
└── main.py             # Local entry point
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `MODEL_PROVIDER` | Yes | `anthropic` or `openai` |
| `MODEL_NAME` | Yes | Model ID (e.g. `claude-sonnet-4-6`, `gpt-4o`) |
| `ANTHROPIC_API_KEY` | If using Anthropic | Anthropic API key |
| `OPENAI_API_KEY` | If using OpenAI | OpenAI API key |
| `LANGSMITH_API_KEY` | Yes | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project name (default: `email-agent`) |
| `GMAIL_CREDENTIALS_PATH` | No | Path to OAuth credentials (default: `~/.email-agent/credentials.json`) |
| `GMAIL_TOKEN_PATH` | No | Path to cached token (default: `~/.email-agent/token.json`) |

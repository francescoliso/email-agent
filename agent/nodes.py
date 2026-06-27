import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from agent.state import AgentState, EmailThread
from agent.prompts import ANALYZE_SYSTEM, DRAFT_SYSTEM, SUMMARIZE_SYSTEM
from config import settings
import gmail.client as gmail_client

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = settings.build_llm()
    return _llm


@traceable(name="fetch_emails")
def fetch_emails(state: AgentState) -> AgentState:
    errors = list(state.get("errors", []))
    try:
        threads = gmail_client.fetch_threads(days_back=7)
        logger.info(f"Fetched {len(threads)} threads from the past 7 days")
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        threads = []
        errors.append(f"fetch_emails: {e}")
    return {**state, "threads": threads, "errors": errors}


def _analyze_thread(thread: EmailThread) -> tuple:
    llm = _get_llm()
    try:
        response = llm.invoke([
            SystemMessage(content=ANALYZE_SYSTEM),
            HumanMessage(content=_format_thread(thread)),
        ])
        parsed = _parse_json(response.content)
        return {
            **thread,
            "needs_followup": bool(parsed.get("needs_followup", False)),
            "followup_reason": parsed.get("reason", ""),
        }, None
    except Exception as e:
        return thread, f"analyze_emails[{thread['thread_id']}]: {e}"


@traceable(name="analyze_emails")
def analyze_emails(state: AgentState) -> AgentState:
    errors = list(state.get("errors", []))
    results: dict[str, EmailThread] = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_analyze_thread, t): t["thread_id"] for t in state["threads"]}
        for future in as_completed(futures):
            thread, error = future.result()
            results[thread["thread_id"]] = thread
            if error:
                logger.error(error)
                errors.append(error)

    updated_threads = [results[t["thread_id"]] for t in state["threads"]]
    flagged = sum(1 for t in updated_threads if t["needs_followup"])
    logger.info(f"Analysis complete: {flagged}/{len(updated_threads)} threads need follow-up")
    return {**state, "threads": updated_threads, "errors": errors}


@traceable(name="draft_followups")
def draft_followups(state: AgentState) -> AgentState:
    llm = _get_llm()
    errors = list(state.get("errors", []))
    updated_threads: list[EmailThread] = []

    for thread in state["threads"]:
        if not thread["needs_followup"]:
            updated_threads.append(thread)
            continue
        try:
            thread_text = _format_thread(thread)
            prompt = f"{thread_text}\n\nReason a follow-up is needed: {thread['followup_reason']}"
            response = llm.invoke([
                SystemMessage(content=DRAFT_SYSTEM),
                HumanMessage(content=prompt),
            ])
            thread = {**thread, "draft_body": response.content.strip()}
        except Exception as e:
            logger.error(f"draft failed for thread {thread['thread_id']}: {e}")
            errors.append(f"draft_followups[{thread['thread_id']}]: {e}")
        updated_threads.append(thread)

    return {**state, "threads": updated_threads, "errors": errors}


@traceable(name="save_drafts")
def save_drafts(state: AgentState) -> AgentState:
    errors = list(state.get("errors", []))
    updated_threads: list[EmailThread] = []

    for thread in state["threads"]:
        if not thread["needs_followup"] or not thread["draft_body"]:
            updated_threads.append(thread)
            continue
        try:
            to = _pick_reply_to(thread)
            draft_id = gmail_client.create_draft(
                thread_id=thread["thread_id"],
                to=to,
                subject=thread["subject"],
                body=thread["draft_body"],
            )
            thread = {**thread, "draft_id": draft_id}
            logger.info(f"Draft created: {draft_id} for thread '{thread['subject']}'")
        except Exception as e:
            logger.error(f"save_draft failed for thread {thread['thread_id']}: {e}")
            errors.append(f"save_drafts[{thread['thread_id']}]: {e}")
        updated_threads.append(thread)

    return {**state, "threads": updated_threads, "errors": errors}


@traceable(name="summarize")
def summarize(state: AgentState) -> AgentState:
    llm = _get_llm()
    threads = state["threads"]
    flagged = [t for t in threads if t["needs_followup"]]
    saved = [t for t in threads if t.get("draft_id")]
    errors = state.get("errors", [])

    stats = (
        f"Threads reviewed: {len(threads)}\n"
        f"Needing follow-up: {len(flagged)}\n"
        f"Drafts created: {len(saved)}\n"
        f"Errors: {len(errors)}\n"
    )
    if errors:
        stats += "Error details:\n" + "\n".join(f"  - {e}" for e in errors)

    try:
        response = llm.invoke([
            SystemMessage(content=SUMMARIZE_SYSTEM),
            HumanMessage(content=stats),
        ])
        summary = response.content.strip()
    except Exception:
        summary = stats

    logger.info(f"Run summary: {summary}")
    return {**state, "run_summary": summary}


# ── helpers ──────────────────────────────────────────────────────────────────

def _format_thread(thread: EmailThread) -> str:
    lines = [f"Subject: {thread['subject']}", ""]
    for msg in thread["messages"]:
        lines.append(f"From: {msg['from']}  |  Date: {msg['date']}")
        lines.append(msg["body"].strip()[:2000])  # cap per-message size
        lines.append("---")
    return "\n".join(lines)


def _parse_json(text: str) -> dict:
    """Parse JSON from LLM response, stripping markdown code fences if present."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def _pick_reply_to(thread: EmailThread) -> str:
    last_msg = thread["messages"][-1]
    return last_msg.get("from", ", ".join(thread["participants"]))

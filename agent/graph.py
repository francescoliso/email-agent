from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import fetch_emails, analyze_emails, draft_followups, save_drafts, summarize

_builder = StateGraph(AgentState)

_builder.add_node("fetch_emails", fetch_emails)
_builder.add_node("analyze_emails", analyze_emails)
_builder.add_node("draft_followups", draft_followups)
_builder.add_node("save_drafts", save_drafts)
_builder.add_node("summarize", summarize)

_builder.set_entry_point("fetch_emails")
_builder.add_edge("fetch_emails", "analyze_emails")
_builder.add_edge("analyze_emails", "draft_followups")
_builder.add_edge("draft_followups", "save_drafts")
_builder.add_edge("save_drafts", "summarize")
_builder.add_edge("summarize", END)

graph = _builder.compile()

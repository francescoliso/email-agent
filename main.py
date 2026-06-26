"""Local entry point. Run: python main.py"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

from agent.graph import graph
from agent.state import AgentState


def run():
    initial_state: AgentState = {
        "threads": [],
        "run_summary": "",
        "errors": [],
    }

    final_state = graph.invoke(initial_state)

    print("\n" + "=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)
    print(final_state["run_summary"])

    drafts_created = [t for t in final_state["threads"] if t.get("draft_id")]
    if drafts_created:
        print(f"\nDrafts created ({len(drafts_created)}):")
        for t in drafts_created:
            print(f"  • [{t['draft_id']}] {t['subject']}")

    if final_state["errors"]:
        print(f"\nErrors ({len(final_state['errors'])}):")
        for e in final_state["errors"]:
            print(f"  ✗ {e}")

    return final_state


if __name__ == "__main__":
    run()

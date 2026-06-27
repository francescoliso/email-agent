"""Local entry point. Run: python main.py"""

import logging
import sys
import warnings
warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

from agent.graph import graph
from agent.state import AgentState
import gmail.client as gmail_client


def review_and_send(drafts: list) -> None:
    if not drafts:
        return

    print(f"\n{'=' * 60}")
    print(f"REVIEW DRAFTS ({len(drafts)} to review)")
    print(f"{'=' * 60}")

    for i, thread in enumerate(drafts, 1):
        print(f"\n[{i}/{len(drafts)}] Subject: {thread['subject']}")
        print(f"To: {thread['participants']}")
        print(f"Reason: {thread['followup_reason']}")
        print(f"\n--- DRAFT ---\n{thread['draft_body']}\n-------------")

        while True:
            choice = input("Action: [y] send / [e] edit / [n] skip  → ").strip().lower()

            if choice == "y":
                gmail_client.send_draft(thread["draft_id"])
                print("✓ Sent.")
                break
            elif choice == "e":
                print("Paste your edited reply (press Enter twice when done):")
                lines = []
                while True:
                    line = input()
                    if line == "" and lines and lines[-1] == "":
                        break
                    lines.append(line)
                new_body = "\n".join(lines).strip()

                new_draft_id = gmail_client.create_draft(
                    thread_id=thread["thread_id"],
                    to=thread["participants"][0] if thread["participants"] else "",
                    subject=thread["subject"],
                    body=new_body,
                )
                gmail_client.send_draft(new_draft_id)
                print("✓ Edited and sent.")
                break
            elif choice == "n" or choice == "":
                print("↷ Skipped — draft kept in Gmail.")
                break
            else:
                print("Type 'y' to send, 'e' to edit, or 'n' to skip.")


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

    if final_state["errors"]:
        print(f"\nErrors ({len(final_state['errors'])}):")
        for e in final_state["errors"]:
            print(f"  ✗ {e}")

    drafts_created = [t for t in final_state["threads"] if t.get("draft_id")]
    review_and_send(drafts_created)


if __name__ == "__main__":
    run()

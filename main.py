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
import calendar_tool.client as calendar_client


def _maybe_schedule_meeting(thread: dict) -> None:
    if thread.get("is_meeting_request") and thread.get("meeting_datetime"):
        try:
            attendees = [p for p in thread["participants"] if "@" in p]
            event_url = calendar_client.create_event(
                summary=thread["subject"],
                start_iso=thread["meeting_datetime"],
                attendees=attendees,
                description=f"Scheduled by email agent from thread: {thread['subject']}",
            )
            print(f"📅 Google Meet created: {event_url}")
        except Exception as e:
            print(f"⚠ Could not create calendar event: {e}")


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
        if thread.get("is_meeting_request"):
            print(f"📅 Meeting request detected — event will be created on send")
        print(f"\n--- DRAFT ---\n{thread['draft_body']}\n-------------")

        while True:
            print("Action: [y] send / [e] edit / [n] skip", flush=True)
            choice = input("→ ").strip().lower()

            if choice == "y":
                gmail_client.send_draft(thread["draft_id"])
                _maybe_schedule_meeting(thread)
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
                # Delete old draft only after the new one is successfully sent
                try:
                    gmail_client.delete_draft(thread["draft_id"])
                except Exception:
                    pass
                _maybe_schedule_meeting(thread)
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

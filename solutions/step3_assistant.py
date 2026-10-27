#!/usr/bin/env python3
"""LAB PART 3 - human oversight.

An answer reaches the requester only when it is safe to release. Everything else is held in
a review queue until a licensed clinician approves, edits or rejects it (CHS-POL-001 s6).

Run:
    python step3_assistant.py "What does the sepsis pathway require in the first hour?"
    python step3_assistant.py --urgent "..."
    python step3_assistant.py --status <review-id>

Then open the clinician console in a second terminal:
    streamlit run reviewer_app.py
"""
from __future__ import annotations

import argparse
import getpass

import review_queue
from ask_agent import ask


def should_hold(result: dict) -> tuple[bool, str]:
    """Decide whether this answer must be held for clinician review.

    Fail closed: anything the agent flagged, anything Low confidence, and anything without a
    citation is held. An uncited answer is ungrounded by definition (CHS-POL-001).
    """
    if result.get("requires_clinician_review"):
        return True, result.get("review_reason") or "The agent deferred this request."
    if result.get("confidence") == "Low":
        return True, "Low confidence"
    if not result.get("citations"):
        return True, "No citation from the approved corpus"
    return False, ""


def handle(question: str, *, requester: str, urgent: bool = False) -> dict:
    result = ask(question)
    hold, reason = should_hold(result)

    if not hold:
        return {"released": True, "result": result}

    queued = dict(result)
    queued["review_reason"] = result.get("review_reason") or reason
    item_id = review_queue.enqueue(
        question=question,
        result=queued,
        requester=requester,
        urgency="urgent" if urgent else "routine",
    )
    return {"released": False, "review_id": item_id, "reason": queued["review_reason"], "result": result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?")
    parser.add_argument("--urgent", action="store_true", help="CHS-POL-002 Tier 2 timing")
    parser.add_argument("--requester", default=None)
    parser.add_argument("--status", metavar="REVIEW_ID")
    args = parser.parse_args()

    if args.status:
        item = review_queue.get_item(args.status)
        if item is None:
            print(f"No review item {args.status}")
            return
        print(f"status   : {item['status']}")
        print(f"question : {item['question']}")
        if item["status"] == review_queue.PENDING:
            print(f"queued   : {item['created_at']} ({item['urgency']})")
            print("\nHeld for clinician review. Nothing is released until a clinician decides.")
        else:
            print(f"reviewer : {item['reviewer']} at {item['decided_at']}")
            print(f"note     : {item['reviewer_note']}")
            print(f"\n{item['final_answer']}")
        return

    if not args.question:
        parser.error("a question is required unless --status is used")

    outcome = handle(args.question, requester=args.requester or getpass.getuser(), urgent=args.urgent)
    result = outcome["result"]

    print(f"\nQ: {args.question}\n")
    if outcome["released"]:
        print(result["answer"])
        print(f"\nConfidence: {result['confidence']}")
        for citation in result["citations"]:
            detail = f" - {citation['detail']}" if citation.get("detail") else ""
            print(f"  * {citation['document']}{detail}")
    else:
        print("Held for clinician review - not released to the requester.")
        print(f"\nReason    : {outcome['reason']}")
        print(f"Review ID : {outcome['review_id']}")
        print(f"Timing    : {'within 15 minutes (Tier 2)' if args.urgent else 'within 1 business hour'}")
        print(f"\nCheck later with:  python step3_assistant.py --status {outcome['review_id']}")


if __name__ == "__main__":
    main()

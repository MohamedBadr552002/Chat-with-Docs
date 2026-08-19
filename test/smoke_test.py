"""
Quick smoke test — validates the full pipeline without the UI.
Requires GOOGLE_API_KEY in .env and Redis running.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import textwrap
from src.ingestion.pipeline import ingest_wikipedia, get_knowledge_stats
from src.workflow.orchestrator import WorkflowOrchestrator


def _hr():
    print("─" * 70)


def main():
    _hr()
    print("EvalGen AI — Smoke Test")
    _hr()

    # 1. Ingest a Wikipedia page
    print("Step 1: Ingesting Wikipedia — 'Large language model'…")
    result = ingest_wikipedia("Large language model")
    print(f"  Status: {result['status']}  |  Chunks added: {result['chunks_added']}")

    stats = get_knowledge_stats()
    print(f"  Knowledge base total chunks: {stats['total_chunks']}")
    _hr()

    # 2. Run the workflow
    question = "What is a large language model and how does it work?"
    print(f"Step 2: Running workflow for:\n  '{question}'")
    _hr()

    orch = WorkflowOrchestrator()

    def on_iter(data):
        dec = data["evaluation"].get("decision","?")
        score = data["evaluation"].get("overall_score", 0)
        print(f"  [Iter {data['iteration']}] Decision: {dec.upper()}  Score: {score:.1f}/10")
        if dec == "reject":
            fb = data["evaluation"].get("feedback", "")
            print(f"  Feedback: {textwrap.shorten(fb, 120)}")

    result = orch.run_streaming(question, on_iteration=on_iter)
    _hr()

    print(f"Final decision   : {result['final_decision'].upper()}")
    print(f"Final score      : {result['final_score']:.1f}/10")
    print(f"Total iterations : {result['total_iterations']}")
    if result.get("terminated_by_limit"):
        print(f"WARNING          : {result.get('warning')}")
    _hr()
    print("Final Answer:")
    print(textwrap.fill(result["final_answer"], width=70))
    _hr()


if __name__ == "__main__":
    main()

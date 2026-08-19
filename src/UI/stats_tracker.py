"""Real-time stats computed from session state and backend."""
import time
from src.knowledge.cache import get_redis_client
from src.ingestion.vectorstore import get_vectorstore, collection_count
from src.utils.config import GENERATOR_MODEL, EVALUATOR_MODEL, REDIS_HOST, REDIS_PORT

def get_redis_status():
    c = get_redis_client()
    return c is not None

def get_redis_stats(redis_client):
    if redis_client is None:
        return {"hit_rate": 0, "keys": 0, "memory": "N/A"}
    try:
        info = redis_client.info()
        keys = redis_client.dbsize()
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = round(hits / total * 100) if total > 0 else 0
        mem = info.get("used_memory_human", "N/A")
        return {"hit_rate": hit_rate, "keys": keys, "memory": mem}
    except:
        return {"hit_rate": 0, "keys": 0, "memory": "N/A"}

def count_chunks_by_type():
    """Count stored chunks per file type from ChromaDB metadata."""
    try:
        vs = get_vectorstore()
        raw = vs._collection.get(include=["metadatas"])
        counts = {"PDF": 0, "DOCX": 0, "TXT": 0, "PPTX": 0,
                  "Web": 0, "Wikipedia": 0, "Audio": 0, "Code": 0}
        ext_map = {
            ".pdf": "PDF", ".docx": "DOCX", ".txt": "TXT",
            ".ppt": "PPTX", ".pptx": "PPTX", ".wav": "Audio",
            ".py": "Code", ".js": "Code", ".ts": "Code", ".java": "Code",
            ".cpp": "Code", ".c": "Code", ".cs": "Code", ".go": "Code",
            ".html": "Code", ".css": "Code", ".sql": "Code",
        }
        for meta in raw.get("metadatas", []):
            if not meta:
                continue
            src = meta.get("source", "")
            if "wikipedia" in src.lower():
                counts["Wikipedia"] += 1
            elif src.startswith("http"):
                counts["Web"] += 1
            else:
                import os
                ext = os.path.splitext(src)[1].lower()
                cat = ext_map.get(ext, "TXT")
                counts[cat] += 1
        return counts
    except:
        return {k: 0 for k in ["PDF","DOCX","TXT","PPTX","Web","Wikipedia","Audio","Code"]}

def compute_session_stats(session):
    """Derive real platform stats from session_state."""
    messages = session.get("messages", [])
    iterations_log = session.get("all_iterations_log", [])
    queries = sum(1 for m in messages if m["role"] == "user")
    results = [m["content"] for m in messages if m["role"] == "assistant"]
    successful = sum(1 for r in results if r.get("final_decision") == "accept")
    scores = [r.get("final_score", 0) for r in results if r.get("final_score")]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    iters_used = sum(r.get("total_iterations", 1) for r in results)
    iters_saved = sum(max(0, 4 - r.get("total_iterations", 4)) for r in results)
    total_chunks = collection_count()
    return {
        "queries": queries, "successful": successful,
        "avg_score": avg_score, "iters_saved": iters_saved,
        "knowledge_items": total_chunks,
    }

def format_elapsed(start_ts):
    if start_ts is None:
        return "—"
    secs = int(time.time() - start_ts)
    return f"{secs // 60}m {secs % 60}s"

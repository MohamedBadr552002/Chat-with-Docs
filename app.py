import os, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.graph_objects as go
from src.UI.ui_styles import STYLES
from src.UI.stats_tracker import (
    get_redis_status, get_redis_stats, count_chunks_by_type,
    compute_session_stats, format_elapsed, GENERATOR_MODEL, EVALUATOR_MODEL
)
from src.knowledge.cache import get_redis_client

st.set_page_config(page_title="Evaluator-Generator AI", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
st.markdown(STYLES, unsafe_allow_html=True)

# ÔöÇÔöÇ session state ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
for k, v in {"messages": [], "iterations": [], "orchestrator": None,
              "ingested": [], "kb_count": 0, "page": "Dashboard",
              "session_start": None, "token_count": 0}.items():
    if k not in st.session_state: st.session_state[k] = v

# heavy resources — cached once per process, not per rerun
@st.cache_resource(show_spinner="⏳ Loading AI models… (first run only)")
def _load_orchestrator():
    from src.workflow.orchestrator import WorkflowOrchestrator
    return WorkflowOrchestrator()

@st.cache_resource(show_spinner=False)
def _load_vectorstore():
    from src.ingestion.vectorstore import get_vectorstore
    return get_vectorstore()

def get_orch():
    return _load_orchestrator()

# preload vectorstore so the embedding model loads during spinner, not later
_vs = _load_vectorstore()

def _chunk_count() -> int:
    try:
        return _vs._collection.count()
    except Exception:
        return 0

# compute stats once per render
_redis_ok     = get_redis_status()
_redis_client = get_redis_client()
_redis_stats  = get_redis_stats(_redis_client)
_ks_counts    = count_chunks_by_type()
_stats        = compute_session_stats(st.session_state)

# ÔöÇÔöÇ sidebar ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 14px 12px;border-bottom:1px solid var(--border);margin-bottom:8px;display:flex;align-items:center;gap:10px">
      <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#7c3aed,#a855f7);display:flex;align-items:center;justify-content:center;font-size:18px">🧠</div>
      <div><div style="font-weight:700;font-size:14px;color:var(--t1)">EVALUATOR-GENERATOR AI</div>
      <div style="font-size:10px;color:var(--t3)">Intelligent QA Platform</div></div>
    </div>""", unsafe_allow_html=True)

    pages = [("🏠","Dashboard"),("💬","New Conversation"),("🗂️","Conversations")]
    st.markdown('<div class="nav-sec">Knowledge Hub</div>', unsafe_allow_html=True)
    pages += [("⬆️","Upload & Ingest"),("📚","Knowledge Sources"),("🌐","Web & Wikipedia"),("🎵","Audio Transcriptions"),("</>" ,"Source Code")]
    st.markdown('<div class="nav-sec">Evaluation</div>', unsafe_allow_html=True)
    pages += [("📋","Evaluation Logs"),("📝","Feedback History"),("📈","Analytics")]
    st.markdown('<div class="nav-sec">System</div>', unsafe_allow_html=True)
    pages += [("⚙️","Settings"),("👥","Users & Permissions"),("🔍","Logs & Monitoring")]

    for icon, label in [("🏠","Dashboard"),("💬","New Conversation"),("🗂️","Conversations")]:
        active = "nav-active" if st.session_state.page == label else ""
        st.markdown(f'<div class="nav-item {active}">{icon}&nbsp;&nbsp;{label}</div>', unsafe_allow_html=True)

    st.markdown('<div class="nav-sec">Knowledge Hub</div>', unsafe_allow_html=True)
    for icon, label in [("⬆️","Upload & Ingest"),("📚","Knowledge Sources"),("🌐","Web & Wikipedia"),("🎵","Audio Transcriptions"),("</>" ,"Source Code")]:
        active = "nav-active" if st.session_state.page == label else ""
        st.markdown(f'<div class="nav-item {active}">{icon}&nbsp;&nbsp;{label}</div>', unsafe_allow_html=True)

    st.markdown('<div class="nav-sec">Evaluation</div>', unsafe_allow_html=True)
    for icon, label in [("📋","Evaluation Logs"),("📝","Feedback History"),("📈","Analytics")]:
        st.markdown(f'<div class="nav-item">{icon}&nbsp;&nbsp;{label}</div>', unsafe_allow_html=True)

    st.markdown('<div class="nav-sec">System</div>', unsafe_allow_html=True)
    for icon, label in [("⚙️","Settings"),("👥","Users & Permissions"),("🔍","Logs & Monitoring")]:
        st.markdown(f'<div class="nav-item">{icon}&nbsp;&nbsp;{label}</div>', unsafe_allow_html=True)

    st.markdown("<hr style='border-color:var(--border);margin:14px 6px 8px'>", unsafe_allow_html=True)
    st.markdown("""
    <div style="margin:0 8px 14px;padding:10px 12px;
                background:linear-gradient(135deg,#7c3aed14,#3b82f614);
                border:1px solid var(--border);border-radius:10px;text-align:center">
      <div style="font-size:11px;font-weight:600;color:var(--t1)">Evaluator-Generator AI</div>
      <div style="font-size:9px;color:var(--t3);margin-top:3px">Self-evaluating &middot; v2.0.0</div>
    </div>""", unsafe_allow_html=True)

# ÔöÇÔöÇ main layout ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
# sticky right panel via CSS
st.markdown("""
<style>
[data-testid="column"]:last-child > div {
  position: sticky; top: 0; max-height: 100vh; overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)
main_col, right_col = st.columns([2.3, 1])

with main_col:
    # top status bar
    total_iters = len(st.session_state.iterations)
    last_eval = st.session_state.iterations[-1].get("evaluation", {}) if st.session_state.iterations else {}
    stage = "Evaluator Feedback" if st.session_state.iterations and last_eval.get("decision") == "reject" else ("Completed" if st.session_state.iterations else "Waiting")
    st.markdown(f"""
    <div style="background:var(--bg2);border-bottom:1px solid var(--border);padding:10px 18px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
      <div style="display:flex;align-items:center;gap:8px">
        <span style="font-weight:700;font-size:15px;color:var(--t1)">Intelligent QA Session</span>
        <span class="pill pill-g">🟢 Active</span>
      </div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:5px 10px;font-size:12px">
          🔁 <span style="color:var(--t2)">Loop</span> <b style="color:var(--t1)">{total_iters} / 4</b>
        </div>
        <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:5px 10px;font-size:12px">
          🎯 <span style="color:var(--t2)">Stage:</span> <b style="color:var(--amber)">{stage}</b>
        </div>
        <span class="pill {'pill-g' if _redis_ok else 'pill-r'}">{"✅ Redis Cache" if _redis_ok else "❌ Redis Off"}</span>
        <span class="pill pill-g">🟢 LLM Online</span>
        <span style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:5px 10px;font-size:11px;color:var(--t2)">🤖 {GENERATOR_MODEL}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # chat history
    chat_area = st.container()
    with chat_area:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="display:flex;justify-content:flex-end;margin:0 18px 14px;gap:10px">
                  <div style="max-width:68%">
                    <div class="user-bubble">{msg["content"]}</div>
                  </div>
                  <div style="width:34px;height:34px;border-radius:50%;background:var(--blue);display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0">U</div>
                </div>""", unsafe_allow_html=True)
            else:
                result = msg["content"]
                for rec in result.get("iterations", []):
                    ev = rec["evaluation"]
                    dec = ev.get("decision", "reject")
                    score = ev.get("overall_score", 0)
                    it = rec["iteration"]
                    badge_color = "#10b981" if it > 1 else "#7c3aed"
                    badge_label = f"Iteration {it}" + (" ┬À Improved" if it > 1 else "")

                    # iteration divider
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:10px;margin:6px 18px 8px">
                      <div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,{badge_color},{badge_color}88);display:flex;align-items:center;justify-content:center;font-size:15px">{"🤖" if it==1 else "🧩"}</div>
                      <div style="flex:1;border-top:1px dashed var(--border)"></div>
                      <span style="background:{badge_color};color:#fff;font-size:11px;font-weight:700;padding:2px 9px;border-radius:6px">Iteration {it}</span>
                    </div>""", unsafe_allow_html=True)

                    gc, ec = st.columns([1.1, 0.9])
                    with gc:
                        st.markdown(f"""
                        <div class="card card-glow" style="margin:0 0 0 18px;border-left:3px solid {badge_color}">
                          <div style="display:flex;align-items:center;gap:7px;font-weight:600;font-size:13px;color:{badge_color};margin-bottom:8px">
                            <span style="font-size:16px">🤖</span> Generator LLM
                            <span style="background:{badge_color};color:#fff;font-size:10px;padding:1px 7px;border-radius:5px">Iteration {it}</span>
                          </div>
                          <div style="font-size:13px;color:var(--t2);line-height:1.7">{rec["answer"].replace(chr(10),"<br>")}</div>
                        </div>""", unsafe_allow_html=True)
                    with ec:
                        dims = ev.get("dimension_scores", {})
                        if dims:
                            fig = go.Figure()
                            cats = list(dims.keys())
                            vals = list(dims.values())
                            fig.add_trace(go.Scatterpolar(r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself",
                                fillcolor="rgba(124,58,237,0.18)", line=dict(color="#a855f7", width=2), marker=dict(size=4)))
                            fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)",
                                radialaxis=dict(visible=True,range=[0,10],tickfont=dict(color="#55557a",size=8),gridcolor="#252545",linecolor="#252545"),
                                angularaxis=dict(tickfont=dict(color="#9090b8",size=9),gridcolor="#252545")),
                                paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=25,r=25,t=20,b=10),height=190,showlegend=False)
                            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False},
                                            key=f"evaluation-radar-{len(st.session_state.messages)}-{it}")

                    # evaluator block
                    color_ev = "#10b981" if dec == "accept" else "#f59e0b"
                    decision_label = "✅ Accepted" if dec == "accept" else "⚠️ Needs Improvement"
                    fb = ev.get("feedback", "")
                    st.markdown(f"""
                    <div style="margin:8px 18px 14px">
                      <div class="card" style="border-left:3px solid {color_ev}">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:7px">
                          <div style="display:flex;align-items:center;gap:7px;font-weight:600;font-size:13px;color:{color_ev}">
                            <span>⚖️</span> Evaluator LLM
                            <span style="background:var(--card2);color:var(--t2);font-size:10px;padding:1px 7px;border-radius:5px">Iteration {it}</span>
                          </div>
                          <span class="score-chip">Score: {score:.1f} / 10</span>
                        </div>
                        <div style="color:{color_ev};font-weight:600;font-size:13px;margin-bottom:6px">{decision_label}</div>
                        <div style="font-size:12px;color:var(--t2)">{fb.replace(chr(10),"<br>") if fb else ""}</div>
                      </div>
                    </div>""", unsafe_allow_html=True)

                # final answer highlight
                if result.get("final_decision") == "accept":
                    st.markdown(f"""
                    <div style="margin:0 18px 16px;background:#10b98110;border:1px solid #10b98133;border-radius:12px;padding:14px">
                      <div style="font-weight:700;color:#10b981;margin-bottom:6px">✅ Final Answer Accepted</div>
                      <div style="font-size:13px;color:var(--t1)">{result["final_answer"].replace(chr(10),"<br>")}</div>
                    </div>""", unsafe_allow_html=True)
                elif result.get("terminated_by_limit"):
                    st.markdown(f"""
                    <div style="margin:0 18px 16px;background:#ef444410;border:1px solid #ef444433;border-radius:12px;padding:14px">
                      <div style="font-weight:700;color:#ef4444;margin-bottom:6px">⚠️ Max Iterations Reached</div>
                      <div style="font-size:13px;color:var(--t1)">{result["final_answer"].replace(chr(10),"<br>")}</div>
                    </div>""", unsafe_allow_html=True)

    # ÔöÇÔöÇ input area ÔöÇÔöÇ
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with st.container():
        q_col, btn_col = st.columns([8, 1])
        with q_col:
            question = st.text_input("Question", placeholder="Ask a question about your documents...",
                                     label_visibility="collapsed", key="q_input")
        with btn_col:
            ask = st.button("▶", width="stretch")

    st.markdown("<div style='font-size:11px;color:var(--t3);padding:0 4px'>The system will stop after 4 iterations if the answer is not satisfactory.</div>", unsafe_allow_html=True)

    if ask and question.strip():
        if _chunk_count() == 0:
            st.warning("⬆️ Upload knowledge sources first using Quick Ingest in the right panel.")
        else:
            if st.session_state.session_start is None:
                st.session_state.session_start = time.time()
            st.session_state.messages.append({"role": "user", "content": question})
            st.session_state.iterations = []
            with st.spinner("Running Evaluator–Generator workflow…"):
                try:
                    orch = get_orch()
                    result = orch.run_streaming(question, on_iteration=lambda d: st.session_state.iterations.append(d))
                    st.session_state.messages.append({"role": "assistant", "content": result})
                    # approximate token count (4 chars ≈ 1 token)
                    ans_chars = sum(len(r["answer"]) for r in result.get("iterations",[]))
                    st.session_state.token_count = st.session_state.get("token_count",0) + ans_chars // 4
                except Exception as e:
                    st.error(f"Error: {e}")
            st.rerun()

    # ÔöÇÔöÇ platform analytics (real) ÔöÇÔöÇ
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;font-weight:700;letter-spacing:1px;color:var(--t3);text-transform:uppercase;padding:0 4px;margin-bottom:8px">Platform Analytics</div>', unsafe_allow_html=True)
    ac1,ac2,ac3,ac4,ac5 = st.columns(5)
    _score_str = f"{_stats['avg_score']:.1f} / 10" if _stats['avg_score'] else "—"
    analytics = [
        ("Total Queries", str(_stats['queries']) or "0", ""),
        ("Successful Answers", str(_stats['successful']) or "0", ""),
        ("Avg Evaluation Score", _score_str, ""),
        ("Iterations Saved", str(_stats['iters_saved']), ""),
        ("Knowledge Items", str(_stats['knowledge_items']), ""),
    ]
    for col,(lbl,val,delta) in zip([ac1,ac2,ac3,ac4,ac5], analytics):
        with col:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-lbl">{lbl}</div>
              <div class="stat-val" style="font-size:{'20px' if len(val)>6 else '22px'}">{val}</div>
              <div style="margin-top:8px;height:36px;background:linear-gradient(90deg,#7c3aed18,#a855f733);border-radius:6px"></div>
            </div>""", unsafe_allow_html=True)

# ÔöÇÔöÇ right panel ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
with right_col:
    st.markdown("<div style='padding:10px 12px 0'>", unsafe_allow_html=True)

    # workflow visualizer
    st.markdown("""
    <div class="card" style="margin-bottom:10px">
      <div style="font-weight:700;font-size:13px;color:var(--t1);margin-bottom:12px">⚙️ WORKFLOW VISUALIZER</div>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:4px">
        <div class="wf-node">
          <div class="wf-circle" style="background:#3b82f622;border:2px solid #3b82f6">👤</div>
          <span>User</span>
        </div>
        <div style="flex:1;border-top:2px solid #7c3aed;position:relative"><span style="position:absolute;top:-8px;right:-2px;color:#7c3aed;font-size:10px">▶</span></div>
        <div class="wf-node">
          <div class="wf-circle" style="background:#7c3aed22;border:2px solid #7c3aed">🤖</div>
          <span>Generator</span>
        </div>
        <div style="flex:1;border-top:2px solid #a855f7;position:relative"><span style="position:absolute;top:-8px;right:-2px;color:#a855f7;font-size:10px">▶</span></div>
        <div class="wf-node">
          <div class="wf-circle" style="background:#f59e0b22;border:2px solid #f59e0b">⚖️</div>
          <span>Evaluator</span>
        </div>
        <div style="flex:1;border-top:2px solid #10b981;position:relative"><span style="position:absolute;top:-8px;right:-2px;color:#10b981;font-size:10px">▶</span></div>
        <div class="wf-node">
          <div class="wf-circle" style="background:#10b98122;border:2px solid #10b981">✅</div>
          <span>Final</span>
        </div>
      </div>
      <div style="margin-top:8px;font-size:10px;color:#ef4444;text-align:center">↩ No → Feedback → Generator (max 4x)</div>
    </div>""", unsafe_allow_html=True)

    # knowledge sources
    kc = _chunk_count()
    st.markdown(f"""
    <div class="card" style="margin-bottom:10px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
        <div style="font-weight:700;font-size:13px;color:var(--t1)">📚 KNOWLEDGE SOURCES</div>
        <span class="pill pill-v">{len(st.session_state.ingested)}</span>
      </div>""", unsafe_allow_html=True)

    ks_types = [
        ("📄","#ef4444","PDF","PDF"),("📝","#3b82f6","DOCX","DOCX"),
        ("📃","#10b981","TXT","TXT"),("📊","#f59e0b","PPTX","PPTX"),
        ("🌐","#06b6d4","Web","Web"),("📖","#a855f7","Wikipedia","Wikipedia"),
        ("🎵","#ec4899","Audio","Audio"),("💻","#7c3aed","Code","Code"),
    ]
    cols = st.columns(4)
    for i,(icon,color,label,key) in enumerate(ks_types):
        with cols[i%4]:
            cnt = _ks_counts.get(key, 0)
            st.markdown(f"""
            <div style="background:var(--card2);border:1px solid {color}33;border-radius:8px;padding:8px;text-align:center;margin-bottom:6px">
              <div style="font-size:18px">{icon}</div>
              <div style="font-size:9px;color:var(--t2);margin-top:2px">{label}</div>
              <div style="font-size:14px;font-weight:700;color:{color}">{cnt}</div>
            </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # session insights (real)
    last_score = 0.0
    if st.session_state.messages:
        last_res = [m["content"] for m in st.session_state.messages if m["role"]=="assistant"]
        if last_res: last_score = last_res[-1].get("final_score", 0.0)
    pct = int(last_score * 10)
    conf_label = "High" if pct >= 75 else ("Medium" if pct >= 50 else "Low")
    conf_color = "#10b981" if pct >= 75 else ("#f59e0b" if pct >= 50 else "#ef4444")
    elapsed = format_elapsed(st.session_state.session_start)
    fig_g = go.Figure(go.Pie(values=[max(pct,1), max(100-pct,1)], hole=0.72,
        marker=dict(colors=[conf_color,"#252545"]), textinfo="none", hoverinfo="skip"))
    fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=5,r=5,t=5,b=5), height=110, showlegend=False)

    st.markdown(f"""<div class="card" style="margin-bottom:10px">
      <div style="font-weight:700;font-size:13px;color:var(--t1);margin-bottom:8px">💡 SESSION INSIGHTS <span style="font-size:10px;color:{conf_color}">🟢 Live</span></div>
      <div style="display:flex;align-items:center;gap:12px">""", unsafe_allow_html=True)
    gi, ii = st.columns([1, 1.5])
    with gi:
        st.plotly_chart(fig_g, width="stretch", config={"displayModeBar": False},
            key="knowledge-distribution-chart")
        st.markdown(f'<div style="text-align:center;margin-top:-70px;font-size:18px;font-weight:700;color:{conf_color}">{pct}%</div><div style="text-align:center;font-size:9px;color:var(--t2);margin-bottom:40px">{conf_label}</div>', unsafe_allow_html=True)
    with ii:
        token_est = st.session_state.get("token_count", 0)
        insights = [
            ("🔢","Total Tokens", f"{token_est:,}" if token_est else "—"),
            ("⏱️","Session Time", elapsed),
            ("⚡","Cache Hit Rate", f"{_redis_stats['hit_rate']}%"),
            ("🗄️","Redis Keys", str(_redis_stats['keys'])),
        ]
        for ico,lbl,val in insights:
            st.markdown(f'<div class="insight-row"><span style="color:var(--t3)">{ico} {lbl}</span><span style="font-weight:600;color:var(--t1)">{val}</span></div>', unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    # recent conversations (real from session)
    st.markdown("""
    <div class="card">
      <div style="font-weight:700;font-size:13px;color:var(--t1);margin-bottom:8px">🕒 RECENT CONVERSATIONS</div>""", unsafe_allow_html=True)
    real_msgs = [(m,a) for m,a in zip(
        [x for x in st.session_state.messages if x["role"]=="user"],
        [x for x in st.session_state.messages if x["role"]=="assistant"]
    )]
    if real_msgs:
        for user_m, asst_m in reversed(real_msgs[-4:]):
            res = asst_m["content"]
            dec = res.get("final_decision","reject")
            iters = res.get("total_iterations",1)
            color = "var(--green)" if dec=="accept" else "var(--amber)"
            status = f"✔ Accepted ({iters} iter)" if dec=="accept" else f"⚠️ {iters}/4 iterations"
            q = user_m["content"][:45] + ("…" if len(user_m["content"])>45 else "")
            st.markdown(f"""
            <div class="conv-row">
              <div style="flex:1;min-width:0">
                <div style="font-size:12px;font-weight:500;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">Ôùë {q}</div>
                <div style="font-size:10px;color:{color};margin-top:1px">{status}</div>
              </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:12px;color:var(--t3);padding:8px 0">No conversations yet. Ask your first question!</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ingest shortcuts
    st.markdown("""<div class="card">
      <div style="font-weight:700;font-size:13px;color:var(--t1);margin-bottom:10px">⬆️ Quick Ingest</div>""", unsafe_allow_html=True)

    up_file = st.file_uploader("Upload File", accept_multiple_files=False,
        type=["pdf","docx","txt","py","js","ppt","pptx","wav","html","css","sql"],
        label_visibility="collapsed")
    if up_file and st.button("Ingest File", width="stretch"):
        from src.ingestion.pipeline import ingest_file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(up_file.name).suffix) as tmp:
            tmp.write(up_file.read()); tmp_path = tmp.name
        try:
            r = ingest_file(tmp_path)
            st.success(f"✅ {up_file.name} → {r['chunks_added']} chunks")
            st.session_state.ingested.append(up_file.name)
        except Exception as e: st.error(str(e))
        finally: os.unlink(tmp_path)

    url_in = st.text_input("Web URL", placeholder="https://...", label_visibility="collapsed")
    if st.button("Ingest URL", width="stretch") and url_in.strip():
        from src.ingestion.pipeline import ingest_url
        try:
            r = ingest_url(url_in.strip())
            st.success(f"✅ URL → {r['chunks_added']} chunks")
            st.session_state.ingested.append(url_in.strip()[:30])
        except Exception as e: st.error(str(e))

    wiki_in = st.text_input("Wikipedia", placeholder="Search topic...", label_visibility="collapsed")
    if st.button("Ingest Wikipedia", width="stretch") and wiki_in.strip():
        from src.ingestion.pipeline import ingest_wikipedia
        try:
            r = ingest_wikipedia(wiki_in.strip())
            st.success(f"✅ Wikipedia → {r['chunks_added']} chunks")
            st.session_state.ingested.append(f"Wiki:{wiki_in.strip()}")
        except Exception as e: st.error(str(e))

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
  --bg:     #080818;
  --bg2:    #0d0d20;
  --bg3:    #111128;
  --card:   #141430;
  --card2:  #1a1a3a;
  --v:      #7c3aed;
  --vl:     #a855f7;
  --blue:   #3b82f6;
  --green:  #10b981;
  --amber:  #f59e0b;
  --red:    #ef4444;
  --cyan:   #06b6d4;
  --pink:   #ec4899;
  --t1:     #eeeeff;
  --t2:     #8888b0;
  --t3:     #50507a;
  --border: #1e1e40;
}

/* ── Base ── */
.stApp { background: var(--bg) !important; font-family: 'Inter', sans-serif; }
html, body, [class*="css"] { background: var(--bg); color: var(--t1); }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
h1,h2,h3,h4,h5,h6 { color: var(--t1) !important; }
hr { border-color: var(--border) !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] > div {
  background: var(--bg2) !important;
  border-right: 1px solid var(--border);
  padding-top: 0 !important;
  display: flex;
  flex-direction: column;
}
section[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  width: 220px !important;
  min-width: 220px !important;
}
/* hide streamlit's own collapse button */
[data-testid="collapsedControl"] { display: none !important; }

/* ── Inputs ── */
.stButton > button {
  background: var(--v) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  transition: background .2s, transform .1s;
}
.stButton > button:hover {
  background: #6d28d9 !important;
  transform: translateY(-1px);
}
.stButton > button:active { transform: translateY(0); }

.stTextInput input {
  background: var(--card2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--t1) !important;
  font-size: 14px !important;
  padding: 10px 14px !important;
}
.stTextInput input:focus { border-color: var(--v) !important; box-shadow: 0 0 0 3px #7c3aed22 !important; }
.stTextInput label { display: none !important; }

.stFileUploader { background: var(--card2) !important; border-radius: 10px !important; border: 1px dashed var(--border) !important; }
.stFileUploader label { color: var(--t2) !important; font-size: 13px !important; }

/* ── Cards ── */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 12px;
}
.card-glow { border-color: #7c3aed44; box-shadow: 0 0 24px #7c3aed14; }

/* ── Pills / Badges ── */
.pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 10px; border-radius: 99px; font-size: 11px; font-weight: 500;
}
.pill-g  { background: #10b98115; color: #10b981; border: 1px solid #10b98130; }
.pill-v  { background: #7c3aed15; color: #a855f7; border: 1px solid #7c3aed30; }
.pill-a  { background: #f59e0b15; color: #f59e0b; border: 1px solid #f59e0b30; }
.pill-r  { background: #ef444415; color: #ef4444; border: 1px solid #ef444430; }
.pill-c  { background: #06b6d415; color: #06b6d4; border: 1px solid #06b6d430; }

/* ── Sidebar nav ── */
.nav-logo {
  padding: 16px 14px 12px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 6px;
  display: flex; align-items: center; gap: 10px;
}
.nav-logo-icon {
  width: 34px; height: 34px; border-radius: 10px;
  background: linear-gradient(135deg,#7c3aed,#a855f7);
  display: flex; align-items: center; justify-content: center; font-size: 17px;
  flex-shrink: 0;
}
.nav-sec {
  font-size: 9px; font-weight: 700; letter-spacing: 1.3px;
  color: var(--t3); text-transform: uppercase;
  padding: 10px 14px 5px;
}
.nav-item {
  display: flex; align-items: center; gap: 9px;
  padding: 7px 12px; border-radius: 8px; cursor: pointer;
  font-size: 12.5px; color: var(--t2); margin: 1px 6px;
  transition: background .15s, color .15s;
}
.nav-item:hover  { background: var(--card); color: var(--t1); }
.nav-active { background: linear-gradient(135deg,#7c3aed,#6d28d9) !important; color: #fff !important; font-weight: 600; }

/* ── Stat cards ── */
.stat-card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 16px;
}
.stat-val  { font-size: 24px; font-weight: 800; color: var(--t1); line-height: 1.1; }
.stat-lbl  { font-size: 10.5px; color: var(--t3); margin-bottom: 4px; text-transform: uppercase; letter-spacing: .5px; }
.stat-bar  { margin-top: 10px; height: 4px; border-radius: 3px; background: var(--border); overflow: hidden; }
.stat-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg,var(--v),var(--vl)); }

/* ── Workflow nodes ── */
.wf-node { display: inline-flex; flex-direction: column; align-items: center; gap: 4px; font-size: 10px; color: var(--t2); }
.wf-circle { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 17px; }

/* ── Chat bubbles ── */
.user-bubble {
  background: linear-gradient(135deg,#3b82f618,#3b82f608);
  border: 1px solid #3b82f630;
  border-radius: 14px 14px 4px 14px;
  padding: 12px 16px; font-size: 14px; color: var(--t1); line-height: 1.6;
}
.ai-bubble {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 4px 14px 14px 14px;
  padding: 14px 16px; font-size: 13.5px; color: var(--t2); line-height: 1.7;
}

/* ── Score chip ── */
.score-chip {
  background: #f59e0b15; color: #f59e0b;
  border: 1px solid #f59e0b40; border-radius: 8px;
  padding: 3px 10px; font-size: 12px; font-weight: 700;
}

/* ── Insight rows ── */
.insight-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 12px;
}
.insight-row:last-child { border-bottom: none; }

/* ── Conversation rows ── */
.conv-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0; border-bottom: 1px solid var(--border);
}
.conv-row:last-child { border-bottom: none; }

/* ── Knowledge source mini cards ── */
.ks-mini {
  background: var(--card2); border-radius: 10px; padding: 10px 6px;
  text-align: center; border: 1px solid var(--border);
  transition: border-color .2s;
}
.ks-mini:hover { border-color: var(--v); }

/* ── Top status bar ── */
.status-bar {
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  padding: 10px 20px;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 8px;
}

/* ── Input area ── */
.input-area {
  background: var(--bg2);
  border-top: 1px solid var(--border);
  padding: 14px 20px;
  position: sticky; bottom: 0; z-index: 10;
}

/* ── Welcome state ── */
.welcome-box {
  text-align: center; padding: 60px 20px;
  color: var(--t3);
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
</style>
"""

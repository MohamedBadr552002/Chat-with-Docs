# EvalGen AI — Evaluator–Generator Platform

An intelligent AI platform built around an **Evaluator–Generator feedback loop**.
Answers are not just generated — they are self-evaluated and iteratively improved.

---

## Architecture

```
User Question
     │
     ▼
┌─────────────┐    retrieves context    ┌──────────────────────┐
│  Generator  │◄───────────────────────│  External Knowledge  │
│  LLM Agent  │                         │  Layer (ChromaDB +   │
│  + Memory   │─────────────────────►  │  BM25 + Redis Cache) │
└─────────────┘   generated answer      └──────────────────────┘
     │
     ▼
┌─────────────┐
│  Evaluator  │  scores: accuracy, relevance, completeness,
│  LLM Agent  │  grounding, no-hallucination, clarity
│  + Memory   │
└──────┬──────┘
       │
  ┌────┴────┐
  │         │
Accept    Reject (feedback)
  │         │
  ▼         └──► Generator (up to 4 iterations)
Final Answer
```

## Supported Knowledge Sources

| Type | Details |
|------|---------|
| PDF | Multi-page documents |
| DOCX | Word documents |
| TXT | Plain text and source code |
| PPT/PPTX | Slide text extraction |
| Source Code | .py .js .ts .java .cpp .go … |
| Web URL | Live web page scraping |
| Wikipedia | Auto-search and load |
| WAV | Speech-to-text via OpenAI Whisper |

## Setup

### 1. Prerequisites
- Python 3.10+
- An OpenRouter API key
- Redis is optional, but recommended for caching
- Docker Desktop is optional if Redis is run in a container

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

On Windows, use a virtual environment if possible:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure environment
```bash
copy .env.example .env
# Set GOOGLE_API_KEY to your OpenRouter API key.
# Despite its historical name, the application sends this key to OpenRouter.
```

### 4. Start Redis (optional)

Run only the Redis container:

```bash
docker run -d --name chat-docs-redis -p 6379:6379 redis:7-alpine
```

The local app connects to `localhost:6379`. To stop and remove the container:

```bash
docker stop chat-docs-redis
docker rm chat-docs-redis
```

> **Note:** Redis is optional. If it is unavailable, the platform continues with caching disabled.

### 5. Run the app
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The first startup may take time while the
Hugging Face embedding model is downloaded and loaded.

### 6. Run the full stack with Docker Compose

This starts both the app and Redis in containers:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Open `http://localhost:8501`. Stop the stack with `Ctrl+C`, or run:

```bash
docker compose -f docker/docker-compose.yml down
```

### 7. Smoke test (no UI)
```bash
python test/smoke_test.py
```

The smoke test requires Redis if caching is desired, internet access for Wikipedia,
and a valid OpenRouter API key. It ingests a Wikipedia page and runs the evaluator-generator
workflow.

## Project Structure

```
chat_with_Doc/
├── app.py                    # Streamlit UI
├── architecture.md           # Architecture notes
├── test/smoke_test.py        # End-to-end smoke test
├── requirements.txt
├── docker/                   # Dockerfile and Compose configuration
├── src/
│   ├── agents/               # Generator and evaluator agents
│   ├── ingestion/            # Load, chunk, embed, and store documents
│   ├── knowledge/            # Retrieval and Redis caching
│   ├── UI/                   # Styles and usage statistics
│   ├── utils/                # Configuration and logging
│   └── workflow/             # Evaluator-generator orchestration
│
├── chroma_db/                # ChromaDB persistence
└── logs/                     # Log files
```

## Key Design Decisions

### Memory Isolation
The Generator and Evaluator each hold a separate `ConversationBufferMemory` instance.
They are **never shared**. The Generator stores conversation context and prior answers;
the Evaluator stores evaluation history and decisions.

### Redis Caching Strategy
| Cache Type | Key Pattern | TTL |
|-----------|------------|-----|
| Retrieval results | `eval_gen:retrieval:<hash>` | 1 hour |
| LLM responses | `eval_gen:llm:<hash>` | 1 hour |
| Evaluation results | `eval_gen:evaluation:<hash>` | 1 hour |
| Ingestion markers | `ingested:<hash>` | 1 hour |

### Evaluator Thresholds
- **Accept** if: `overall_score ≥ 7.5` AND no individual dimension below `6.0`
- Six dimensions: accuracy, relevance, completeness, grounding, no_hallucination, clarity

### LCEL Chain Structure
```python
chain = prompt | llm | StrOutputParser()
# Used inside RunnableLambda steps within the orchestrator loop
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | — | **Required.** OpenRouter API key (legacy variable name) |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_TTL` | `3600` | Cache TTL in seconds |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB storage directory |
| `GENERATOR_MODEL` | `gemini-1.5-flash` | OpenRouter model used by the Generator |
| `EVALUATOR_MODEL` | `gemini-1.5-flash` | OpenRouter model used by the Evaluator |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace embedding model |
| `MAX_ITERATIONS` | `4` | Maximum feedback loop iterations |
| `TOP_K_RETRIEVAL` | `5` | Number of chunks to retrieve |

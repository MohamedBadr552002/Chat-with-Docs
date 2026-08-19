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
- Redis server running on `localhost:6379`
- Google Gemini API key

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
copy .env.example .env
# Edit .env and set GOOGLE_API_KEY=your_key_here
```

### 4. Start Redis (Windows)
Download from https://github.com/microsoftarchive/redis/releases
or use Docker:
```bash
docker run -d -p 6379:6379 redis:latest
```
> **Note:** Redis is optional. The platform degrades gracefully without it (caching is disabled).

### 5. Run the app
```bash
streamlit run app.py
```

### 6. (Optional) CLI ingestion
```bash
python ingest_cli.py --file document.pdf --wiki "Artificial intelligence" --url https://example.com
```

### 7. Smoke test (no UI)
```bash
python smoke_test.py
```

## Project Structure

```
chat_with_Doc/
├── app.py                    # Streamlit UI
├── config.py                 # Central configuration
├── logger_config.py          # Loguru logging setup
├── ingest_cli.py             # CLI ingestion helper
├── smoke_test.py             # End-to-end smoke test
├── requirements.txt
├── .env.example
│
├── ingestion/                # Knowledge ingestion pipeline
│   ├── loaders.py            # File/URL/Wikipedia/WAV loaders
│   ├── chunker.py            # Recursive text splitter
│   ├── embeddings.py         # HuggingFace embedding provider
│   ├── vectorstore.py        # ChromaDB manager
│   └── pipeline.py           # Orchestrates load→chunk→embed→store
│
├── knowledge/                # External knowledge layer
│   ├── retriever.py          # Hybrid dense+BM25 retriever
│   └── cache.py              # Redis caching module
│
├── agents/                   # LLM agents
│   ├── generator.py          # Generator LLM + isolated memory
│   └── evaluator.py          # Evaluator LLM + isolated memory
│
├── workflow/                 # LCEL orchestration
│   └── orchestrator.py       # Feedback loop (max 4 iterations)
│
├── chroma_db/                # ChromaDB persistence (auto-created)
└── logs/                     # Log files (auto-created)
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
| `GOOGLE_API_KEY` | — | **Required.** Gemini API key |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_TTL` | `3600` | Cache TTL in seconds |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB storage directory |
| `GENERATOR_MODEL` | `gemini-1.5-flash` | Generator LLM model |
| `EVALUATOR_MODEL` | `gemini-1.5-flash` | Evaluator LLM model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace embedding model |
| `MAX_ITERATIONS` | `4` | Maximum feedback loop iterations |
| `TOP_K_RETRIEVAL` | `5` | Number of chunks to retrieve |

# Docker deployment

Start the application and Redis from the repository root:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Open <http://localhost:8501>. Set `GOOGLE_API_KEY` in a root `.env` file or pass it on the command line:

```bash
GOOGLE_API_KEY=your_key docker compose -f docker/docker-compose.yml up --build
```

The Compose setup persists ChromaDB in `chroma_db/`, application logs in `logs/`, uploaded files in `uploads/`, and Redis data in the named `redis_data` volume.

Run the optional end-to-end smoke test with the same application image:

```bash
docker compose -f docker/docker-compose.yml --profile test run --rm --build smoke-test
```

The smoke test requires a valid `GOOGLE_API_KEY` and network access to Wikipedia and Gemini.
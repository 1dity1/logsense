# logsense

An AI-powered log analysis tool. Upload your server logs, ask questions in plain English, get answers.

Built this after realizing that most developers drown in log files during incidents. Ctrl+F only gets you so far when you have thousands of lines across multiple services.

## What it does

Upload any log file — server logs, error logs, access logs. Then ask things like:

"What errors occurred between 10am and 11am?"
"Which IP triggered rate limits?"
"Any database connection issues?"
"Show me all OOM events"

The tool chunks the logs, finds the relevant sections, and sends them to an LLM with your question. Answers come back in seconds.

## How it works

Logs get split into chunks and stored in memory. When you ask a question, keyword matching finds the most relevant chunks. Those chunks become the context for a Groq LLaMA 3 call. The answer gets cached in Redis-lite (a Redis-compatible KV store I built from scratch in C++) so repeated questions don't hit the API.

## Stack

- Backend: FastAPI + Python
- LLM: Groq LLaMA 3.1 (llama-3.1-8b-instant)
- Caching: Redis-lite (custom C++ KV store)
- Frontend: React + TypeScript

## Running locally

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install fastapi uvicorn groq python-multipart python-dotenv
echo "GROQ_API_KEY=your_key_here" > .env
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install && npm start
```

Also needs redis-lite running on port 6379 for caching.
github.com/1dity1/redis-lite

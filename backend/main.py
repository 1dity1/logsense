from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from redis_client import RedisLiteClient

load_dotenv()

app = FastAPI(title="LogSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
cache = RedisLiteClient(host="localhost", port=6379)

log_chunks = []
uploaded_files = []

class QueryRequest(BaseModel):
    question: str

def chunk_text(text: str, chunk_size: int = 800) -> list:
    lines = text.split("\n")
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        current.append(line)
        current_len += len(line)
        if current_len >= chunk_size:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
    if current:
        chunks.append("\n".join(current))
    return chunks

def find_relevant_chunks(question: str, chunks: list, top_k: int = 5) -> list:
    question_lower = question.lower()
    keywords = question_lower.split()
    scored = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for kw in keywords if kw in chunk_lower)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(reverse=True)
    return [c for _, c in scored[:top_k]]

@app.get("/")
def root():
    return {"status": "LogSense running"}

@app.post("/upload")
async def upload_log(file: UploadFile = File(...)):
    global log_chunks, uploaded_files
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    content = file_path.read_text(errors="ignore")
    chunks = chunk_text(content)
    log_chunks.extend(chunks)
    uploaded_files.append(file.filename)
    return {
        "filename": file.filename,
        "lines": len(content.split("\n")),
        "chunks": len(chunks),
        "status": "indexed"
    }

@app.post("/query")
async def query_logs(req: QueryRequest):
    global log_chunks

    if not log_chunks:
        raise HTTPException(status_code=400, detail="No logs uploaded yet")

    # Check Redis-lite cache first
    cache_key = cache.hash_key(req.question)
    cached = cache.get(cache_key)
    if cached:
        return {"answer": cached, "cached": True}

    # Cache miss — call Groq
    relevant = find_relevant_chunks(req.question, log_chunks)
    context = "\n\n".join(relevant) if relevant else "\n\n".join(log_chunks[:5])

    prompt = f"""You are a log analysis expert. Analyze the following log excerpts and answer the question clearly and concisely.

Log excerpts:
{context}

Question: {req.question}

Answer:"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=512
    )

    answer = response.choices[0].message.content

    # Store in Redis-lite cache for 1 hour
    cache.setex(cache_key, 3600, answer)

    return {"answer": answer, "cached": False}

@app.get("/stats")
async def stats():
    return {
        "files_uploaded": len(uploaded_files),
        "filenames": uploaded_files,
        "total_chunks": len(log_chunks),
        "ready": len(log_chunks) > 0
    }

@app.delete("/reset")
async def reset():
    global log_chunks, uploaded_files
    log_chunks = []
    uploaded_files = []
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    return {"status": "reset done"}

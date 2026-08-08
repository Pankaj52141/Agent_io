"""
FastAPI Main Application — Routes and middleware for the Financial Data AI Agent.
Serves the frontend, handles authentication, queries, and feedback.
"""
import os
import json
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import USERS, ROLE_RESTRICTIONS, FEEDBACK_DIR, OPENAI_API_KEY
from backend.rbac.models import (
    LoginRequest, LoginResponse, QueryRequest, QueryResponse,
    FeedbackRequest,
)
from backend.rbac.auth import (
    authenticate_user, create_access_token, decode_token, get_current_user,
)
from backend.rbac.enforcer import get_restricted_categories, get_allowed_categories
from backend.agent.orchestrator import AgentOrchestrator


# ─── Global agent instance ──────────────────────────────
agent: AgentOrchestrator | None = None

# Store last query/answer per query_id for feedback
query_history: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the agent on startup."""
    global agent
    print("[Server] Initializing Agent Orchestrator...")
    print(f"[Server] OPENAI_API_KEY loaded: {'Yes' if OPENAI_API_KEY else 'NO — .env not loaded!'}")
    agent = AgentOrchestrator()
    print("[Server] Agent ready!")
    yield
    print("[Server] Shutting down...")


app = FastAPI(
    title="Financial Data AI Agent",
    description="An agentic financial data assistant with RBAC and feedback",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helper: Extract token from Authorization header ─────
def get_token_from_header(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    return authorization.split(" ", 1)[1]


# ─── Auth Routes ─────────────────────────────────────────
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    user = authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token({"email": request.email, "role": user["role"]})
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_name=user["name"],
        user_role=user["role"],
    )


@app.get("/api/auth/me")
async def get_me(token: str = Depends(get_token_from_header)):
    """Get current user info from token."""
    user = get_current_user(token)
    role = user["role"]
    restricted = get_restricted_categories(role)
    allowed = get_allowed_categories(role)
    return {
        "email": [e for e, u in USERS.items() if u["role"] == role][0],
        "name": user["name"],
        "role": role,
        "restricted_categories": list(restricted),
        "allowed_categories": list(allowed),
    }


# ─── Query Route ─────────────────────────────────────────
@app.post("/api/query")
async def handle_query(
    request: QueryRequest,
    token: str = Depends(get_token_from_header),
):
    """Process a natural language query with RBAC enforcement."""
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent not initialized. Please wait...",
        )

    user = get_current_user(token)
    role = user["role"]

    result = agent.query(request.query, role)

    # Store for feedback lookup
    query_history[result["query_id"]] = {
        "query": request.query,
        "answer": result["answer"],
        "role": role,
    }

    # Keep history bounded
    if len(query_history) > 1000:
        oldest = list(query_history.keys())[:500]
        for k in oldest:
            del query_history[k]

    return result


# ─── Feedback Route ──────────────────────────────────────
@app.post("/api/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    token: str = Depends(get_token_from_header),
):
    """Submit feedback on a query response."""
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent not initialized",
        )

    user = get_current_user(token)
    role = user["role"]

    # Look up original query/answer
    history = query_history.get(request.query_id, {})

    agent.submit_feedback(
        query_id=request.query_id,
        query=history.get("query", ""),
        answer=history.get("answer", ""),
        rating=request.rating,
        correction=request.correction,
        preferred_answer=request.preferred_answer,
        role=role,
    )

    return {"status": "ok", "message": "Feedback recorded. Thank you!"}


@app.get("/api/feedback/stats")
async def get_feedback_stats(token: str = Depends(get_token_from_header)):
    """Get feedback statistics."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    get_current_user(token)  # Validate token
    return agent.get_feedback_stats()


# ─── System Info Route ───────────────────────────────────
@app.get("/api/system/roles")
async def get_roles():
    """Get available roles and their permissions (public info for login page)."""
    roles = {}
    for email, user in USERS.items():
        role = user["role"]
        restricted = get_restricted_categories(role)
        roles[role] = {
            "name": user["name"],
            "email": email,
            "restricted_categories": list(restricted),
            "description": _role_description(role),
        }
    return roles


def _role_description(role: str) -> str:
    descs = {
        "ceo": "Full access to all financial data, including compensation and strategic information.",
        "cto": "Access to most data. Restricted from: headcount, compensation, and executive compensation data.",
        "cfo": "Access to financial data. Restricted from: strategy, R&D projects, product roadmap, and legal data.",
    }
    return descs.get(role, "Standard access")


# ─── Serve Frontend ─────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
async def serve_frontend():
    """Serve the main HTML page."""
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Financial Data AI Agent API is running. Frontend not found."}


@app.get("/{filename:path}")
async def serve_static(filename: str):
    """Serve static frontend files."""
    file_path = FRONTEND_DIR / filename
    if file_path.exists() and file_path.is_file():
        # Determine content type
        suffix = file_path.suffix.lower()
        content_types = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        return FileResponse(
            str(file_path),
            media_type=content_types.get(suffix, "application/octet-stream"),
        )
    raise HTTPException(status_code=404, detail="File not found")


# ─── Run ─────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

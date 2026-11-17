import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Path, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.locks import ThreadLocks
from src.api.schemas import SAFE_META, THREAD_ID_PATTERN, AgentInfo, ChatRequest, ChatResponse
from src.core.contracts import AgentResult
from src.workflow.graph import ask
from src.workflow.state import AGENT_NAMES

log = logging.getLogger(__name__)

DEFAULT_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]      # the React dev server
SERVER_ERROR = "Something went wrong on the server. Please try again."


def _default_build():
    from src.workflow.bootstrap import build_runtime        # imported lazily: it loads models and the vector store
    return build_runtime()


def to_response(thread_id: str, result: AgentResult) -> ChatResponse:
    data = jsonable_encoder(result.data) if result.data is not None else None
    return ChatResponse(
        thread_id=thread_id, agent=result.agent, status=result.status, text=result.text,
        citations=[{"source": c.source, "title": c.title, "excerpt": c.excerpt, "verified_at": c.verified_at}
                   for c in result.citations],
        data=data, meta={k: result.meta[k] for k in SAFE_META if k in result.meta}, disclaimer=result.disclaimer,
        login_url=(result.data or {}).get("login_url") if result.status == "needs_login" else None)


def create_app(runtime=None, build=None, cors_origins: list[str] | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.runtime is None:
            app.state.runtime = await asyncio.to_thread(build or _default_build)
        try:
            yield
        finally:
            await app.state.runtime.close()

    app = FastAPI(title="Finnie: AI Finance Assistant", version="0.2.0", lifespan=lifespan)
    app.state.runtime = runtime
    app.state.locks = ThreadLocks()
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins or DEFAULT_ORIGINS,
                       allow_methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["Content-Type"])

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.error("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse({"error": SERVER_ERROR}, status_code=500)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/agents", response_model=list[AgentInfo])
    async def agents(request: Request):
        known = request.app.state.runtime.agents
        return [AgentInfo(name=n, ready=n in known and getattr(known[n], "ready", True)) for n in sorted(AGENT_NAMES)]

    @app.post("/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest, request: Request):
        thread_id = body.thread_id or uuid.uuid4().hex
        async with request.app.state.locks.hold(thread_id):
            result = await ask(request.app.state.runtime.graph, body.message, thread_id=thread_id, agent=body.agent)
        return to_response(thread_id, result)

    @app.delete("/sessions/{thread_id}", status_code=204)
    async def end_session(request: Request, thread_id: str = Path(pattern=THREAD_ID_PATTERN)):
        rt = request.app.state.runtime
        async with request.app.state.locks.hold(thread_id):
            if rt.memory is not None:
                rt.memory.clear(thread_id)
            rt.store.clear_pending(thread_id)
            for name in list(rt.store.opened(thread_id)):
                instance = rt.store.disconnect(thread_id, name)
                close = getattr(instance, "close", None)
                if close:
                    try:
                        await close()
                    except Exception:
                        log.exception("closing a portfolio source failed")
        return Response(status_code=204)

    return app

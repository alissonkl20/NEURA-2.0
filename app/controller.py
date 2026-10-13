import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from service import MistralService

router = APIRouter()
service = MistralService()

SESSIONS: dict[str, list[dict]] = {}


class PromptRequest(BaseModel):
    prompt: str
    session_id: str = "default"
    reset: bool = False


def _get_history(session_id: str, reset: bool) -> list[dict]:
    if reset or session_id not in SESSIONS:
        SESSIONS[session_id] = []
    return SESSIONS[session_id]


@router.get("/")
def root():
    return {"ok": True, "model": service.MODEL}


@router.get("/topicos")
def topicos():
    """Retorna todos os tópicos disponíveis no index.json."""
    return {"topicos": service.router.all_skills()}


@router.post("/ask")
def ask(req: PromptRequest):
    history = _get_history(req.session_id, req.reset)
    prepared = service.prepare(req.prompt)

    messages = [
        prepared["system_message"],
        *history,
        {"role": "user", "content": req.prompt},
    ]

    result = service.ask(messages, max_tokens=prepared["max_tokens"])

    history.append({"role": "user", "content": req.prompt})
    history.append({"role": "assistant", "content": result["response"]})

    result["skills_used"] = prepared["skills_used"]
    return result


@router.post("/ask/stream")
def ask_stream(req: PromptRequest):
    history = _get_history(req.session_id, req.reset)
    prepared = service.prepare(req.prompt)

    messages = [
        prepared["system_message"],
        *history,
        {"role": "user", "content": req.prompt},
    ]

    def event_generator():
        full = ""
        yield "data: " + json.dumps({
            "type": "route",
            "skills_used": prepared["skills_used"],
        }) + "\n\n"

        try:
            for token, done, stats in service.ask_stream(
                messages, max_tokens=prepared["max_tokens"]
            ):
                if done:
                    history.append({"role": "user", "content": req.prompt})
                    history.append({"role": "assistant", "content": full})
                    yield "data: " + json.dumps({
                        "type": "done", "done": True, "stats": stats,
                    }) + "\n\n"
                    return
                full += token
                yield "data: " + json.dumps({
                    "type": "token", "token": token, "done": False,
                }) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({
                "type": "error", "error": str(e),
            }) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/reload-context")
def reload_context():
    info = service.reload_context()
    return {"ok": True, **info}


@router.post("/rebuild-index")
def rebuild_index():
    import subprocess
    r = subprocess.run(
        ["python", "build_index.py"], capture_output=True, text=True
    )
    return {
        "ok": r.returncode == 0,
        "stdout": r.stdout,
        "stderr": r.stderr,
    }


@router.post("/reset")
def reset(req: PromptRequest):
    SESSIONS.pop(req.session_id, None)
    return {"ok": True, "session_id": req.session_id}
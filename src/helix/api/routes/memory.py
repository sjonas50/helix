"""Memory management API routes."""

from fastapi import APIRouter

from helix.api.schemas.memory import DreamRunResponse, MemoryCreate, MemoryQuery, MemoryResponse

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/", response_model=MemoryResponse, status_code=201)
async def create_memory_record(body: MemoryCreate) -> dict:
    """Create a new memory record for the current org."""
    raise NotImplementedError


@router.post("/search", response_model=list[MemoryResponse])
async def search_memory(body: MemoryQuery) -> list:
    """Semantic search over org memory using pgvector similarity."""
    return []


@router.get("/dream-runs", response_model=list[DreamRunResponse])
async def list_dream_runs() -> list:
    """List Dream Cycle runs for the current org."""
    return []


@router.post("/dream-runs/trigger", response_model=DreamRunResponse, status_code=202)
async def trigger_dream_cycle() -> dict:
    """Manually trigger a Dream Cycle for the current org."""
    raise NotImplementedError

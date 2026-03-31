"""Memory management API routes."""

from fastapi import APIRouter, Depends

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user
from helix.api.schemas.memory import DreamRunResponse, MemoryCreate, MemoryQuery, MemoryResponse

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/", response_model=MemoryResponse, status_code=201)
async def create_memory_record(
    body: MemoryCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Create a new memory record for the current org."""
    raise NotImplementedError


@router.post("/search", response_model=list[MemoryResponse])
async def search_memory(
    body: MemoryQuery,
    user: CurrentUser = Depends(get_current_user),
) -> list:
    """Semantic search over org memory using pgvector similarity."""
    return []


@router.get("/dream-runs", response_model=list[DreamRunResponse])
async def list_dream_runs(
    user: CurrentUser = Depends(get_current_user),
) -> list:
    """List Dream Cycle runs for the current org."""
    return []


@router.post("/dream-runs/trigger", response_model=DreamRunResponse, status_code=202)
async def trigger_dream_cycle(
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Manually trigger a Dream Cycle for the current org."""
    raise NotImplementedError

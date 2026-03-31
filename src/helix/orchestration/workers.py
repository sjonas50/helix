"""Worker agent factory using LangGraph react agents."""


import structlog
from langchain_core.tools import tool

logger = structlog.get_logger()


@tool
def search_data(query: str) -> str:
    """Search enterprise data sources."""
    return f"Search results for: {query}"


@tool
def read_record(record_type: str, record_id: str) -> str:
    """Read a record from an integrated system."""
    return f"Record {record_type}/{record_id}: [data]"


@tool
def write_record(record_type: str, record_id: str, data: str) -> str:
    """Write/update a record in an integrated system. Requires approval for HIGH+ risk."""
    return f"Updated {record_type}/{record_id}"


@tool
def send_notification(channel: str, message: str) -> str:
    """Send a notification via Slack, email, etc."""
    return f"Notification sent to {channel}"


TOOLS_BY_ROLE: dict[str, list] = {
    "researcher": [search_data, read_record],
    "implementer": [search_data, read_record, write_record, send_notification],
    "verifier": [search_data, read_record],
    "coordinator": [search_data, read_record, write_record, send_notification],
}


def get_tools_for_role(role: str) -> list:
    """Get tools available for a given agent role."""
    return TOOLS_BY_ROLE.get(role, [search_data, read_record])


def validate_hierarchy_depth(current_depth: int, max_depth: int = 2) -> bool:
    """Check if spawning would exceed hierarchy limit."""
    return current_depth < max_depth

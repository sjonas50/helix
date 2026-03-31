"""PydanticAI structured output wrapper for type-safe LLM extraction.

Uses PydanticAI to call an LLM and validate the response against
a Pydantic model, ensuring structured, typed outputs.
"""

from typing import TypeVar

import structlog
from pydantic import BaseModel
from pydantic_ai import Agent as PydanticAgent

logger = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


async def structured_call(
    prompt: str,
    output_type: type[T],
    model: str = "claude-sonnet-4-6",
) -> T:
    """Call LLM and get structured output validated by Pydantic.

    Uses PydanticAI for type-safe extraction.

    Args:
        prompt: The user prompt to send to the LLM.
        output_type: Pydantic model class to validate the response against.
        model: Model identifier (without provider prefix).

    Returns:
        An instance of output_type populated from the LLM response.
    """
    agent: PydanticAgent[None, T] = PydanticAgent(
        model=f"anthropic:{model}",
        output_type=output_type,
    )
    result = await agent.run(prompt)

    logger.info(
        "structured.call_complete",
        model=model,
        output_type=output_type.__name__,
    )

    return result.output

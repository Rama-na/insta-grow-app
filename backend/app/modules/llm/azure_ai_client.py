"""
Azure AI Projects client — singleton wrapper.

Uses AzureKeyCredential for API-key auth (no managed identity required).
Falls back gracefully when credentials are absent (dev/test without Azure).
"""
from __future__ import annotations
from functools import lru_cache
from typing import Optional

from app.core.config import settings
from app.core.logging_setup import logger

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.projects import AIProjectClient
    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False
    logger.warning("azure-ai-projects not installed. LLM features will be disabled.")


@lru_cache(maxsize=1)
def get_azure_project_client() -> Optional["AIProjectClient"]:
    """
    Return a cached AIProjectClient instance.
    Returns None if Azure credentials are not configured or SDK is missing.
    """
    if not HAS_AZURE:
        return None

    if not settings.llm_enabled:
        logger.info("Azure AI credentials not set — LLM features disabled.")
        return None

    try:
        client = AIProjectClient(
            endpoint=settings.azure_ai_endpoint,
            credential=AzureKeyCredential(settings.azure_ai_api_key),
        )
        logger.info(
            f"Azure AI Projects client initialised. "
            f"Agent: {settings.azure_ai_agent_name}:{settings.azure_ai_agent_version}"
        )
        return client
    except Exception as exc:
        logger.error(f"Failed to initialise Azure AI client: {exc}")
        return None


def call_agent(prompt: str, max_tokens: int = 400) -> Optional[str]:
    """
    Send *prompt* to the configured Azure AI Agent and return the response text.

    Returns None on any error so callers can fall back to rule-based output.
    """
    client = get_azure_project_client()
    if client is None:
        return None

    try:
        openai_client = client.get_openai_client()
        response = openai_client.responses.create(
            input=[{"role": "user", "content": prompt}],
            max_output_tokens=max_tokens,
            extra_body={
                "agent_reference": {
                    "name": settings.azure_ai_agent_name,
                    "version": settings.azure_ai_agent_version,
                    "type": "agent_reference",
                }
            },
        )
        text = response.output_text
        logger.debug(f"LLM response ({len(text)} chars): {text[:120]}…")
        return text
    except Exception as exc:
        logger.warning(f"LLM call failed: {exc}. Falling back to rule-based output.")
        return None

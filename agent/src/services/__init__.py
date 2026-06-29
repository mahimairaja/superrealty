"""Agent-side services. The agent makes no direct third-party calls; it goes through
the backend via the BackendApiClient."""

from src.services.api_client import BackendApiClient

__all__ = ["BackendApiClient"]

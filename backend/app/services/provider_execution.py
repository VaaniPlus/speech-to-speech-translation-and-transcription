"""Execution helpers for synchronous model providers."""

import asyncio
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class ProviderCallTimeout(Exception):
    """Raised when a synchronous provider call exceeds its configured deadline."""


async def run_provider_call(
    provider_call: Callable[[], T],
    timeout_seconds: float,
) -> T:
    """Run a blocking provider call off-loop and stop waiting at its deadline."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(provider_call),
            timeout=timeout_seconds,
        )
    except TimeoutError as error:
        raise ProviderCallTimeout from error

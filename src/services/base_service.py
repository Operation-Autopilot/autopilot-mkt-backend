"""Base service class providing shared utilities for all service classes."""

import asyncio
from typing import Any


class BaseService:
    """Base class for all service classes.

    Provides common utilities such as async-safe Supabase query execution
    to avoid code duplication across service implementations.
    """

    async def _execute_sync(self, query: Any) -> Any:
        """Run synchronous Supabase query in thread pool to avoid blocking event loop.

        All Supabase Python client methods are synchronous (blocking I/O).
        Wrapping them with asyncio.to_thread() offloads the blocking call to a
        worker thread, keeping the event loop free for other requests.

        Args:
            query: A Supabase query object with an .execute() method.

        Returns:
            The result of query.execute().
        """
        return await asyncio.to_thread(query.execute)

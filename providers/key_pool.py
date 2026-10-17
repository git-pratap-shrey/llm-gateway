"""Thread-safe round-robin API key pool for provider clients."""

import logging
import threading
from typing import List


class KeyPool:
    """Thread-safe pool of API keys with round-robin selection.

    Distributes API keys evenly across requests to avoid exhausting
    rate limits on a single key.
    """

    def __init__(self, keys: List[str]) -> None:
        """Initialize the key pool.

        Args:
            keys: List of API keys. Must not be empty.

        Raises:
            ValueError: If keys list is empty.
        """
        if not keys:
            logging.error("KeyPool: Initialization failed - keys list is empty.")
            raise ValueError("KeyPool requires at least one key")

        # Strip whitespace from keys
        self._keys = [key.strip() for key in keys if key.strip()]

        if not self._keys:
            logging.error("KeyPool: Initialization failed - no non-empty keys provided.")
            raise ValueError("KeyPool requires at least one non-empty key")

        self._index = 0
        self._lock = threading.Lock()
        logging.info(f"KeyPool: Initialized pool with {len(self._keys)} key(s).")

    def get_next(self) -> str:
        """Get the next key in round-robin order.

        Thread-safe. Each call advances to the next key in the pool.

        Returns:
            The next API key.
        """
        with self._lock:
            current_index = self._index
            key = self._keys[self._index]
            self._index = (self._index + 1) % len(self._keys)
            masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
            logging.debug(
                f"KeyPool: Selected key at index {current_index}/{len(self._keys)} ({masked}). Next index: {self._index}."
            )
            return key

    def __len__(self) -> int:
        """Return the number of keys in the pool."""
        return len(self._keys)

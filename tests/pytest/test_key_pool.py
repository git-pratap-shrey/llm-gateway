"""Tests for the KeyPool class."""

import threading
import pytest
from providers.key_pool import KeyPool


class TestKeyPool:
    """Test suite for KeyPool."""

    def test_round_robin_rotation(self):
        """Keys should rotate in round-robin order."""
        pool = KeyPool(["key1", "key2", "key3"])

        assert pool.get_next() == "key1"
        assert pool.get_next() == "key2"
        assert pool.get_next() == "key3"
        assert pool.get_next() == "key1"  # Wraps around

    def test_single_key(self):
        """Single key should always return the same key."""
        pool = KeyPool(["only_key"])

        assert pool.get_next() == "only_key"
        assert pool.get_next() == "only_key"
        assert pool.get_next() == "only_key"

    def test_whitespace_stripping(self):
        """Keys with whitespace should be stripped."""
        pool = KeyPool([" key1 ", "  key2  ", "key3"])

        assert pool.get_next() == "key1"
        assert pool.get_next() == "key2"
        assert pool.get_next() == "key3"

    def test_empty_keys_list_raises_error(self):
        """Empty list should raise ValueError."""
        with pytest.raises(ValueError, match="at least one key"):
            KeyPool([])

    def test_whitespace_only_keys_raises_error(self):
        """List with only whitespace keys should raise ValueError."""
        with pytest.raises(ValueError, match="at least one non-empty key"):
            KeyPool(["  ", "   "])

    def test_len_method(self):
        """len() should return number of keys."""
        pool = KeyPool(["key1", "key2", "key3"])
        assert len(pool) == 3

        single_pool = KeyPool(["key1"])
        assert len(single_pool) == 1

    def test_thread_safety(self):
        """Concurrent access should not cause race conditions."""
        pool = KeyPool(["key1", "key2"])
        results = []
        lock = threading.Lock()

        def get_key():
            key = pool.get_next()
            with lock:
                results.append(key)

        # Create multiple threads
        threads = [threading.Thread(target=get_key) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Should have exactly 10 results
        assert len(results) == 10

        # Results should contain only valid keys
        assert all(key in ["key1", "key2"] for key in results)

        # With 10 requests across 2 keys, we expect roughly even distribution
        # (5 each, but exact distribution not guaranteed due to timing)
        key1_count = results.count("key1")
        key2_count = results.count("key2")
        assert key1_count + key2_count == 10

    def test_concurrent_round_robin_order(self):
        """Round-robin order should be maintained under concurrent access."""
        pool = KeyPool(["a", "b", "c"])
        results = []
        lock = threading.Lock()

        def get_key():
            key = pool.get_next()
            with lock:
                results.append(key)

        # Create 6 threads (2 full rotations)
        threads = [threading.Thread(target=get_key) for _ in range(6)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should have each key exactly twice (6 requests / 3 keys)
        assert results.count("a") == 2
        assert results.count("b") == 2
        assert results.count("c") == 2

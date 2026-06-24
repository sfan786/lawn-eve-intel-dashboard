"""
Tests for esi_client.py — in-memory caching, eviction, and error handling.

Patches `requests.get` / `requests.post` via pytest-mock so no real network
calls are made. Clears the module-level `_cache` dict before each test to
avoid state leakage between tests.
"""

import time
import threading
import unittest.mock as mock

import pytest
import requests

import esi_client


# ---------------------------------------------------------------------------
# Fixture: clear cache before each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    with esi_client._cache_lock:
        esi_client._cache.clear()
    yield
    with esi_client._cache_lock:
        esi_client._cache.clear()


def _mock_response(data, status=200):
    """Build a minimal requests.Response mock."""
    resp = mock.MagicMock()
    resp.status_code = status
    resp.json.return_value = data
    resp.raise_for_status = mock.MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=resp
        )
    return resp


# ---------------------------------------------------------------------------
# Cache hit / miss
# ---------------------------------------------------------------------------

class TestCacheHit:
    def test_second_call_does_not_fetch(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_response({"name": "Sys", "system_id": 1}))
        esi_client.get_system_info(1)
        esi_client.get_system_info(1)
        assert mock_get.call_count == 1

    def test_cache_hit_returns_same_data(self, mocker):
        data = {"name": "TestSystem", "system_id": 42}
        mocker.patch("requests.get", return_value=_mock_response(data))
        result1 = esi_client.get_system_info(42)
        result2 = esi_client.get_system_info(42)
        assert result1 == result2 == data

    def test_different_system_ids_each_fetch(self, mocker):
        mock_get = mocker.patch(
            "requests.get",
            side_effect=[
                _mock_response({"system_id": 1}),
                _mock_response({"system_id": 2}),
            ],
        )
        esi_client.get_system_info(1)
        esi_client.get_system_info(2)
        assert mock_get.call_count == 2


class TestCacheMissAfterTTL:
    def test_expired_entry_triggers_refetch(self, mocker):
        data = {"name": "Sys", "system_id": 1}
        mock_get = mocker.patch("requests.get", return_value=_mock_response(data))

        esi_client.get_system_info(1)
        assert mock_get.call_count == 1

        # Manually expire the cache entry
        with esi_client._cache_lock:
            esi_client._cache["system_1"]["expires_at"] = time.time() - 1

        esi_client.get_system_info(1)
        assert mock_get.call_count == 2


# ---------------------------------------------------------------------------
# Cache eviction
# ---------------------------------------------------------------------------

class TestCacheEviction:
    def test_eviction_at_capacity(self):
        """Inserting MAX_CACHE_SIZE+1 items prunes the cache below capacity."""
        max_size = esi_client.MAX_CACHE_SIZE  # 1000
        for i in range(max_size + 1):
            esi_client._set_cache(f"key_{i}", {"data": i}, "sovereignty")

        with esi_client._cache_lock:
            size = len(esi_client._cache)

        # After inserting 1001 items: 1000 - 200 pruned + 1 new = 801
        assert size <= max_size
        assert size >= max_size * 0.75  # at least 75% of capacity remains

    def test_eviction_keeps_newest_entries(self):
        """After eviction the most-recently-added entries should survive."""
        max_size = esi_client.MAX_CACHE_SIZE
        # Fill to capacity
        for i in range(max_size):
            esi_client._set_cache(f"key_{i}", i, "sovereignty")

        # Add one more to trigger eviction — use a far-future TTL so it survives
        esi_client._set_cache("key_new", "new", "system_info")  # 24h TTL

        with esi_client._cache_lock:
            assert "key_new" in esi_client._cache


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:
    def test_concurrent_reads_no_exception(self, mocker):
        """20 threads concurrently calling get_system_info() must not raise."""
        mocker.patch("requests.get", return_value=_mock_response({"system_id": 1}))
        errors = []

        def call():
            try:
                esi_client.get_system_info(1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=call) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Exceptions in threads: {errors}"

    def test_concurrent_cache_writes_no_corruption(self):
        """20 threads writing different keys must not corrupt the cache."""
        errors = []

        def write(i):
            try:
                esi_client._set_cache(f"concurrent_{i}", i, "sovereignty")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # All 20 entries should be present (cache starts empty)
        with esi_client._cache_lock:
            for i in range(20):
                assert f"concurrent_{i}" in esi_client._cache


# ---------------------------------------------------------------------------
# bulk_resolve_names chunking
# ---------------------------------------------------------------------------

class TestBulkResolveNames:
    def test_2500_ids_makes_3_post_calls(self, mocker):
        """2500 uncached IDs should be chunked into 3 POST /universe/names/ calls."""
        mock_post = mocker.patch(
            "requests.post",
            return_value=_mock_response([]),  # empty list is fine for chunking test
        )
        ids = list(range(1, 2501))
        esi_client.bulk_resolve_names(ids)
        assert mock_post.call_count == 3

    def test_1000_ids_makes_1_post_call(self, mocker):
        mock_post = mocker.patch("requests.post", return_value=_mock_response([]))
        esi_client.bulk_resolve_names(list(range(1, 1001)))
        assert mock_post.call_count == 1

    def test_1001_ids_makes_2_post_calls(self, mocker):
        mock_post = mocker.patch("requests.post", return_value=_mock_response([]))
        esi_client.bulk_resolve_names(list(range(1, 1002)))
        assert mock_post.call_count == 2

    def test_already_cached_ids_filtered_out(self, mocker):
        """IDs already in cache should not be sent to ESI."""
        # Pre-populate cache with ID 1
        esi_client._set_cache("character_1", "Pilot One", "entity_info")

        mock_post = mocker.patch("requests.post", return_value=_mock_response([]))
        esi_client.bulk_resolve_names([1, 2, 3])
        # Only IDs 2 and 3 are uncached → 1 POST call
        assert mock_post.call_count == 1
        # Verify that the body sent does NOT contain ID 1
        sent_ids = mock_post.call_args[1]["json"]
        assert 1 not in sent_ids

    def test_empty_list_makes_no_calls(self, mocker):
        mock_post = mocker.patch("requests.post", return_value=_mock_response([]))
        esi_client.bulk_resolve_names([])
        assert mock_post.call_count == 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_esi_get_raises_on_http_error(self, mocker):
        mocker.patch("requests.get", return_value=_mock_response({}, status=503))
        with pytest.raises(requests.exceptions.HTTPError):
            esi_client.esi_get("/universe/systems/1/")

    def test_esi_get_raises_on_timeout(self, mocker):
        mocker.patch("requests.get", side_effect=requests.exceptions.Timeout())
        with pytest.raises(requests.exceptions.Timeout):
            esi_client.esi_get("/universe/systems/1/")

    def test_get_type_name_returns_fallback_on_error(self, mocker):
        mocker.patch("requests.get", side_effect=Exception("network error"))
        result = esi_client.get_type_name(99999)
        assert result == "Type 99999"

    def test_get_character_name_returns_fallback_on_error(self, mocker):
        mocker.patch("requests.get", side_effect=Exception("network error"))
        result = esi_client.get_character_name(12345)
        assert result == "Pilot 12345"

    def test_get_zkill_system_returns_empty_list_on_error(self, mocker):
        mocker.patch("requests.get", side_effect=Exception("timeout"))
        result = esi_client.get_zkill_system(30000142)
        assert result == []

    def test_bulk_resolve_names_silently_handles_error(self, mocker):
        mocker.patch("requests.post", side_effect=Exception("network down"))
        # Should not raise — just logs and returns
        esi_client.bulk_resolve_names([1, 2, 3])

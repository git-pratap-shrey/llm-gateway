"""Tests for result_store.result_store.Result_store.

Uses an in-memory SQLite database via the RESULT_DB_PATH env-var so no disk
artefact is produced and tests remain isolated from each other.
"""
import os
import pytest

# Point at an in-memory SQLite so tests never touch the real DB file
os.environ["RESULT_DB_PATH"] = ":memory:"

from result_store.result_store import Result_store


@pytest.fixture()
def store():
    """Fresh Result_store backed by an in-memory SQLite database."""
    return Result_store()


# ---------------------------------------------------------------------------
# create_job
# ---------------------------------------------------------------------------

def test_create_job_stores_record(store):
    job_id = "job-create-001"
    input_data = {"provider": "gemini", "model": "gemma-4-31b-it", "messages": []}

    store.create_job(job_id, input_data)
    result = store.check_status(job_id)

    assert result is not None
    assert result["job_id"] == job_id
    assert result["status"] == "queued"
    assert result["response"] is None


def test_create_job_serialises_input(store):
    job_id = "job-create-002"
    input_data = {"provider": "openrouter", "model": "meta-llama/llama-3"}

    store.create_job(job_id, input_data)
    result = store.check_status(job_id)

    # data is stored as str(input_data)
    assert "openrouter" in result["data"]


# ---------------------------------------------------------------------------
# update_job
# ---------------------------------------------------------------------------

def test_update_job_changes_status(store):
    job_id = "job-update-001"
    store.create_job(job_id, {})

    store.update_job(job_id, status="processing", output=None)
    result = store.check_status(job_id)

    assert result["status"] == "processing"


def test_update_job_stores_output(store):
    job_id = "job-update-002"
    store.create_job(job_id, {})

    store.update_job(job_id, status="completed", output="The answer is 42.")
    result = store.check_status(job_id)

    assert result["status"] == "completed"
    assert "42" in result["response"]


def test_update_job_marks_failed(store):
    job_id = "job-update-003"
    store.create_job(job_id, {})

    store.update_job(job_id, status="failed", output=None)
    result = store.check_status(job_id)

    assert result["status"] == "failed"


def test_update_job_nonexistent_is_silent(store):
    """Updating a job that does not exist must not raise."""
    store.update_job("no-such-job", status="completed", output="x")  # should not raise


# ---------------------------------------------------------------------------
# check_status
# ---------------------------------------------------------------------------

def test_check_status_returns_none_for_missing(store):
    result = store.check_status("does-not-exist")
    assert result is None


def test_check_status_returns_dict(store):
    job_id = "job-check-001"
    store.create_job(job_id, {"provider": "gemini"})

    result = store.check_status(job_id)

    assert isinstance(result, dict)
    assert "job_id" in result
    assert "status" in result
    assert "response" in result
    assert "data" in result


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------

def test_full_job_lifecycle(store):
    job_id = "job-lifecycle-001"
    input_data = {"provider": "ollama_cloud", "model": "gemma4:cloud"}

    # 1. Create
    store.create_job(job_id, input_data)
    r = store.check_status(job_id)
    assert r["status"] == "queued"

    # 2. Processing
    store.update_job(job_id, status="processing", output=None)
    r = store.check_status(job_id)
    assert r["status"] == "processing"

    # 3. Completed
    store.update_job(job_id, status="completed", output="done")
    r = store.check_status(job_id)
    assert r["status"] == "completed"
    assert "done" in r["response"]


def test_multiple_independent_jobs(store):
    for i in range(5):
        store.create_job(f"multi-job-{i}", {"idx": i})

    for i in range(5):
        r = store.check_status(f"multi-job-{i}")
        assert r is not None
        assert r["status"] == "queued"

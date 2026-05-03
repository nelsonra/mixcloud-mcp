import pytest
from mixcloud_mcp import upload_log


@pytest.fixture(autouse=True)
def clear_log():
    upload_log._log.clear()
    yield
    upload_log._log.clear()


def test_record_stores_entry():
    upload_log.record({"name": "Test Mix", "status": "success"})
    assert len(upload_log._log) == 1
    assert upload_log._log[0]["name"] == "Test Mix"


def test_record_adds_uploaded_at_timestamp():
    upload_log.record({"name": "Test Mix"})
    assert "uploaded_at" in upload_log._log[0]


def test_recent_returns_n_entries():
    for i in range(10):
        upload_log.record({"name": f"mix {i}"})
    assert len(upload_log.recent(3)) == 3


def test_recent_default_is_five():
    for i in range(10):
        upload_log.record({"name": f"mix {i}"})
    assert len(upload_log.recent()) == 5


def test_recent_most_recent_first():
    upload_log.record({"name": "first"})
    upload_log.record({"name": "second"})
    results = upload_log.recent(2)
    assert results[0]["name"] == "second"
    assert results[1]["name"] == "first"


def test_log_is_capped_at_twenty():
    for i in range(25):
        upload_log.record({"name": f"mix {i}"})
    assert len(upload_log._log) == 20


def test_recent_clamps_to_available_entries():
    upload_log.record({"name": "only one"})
    assert len(upload_log.recent(10)) == 1

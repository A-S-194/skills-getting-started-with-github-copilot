import sys
import os
import pathlib
from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

# Ensure src/ is importable so we can import the app module
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import app as app_module


client = TestClient(app_module.app)


# Keep a snapshot of the original in-memory activities so tests are isolated
INITIAL_ACTIVITIES = deepcopy(app_module.activities)


@pytest.fixture(autouse=True)
def restore_activities():
    # Restore the in-memory activities before each test
    app_module.activities.clear()
    app_module.activities.update(deepcopy(INITIAL_ACTIVITIES))
    yield


def test_root_redirect():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (307, 308)
    assert response.headers.get("location") == "/static/index.html"


def test_get_activities():
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    # Basic sanity check for a known activity
    assert "Chess Club" in data
    assert "participants" in data["Chess Club"]


def test_signup_success():
    activity = "Chess Club"
    email = "new_student@example.com"

    path = f"/activities/{quote(activity)}/signup"
    resp = client.post(path, params={"email": email})
    assert resp.status_code == 200
    payload = resp.json()
    assert "Signed up" in payload.get("message", "")

    # Ensure participant was actually added in the in-memory store
    assert email in app_module.activities[activity]["participants"]


def test_signup_duplicate_shows_error():
    activity = "Chess Club"
    email = "duplicate_student@example.com"

    path = f"/activities/{quote(activity)}/signup"
    # First signup should succeed
    r1 = client.post(path, params={"email": email})
    assert r1.status_code == 200

    # Second signup should return 400
    r2 = client.post(path, params={"email": email})
    assert r2.status_code == 400
    assert r2.json().get("detail") == "Student already signed up for this activity"


def test_signup_nonexistent_activity_returns_404():
    activity = "No Such Activity"
    email = "someone@example.com"
    path = f"/activities/{quote(activity)}/signup"
    r = client.post(path, params={"email": email})
    assert r.status_code == 404
    assert r.json().get("detail") == "Activity not found"

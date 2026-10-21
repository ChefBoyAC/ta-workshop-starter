from pathlib import Path

import pytest

from app import app, tasks


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client():
    """Provide a Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def reset_tasks():
    """Reset the in-memory task data before each test."""
    tasks.clear()
    tasks.extend([
        {"id": 1, "title": "Project-1 Report"},
        {"id": 2, "title": "Project-2 MMFs"}
    ])


def test_index(client):
    """Render the task page with all priority choices."""
    response = client.get('/')

    assert response.status_code == 200
    assert b"Task Tracker" in response.data
    assert b'id="task-priority"' in response.data
    assert b'<option value="Low">Low</option>' in response.data
    assert b'<option value="Medium" selected>Medium</option>' in response.data
    assert b'<option value="High">High</option>' in response.data


def test_get_tasks_defaults_missing_priority_to_medium(client):
    """Return and persist Medium for legacy tasks without priority."""
    response = client.get('/api/tasks')

    assert response.status_code == 200
    assert [task['priority'] for task in response.get_json()] == [
        "Medium",
        "Medium"
    ]
    assert all(task['priority'] == "Medium" for task in tasks)


def test_add_task_success(client):
    """Create a task with the default Medium priority."""
    response = client.post('/api/tasks', json={"title": "Test new task"})

    assert response.status_code == 201
    assert response.get_json()['title'] == "Test new task"
    assert response.get_json()['priority'] == "Medium"

    get_response = client.get('/api/tasks')
    assert len(get_response.get_json()) == 3
    assert get_response.get_json()[-1]['priority'] == "Medium"


def test_add_task_with_selected_priority(client):
    """Store and return the priority selected by the user."""
    response = client.post(
        '/api/tasks',
        json={"title": "Urgent task", "priority": "High"}
    )

    assert response.status_code == 201
    assert response.get_json()['priority'] == "High"

    stored_task = client.get('/api/tasks').get_json()[-1]
    assert stored_task['title'] == "Urgent task"
    assert stored_task['priority'] == "High"


def test_add_task_rejects_invalid_priority(client):
    """Reject priorities outside the supported values."""
    response = client.post(
        '/api/tasks',
        json={"title": "Invalid task", "priority": "Critical"}
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_add_task_missing_title(client):
    """Reject task requests without a title."""
    response = client.post('/api/tasks', json={"wrong_key": "value"})
    assert response.status_code == 400
    assert "error" in response.get_json()

    response2 = client.post('/api/tasks', json={})
    assert response2.status_code == 400


def test_delete_task(client):
    """Delete an existing task."""
    response = client.delete('/api/tasks/1')

    assert response.status_code == 200
    get_response = client.get('/api/tasks')
    data = get_response.get_json()
    assert len(data) == 1
    assert data[0]['id'] == 2


def test_frontend_submits_and_renders_priority(client):
    """Verify frontend code submits and displays task priority."""
    javascript = (PROJECT_ROOT / 'static' / 'app.js').read_text()

    assert "document.getElementById('task-priority')" in javascript
    assert "JSON.stringify({ title, priority })" in javascript
    assert "Priority: ${displayPriority}" in javascript
    assert "priority-${displayPriority.toLowerCase()}" in javascript


def test_priority_styles_are_defined():
    """Verify distinct styles exist for every supported priority."""
    stylesheet = (PROJECT_ROOT / 'static' / 'style.css').read_text()

    assert '.priority-low' in stylesheet
    assert '.priority-medium' in stylesheet
    assert '.priority-high' in stylesheet

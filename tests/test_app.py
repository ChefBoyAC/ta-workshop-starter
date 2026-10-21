import pytest

from app import app, tasks


@pytest.fixture
def client():
    """Provide a Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def reset_tasks():
    """Reset the in-memory task list before each test."""
    tasks.clear()
    tasks.extend([
        {"id": 1, "title": "Project-1 Report"},
        {"id": 2, "title": "Project-2 MMFs"}
    ])


def test_index(client):
    """Render the task tracker page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Task Tracker" in response.data


def test_get_tasks(client):
    """Return existing tasks with a default priority."""
    response = client.get('/api/tasks')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert all(task['priority'] == 'Medium' for task in data)


@pytest.mark.parametrize('priority', ['Low', 'Medium', 'High'])
def test_add_task_supported_priorities(client, priority):
    """Create and persist a task for each supported priority."""
    response = client.post(
        '/api/tasks',
        json={"title": f"{priority} task", "priority": priority}
    )

    assert response.status_code == 201
    created_task = response.get_json()
    assert created_task['priority'] == priority

    get_response = client.get('/api/tasks')
    saved_task = get_response.get_json()[-1]
    assert saved_task['priority'] == priority


def test_add_task_without_priority_defaults_to_medium(client):
    """Default an omitted priority to Medium."""
    response = client.post('/api/tasks', json={"title": "Default task"})

    assert response.status_code == 201
    assert response.get_json()['priority'] == 'Medium'
    assert client.get('/api/tasks').get_json()[-1]['priority'] == 'Medium'


def test_add_task_with_empty_priority_defaults_to_medium(client):
    """Default an empty priority to Medium."""
    response = client.post(
        '/api/tasks',
        json={"title": "Empty priority task", "priority": ""}
    )

    assert response.status_code == 201
    assert response.get_json()['priority'] == 'Medium'
    assert client.get('/api/tasks').get_json()[-1]['priority'] == 'Medium'


@pytest.mark.parametrize('priority', ['Urgent', 'low', 1, None])
def test_add_task_rejects_invalid_priority(client, priority):
    """Reject priority values outside the supported choices."""
    response = client.post(
        '/api/tasks',
        json={"title": "Invalid priority task", "priority": priority}
    )

    if priority is None:
        assert response.status_code == 201
        assert response.get_json()['priority'] == 'Medium'
    else:
        assert response.status_code == 400
        assert "error" in response.get_json()


def test_add_task_missing_title(client):
    """Reject requests without a title."""
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

from tests.conftest import login


def test_admin_timetable_check_returns_structured_conflict_types(client):
    admin_headers = login(client, "admin", "Admin@123")
    response = client.post(
        "/api/timetable/check",
        headers=admin_headers,
        json=[
            {
                "sectionCode": "SEC-A",
                "dayOfWeek": 2,
                "startPeriod": 1,
                "endPeriod": 3,
                "startWeek": 1,
                "endWeek": 10,
                "roomId": 4,
                "lecturerId": 8,
            },
            {
                "sectionCode": "SEC-B",
                "dayOfWeek": 2,
                "startPeriod": 3,
                "endPeriod": 5,
                "startWeek": 5,
                "endWeek": 15,
                "roomId": 4,
                "lecturerId": 9,
            },
        ],
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "type": "ROOM",
            "sectionA": "SEC-A",
            "sectionB": "SEC-B",
            "dayOfWeek": 2,
            "periods": {"start": 3, "end": 3},
            "weeks": {"start": 5, "end": 10},
        }
    ]


def test_admin_timetable_check_rejects_invalid_slot_range(client):
    admin_headers = login(client, "admin", "Admin@123")
    response = client.post(
        "/api/timetable/check",
        headers=admin_headers,
        json=[
            {
                "sectionCode": "SEC-A",
                "dayOfWeek": 2,
                "startPeriod": 5,
                "endPeriod": 3,
            }
        ],
    )
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"

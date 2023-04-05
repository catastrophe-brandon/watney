import datetime

import requests


def report_data():
    return {
        "report": [
            {
                "repo_name": "string",
                "repo_url": "string",
                "broken_links": [{"file": "string", "url": "string", "status_code": 0}],
            }
        ],
        "report_date": datetime.datetime.utcnow().isoformat(),
    }


def test_report():
    """
    Basic request, post a report then get the data
    :return:
    """
    headers = {"Content-type": "application/json"}
    response = requests.post(
        "http://localhost:8000/report", headers=headers, json=report_data
    )
    assert response.status_code in [200, 201]
    report_id = response.json()["report_id"]

    # Posting the same data twice should fail
    response = requests.post(
        "http://localhost:8000/report", headers=headers, json=report_data
    )
    assert response.status_code == 409

    assert report_id is not None
    response = requests.get(f"http://localhost:8000/report/{report_id}")
    assert response.status_code == 200
    assert response.json()["report_date"] == report_data["report_date"]


def test_post_bad_report():
    """
    Post an invalid report, confirm a 400
    :return:
    """
    pass


def test_broken_links_not_enough_data():
    response = requests.get("http://localhost:8000/broken_links")
    assert response.status_code == 200
    assert "Not enough data" in str(response.content)


def test_broken_links():
    """
    Basic happy path test for /broken_links
    :return:
    """
    response = requests.get("http://localhost:8000/broken_links")
    assert response.status_code == 200, str(response.content)


def test_get_report():
    # Get an existing report
    headers = {"Content-type": "application/json"}
    response = requests.post(
        "http://localhost:8000/report", headers=headers, json=report_data()
    )
    assert response.status_code in [201]
    report_id = response.json()["report_id"]

    response = requests.get(f"http://localhost:8000/report/{report_id}")
    assert response.status_code == 200

    # Request a non-existent report, expect 404
    pass

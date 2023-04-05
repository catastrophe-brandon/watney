import datetime
from uuid import UUID

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

TEST_HOST = "localhost:8000"

def test_report():
    """
    Basic request, post a report then get the data
    :return:
    """
    headers = {"Content-type": "application/json"}
    response = requests.post(
        f"http://{TEST_HOST}/report", headers=headers, json=report_data
    )
    assert response.status_code in [200, 201]
    report_id = response.json()["report_id"]

    # Posting the same data twice should fail
    response = requests.post(
        f"http://{TEST_HOST}/report", headers=headers, json=report_data
    )
    assert response.status_code == 409

    assert report_id is not None
    response = requests.get(f"http://{TEST_HOST}/report/{report_id}")
    assert response.status_code == 200
    assert response.json()["report_date"] == report_data["report_date"]


def test_post_bad_report():
    """
    Post an invalid report, confirm a 400
    :return:
    """
    pass


def test_broken_links_not_enough_data():
    response = requests.get(f"http://{TEST_HOST}/broken_links")
    assert response.status_code == 200


def test_broken_links():
    """
    Basic happy path test for /broken_links
    :return:
    """
    response = requests.get(f"http://{TEST_HOST}/broken_links")
    assert response.status_code == 200, str(response.content)


def test_get_report():
    # Get an existing report
    headers = {"Content-type": "application/json"}
    response = requests.post(
        f"http://{TEST_HOST}/report", headers=headers, json=report_data()
    )
    assert response.status_code in [201]
    report_id = response.json()["report_id"]

    response = requests.get(f"http://{TEST_HOST}/report/{report_id}")
    assert response.status_code == 200

    # Request a non-existent report, expect 404
    import uuid
    response = requests.get(f"http://{TEST_HOST}/report/{uuid.uuid4()}")
    assert response.status_code == 404

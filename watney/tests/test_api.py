import datetime
from uuid import UUID

import requests
from watney.tests.test_fixtures import empty_db, fake_report
from faker import Faker

fake = Faker()


def create_broken_links(url: str) -> list:
    result = []
    for i in range(0, 20):
        result.append({"file": fake.file_path(), "url": url, "status_code": 404})
    return result


def create_fake_report_data() -> list:
    result = []
    for i in range(0, 20):
        url = fake.url()
        result.append(
            {
                "repo_name": fake.domain_word(),
                "repo_url": url,
                "broken_links": create_broken_links(url),
            }
        )
    return result


def report_data():
    return {
        "report": create_fake_report_data(),
        "report_date": datetime.datetime.utcnow().isoformat(),
    }


TEST_HOST = "localhost:8000"


def test_report():
    """
    Basic request, post a report then get the data
    :return:
    """
    headers = {"Content-type": "application/json"}
    test_report_data = report_data()
    response = requests.post(
        f"http://{TEST_HOST}/report", headers=headers, json=test_report_data
    )
    assert response.status_code in [200, 201]
    report_id = response.json()["report_id"]

    # Posting the same data twice should fail
    response = requests.post(
        f"http://{TEST_HOST}/report", headers=headers, json=test_report_data
    )
    assert response.status_code == 409
    assert report_id is not None

    # should be able to retrieve the saved report data by id
    response = requests.get(f"http://{TEST_HOST}/report/{report_id}")
    assert response.status_code == 200
    assert response.json()["report_date"] == test_report_data["report_date"]


def test_post_bad_report():
    """
    Post an invalid report, confirm a 400
    :return:
    """
    headers = {"Content-type": "application/json"}
    response = requests.post(f"http://{TEST_HOST}/report", headers=headers, json={})
    assert response.status_code == 422


def test_broken_links_not_enough_data(empty_db):
    response = requests.get(f"http://{TEST_HOST}/broken_links")
    assert response.status_code == 409


def test_broken_links_no_prev_data(fake_report):
    """
    Test when there is no previous report data and we call /broken_links
    :return:
    """
    response = requests.get(f"http://{TEST_HOST}/broken_links")
    assert response.status_code == 200, str(response.content)
    assert not response.json()["existing_broken_links"]
    assert response.json()["new_broken_links"] is not None


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

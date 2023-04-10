import datetime
from uuid import UUID

import pytest
import requests
from watney.tests.test_fixtures import empty_db, fake_report, two_reports_one_empty
from faker import Faker

fake = Faker()

TEST_PROTO = "http"
TEST_HOST = "localhost:8000"
URL_ANCHOR = f"{TEST_PROTO}://{TEST_HOST}"
REPORT_URL = f"{URL_ANCHOR}/report"
BROKEN_LINKS_URL = f"{URL_ANCHOR}/broken_links"
MAX_BROKEN_LINKS = 20
MAX_REPOS = 20


def create_broken_links(url: str) -> list:
    result = []
    for i in range(0, MAX_BROKEN_LINKS):
        result.append({"file": fake.file_path(), "url": url, "status_code": 404})
    return result


def create_fake_report_data() -> list:
    result = []
    for i in range(0, MAX_REPOS):
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


def fake_empty_report():
    result = []
    for i in range(0, MAX_REPOS):
        url = fake.url()
        result.append(
            {
                "repo_name": fake.domain_word(),
                "repo_url": url,
                "broken_links": [],
            }
        )
    return result


def test_report():
    """
    Basic request, post a report then get the data
    :return:
    """
    headers = {"Content-type": "application/json"}
    test_report_data = report_data()
    response = requests.post(REPORT_URL, headers=headers, json=test_report_data)
    assert response.status_code in [200, 201]
    report_id = response.json()["report_id"]

    # Posting the same data twice should fail
    response = requests.post(REPORT_URL, headers=headers, json=test_report_data)
    assert response.status_code == 409
    assert report_id is not None

    # should be able to retrieve the saved report data by id
    response = requests.get(f"{REPORT_URL}/{report_id}")
    assert response.status_code == 200
    assert response.json()["report_date"] == test_report_data["report_date"]


def test_post_bad_report():
    """
    Post an invalid report, confirm a 400
    :return:
    """
    headers = {"Content-type": "application/json"}
    response = requests.post(REPORT_URL, headers=headers, json={})
    assert response.status_code == 422


def test_broken_links_not_enough_data(empty_db):
    response = requests.get(BROKEN_LINKS_URL)
    assert response.status_code == 409


def test_broken_links_no_prev_data(two_reports_one_empty):
    """
    Verify that when there is no previous report data all links are reported as new
    :return:
    """
    response = requests.get(BROKEN_LINKS_URL)
    assert response.status_code == 200, str(response.content)
    assert not response.json()["existing_broken_links"]
    assert response.json()["new_broken_links"] is not None


def test_get_report(fake_report):
    # Get an existing report
    response = requests.get(f"{REPORT_URL}/{fake_report}")
    assert response.status_code == 200

    # Request a non-existent report, expect 404
    import uuid

    response = requests.get(f"{REPORT_URL}/{uuid.uuid4()}")
    assert response.status_code == 404


def test_broken_links_all_new_broken(two_reports_one_empty):
    """
    Get the diff between the two most recent reports.
    :return:
    """
    response = requests.get(BROKEN_LINKS_URL)
    assert response.status_code == 200
    assert response.json()["existing_broken_links"] is None
    assert len(response.json()["new_broken_links"]) is MAX_BROKEN_LINKS * MAX_REPOS

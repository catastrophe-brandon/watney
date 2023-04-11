import datetime
from uuid import UUID

import pytest
import requests

from watney.helpers import clone_report
from watney.tests.test_fixtures import (
    empty_db,
    fake_report,
    two_reports_one_empty,
    new_report_empty, MAX_BROKEN_LINKS, MAX_REPOS
)
from faker import Faker

fake = Faker()

TEST_PROTO = "http"
TEST_HOST = "localhost:8000"
URL_ANCHOR = f"{TEST_PROTO}://{TEST_HOST}"
REPORT_URL = f"{URL_ANCHOR}/report"
BROKEN_LINKS_URL = f"{URL_ANCHOR}/broken_links"


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
    assert len(response.json()["existing_broken_links"]) == 0
    assert len(response.json()["new_broken_links"]) == MAX_BROKEN_LINKS * MAX_REPOS


def test_broken_links_no_new_data(new_report_empty):
    """
    Verify that when the new report contains no links every broken
    link is considered "fixed"
    :param new_report_empty:
    :return:
    """
    response = requests.get(BROKEN_LINKS_URL)
    assert response.status_code == 200, str(response.content)
    assert not response.json()["existing_broken_links"]
    assert not response.json()["new_broken_links"]


def test_newly_broken_links(fake_report):
    """
    Submit two reports where the broken links are the same.
    On the second report everything should be considered "existing".
    Submit a third report with one more broken link.
    Confirm the link is counted as "new"
    """
    import uuid

    new_uuid = uuid.uuid4()
    new_ts = "2023-03-14T14:15:34.726727"
    clone_report(fake_report, new_uuid, new_ts)

    response = requests.get(f"{REPORT_URL}/{new_uuid}")
    assert response.status_code == 200, str(response.content)

    # Two identical reports, all links are existing broken links
    response = requests.get(BROKEN_LINKS_URL)
    assert response.status_code == 200, str(response.content)
    assert len(response.json()["existing_broken_links"]) == MAX_BROKEN_LINKS * MAX_REPOS
    assert len(response.json()["new_broken_links"]) == 0

    # Third report, add 1 broken link
    # TODO: create report with additional broken link
    response = requests.get(BROKEN_LINKS_URL)
    assert response.status_code == 200, str(response.content)
    assert len(response.json()["existing_broken_links"]) == MAX_BROKEN_LINKS * MAX_REPOS
    assert len(response.json()["new_broken_links"]) == 1


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
    assert len(response.json()["existing_broken_links"]) == 0
    assert len(response.json()["new_broken_links"]) == MAX_BROKEN_LINKS * MAX_REPOS

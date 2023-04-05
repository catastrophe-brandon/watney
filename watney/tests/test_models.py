import datetime
import uuid
from typing import List
from faker import Faker

import pytest

fake = Faker()

from watney.main import (
    report_exists_for_date,
    session,
    create_data,
    report_exists,
    get_last_report_id_and_datestamp,
    BrokenLinkReportData,
)
from watney.main import BrokenLinkRepo, BrokenLink

FAKE_REPORT_DATE = datetime.datetime.fromisoformat("2023-03-14T14:15:34.726727")
FAKE_REPORT_UUID = uuid.uuid4()


def create_fake_link_data(url) -> BrokenLink:
    result = []
    for i in range(0, 10):
        result.append(BrokenLink(file=fake.file_path, url=url, status_code=404))
    return result


def create_fake_repo() -> BrokenLinkRepo:
    url = fake.url
    return BrokenLinkRepo(name=fake.domain_word, url=url, broken_links=create_fake_link_data(url))


def create_fake_repos() -> List[BrokenLinkRepo]:
    result = []
    for i in range(0, 20):
        result.append(create_fake_repo())
    return result


def create_fake_report(
        report_id: uuid.UUID, report_ts: datetime
) -> BrokenLinkReportData:
    BrokenLinkReportData()
    fake_repos = create_fake_repos()
    blrd = None
    for fake_repo in fake_repos:
        broken_link_data = BrokenLink(file=fake_repo.file, url=fake_repo.url, status_code=fake_repo.status_code)
        report_data = create_data(
            report_id=report_id,
            report_date=report_ts,
            repo=fake_repo,
            link=broken_link_data,
        )
        blrd = report_data
        session.add(report_data)
    session.commit()
    return blrd


def db_cleanup(broken_link_report_data: List[BrokenLinkReportData]):
    for blrd in broken_link_report_data:
        session.delete(blrd)
    session.commit()


@pytest.fixture
def fake_report():
    report_data = create_fake_report(FAKE_REPORT_UUID, FAKE_REPORT_DATE)
    yield
    db_cleanup([report_data])


@pytest.fixture
def multiple_reports():
    last_id = None
    last_date = None
    all_data = []
    for i in range(0, 100):
        last_id = uuid.uuid4()
        last_date = datetime.datetime.utcnow()
        all_data.append(create_fake_report(last_id, last_date))
    yield last_id, last_date
    db_cleanup(all_data)


def test_report_exists(fake_report):
    assert report_exists(FAKE_REPORT_UUID)
    assert not report_exists(uuid.uuid4())


def test_report_exists_for_date(fake_report):
    # Create a report and confirm it returns true
    assert report_exists_for_date(FAKE_REPORT_DATE)
    # Search for a non-existent report, confirm it returns false
    assert not report_exists_for_date(datetime.datetime.now())


def test_get_last_report_id_and_datestamp(multiple_reports):
    result = get_last_report_id_and_datestamp()
    assert result[0] == multiple_reports[0]
    assert result[1] == multiple_reports[1]

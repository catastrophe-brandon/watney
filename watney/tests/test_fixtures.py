from typing import List

import pytest
import datetime
import uuid

from sqlalchemy.orm.exc import ObjectDeletedError

from watney.db.models import BrokenLinkReportData, create_tables, BrokenLinkFileData
from watney.db.session import get_session, get_engine_from_settings
from watney.helpers import create_data, clear_db, delete_report_data
from watney.schema import BrokenLink, BrokenLinkRepo

from faker import Faker

fake = Faker()

FAKE_REPORT_DATE = datetime.datetime.fromisoformat("2023-03-14T14:15:34.726727")
FAKE_EMPTY_REPORT_DATE = datetime.datetime.fromisoformat("2023-03-11T22:33:32.87")
FAKE_REPORT_UUID = uuid.uuid4()
FAKE_EMPTY_REPORT_UUID = uuid.uuid4()
MAX_BROKEN_LINKS = 20
MAX_REPOS = 20


def create_fake_link_data(url) -> List[BrokenLink]:
    result = []
    for i in range(0, MAX_BROKEN_LINKS):
        file_path = fake.file_path()
        result.append(BrokenLink(file=file_path, url=url + file_path, status_code=404))
    return result


def create_fake_repo() -> BrokenLinkRepo:
    url = fake.url()
    return BrokenLinkRepo(
        repo_name=fake.domain_word(),
        repo_url=url,
        broken_links=create_fake_link_data(url),
    )


def create_fake_repos() -> List[BrokenLinkRepo]:
    result = []
    for i in range(0, MAX_REPOS):
        result.append(create_fake_repo())
    return result


def create_fake_empty_report(report_id: uuid.UUID, report_ts: datetime):
    """
    Create a report with no broken links
    :param report_id:
    :param report_ts:
    :return:
    """
    with get_session() as session:
        session.add(BrokenLinkReportData(report_id=report_id, date=report_ts))
        session.commit()


def create_fake_report(report_id: uuid.UUID, report_ts: datetime):
    """
    Models and persists fake report data to the db.
    :param report_id:
    :param report_ts:
    :return:
    """
    fake_repos = create_fake_repos()
    with get_session() as session:
        session.add(BrokenLinkReportData(report_id=report_id, date=report_ts))
        for fake_repo in fake_repos:
            for broken_link in fake_repo.broken_links:
                broken_link_data = BrokenLinkFileData(
                    report_id=report_id,
                    repo_name=fake_repo.repo_name,
                    repo_url=fake_repo.repo_url,
                    file=broken_link.file,
                    url=broken_link.url,
                    status_code=broken_link.status_code,
                )
                session.add(broken_link_data)
        session.commit()


@pytest.fixture
def fake_report():
    create_tables(get_engine_from_settings())
    clear_db()
    create_fake_report(FAKE_REPORT_UUID, FAKE_REPORT_DATE)
    yield FAKE_REPORT_UUID
    try:
        pass
    #        delete_report_data(FAKE_REPORT_UUID)
    except ObjectDeletedError:
        pass


@pytest.fixture
def two_reports_one_empty():
    """
    Creates two reports:
    - One has zero broken links
    - The second has a few broken links
    :return:
    """
    create_tables(get_engine_from_settings())
    clear_db()
    create_fake_empty_report(FAKE_EMPTY_REPORT_UUID, FAKE_EMPTY_REPORT_DATE)
    create_fake_report(FAKE_REPORT_UUID, FAKE_REPORT_DATE)
    yield FAKE_EMPTY_REPORT_UUID, FAKE_REPORT_UUID
    try:
        delete_report_data(FAKE_EMPTY_REPORT_UUID)
        delete_report_data(FAKE_REPORT_UUID)
    except ObjectDeletedError:
        pass


@pytest.fixture
def new_report_empty():
    """
    Creates two reports
    - Previous report has broken links
    - The new report has no broken links
    :return:
    """
    create_tables(get_engine_from_settings())
    clear_db()
    prev_report_uuid = uuid.uuid4()
    prev_report_ts = "2023-03-14T14:15:34.726727"
    new_empty_report_uuid = uuid.uuid4()
    new_empty_report_ts = "2023-03-20T14:20:38.23"
    create_fake_report(prev_report_uuid, prev_report_ts)
    create_fake_empty_report(new_empty_report_uuid, new_empty_report_ts)
    yield prev_report_uuid, new_empty_report_uuid
    try:
        delete_report_data(prev_report_uuid)
        delete_report_data(new_empty_report_uuid)
    except ObjectDeletedError:
        pass


@pytest.fixture
def multiple_reports():
    last_id = None
    last_date = None
    all_data = []
    for i in range(0, 100):
        last_id = uuid.uuid4()
        last_date = datetime.datetime.utcnow()
        create_fake_report(last_id, last_date)
        all_data.append(last_id)
    yield last_id, last_date
    for data in all_data:
        delete_report_data(data)


@pytest.fixture
def empty_db():
    create_tables(get_engine_from_settings())
    clear_db()

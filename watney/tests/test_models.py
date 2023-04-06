import datetime
import uuid

from watney.helpers import report_exists_for_date
from watney.helpers import (
    report_exists,
    get_last_report_id_and_datestamp,
)
from watney.tests.test_fixtures import (
    FAKE_REPORT_UUID,
    FAKE_REPORT_DATE,
    fake_report,
    multiple_reports,
)


def test_report_exists(fake_report):
    assert report_exists(FAKE_REPORT_UUID)
    assert not report_exists(uuid.uuid4())


def test_report_exists_for_date(fake_report):
    assert report_exists_for_date(FAKE_REPORT_DATE)
    assert not report_exists_for_date(datetime.datetime.now())


def test_get_last_report_id_and_datestamp(multiple_reports):
    result = get_last_report_id_and_datestamp()
    assert result[0] == multiple_reports[0]
    assert result[1] == multiple_reports[1]

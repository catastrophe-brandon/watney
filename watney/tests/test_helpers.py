from watney.helpers import clear_db, get_report_by_id


def test_clear_db(fake_report):
    """
    Confirm that we can clear the table in the db between tests
    :return:
    """
    clear_db()
    assert not get_report_by_id(fake_report)

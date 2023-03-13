import uuid
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI

from api import BrokenLinkReport, BrokenLinksResponse
from models.models import persist, get_last_report_id_and_datestamp

app = FastAPI()


@app.post("/report")
def report(broken_link_report: BrokenLinkReport):
    """
    Store new broken link report data.
    :param broken_link_report:
    :return:
    """
    print(broken_link_report)
    persist(broken_link_report)
    return


@app.get("/report")
def get_report(uuid: UUID):
    """
    Retrieve the data from a specific report.
    :param uuid:
    :return:
    """
    return {"report": []}


@app.get("/broken_links")
def broken_links():
    return BrokenLinksResponse(new_broken_links=[], existing_broken_links=[], last_report_id=uuid.uuid4(),
                               last_report_date=datetime.now())


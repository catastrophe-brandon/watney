from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class BrokenLink(BaseModel):
    """
    Minimal details about a broken link
    """

    file: str
    url: str
    status_code: int


class BrokenLinkRepo(BaseModel):
    """
    Repo-level information about the broken links
    """

    repo_name: str
    repo_url: str
    broken_links: List[BrokenLink]


class BrokenLinkReport(BaseModel):
    """
    An aggregation of all the data about broken links. The "report"
    """

    report: List[BrokenLinkRepo]
    report_date: datetime
    report_id: Optional[UUID]


class BrokenLinkDetails(BaseModel):
    """
    Broken link full details for use in the response to /broken-links
    """
    file: str
    url: str
    status_code: int
    repo_name: str
    repo_url: str


class BrokenLinksResponse(BaseModel):
    """
    A report that includes data about newly-broken links, links that were already known to be
    broken, and details about the most recently reported broken link data.
    """

    new_broken_links: List[BrokenLinkDetails]
    existing_broken_links: List[BrokenLinkDetails]
    last_report_id: UUID
    last_report_date: datetime


class ReportSummary(BaseModel):
    report_id: str
    report_date: datetime


class ReportList(BaseModel):
    reports: List[ReportSummary]



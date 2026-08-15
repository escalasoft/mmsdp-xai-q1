import hashlib
import json

import extraction.qt_jira_cloud_acquisition as module
from extraction.qt_issue_extraction import (
    QtIssueExtractionSpecification,
    QtIssueExtractor,
)


def test_acquisition_normalizes_without_using_updated(monkeypatch, tmp_path) -> None:
    issue = {
        "key": "QTBUG-7",
        "fields": {
            "summary": "Historical defect",
            "issuetype": {"name": "Bug"},
            "status": {"name": "Closed"},
            "resolution": {"name": "Fixed"},
            "priority": {"name": "P1"},
            "created": "2012-01-01T00:00:00.000+0000",
            "updated": "2025-11-22T00:00:00.000+0000",
            "resolutiondate": "2012-01-03T00:00:00.000+0000",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Details"}],
                    }
                ],
            },
            "reporter": {"accountId": "reporter-1"},
            "assignee": None,
            "components": [{"name": "Core"}, {"name": "GUI"}],
            "versions": [{"name": "4.8"}],
            "fixVersions": [{"name": "5.0"}],
        },
    }
    monkeypatch.setattr(
        module,
        "_request",
        lambda query, token: {"issues": [issue], "isLast": True},
    )

    manifest = module.acquire_qtbug_issues(("QTBUG-7",), tmp_path)
    normalized_path = tmp_path / "qtbug-issues.json"
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    assert normalized[0]["updated_timestamp"] is None
    assert normalized[0]["component"] == '["Core","GUI"]'
    assert normalized[0]["description"] == "Details"
    assert (
        manifest["normalized_source_sha256"]
        == hashlib.sha256(normalized_path.read_bytes()).hexdigest()
    )

    specification = QtIssueExtractionSpecification(
        "qtbase",
        module.CANONICAL_SOURCE,
        "fixture-source",
        manifest["normalized_source_sha256"],
        "QTBUG",
        module.SCHEMA_VERSION,
        "1.0.0",
    )
    result = QtIssueExtractor().extract(specification, normalized_path)
    assert result.extracted_issue_count == 1
    assert result.issues[0].updated_timestamp is None

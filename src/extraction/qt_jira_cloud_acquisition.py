"""Minimal anonymous acquisition of exact QTBUG evidence from Qt Jira Cloud."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path

CANONICAL_SOURCE = "https://qt-project.atlassian.net"
PROJECT_IDENTIFIER = "QTBUG"
ENDPOINT = f"{CANONICAL_SOURCE}/rest/api/3/search/jql"
SCHEMA_VERSION = "qt-jira-cloud-normalized-1.0.0"
FIELDS = (
    "summary",
    "issuetype",
    "status",
    "resolution",
    "priority",
    "created",
    "resolutiondate",
    "description",
    "reporter",
    "assignee",
    "components",
    "versions",
    "fixVersions",
)


class QtJiraCloudAcquisitionError(RuntimeError):
    """A sanitized failure while reading the authoritative Jira source."""


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _text_from_adf(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        fragments: list[str] = []
        text = value.get("text")
        if isinstance(text, str):
            fragments.append(text)
        content = value.get("content", ())
        if isinstance(content, list):
            for item in content:
                child = _text_from_adf(item)
                if child:
                    fragments.append(child)
        separator = "\n" if value.get("type") in {"paragraph", "heading"} else ""
        return separator.join(fragments) or None
    if isinstance(value, list):
        values = tuple(filter(None, (_text_from_adf(item) for item in value)))
        return "\n".join(values) or None
    raise QtJiraCloudAcquisitionError("Jira description uses an unsupported schema")


def _named(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise QtJiraCloudAcquisitionError("Jira named field is malformed")
    name = value.get("name")
    if name is None:
        return None
    if not isinstance(name, str):
        raise QtJiraCloudAcquisitionError("Jira named field has no stable text")
    return name


def _user(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise QtJiraCloudAcquisitionError("Jira user field is malformed")
    identifier = value.get("accountId")
    if identifier is None:
        return None
    if not isinstance(identifier, str) or not identifier.strip():
        raise QtJiraCloudAcquisitionError("Jira user has no stable account identifier")
    return identifier


def _names(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise QtJiraCloudAcquisitionError(f"Jira {field_name} field is malformed")
    names = []
    for item in value:
        name = _named(item)
        if name is not None:
            names.append(name)
    return tuple(sorted(set(names)))


def _normalize(issue: object) -> dict[str, object]:
    if not isinstance(issue, Mapping):
        raise QtJiraCloudAcquisitionError("Jira issue record is malformed")
    key = issue.get("key")
    fields = issue.get("fields")
    if (
        not isinstance(key, str)
        or not key.startswith("QTBUG-")
        or not isinstance(fields, Mapping)
    ):
        raise QtJiraCloudAcquisitionError("Jira issue identity is malformed")
    components = _names(fields.get("components"), "components")
    versions = _names(fields.get("versions"), "versions")
    fix_versions = _names(fields.get("fixVersions"), "fixVersions")
    created = fields.get("created")
    resolved = fields.get("resolutiondate")
    if created is not None and not isinstance(created, str):
        raise QtJiraCloudAcquisitionError("Jira created timestamp is malformed")
    if resolved is not None and not isinstance(resolved, str):
        raise QtJiraCloudAcquisitionError("Jira resolution timestamp is malformed")
    return {
        "issue_identifier": key,
        "project_identifier": PROJECT_IDENTIFIER,
        "issue_type": _named(fields.get("issuetype")),
        "status": _named(fields.get("status")),
        "resolution": _named(fields.get("resolution")),
        "priority": _named(fields.get("priority")),
        "created_timestamp": created,
        "updated_timestamp": None,
        "resolved_timestamp": resolved,
        "summary": fields.get("summary"),
        "description": _text_from_adf(fields.get("description")),
        "reporter_identifier": _user(fields.get("reporter")),
        "assignee_identifier": _user(fields.get("assignee")),
        "component": json.dumps(components, ensure_ascii=False, separators=(",", ":")),
        "version": json.dumps(versions, ensure_ascii=False, separators=(",", ":")),
        "fix_versions": list(fix_versions),
        "metadata": {
            "component_representation": "canonical-json-array",
            "version_representation": "canonical-json-array",
        },
    }


def _request(query: str, next_page_token: str | None) -> dict[str, object]:
    parameters = {
        "jql": query,
        "maxResults": "100",
        "fields": ",".join(FIELDS),
    }
    if next_page_token is not None:
        parameters["nextPageToken"] = next_page_token
    request = urllib.request.Request(
        f"{ENDPOINT}?{urllib.parse.urlencode(parameters)}",
        headers={"Accept": "application/json", "User-Agent": "mmsdp-xai-q1/1.0"},
        method="GET",
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise QtJiraCloudAcquisitionError(
                        "Jira returned a non-success status"
                    )
                value = json.loads(response.read().decode("utf-8"))
                if not isinstance(value, dict):
                    raise QtJiraCloudAcquisitionError("Jira response is not an object")
                return value
        except urllib.error.HTTPError as error:
            if error.code not in {429, 502, 503, 504} or attempt == 4:
                raise QtJiraCloudAcquisitionError(
                    f"Jira acquisition failed with HTTP {error.code}"
                ) from error
        except (
            urllib.error.URLError,
            TimeoutError,
            UnicodeError,
            json.JSONDecodeError,
        ) as error:
            if attempt == 4:
                raise QtJiraCloudAcquisitionError("Jira acquisition failed") from error
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def acquire_qtbug_issues(
    identifiers: Iterable[str], destination: str | Path
) -> dict[str, object]:
    """Acquire exact referenced QTBUG records and persist the source artifacts."""
    requested = tuple(sorted(set(identifiers)))
    if not requested or any(
        not item.startswith("QTBUG-") or not item[6:].isdigit() for item in requested
    ):
        raise ValueError("identifiers must contain exact QTBUG-<digits> values")
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "raw": root / "qtbug-jira-cloud-raw.json",
        "normalized": root / "qtbug-issues.json",
        "manifest": root / "qtbug-jira-cloud-acquisition.json",
    }
    queries = [
        (
            "project = QTBUG AND key IN "
            f"({','.join(requested[offset : offset + 75])}) ORDER BY key ASC"
        )
        for offset in range(0, len(requested), 75)
    ]
    existing = tuple(path.exists() for path in paths.values())
    if all(existing):
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        raw = paths["raw"].read_bytes()
        normalized = paths["normalized"].read_bytes()
        if (
            not isinstance(manifest, dict)
            or manifest.get("canonical_source") != CANONICAL_SOURCE
            or manifest.get("queries") != queries
            or manifest.get("requested_identifier_count") != len(requested)
            or manifest.get("raw_artifact_sha256") != _digest_bytes(raw)
            or manifest.get("normalized_source_sha256") != _digest_bytes(normalized)
        ):
            raise QtJiraCloudAcquisitionError(
                "existing Jira artifacts disagree with the requested acquisition"
            )
        return {
            **manifest,
            "paths": {key: str(value) for key, value in paths.items()},
        }
    if any(existing):
        raise FileExistsError(
            "Qt Jira acquisition destination already contains artifacts"
        )

    raw_issues: dict[str, object] = {}
    for query in queries:
        token = None
        while True:
            response = _request(query, token)
            issues = response.get("issues")
            if not isinstance(issues, list):
                raise QtJiraCloudAcquisitionError("Jira response has no issue array")
            for issue in issues:
                if not isinstance(issue, Mapping) or not isinstance(
                    issue.get("key"), str
                ):
                    raise QtJiraCloudAcquisitionError(
                        "Jira returned malformed issue identity"
                    )
                raw_issues[issue["key"]] = issue
            if response.get("isLast") is True:
                break
            token = response.get("nextPageToken")
            if not isinstance(token, str) or not token:
                raise QtJiraCloudAcquisitionError("Jira pagination token is missing")

    ordered_raw = [raw_issues[key] for key in sorted(raw_issues)]
    normalized = [_normalize(issue) for issue in ordered_raw]
    raw_bytes = _canonical_bytes(ordered_raw)
    normalized_bytes = _canonical_bytes(normalized)
    acquired_at = datetime.now(UTC).isoformat()
    missing = tuple(sorted(set(requested) - set(raw_issues)))
    manifest = {
        "canonical_source": CANONICAL_SOURCE,
        "endpoint": ENDPOINT,
        "project_identifier": PROJECT_IDENTIFIER,
        "acquired_at": acquired_at,
        "schema_version": SCHEMA_VERSION,
        "fields": list(FIELDS),
        "updated_timestamp_policy": "not-requested-not-authoritative",
        "query_policy": "exact-commit-message-QTBUG-identifiers-only",
        "queries": queries,
        "requested_identifier_count": len(requested),
        "record_count": len(normalized),
        "missing_identifier_count": len(missing),
        "missing_identifiers": list(missing),
        "raw_artifact_sha256": _digest_bytes(raw_bytes),
        "normalized_source_sha256": _digest_bytes(normalized_bytes),
    }
    paths["raw"].write_bytes(raw_bytes)
    paths["normalized"].write_bytes(normalized_bytes)
    paths["manifest"].write_bytes(_canonical_bytes(manifest))
    return {**manifest, "paths": {key: str(value) for key, value in paths.items()}}

"""Bounded public-registry access and explicit, integrity-checked snapshots."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx

from . import __version__
from .disease import APP_NAME, SEARCH_CONDITION, has_disease_label

API_BASE = "https://clinicaltrials.gov/api/v2/"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
NCT_PATTERN = re.compile(r"NCT[0-9]{8}\Z")
SEARCH_KEYS = {
    "query.cond",
    "query.intr",
    "filter.overallStatus",
    "filter.advanced",
    "format",
    "pageSize",
    "pageToken",
    "countTotal",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RegistryError(Exception):
    """Safe errors for tool output: never include response bodies or credentials."""

    def __init__(self, code: str, message: str, retryable: bool = False):
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


def validate_nct(nct_id: Any) -> str:
    if type(nct_id) is not str or not NCT_PATTERN.fullmatch(nct_id):
        raise RegistryError(
            "invalid_input", "Use an NCT ID with NCT followed by exactly eight digits."
        )
    return nct_id


def _path(data: Any, *parts: str) -> Any:
    for part in parts:
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


class RegistryClient:
    source_mode = "live"

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            timeout=httpx.Timeout(10.0),
            follow_redirects=False,
            transport=transport,
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    f"{APP_NAME.replace(' ', '-')}/{__version__} "
                    "public-research-prototype"
                ),
            },
        )
        self._sleep = sleep
        self._metadata: dict[str, dict] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def aclose(self) -> None:
        await self.close()

    def metadata(self, nct_id: str) -> dict:
        return deepcopy(
            self._metadata.get(
                nct_id,
                {
                    "retrieved_at": utc_now(),
                    "source_mode": "live",
                    "snapshot_sha256": None,
                },
            )
        )

    async def get_study(self, nct_id: str) -> dict:
        validate_nct(nct_id)
        study = await self._request(f"studies/{nct_id}", {"format": "json"})
        actual = _path(study, "protocolSection", "identificationModule", "nctId")
        if actual != nct_id:
            raise RegistryError(
                "upstream_error",
                "Registry returned a record with an unexpected identifier.",
            )
        self._metadata[nct_id] = {
            "retrieved_at": utc_now(),
            "source_mode": "live",
            "snapshot_sha256": None,
        }
        return study

    async def search(self, params: dict) -> dict:
        if not isinstance(params, dict) or any(
            key not in SEARCH_KEYS for key in params
        ):
            raise RegistryError(
                "invalid_input", "Unsupported registry search parameters."
            )
        return await self._request("studies", params)

    @staticmethod
    def _delay(response: httpx.Response | None, attempt: int) -> float:
        fallback = min(0.5 * 2**attempt, 5.0)
        if response is None or "Retry-After" not in response.headers:
            return fallback
        raw = response.headers["Retry-After"]
        try:
            delay = float(raw)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(raw)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                delay = (parsed - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                return fallback
        # NaN comparisons do not behave like ordinary bounds.
        if delay != delay:
            return fallback
        return max(0.0, min(delay, 5.0))

    async def _request(self, path: str, params: dict) -> dict:
        if path != "studies" and not re.fullmatch(r"studies/NCT[0-9]{8}", path):
            raise RegistryError("invalid_input", "Unsupported registry resource.")
        for attempt in range(3):
            response = None
            try:
                async with self._client.stream("GET", path, params=params) as response:
                    if response.status_code == 429 or 500 <= response.status_code < 600:
                        if attempt < 2:
                            delay = self._delay(response, attempt)
                        else:
                            raise RegistryError(
                                "upstream_error",
                                "ClinicalTrials.gov is temporarily unavailable "
                                "or rate limited.",
                                True,
                            )
                    elif response.status_code == 404:
                        raise RegistryError(
                            "not_found",
                            "No registry record was found for this identifier.",
                        )
                    elif response.status_code == 400:
                        raise RegistryError(
                            "invalid_input",
                            "The registry could not process these search criteria.",
                        )
                    elif response.status_code != 200:
                        raise RegistryError(
                            "upstream_error",
                            "ClinicalTrials.gov returned an unsuccessful response.",
                        )
                    else:
                        content_length = response.headers.get("Content-Length", "")
                        if (
                            content_length.isdigit()
                            and int(content_length) > MAX_RESPONSE_BYTES
                        ):
                            raise RegistryError(
                                "upstream_error",
                                "Registry response exceeds the supported size limit.",
                            )
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > MAX_RESPONSE_BYTES:
                                raise RegistryError(
                                    "upstream_error",
                                    "Registry response exceeds "
                                    "the supported size limit.",
                                )
                        try:
                            data = json.loads(body)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            raise RegistryError(
                                "upstream_error", "Registry returned invalid JSON."
                            ) from None
                        if not isinstance(data, dict):
                            raise RegistryError(
                                "upstream_error",
                                "Registry returned an unexpected response structure.",
                            )
                        return data
            except httpx.RequestError:
                if attempt == 2:
                    raise RegistryError(
                        "upstream_error",
                        "ClinicalTrials.gov could not be reached "
                        "within the request limits.",
                        True,
                    ) from None
                delay = self._delay(None, attempt)
            await self._sleep(delay)
        raise RegistryError(
            "upstream_error", "ClinicalTrials.gov could not be reached.", True
        )


class SnapshotRegistry:
    """Read frozen public records without a silent live-to-snapshot fallback.

    Only development files are opened by default. Held-out files are read only
    when an evaluator explicitly creates this client with include_heldout=True.
    """

    source_mode = "snapshot"

    def __init__(self, manifest_path: str | Path, *, include_heldout: bool = False):
        self.manifest_path = Path(manifest_path).resolve()
        self._records: dict[str, dict] = {}
        self._metadata: dict[str, dict] = {}
        public_root = (self.manifest_path.parent / "public").resolve()
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8-sig"))
            if not isinstance(manifest, list):
                raise ValueError("Manifest must be an array")
            for entry in manifest:
                if not isinstance(entry, dict):
                    raise ValueError("Invalid manifest entry")
                split = entry.get("split")
                if split == "heldout" and not include_heldout:
                    continue
                if split not in {"development", "heldout"}:
                    raise ValueError("Invalid split")
                nct_id = validate_nct(entry.get("nct_id"))
                if nct_id in self._records:
                    raise ValueError("Duplicate identifier")
                relative = entry.get("file")
                if not isinstance(relative, str) or Path(relative).is_absolute():
                    raise ValueError("Invalid snapshot path")
                path = (self.manifest_path.parent / relative).resolve()
                if not path.is_relative_to(public_root / split):
                    raise ValueError("Snapshot outside declared public split")
                if path.name != f"{nct_id}.json":
                    raise ValueError("Snapshot name does not match identifier")
                content = path.read_bytes()
                if len(content) > MAX_RESPONSE_BYTES:
                    raise ValueError("Snapshot exceeds supported size")
                digest = hashlib.sha256(content).hexdigest()
                if digest != entry.get("sha256"):
                    raise ValueError("Snapshot integrity mismatch")
                study = json.loads(content)
                if (
                    not isinstance(study, dict)
                    or _path(study, "protocolSection", "identificationModule", "nctId")
                    != nct_id
                ):
                    raise ValueError("Snapshot identifier mismatch")
                if (
                    not isinstance(entry.get("retrieved_at"), str)
                    or not entry["retrieved_at"]
                ):
                    raise ValueError("Snapshot retrieval time missing")
                self._records[nct_id] = study
                self._metadata[nct_id] = {
                    "retrieved_at": entry["retrieved_at"],
                    "source_mode": "snapshot",
                    "snapshot_sha256": digest,
                }
        except (OSError, ValueError, TypeError, RegistryError):
            raise RegistryError(
                "upstream_error",
                "Public snapshot manifest or integrity validation failed.",
            ) from None

    async def close(self) -> None:
        return None

    async def aclose(self) -> None:
        return None

    def metadata(self, nct_id: str) -> dict:
        if nct_id not in self._metadata:
            raise RegistryError(
                "not_found", "This record is not in the selected public snapshot set."
            )
        return deepcopy(self._metadata[nct_id])

    async def get_study(self, nct_id: str) -> dict:
        validate_nct(nct_id)
        if nct_id not in self._records:
            raise RegistryError(
                "not_found", "This record is not in the selected public snapshot set."
            )
        return deepcopy(self._records[nct_id])

    async def search(self, params: dict) -> dict:
        if not isinstance(params, dict) or any(
            key not in SEARCH_KEYS for key in params
        ):
            raise RegistryError(
                "invalid_input", "Unsupported registry search parameters."
            )
        condition = params.get("query.cond", SEARCH_CONDITION)
        if (
            not isinstance(condition, str)
            or condition.strip().casefold() != SEARCH_CONDITION.casefold()
        ):
            raise RegistryError(
                "invalid_input",
                f"Snapshot search supports only the fixed {SEARCH_CONDITION} scope.",
            )
        intervention = params.get("query.intr", "")
        if not isinstance(intervention, str):
            raise RegistryError("invalid_input", "Intervention must be text.")
        matches = []
        for study in self._records.values():
            p = study.get("protocolSection", {})
            if (
                _path(p, "statusModule", "overallStatus") != "COMPLETED"
                or _path(p, "designModule", "studyType") != "INTERVENTIONAL"
            ):
                continue
            conditions = _path(p, "conditionsModule", "conditions") or []
            if not has_disease_label(conditions):
                continue
            interventions = _path(p, "armsInterventionsModule", "interventions") or []
            searchable = []
            if isinstance(interventions, list):
                for item in interventions:
                    if not isinstance(item, dict):
                        continue
                    for key in ("name", "description"):
                        if isinstance(item.get(key), str):
                            searchable.append(item[key])
                    if isinstance(item.get("otherNames"), list):
                        searchable.extend(
                            x for x in item["otherNames"] if isinstance(x, str)
                        )
            if intervention and not any(
                intervention.casefold() in text.casefold() for text in searchable
            ):
                continue
            matches.append(study)
        try:
            page_size = int(params.get("pageSize", 20))
            raw_token = params.get("pageToken", "0")
            if (
                not isinstance(raw_token, str)
                or not raw_token.isascii()
                or not raw_token.isdigit()
            ):
                raise ValueError
            offset = int(raw_token)
            if not 1 <= page_size <= 100:
                raise ValueError
        except (ValueError, TypeError):
            raise RegistryError(
                "invalid_input", "Invalid snapshot pagination parameters."
            ) from None
        result = {
            "studies": deepcopy(matches[offset : offset + page_size]),
            "search_semantics": "bounded_snapshot",
        }
        if offset + page_size < len(matches):
            result["nextPageToken"] = str(offset + page_size)
        return result

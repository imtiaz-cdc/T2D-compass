"""Network and snapshot boundary tests using only synthetic records."""

import hashlib
import json

import httpx
import pytest

from alz_compass.registry import (
    MAX_RESPONSE_BYTES,
    RegistryClient,
    RegistryError,
    SnapshotRegistry,
)


def record(nct_id="NCT00000001"):
    return {
        "hasResults": False,
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": "SYNTHETIC only"},
            "statusModule": {"overallStatus": "COMPLETED"},
            "designModule": {"studyType": "INTERVENTIONAL"},
            "conditionsModule": {"conditions": ["Type 2 Diabetes"]},
            "armsInterventionsModule": {
                "interventions": [
                    {
                        "name": "Synthetic exercise",
                        "description": "Movement",
                        "otherNames": ["Activity"],
                    }
                ]
            },
        },
    }


async def test_get_uses_fixed_origin_and_explicit_timeout():
    def handler(request):
        assert (
            str(request.url)
            == "https://clinicaltrials.gov/api/v2/studies/NCT00000001?format=json"
        )
        assert request.extensions["timeout"]["read"] == 10.0
        return httpx.Response(200, json=record())

    async with RegistryClient(transport=httpx.MockTransport(handler)) as client:
        assert await client.get_study("NCT00000001") == record()
        assert client.metadata("NCT00000001")["source_mode"] == "live"


@pytest.mark.parametrize(
    "value",
    ["https://evil.test", "NCT00000001/../../x", "NCT1", "nct00000001", 1, None],
)
async def test_invalid_identifier_never_requests_network(value):
    def handler(request):
        raise AssertionError("Must not make request")

    async with RegistryClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RegistryError) as error:
            await client.get_study(value)
        assert error.value.code == "invalid_input"


async def test_redirect_is_not_followed_and_body_is_not_exposed():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(
            302,
            headers={"Location": "https://evil.test/secret"},
            text="secret upstream details",
        )

    async with RegistryClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RegistryError) as error:
            await client.get_study("NCT00000001")
    assert len(requested) == 1
    assert error.value.code == "upstream_error"
    assert "secret" not in str(error.value)
    assert "evil" not in str(error.value)


async def test_retry_after_is_bounded_and_retry_succeeds():
    calls, sleeps = [], []

    async def sleep(delay):
        sleeps.append(delay)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "600"})
        if len(calls) == 2:
            return httpx.Response(503)
        return httpx.Response(200, json=record())

    async with RegistryClient(
        transport=httpx.MockTransport(handler), sleep=sleep
    ) as client:
        assert await client.get_study("NCT00000001") == record()
    assert len(calls) == 3
    assert sleeps == [5.0, 1.0]


async def test_timeout_stops_after_three_attempts_without_exception_details():
    calls, sleeps = [], []

    async def sleep(delay):
        sleeps.append(delay)

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("private network details", request=request)

    async with RegistryClient(
        transport=httpx.MockTransport(handler), sleep=sleep
    ) as client:
        with pytest.raises(RegistryError) as error:
            await client.get_study("NCT00000001")
    assert len(calls) == 3
    assert sleeps == [0.5, 1.0]
    assert error.value.retryable is True
    assert "private" not in str(error.value)


@pytest.mark.parametrize(
    "status, expected",
    [
        (404, "not_found"),
        (400, "invalid_input"),
        (401, "upstream_error"),
        (403, "upstream_error"),
    ],
)
async def test_nonretryable_http_errors(status, expected):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="sensitive text")

    async with RegistryClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RegistryError) as error:
            await client.get_study("NCT00000001")
    assert error.value.code == expected
    assert error.value.retryable is False
    assert len(calls) == 1
    assert "sensitive" not in str(error.value)


@pytest.mark.parametrize("body", [b"not-json", b"[]", b"null", b"true"])
async def test_unexpected_response_payload_rejected(body):
    async with RegistryClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=body))
    ) as client:
        with pytest.raises(RegistryError) as error:
            await client.get_study("NCT00000001")
    assert error.value.code == "upstream_error"


async def test_mismatched_identifier_rejected():
    async with RegistryClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json=record("NCT00000002"))
        )
    ) as client:
        with pytest.raises(RegistryError, match="unexpected identifier"):
            await client.get_study("NCT00000001")


async def test_response_size_limit_enforced():
    body = b" " * (MAX_RESPONSE_BYTES + 1)
    async with RegistryClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=body))
    ) as client:
        with pytest.raises(RegistryError, match="size limit"):
            await client.get_study("NCT00000001")


async def test_search_parameter_allowlist():
    def handler(request):
        assert request.url.path == "/api/v2/studies"
        assert request.url.params["query.cond"] == "Type 2 Diabetes"
        return httpx.Response(200, json={"studies": []})

    async with RegistryClient(transport=httpx.MockTransport(handler)) as client:
        assert await client.search({"query.cond": "Type 2 Diabetes"}) == {"studies": []}
        with pytest.raises(RegistryError) as error:
            await client.search({"url": "https://evil.test"})
        assert error.value.code == "invalid_input"


@pytest.fixture
def snapshot(tmp_path):
    public = tmp_path / "public" / "development"
    public.mkdir(parents=True)
    path = public / "NCT00000001.json"
    content = json.dumps(record()).encode("utf-8")
    path.write_bytes(content)
    manifest = [
        {
            "nct_id": "NCT00000001",
            "split": "development",
            "file": "public/development/NCT00000001.json",
            "sha256": hashlib.sha256(content).hexdigest(),
            "retrieved_at": "2026-01-01T00:00:00Z",
        }
    ]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, path, manifest


async def test_snapshot_is_explicit_and_integrity_checked(snapshot):
    manifest_path, path, manifest = snapshot
    client = SnapshotRegistry(manifest_path)
    study = await client.get_study("NCT00000001")
    assert study == record()
    assert client.metadata("NCT00000001") == {
        "retrieved_at": "2026-01-01T00:00:00Z",
        "source_mode": "snapshot",
        "snapshot_sha256": manifest[0]["sha256"],
    }
    study["hasResults"] = True
    assert (await client.get_study("NCT00000001"))["hasResults"] is False
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(RegistryError, match="integrity validation"):
        SnapshotRegistry(manifest_path)


async def test_heldout_files_are_not_opened_by_default(snapshot):
    manifest_path, _, manifest = snapshot
    # Deliberately nonexistent synthetic heldout file: default must never open it.
    manifest.append(
        {
            "nct_id": "NCT00000002",
            "split": "heldout",
            "file": "public/heldout/NCT00000002.json",
            "sha256": "missing",
            "retrieved_at": "2026-01-01T00:00:00Z",
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    client = SnapshotRegistry(manifest_path)
    with pytest.raises(RegistryError) as error:
        await client.get_study("NCT00000002")
    assert error.value.code == "not_found"
    with pytest.raises(RegistryError):
        SnapshotRegistry(manifest_path, include_heldout=True)


@pytest.mark.parametrize(
    "file",
    [
        "../NCT00000001.json",
        "public/development/../../../NCT00000001.json",
        "public/heldout/NCT00000001.json",
        "public/development/NCT00000002.json",
    ],
)
def test_snapshot_path_and_id_match_are_enforced(snapshot, file):
    manifest_path, _, manifest = snapshot
    manifest[0]["file"] = file
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RegistryError, match="integrity validation"):
        SnapshotRegistry(manifest_path)


async def test_snapshot_literal_intervention_search_and_absent_id(snapshot):
    client = SnapshotRegistry(snapshot[0])
    result = await client.search({"query.intr": "exercise", "pageSize": 20})
    assert result["studies"] == [record()]
    assert result["search_semantics"] == "bounded_snapshot"
    assert (await client.search({"query.intr": "missing"}))["studies"] == []
    assert (await client.search({"query.intr": "ACTIVITY"}))["studies"] == [record()]
    with pytest.raises(RegistryError) as error:
        await client.get_study("NCT00000099")
    assert error.value.code == "not_found"


@pytest.mark.parametrize(
    "labels, expected_match",
    [
        (["Type 2 Diabetes"], True),
        (["Diabetes Mellitus, Type II"], True),
        (["T2DM"], True),
        (["NIDDM"], True),
        (["Type 2 Diabetes Prevention"], True),
        (["Type 1 Diabetes", "Type 2 Diabetes"], True),
        (["Diabetes"], False),
        (["Type 1 Diabetes"], False),
        (["Gestational Diabetes"], False),
        (["Prediabetes"], False),
        (["Obesity"], False),
        (["Without Type 2 Diabetes (T2DM)"], False),
        ([], False),
    ],
)
async def test_snapshot_type2_scope_uses_explicit_labels(
    snapshot, labels, expected_match
):
    manifest_path, path, manifest = snapshot
    source = record()
    source["protocolSection"]["conditionsModule"]["conditions"] = labels
    content = json.dumps(source).encode("utf-8")
    path.write_bytes(content)
    manifest[0]["sha256"] = hashlib.sha256(content).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    client = SnapshotRegistry(manifest_path)
    result = await client.search({"query.cond": "Type 2 Diabetes"})
    assert result["studies"] == ([source] if expected_match else [])
    # A direct lookup still preserves an outside-scope source for inspection.
    assert await client.get_study("NCT00000001") == source


@pytest.mark.parametrize(
    "condition", ["Obesity", "Diabetes", "Type 1 Diabetes", "", None, 7]
)
async def test_snapshot_does_not_silently_ignore_a_different_condition(
    snapshot, condition
):
    with pytest.raises(RegistryError, match="fixed Type 2 Diabetes scope") as error:
        await SnapshotRegistry(snapshot[0]).search({"query.cond": condition})
    assert error.value.code == "invalid_input"

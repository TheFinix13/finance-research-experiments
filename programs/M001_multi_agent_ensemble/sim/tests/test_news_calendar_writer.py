"""Tests for the Phase 6b news calendar writer + backfill CLI.

CI-clean: never touches the network. All Dukascopy interactions in the
CLI smoke test go through an injected stub fetcher.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from programs.M001_multi_agent_ensemble.scripts import (
    backfill_news_calendar as cli,
)
from programs.M001_multi_agent_ensemble.sim.regime.news_calendar_writer import (
    PARSER_VERSION,
    BackfillMetadata,
    ManifestFile,
    _current_git_sha,
    compute_file_sha256,
    events_to_dataframe,
    verify_manifest,
    write_events_partition,
    write_manifest,
)


UTC = timezone.utc


def _canonical_event(**kwargs):
    """Build one canonical event dict, mirroring Dukascopy's normalised
    output.
    """
    row = {
        "timestamp": datetime(2024, 1, 5, 13, 30, tzinfo=UTC),
        "currency": "USD",
        "event": "Non-Farm Employment Change",
        "importance": 3,
        "actual": 216.0,
        "forecast": 170.0,
        "previous": 173.0,
        "unit": "K",
        "source": "DK",
        "source_event_id": "d_42091872",
        "ingested_at_utc": datetime(2026, 7, 3, tzinfo=UTC),
    }
    row.update(kwargs)
    return row


# ---------------------------------------------------------------------------
# events_to_dataframe
# ---------------------------------------------------------------------------

class TestEventsToDataFrame:
    def test_empty_input_returns_empty_schema(self):
        df = events_to_dataframe([])
        assert df.empty
        assert list(df.columns) == [
            "timestamp", "currency", "event", "importance",
            "actual", "forecast", "previous", "unit",
            "source", "source_event_id", "ingested_at_utc",
        ]
        assert str(df["importance"].dtype) == "int8"

    def test_single_row_roundtrip(self):
        df = events_to_dataframe([_canonical_event()])
        assert len(df) == 1
        row = df.iloc[0]
        assert row["currency"] == "USD"
        assert row["importance"] == 3
        assert row["timestamp"] == pd.Timestamp("2024-01-05T13:30:00Z")
        assert row["source"] == "DK"

    def test_out_of_range_importance_dropped_with_warning(self, caplog):
        df = events_to_dataframe([
            _canonical_event(importance=3, source_event_id="a"),
            _canonical_event(importance=7, source_event_id="b"),
        ])
        assert len(df) == 1
        assert df.iloc[0]["source_event_id"] == "a"
        assert any("out-of-range importance" in r.message
                   for r in caplog.records)

    def test_missing_optional_columns_filled_with_nan(self):
        df = events_to_dataframe([{
            "timestamp": datetime(2024, 1, 5, 13, 30, tzinfo=UTC),
            "currency": "USD", "event": "X", "importance": 2,
            "source": "DK", "source_event_id": "s_1",
            "ingested_at_utc": datetime(2026, 7, 3, tzinfo=UTC),
        }])
        row = df.iloc[0]
        assert pd.isna(row["actual"])
        assert pd.isna(row["forecast"])
        assert pd.isna(row["previous"])
        assert pd.isna(row["unit"])

    def test_currency_uppercased(self):
        df = events_to_dataframe([_canonical_event(currency="usd")])
        assert df.iloc[0]["currency"] == "USD"

    def test_source_uppercased(self):
        df = events_to_dataframe([_canonical_event(source="dk")])
        assert df.iloc[0]["source"] == "DK"

    def test_extra_columns_dropped(self):
        row = _canonical_event(extra_key="ignored")
        df = events_to_dataframe([row])
        assert "extra_key" not in df.columns


# ---------------------------------------------------------------------------
# write_events_partition
# ---------------------------------------------------------------------------

class TestWritePartition:
    def test_writes_expected_path(self, tmp_path: Path):
        df = events_to_dataframe([_canonical_event()])
        target = write_events_partition(
            df, root=tmp_path, source="DK", year=2024, currency="USD",
        )
        assert target == tmp_path / "DK" / "2024" / "USD.parquet"
        assert target.exists()
        assert target.stat().st_size > 0

    def test_roundtrip_via_parquet(self, tmp_path: Path):
        df_in = events_to_dataframe([_canonical_event()])
        target = write_events_partition(
            df_in, root=tmp_path, source="DK", year=2024, currency="USD",
        )
        df_out = pd.read_parquet(target)
        # Compare a stable subset -- parquet round-trip is enough that
        # column-by-column equality on canonical fields is verifiable.
        assert df_out.iloc[0]["source_event_id"] == "d_42091872"
        assert df_out.iloc[0]["importance"] == 3

    def test_invalid_source_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="unknown source"):
            write_events_partition(
                events_to_dataframe([_canonical_event()]),
                root=tmp_path, source="Bogus", year=2024, currency="USD",
            )

    def test_invalid_year_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="year"):
            write_events_partition(
                events_to_dataframe([_canonical_event()]),
                root=tmp_path, source="DK", year=1000, currency="USD",
            )

    def test_empty_currency_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="currency"):
            write_events_partition(
                events_to_dataframe([_canonical_event()]),
                root=tmp_path, source="DK", year=2024, currency=" ",
            )

    def test_empty_dataframe_still_writes(self, tmp_path: Path):
        """Empty-parquet writes are important: they let the manifest
        record that the year/currency partition was fetched but had zero
        events, which is different from "we didn't fetch it".
        """
        df = events_to_dataframe([])
        target = write_events_partition(
            df, root=tmp_path, source="DK", year=2024, currency="USD",
        )
        assert target.exists()
        out = pd.read_parquet(target)
        assert out.empty


# ---------------------------------------------------------------------------
# SHA256
# ---------------------------------------------------------------------------

class TestSha256:
    def test_matches_stdlib(self, tmp_path: Path):
        import hashlib as _hashlib
        payload = b"hello, phase 6b"
        f = tmp_path / "a.bin"
        f.write_bytes(payload)
        assert compute_file_sha256(f) == _hashlib.sha256(payload).hexdigest()

    def test_streams_large_files(self, tmp_path: Path):
        # 1 MB file (bigger than default chunk).
        f = tmp_path / "big.bin"
        f.write_bytes(b"A" * 1_000_000)
        got = compute_file_sha256(f, chunk_bytes=8192)
        # Sanity: same file, same hash regardless of chunk size.
        assert got == compute_file_sha256(f, chunk_bytes=1_000_001)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

class TestManifest:
    def _minimal_metadata(self) -> BackfillMetadata:
        return BackfillMetadata(
            source="DK",
            source_url="https://freeserv.dukascopy.com/2.0/index.php?path=events/get_events",
            parser_version=PARSER_VERSION,
            parser_git_sha="deadbeef",
            backfill_start_utc=datetime(2026, 7, 3, 12, 0, tzinfo=UTC),
            backfill_end_utc=datetime(2026, 7, 3, 13, 0, tzinfo=UTC),
            total_events=100,
        )

    def test_writes_expected_manifest_structure(self, tmp_path: Path):
        # Seed a parquet file that the manifest will describe.
        df = events_to_dataframe([_canonical_event()])
        pq = write_events_partition(
            df, root=tmp_path, source="DK", year=2024, currency="USD",
        )
        sha = compute_file_sha256(pq)
        manifest = write_manifest(
            root=tmp_path,
            source="DK",
            files=[ManifestFile(
                path="2024/USD.parquet", sha256=sha,
                n_events=1, year=2024, currency="USD",
            )],
            metadata=self._minimal_metadata(),
            now_utc=datetime(2026, 7, 3, 12, 30, tzinfo=UTC),
        )
        assert manifest == tmp_path / "DK" / "_manifest.json"
        data = json.loads(manifest.read_text())
        assert data["source"] == "DK"
        assert data["file_count"] == 1
        assert data["metadata"]["parser_version"] == PARSER_VERSION
        assert data["metadata"]["parser_git_sha"] == "deadbeef"
        assert data["files"][0]["sha256"] == sha
        assert data["files"][0]["path"] == "2024/USD.parquet"
        assert data["written_at_utc"] == "2026-07-03T12:30:00+00:00"

    def test_files_sorted_by_year_currency(self, tmp_path: Path):
        (tmp_path / "DK" / "2024").mkdir(parents=True)
        (tmp_path / "DK" / "2023").mkdir()
        for y, c in [(2024, "EUR"), (2023, "USD"), (2024, "USD")]:
            df = events_to_dataframe([])
            write_events_partition(
                df, root=tmp_path, source="DK", year=y, currency=c,
            )
        entries = [
            ManifestFile(path=f"{y}/{c}.parquet",
                         sha256="x", n_events=0, year=y, currency=c)
            for y, c in [(2024, "EUR"), (2023, "USD"), (2024, "USD")]
        ]
        manifest = write_manifest(
            root=tmp_path, source="DK", files=entries,
            metadata=self._minimal_metadata(),
        )
        data = json.loads(manifest.read_text())
        got = [(f["year"], f["currency"]) for f in data["files"]]
        assert got == [(2023, "USD"), (2024, "EUR"), (2024, "USD")]


# ---------------------------------------------------------------------------
# verify_manifest
# ---------------------------------------------------------------------------

class TestVerifyManifest:
    def _seed_archive(self, tmp_path: Path) -> Path:
        df = events_to_dataframe([_canonical_event()])
        pq = write_events_partition(
            df, root=tmp_path, source="DK", year=2024, currency="USD",
        )
        sha = compute_file_sha256(pq)
        manifest = write_manifest(
            root=tmp_path, source="DK",
            files=[ManifestFile(
                path="2024/USD.parquet", sha256=sha,
                n_events=1, year=2024, currency="USD",
            )],
            metadata=BackfillMetadata(
                source="DK",
                source_url="https://x",
                parser_version=PARSER_VERSION,
                parser_git_sha=None,
                backfill_start_utc=datetime(2026, 7, 3, tzinfo=UTC),
                backfill_end_utc=datetime(2026, 7, 3, tzinfo=UTC),
                total_events=1,
            ),
        )
        return manifest

    def test_clean_archive_returns_empty_anomalies(self, tmp_path: Path):
        manifest = self._seed_archive(tmp_path)
        assert verify_manifest(manifest) == []

    def test_missing_file_flags_anomaly(self, tmp_path: Path):
        manifest = self._seed_archive(tmp_path)
        (tmp_path / "DK" / "2024" / "USD.parquet").unlink()
        with pytest.raises(FileNotFoundError, match="missing"):
            verify_manifest(manifest, strict=True)
        # Non-strict path returns anomaly + does not raise.
        anomalies = verify_manifest(manifest, strict=False)
        assert any("missing" in a for a in anomalies)

    def test_hash_mismatch_flags_anomaly(self, tmp_path: Path):
        manifest = self._seed_archive(tmp_path)
        pq_path = tmp_path / "DK" / "2024" / "USD.parquet"
        # Corrupt the file so the sha changes.
        pq_path.write_bytes(pq_path.read_bytes() + b"\x00")
        with pytest.raises(ValueError, match="sha256 mismatch"):
            verify_manifest(manifest, strict=True)

    def test_missing_manifest_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="manifest not found"):
            verify_manifest(tmp_path / "does_not_exist.json")


# ---------------------------------------------------------------------------
# Git sha helper
# ---------------------------------------------------------------------------

class TestGitSha:
    def test_returns_string_or_none(self):
        # Best-effort: this test runs inside a git repo so we expect a
        # 40-char hex SHA. If the environment doesn't have git we accept
        # None (helper is defensive by design).
        sha = _current_git_sha()
        if sha is not None:
            assert len(sha) == 40
            int(sha, 16)

    def test_returns_none_when_git_binary_missing(self, monkeypatch):
        # Force the subprocess call to raise FileNotFoundError by
        # replacing subprocess.run with a stub that always raises.
        def _boom(*a, **kw):
            raise FileNotFoundError()

        monkeypatch.setattr(
            "programs.M001_multi_agent_ensemble.sim.regime."
            "news_calendar_writer.subprocess.run",
            _boom,
        )
        assert _current_git_sha() is None


# ---------------------------------------------------------------------------
# Backfill CLI smoke test
# ---------------------------------------------------------------------------

class TestBackfillCli:
    def test_dry_run_writes_manifest_with_empty_parquets(self, tmp_path: Path):
        out = tmp_path / "archive"
        rc = cli.main([
            "--start", "2023-01-01", "--end", "2024-01-01",
            "--currencies", "USD",
            "--sources", "DK", "--out", str(out),
            "--dry-run",
        ])
        assert rc == 0
        manifest = out / "DK" / "_manifest.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text())
        assert data["source"] == "DK"
        # 2023-01-01 to 2024-01-01 -> 1 year * 1 currency = 1 file.
        assert data["file_count"] == 1
        assert data["files"][0]["year"] == 2023
        assert data["files"][0]["currency"] == "USD"
        assert data["files"][0]["n_events"] == 0
        assert data["metadata"]["total_events"] == 0

    def test_stub_fetcher_events_flow_through(self, tmp_path: Path):
        stub_events = [
            _canonical_event(
                timestamp=datetime(2023, 4, 5, 13, 30, tzinfo=UTC),
                source_event_id="d_stub_1",
            ),
        ]
        stub_fetcher = mock.MagicMock(return_value=stub_events)
        manifest = cli.run_backfill(
            start=datetime(2023, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 1, tzinfo=UTC),
            currencies=("USD",),
            source="DK",
            out_root=tmp_path,
            fetcher=stub_fetcher,
        )
        assert manifest.exists()
        stub_fetcher.assert_called_once()
        pq = tmp_path / "DK" / "2023" / "USD.parquet"
        df = pd.read_parquet(pq)
        assert len(df) == 1
        assert df.iloc[0]["source_event_id"] == "d_stub_1"

    def test_dry_run_and_fetcher_mutually_exclusive(self, tmp_path: Path):
        with pytest.raises(ValueError, match="mutually exclusive"):
            cli.run_backfill(
                start=datetime(2023, 1, 1, tzinfo=UTC),
                end=datetime(2024, 1, 1, tzinfo=UTC),
                currencies=("USD",),
                source="DK",
                out_root=tmp_path,
                dry_run=True,
                fetcher=lambda **kw: [],
            )

    def test_unsupported_source_raises(self, tmp_path: Path):
        with pytest.raises(NotImplementedError, match="not wired in Phase 6b"):
            cli.run_backfill(
                start=datetime(2023, 1, 1, tzinfo=UTC),
                end=datetime(2024, 1, 1, tzinfo=UTC),
                currencies=("USD",),
                source="FF",
                out_root=tmp_path,
            )

    def test_end_before_start_raises_in_iter(self):
        with pytest.raises(ValueError, match="strictly after"):
            list(cli._iter_year_currency(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2023, 1, 1, tzinfo=UTC),
                ("USD",),
            ))

    def test_multi_year_multi_currency_iter(self):
        combos = list(cli._iter_year_currency(
            datetime(2023, 6, 1, tzinfo=UTC),
            datetime(2025, 3, 1, tzinfo=UTC),
            ("USD", "EUR"),
        ))
        # 2023 (Jun-Dec), 2024 (Jan-Dec), 2025 (Jan-Mar) x 2 currencies
        # = 6 combos.
        years = sorted({y for y, _, _, _ in combos})
        assert years == [2023, 2024, 2025]
        currencies = sorted({c for _, c, _, _ in combos})
        assert currencies == ["EUR", "USD"]
        assert len(combos) == 6

    def test_cli_main_unsupported_source_returns_nonzero(
        self, tmp_path: Path, caplog,
    ):
        rc = cli.main([
            "--start", "2023-01-01", "--end", "2024-01-01",
            "--currencies", "USD",
            "--sources", "FF", "--out", str(tmp_path / "archive"),
        ])
        assert rc == 2

    def test_manifest_metadata_captures_stats(self, tmp_path: Path):
        stub = mock.MagicMock(return_value=[_canonical_event()])
        cli.run_backfill(
            start=datetime(2023, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 1, tzinfo=UTC),
            currencies=("USD",),
            source="DK",
            out_root=tmp_path,
            fetcher=stub,
        )
        data = json.loads(
            (tmp_path / "DK" / "_manifest.json").read_text(),
        )
        assert data["metadata"]["parser_version"] == PARSER_VERSION
        # parser_git_sha may be None outside a git repo; if present it
        # must be a 40-char hex SHA.
        sha = data["metadata"]["parser_git_sha"]
        if sha is not None:
            assert len(sha) == 40

"""Tests for the Dukascopy freeserv HTTP fetcher (Phase 6a, 2026-07-03).

CI-clean: never touches the network. All HTTP is mocked via the
``transport`` injection point on ``fetch_events``.

Coverage matrix:

1. URL builder produces the exact spec §1.4 shape (epoch-ms, group=news,
   currencies csv, importance normalised).
2. JSONP unwrap accepts both ``cb({...})`` and ``cb({...});`` shapes,
   and gracefully falls back to plain JSON when the wrap is missing.
3. Event normaliser maps DK importance strings + numeric IDs +
   epoch-ms timestamps into the Phase M canonical row.
4. Chunk iterator yields half-open per-day windows.
5. End-to-end ``fetch_events`` with a fake transport returns the
   expected canonical rows, respects the retry budget on 5xx, and
   records stats correctly.
6. Rate limiter enforces the min-interval gap (no real sleep).
7. Adapter default fetcher wire (``DukascopyAdapter()`` with no
   ``fetcher=``) delegates to the fetch module.
"""
from __future__ import annotations

import json
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest

from programs.M001_multi_agent_ensemble.sim.regime import dukascopy_fetch
from programs.M001_multi_agent_ensemble.sim.regime.dukascopy_fetch import (
    DukascopyFetchStats,
    RateLimiter,
    build_dukascopy_url,
    default_dukascopy_fetcher,
    fetch_events,
    iter_chunks,
    normalize_dukascopy_event,
    unwrap_jsonp,
)
from programs.M001_multi_agent_ensemble.sim.regime.news_calendar_sources import (
    DukascopyAdapter,
)


UTC = timezone.utc


# ---------------------------------------------------------------------------
# URL builder
# ---------------------------------------------------------------------------

class TestBuildUrl:
    def test_epoch_ms_conversion(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 2, tzinfo=UTC)
        url = build_dukascopy_url(start, end, ["USD"], importance="high")
        assert "path=events/get_events" in url
        assert f"start={int(start.timestamp() * 1000)}" in url
        assert f"end={int(end.timestamp() * 1000)}" in url
        assert "currencies=USD" in url
        assert "importance=high" in url
        assert "group=news" in url
        assert "jsonp=cb" in url

    def test_currencies_uppercased_and_csv(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 2, tzinfo=UTC)
        url = build_dukascopy_url(start, end, ["usd", " eur", "gbp"])
        assert "currencies=USD%2CEUR%2CGBP" in url  # comma encoded as %2C

    def test_naive_datetime_raises(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            build_dukascopy_url(
                datetime(2024, 1, 1),
                datetime(2024, 1, 2, tzinfo=UTC),
                ["USD"],
            )

    def test_end_before_start_raises(self):
        start = datetime(2024, 1, 2, tzinfo=UTC)
        end = datetime(2024, 1, 1, tzinfo=UTC)
        with pytest.raises(ValueError, match="strictly after"):
            build_dukascopy_url(start, end, ["USD"])

    def test_invalid_importance_raises(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 2, tzinfo=UTC)
        with pytest.raises(ValueError, match="importance"):
            build_dukascopy_url(start, end, ["USD"], importance="massive")

    def test_empty_currencies_raises(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 2, tzinfo=UTC)
        with pytest.raises(ValueError, match="non-empty"):
            build_dukascopy_url(start, end, [])


# ---------------------------------------------------------------------------
# JSONP unwrap
# ---------------------------------------------------------------------------

class TestUnwrapJsonp:
    def test_standard_wrap(self):
        raw = b'cb({"events": [{"id": 1}]})'
        assert unwrap_jsonp(raw) == {"events": [{"id": 1}]}

    def test_trailing_semicolon(self):
        raw = b'cb({"events": [{"id": 1}]});'
        assert unwrap_jsonp(raw) == {"events": [{"id": 1}]}

    def test_whitespace_tolerant(self):
        raw = b'  cb(  {"a": 1}  )  ;  '
        assert unwrap_jsonp(raw) == {"a": 1}

    def test_plain_json_fallback(self):
        raw = b'{"a": 1, "b": [2, 3]}'
        assert unwrap_jsonp(raw) == {"a": 1, "b": [2, 3]}

    def test_bare_list_plain_json_fallback(self):
        raw = b'[{"id": 1}, {"id": 2}]'
        assert unwrap_jsonp(raw) == [{"id": 1}, {"id": 2}]

    def test_callback_drift_warns_but_parses(self, caplog):
        raw = b'jsonp_callback_9dfe32({"ok": true})'
        result = unwrap_jsonp(raw, expected_callback="cb")
        assert result == {"ok": True}
        assert any("JSONP callback drift" in r.message for r in caplog.records)

    def test_empty_body_raises(self):
        with pytest.raises(ValueError, match="empty response"):
            unwrap_jsonp(b"")

    def test_malformed_payload_raises(self):
        with pytest.raises(ValueError, match="failed to parse"):
            unwrap_jsonp(b"cb(not json)")

    def test_neither_jsonp_nor_json_raises(self):
        with pytest.raises(ValueError, match="neither JSONP-wrapped"):
            unwrap_jsonp(b"just some text no braces no callback")


# ---------------------------------------------------------------------------
# Event normalisation
# ---------------------------------------------------------------------------

class TestNormalizeEvent:
    def test_full_row_all_fields(self):
        ingest = datetime(2026, 7, 3, 12, 0, tzinfo=UTC)
        nfp_utc = datetime(2024, 1, 5, 13, 30, tzinfo=UTC)
        raw = {
            "id": "d_42091872",
            "ts": int(nfp_utc.timestamp() * 1000),
            "country": "USD",
            "title": "Non-Farm Employment Change",
            "importance": "high",
            "actual": 216.0,
            "forecast": 170.0,
            "previous": 173.0,
            "unit": "K",
        }
        row = normalize_dukascopy_event(raw, ingested_at_utc=ingest)
        assert row is not None
        assert row["timestamp"] == nfp_utc
        assert row["currency"] == "USD"
        assert row["event"] == "Non-Farm Employment Change"
        assert row["importance"] == 3
        assert row["actual"] == 216.0
        assert row["forecast"] == 170.0
        assert row["previous"] == 173.0
        assert row["unit"] == "K"
        assert row["source"] == "DK"
        assert row["source_event_id"] == "d_42091872"
        assert row["ingested_at_utc"] == ingest

    def test_importance_case_insensitive(self):
        row = normalize_dukascopy_event({
            "id": 1, "ts": 1704456600000,
            "country": "usd", "title": "X", "importance": "Medium",
        })
        assert row["importance"] == 2
        assert row["currency"] == "USD"

    def test_numeric_importance_accepted(self):
        row = normalize_dukascopy_event({
            "id": 1, "ts": 1704456600000,
            "country": "USD", "title": "X", "importance": 1,
        })
        assert row["importance"] == 1

    def test_unrecognised_importance_returns_none(self, caplog):
        row = normalize_dukascopy_event({
            "id": 1, "ts": 1704456600000,
            "country": "USD", "title": "X", "importance": "critical",
        })
        assert row is None
        assert any("unrecognised" in r.message.lower() for r in caplog.records)

    def test_missing_required_returns_none(self):
        # Missing 'title'
        assert normalize_dukascopy_event({
            "id": 1, "ts": 1704456600000,
            "country": "USD", "importance": "high",
        }) is None
        # Missing 'country'
        assert normalize_dukascopy_event({
            "id": 1, "ts": 1704456600000,
            "title": "X", "importance": "high",
        }) is None
        # Missing 'importance'
        assert normalize_dukascopy_event({
            "id": 1, "ts": 1704456600000,
            "country": "USD", "title": "X",
        }) is None

    def test_iso_timestamp_accepted(self):
        row = normalize_dukascopy_event({
            "id": 1, "ts": "2024-01-05T13:30:00Z",
            "country": "USD", "title": "X", "importance": "high",
        })
        assert row["timestamp"] == datetime(2024, 1, 5, 13, 30, tzinfo=UTC)

    def test_missing_timestamp_becomes_none_all_day(self):
        row = normalize_dukascopy_event({
            "id": 1,
            "country": "USD", "title": "Bank Holiday", "importance": "low",
        })
        assert row is not None
        assert row["timestamp"] is None

    def test_stringy_actual_with_unit(self):
        row = normalize_dukascopy_event({
            "id": 1, "ts": 1704456600000,
            "country": "USD", "title": "NFP",
            "importance": "high", "actual": "200K",
        })
        assert row["actual"] == 200.0
        assert row["unit"] == "K"

    def test_none_input_returns_none(self):
        assert normalize_dukascopy_event(None) is None  # type: ignore[arg-type]

    def test_non_dict_input_returns_none(self):
        assert normalize_dukascopy_event(
            "not a dict"  # type: ignore[arg-type]
        ) is None


# ---------------------------------------------------------------------------
# Chunk iterator
# ---------------------------------------------------------------------------

class TestChunkIterator:
    def test_one_day_chunks(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 4, tzinfo=UTC)
        chunks = list(iter_chunks(start, end, chunk_days=1))
        assert len(chunks) == 3
        assert chunks[0] == (start, datetime(2024, 1, 2, tzinfo=UTC))
        assert chunks[-1] == (datetime(2024, 1, 3, tzinfo=UTC), end)

    def test_multi_day_chunks(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 10, tzinfo=UTC)
        chunks = list(iter_chunks(start, end, chunk_days=3))
        assert len(chunks) == 3
        assert chunks[0] == (start, datetime(2024, 1, 4, tzinfo=UTC))
        assert chunks[1] == (
            datetime(2024, 1, 4, tzinfo=UTC),
            datetime(2024, 1, 7, tzinfo=UTC),
        )
        assert chunks[2] == (
            datetime(2024, 1, 7, tzinfo=UTC),
            datetime(2024, 1, 10, tzinfo=UTC),
        )

    def test_last_chunk_truncates_to_end(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 5, tzinfo=UTC)
        chunks = list(iter_chunks(start, end, chunk_days=3))
        assert chunks[-1] == (
            datetime(2024, 1, 4, tzinfo=UTC),
            datetime(2024, 1, 5, tzinfo=UTC),
        )

    def test_invalid_chunk_days_raises(self):
        with pytest.raises(ValueError):
            list(iter_chunks(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 2, tzinfo=UTC),
                chunk_days=0,
            ))


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def test_no_sleep_on_first_call(self):
        sleeps: list[float] = []
        now = [0.0]
        limiter = RateLimiter(
            min_interval_sec=0.5,
            time_source=lambda: now[0],
            sleep_fn=sleeps.append,
        )
        limiter.wait()
        assert sleeps == []

    def test_sleeps_for_the_deficit(self):
        sleeps: list[float] = []
        now = [0.0]

        def _sleep(sec: float) -> None:
            sleeps.append(sec)
            now[0] += sec

        limiter = RateLimiter(
            min_interval_sec=0.5,
            time_source=lambda: now[0],
            sleep_fn=_sleep,
        )
        limiter.wait()
        # Second call 0.2s later -> should sleep for 0.3s.
        now[0] = 0.2
        limiter.wait()
        assert len(sleeps) == 1
        assert abs(sleeps[0] - 0.3) < 1e-9

    def test_no_sleep_when_gap_already_large(self):
        sleeps: list[float] = []
        now = [0.0]

        def _sleep(sec: float) -> None:
            sleeps.append(sec)
            now[0] += sec

        limiter = RateLimiter(
            min_interval_sec=0.5,
            time_source=lambda: now[0],
            sleep_fn=_sleep,
        )
        limiter.wait()
        now[0] = 10.0  # 10s later, well beyond gap.
        limiter.wait()
        assert sleeps == []


# ---------------------------------------------------------------------------
# Fake transports for end-to-end tests
# ---------------------------------------------------------------------------

def _fake_ok_transport(response_by_url: dict[str, bytes]):
    """Return a transport that maps URL substrings to canned response bytes.

    ``response_by_url`` is matched by substring so tests only need to
    specify the epoch-ms fragment or the currency filter.
    """
    def _transport(url: str, *, headers: dict[str, str], timeout: float):
        for key, body in response_by_url.items():
            if key in url:
                return body
        raise urllib.error.HTTPError(
            url=url, code=404, msg="no fixture matches URL", hdrs={}, fp=None,
        )
    return _transport


def _fake_flaky_transport(
    fail_codes: list[int],
    then_response: bytes,
):
    """Return a transport that raises HTTPErrors from ``fail_codes`` in
    order, then finally returns ``then_response`` (or reraises the last
    error if the list is exhausted).
    """
    remaining = list(fail_codes)

    def _transport(url: str, *, headers: dict[str, str], timeout: float):
        if remaining:
            code = remaining.pop(0)
            raise urllib.error.HTTPError(
                url=url, code=code, msg=f"synthetic {code}",
                hdrs={}, fp=None,
            )
        return then_response
    return _transport


# ---------------------------------------------------------------------------
# fetch_events end-to-end
# ---------------------------------------------------------------------------

class TestFetchEventsEndToEnd:
    def _payload_one_event(self) -> bytes:
        payload = {
            "events": [{
                "id": "d_1",
                "ts": 1704456600000,
                "country": "USD",
                "title": "Non-Farm Employment Change",
                "importance": "high",
                "actual": 216.0,
                "forecast": 170.0,
                "previous": 173.0,
                "unit": "K",
            }],
        }
        return f'cb({json.dumps(payload)});'.encode("utf-8")

    def _no_op_limiter(self) -> RateLimiter:
        return RateLimiter(sleep_fn=lambda _s: None, time_source=lambda: 0.0)

    def test_single_chunk_single_event(self):
        transport = _fake_ok_transport({
            "": self._payload_one_event(),   # match any URL
        })
        stats = DukascopyFetchStats()
        events = fetch_events(
            datetime(2024, 1, 5, tzinfo=UTC),
            datetime(2024, 1, 6, tzinfo=UTC),
            ["USD"],
            transport=transport,
            rate_limiter=self._no_op_limiter(),
            stats=stats,
        )
        assert len(events) == 1
        assert events[0]["source"] == "DK"
        assert events[0]["currency"] == "USD"
        assert events[0]["importance"] == 3
        assert stats.n_events == 1
        assert stats.n_chunks == 1
        assert stats.n_retries == 0

    def test_multi_chunk_accumulates(self):
        transport = _fake_ok_transport({
            "": self._payload_one_event(),
        })
        events = fetch_events(
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 4, tzinfo=UTC),
            ["USD"],
            transport=transport,
            rate_limiter=self._no_op_limiter(),
            chunk_days=1,
        )
        # 3 chunks x 1 event each.
        assert len(events) == 3

    def test_bare_list_payload_accepted(self):
        """DK sometimes returns a bare JSON array instead of the usual
        ``{"events": [...]}`` envelope. The fetcher must handle both.
        """
        single_event = {
            "id": "d_1",
            "ts": 1704456600000,
            "country": "USD",
            "title": "X",
            "importance": "high",
        }
        raw = f'cb([{json.dumps(single_event)}]);'.encode("utf-8")
        transport = _fake_ok_transport({"": raw})
        events = fetch_events(
            datetime(2024, 1, 5, tzinfo=UTC),
            datetime(2024, 1, 6, tzinfo=UTC),
            ["USD"],
            transport=transport,
            rate_limiter=self._no_op_limiter(),
        )
        assert len(events) == 1
        assert events[0]["source_event_id"] == "d_1"

    def test_5xx_retries_then_success(self):
        transport = _fake_flaky_transport(
            fail_codes=[503, 503], then_response=self._payload_one_event(),
        )
        stats = DukascopyFetchStats()
        events = fetch_events(
            datetime(2024, 1, 5, tzinfo=UTC),
            datetime(2024, 1, 6, tzinfo=UTC),
            ["USD"],
            transport=transport,
            rate_limiter=self._no_op_limiter(),
            max_retries=3,
            retry_backoff_base=1.0,
            stats=stats,
        )
        assert len(events) == 1
        assert stats.n_retries == 2

    def test_5xx_exhausts_retries_skips_chunk(self, caplog):
        transport = _fake_flaky_transport(
            fail_codes=[503, 503, 503, 503, 503, 503],
            then_response=self._payload_one_event(),
        )
        stats = DukascopyFetchStats()
        events = fetch_events(
            datetime(2024, 1, 5, tzinfo=UTC),
            datetime(2024, 1, 6, tzinfo=UTC),
            ["USD"],
            transport=transport,
            rate_limiter=self._no_op_limiter(),
            max_retries=2,
            retry_backoff_base=1.0,
            stats=stats,
        )
        assert events == []
        assert stats.n_transport_errors == 1

    def test_4xx_not_retried_except_408_425_429(self):
        # 404 = give up immediately, no retries.
        transport = _fake_flaky_transport(
            fail_codes=[404, 404, 404, 404, 404, 404],
            then_response=self._payload_one_event(),
        )
        stats = DukascopyFetchStats()
        events = fetch_events(
            datetime(2024, 1, 5, tzinfo=UTC),
            datetime(2024, 1, 6, tzinfo=UTC),
            ["USD"],
            transport=transport,
            rate_limiter=self._no_op_limiter(),
            max_retries=3,
            retry_backoff_base=1.0,
            stats=stats,
        )
        assert events == []
        assert stats.n_retries == 0
        assert stats.n_transport_errors == 1

    def test_429_is_retried(self):
        transport = _fake_flaky_transport(
            fail_codes=[429], then_response=self._payload_one_event(),
        )
        stats = DukascopyFetchStats()
        events = fetch_events(
            datetime(2024, 1, 5, tzinfo=UTC),
            datetime(2024, 1, 6, tzinfo=UTC),
            ["USD"],
            transport=transport,
            rate_limiter=self._no_op_limiter(),
            max_retries=2,
            retry_backoff_base=1.0,
            stats=stats,
        )
        assert len(events) == 1
        assert stats.n_retries == 1

    def test_malformed_body_records_transport_error(self):
        transport = _fake_ok_transport({"": b"totally not JSONP"})
        stats = DukascopyFetchStats()
        events = fetch_events(
            datetime(2024, 1, 5, tzinfo=UTC),
            datetime(2024, 1, 6, tzinfo=UTC),
            ["USD"],
            transport=transport,
            rate_limiter=self._no_op_limiter(),
            stats=stats,
        )
        assert events == []
        assert stats.n_transport_errors == 1

    def test_drop_unrecognised_importance_stats_correct(self):
        payload = {
            "events": [
                {
                    "id": "d_1", "ts": 1704456600000, "country": "USD",
                    "title": "X", "importance": "high",
                },
                {
                    "id": "d_2", "ts": 1704456600000, "country": "USD",
                    "title": "Y", "importance": "critical",  # dropped
                },
            ],
        }
        transport = _fake_ok_transport({"": f'cb({json.dumps(payload)})'
                                        .encode("utf-8")})
        stats = DukascopyFetchStats()
        events = fetch_events(
            datetime(2024, 1, 5, tzinfo=UTC),
            datetime(2024, 1, 6, tzinfo=UTC),
            ["USD"],
            transport=transport,
            rate_limiter=self._no_op_limiter(),
            stats=stats,
        )
        assert len(events) == 1
        assert stats.n_events == 1
        assert stats.n_dropped == 1


# ---------------------------------------------------------------------------
# DukascopyAdapter integration
# ---------------------------------------------------------------------------

class TestDukascopyAdapterWire:
    def test_adapter_defaults_to_real_fetcher_lazy_import(self):
        """When ``DukascopyAdapter()`` is constructed with no ``fetcher=``,
        ``.fetch()`` should delegate to
        ``dukascopy_fetch.default_dukascopy_fetcher``. We stub the
        default fetcher to avoid a real network call.
        """
        with mock.patch.object(
            dukascopy_fetch,
            "default_dukascopy_fetcher",
            return_value=[{"tag": "mocked"}],
        ) as m:
            adapter = DukascopyAdapter()  # no fetcher kwarg
            out = adapter.fetch(
                datetime(2024, 1, 5, tzinfo=UTC),
                datetime(2024, 1, 6, tzinfo=UTC),
                ["USD"],
            )
            m.assert_called_once()
            assert out == [{"tag": "mocked"}]

    def test_adapter_uses_injected_fetcher_directly(self):
        """When ``fetcher=`` is provided, the real fetcher must NOT be
        called -- injected stub takes precedence.
        """
        stub = mock.MagicMock(return_value=[{"tag": "stub"}])
        adapter = DukascopyAdapter(fetcher=stub)
        with mock.patch.object(
            dukascopy_fetch, "default_dukascopy_fetcher",
        ) as real:
            out = adapter.fetch(
                datetime(2024, 1, 5, tzinfo=UTC),
                datetime(2024, 1, 6, tzinfo=UTC),
                ["USD"],
            )
        stub.assert_called_once_with(
            start=datetime(2024, 1, 5, tzinfo=UTC),
            end=datetime(2024, 1, 6, tzinfo=UTC),
            currencies=("USD",),
        )
        real.assert_not_called()
        assert out == [{"tag": "stub"}]


# ---------------------------------------------------------------------------
# default_dukascopy_fetcher wrapper
# ---------------------------------------------------------------------------

def test_default_wrapper_forwards_kwargs():
    """The zero-config wrapper must forward its kwargs to
    ``fetch_events`` unchanged.
    """
    with mock.patch.object(
        dukascopy_fetch, "fetch_events", return_value=[{"stub": True}],
    ) as m:
        out = default_dukascopy_fetcher(
            start=datetime(2024, 1, 5, tzinfo=UTC),
            end=datetime(2024, 1, 6, tzinfo=UTC),
            currencies=["USD"],
        )
    m.assert_called_once_with(
        datetime(2024, 1, 5, tzinfo=UTC),
        datetime(2024, 1, 6, tzinfo=UTC),
        ["USD"],
    )
    assert out == [{"stub": True}]

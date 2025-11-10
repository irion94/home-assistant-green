# Privacy & Data Compliance

## Overview

Strava Coach is designed with **privacy-first** principles and strict compliance with Strava's Terms of Service regarding AI and data usage.

## Strava Terms of Service Compliance

### What We DO

✅ **Store activities locally**: Activities are cached in a local SQLite database within your Home Assistant instance
✅ **Compute metrics**: Calculate training metrics (ATL/CTL/TSB) from your activity data
✅ **Display to you only**: All data is visible only to authenticated Home Assistant users
✅ **Use aggregated metrics**: LLM mode receives only computed metrics (readiness, TSB, etc.), never raw Strava data

### What We DO NOT Do

❌ **Train AI models**: Your Strava data is NEVER used to train AI models (violates Strava ToS)
❌ **Share raw data**: Raw activity data (names, lat/lng, streams, HR/power) is never sent to external APIs
❌ **Sell or redistribute**: Your data stays on your Home Assistant instance
❌ **Display publicly**: No data is exposed outside your Home Assistant instance

## LLM Integration (Optional)

### Aggregates-Only Mode (Default: ON)

When LLM suggestions are enabled, the integration enforces **strict filtering**:

#### ✅ ALLOWED Fields (Aggregates)
- `readiness` (0-100 score)
- `atl` (7-day average training load)
- `ctl` (42-day average training load)
- `tsb` (form metric)
- `monotony` (training variety index)
- `rest_days` (consecutive rest days)
- `recent_load_7d` (7-day cumulative load)
- `date`, `day_of_week`

#### ❌ FORBIDDEN Fields (Raw Strava Data)
- Activity IDs, athlete IDs, names
- GPS coordinates (lat/lng), polylines, routes
- Heart rate, power, speed streams
- Elevation profiles, distance, duration
- Any personally identifiable information

### Guardrails

The LLM adapter includes **runtime validation**:

```python
# custom_components/strava_coach/llm/adapter.py
def _filter_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
    """Filter metrics to ensure only aggregates are included."""
    for key in metrics.keys():
        if key in FORBIDDEN_FIELDS:
            if self.aggregates_only:
                raise ValueError(f"Forbidden field '{key}' detected.")
```

If a forbidden field is detected, the LLM request **fails immediately** with an error.

### Tests

See `tests/test_llm_guardrails.py` for comprehensive validation tests ensuring:
- Only allowed fields pass filtering
- Forbidden fields raise exceptions
- Empty metrics are handled safely
- Edge cases are covered

## Data Storage

### Local Database (SQLite)

All data is stored in `/config/strava_coach.db`:

**`activities` table**: Minimal activity data (ID, date, sport, duration, training load)
**`daily_metrics` table**: Computed metrics (ATL, CTL, TSB, readiness)
**`sync_state` table**: Sync timestamps and metadata

### No Cloud Storage

Strava Coach does **not** send data to any cloud service except:
- **Strava API**: OAuth authentication and activity fetch (required)
- **OpenAI API** (if LLM enabled): Aggregated metrics only (see above)

### Data Retention

- Activities: Configurable history window (default 42 days)
- Metrics: Retained indefinitely (aggregates only, safe to keep)
- Sync state: Latest sync metadata only

## User Control

### Opt-In LLM

- LLM suggestions are **disabled by default**
- Requires explicit user action to enable
- Requires manual entry of OpenAI API key
- Can be disabled at any time via integration options

### Opt-In Strava Sync

- Integration requires explicit OAuth authorization
- User can revoke access via Strava settings at any time
- Uninstalling the integration removes all local data

### Data Deletion

To delete all Strava Coach data:

1. Remove the integration: Settings → Devices & Services → Strava Coach → Delete
2. Delete database file: `/config/strava_coach.db`
3. Revoke Strava API access: Strava → Settings → My Apps → Revoke

## Compliance Summary

| Requirement | Status |
|-------------|--------|
| Strava ToS: No AI training | ✅ Compliant |
| GDPR: User data control | ✅ Compliant |
| GDPR: Right to deletion | ✅ Supported |
| GDPR: Data minimization | ✅ Only required fields stored |
| Privacy: Local storage only | ✅ SQLite in HA config |
| Privacy: Aggregates-only LLM | ✅ Enforced by default |

## Questions?

If you have privacy concerns or questions:
- Open an issue: [GitHub Issues](https://github.com/yourusername/ha-strava-coach/issues)
- Review the code: All filtering logic is in `llm/adapter.py`
- Run tests: `make test` includes guardrail validation

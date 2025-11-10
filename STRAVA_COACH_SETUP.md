# Strava Coach Setup Guide

## Step 1: Get Strava API Credentials

1. Go to https://www.strava.com/settings/api
2. Click **"Create Application"**
3. Fill in:
   - **Application Name**: Home Assistant Strava Coach
   - **Category**: Training
   - **Website**: Your HA URL or GitHub repo
   - **Authorization Callback Domain**: Your HA external domain
     - Example: `your-ha.duckdns.org` (without `https://` or path)
     - For Nabu Casa: `abcd1234.ui.nabu.casa`
4. Accept Strava API Agreement
5. Click **"Create"**
6. Note your:
   - **Client ID** (numbers)
   - **Client Secret** (long alphanumeric string)

## Step 2: Add Credentials to Home Assistant

### Option A: Using secrets.yaml (Recommended)

1. **Edit `config/secrets.yaml`** (create if doesn't exist):
   ```yaml
   strava_client_id: "123456"
   strava_client_secret: "abc123def456..."
   ```

2. **Edit `config/configuration.yaml`**, add:
   ```yaml
   strava_coach:
     client_id: !secret strava_client_id
     client_secret: !secret strava_client_secret
   ```

### Option B: Direct in configuration.yaml (Not Recommended)

**Edit `config/configuration.yaml`**, add:
```yaml
strava_coach:
  client_id: "123456"
  client_secret: "abc123def456..."
```

## Step 3: Restart Home Assistant

From Home Assistant:
- Settings → System → Restart

Or via SSH:
```bash
ha core restart
```

Or via Docker:
```bash
docker restart homeassistant
```

## Step 4: Add Strava Coach Integration

1. Go to **Settings → Devices & Services**
2. Click **"Add Integration"**
3. Search for **"Strava Coach"**
4. Click on it
5. You'll be redirected to Strava to authorize
6. Click **"Authorize"** on Strava
7. Configure your preferences:
   - Daily sync time (default 07:00)
   - History window (default 42 days)
   - (Optional) LLM settings

## Step 5: Verify Setup

Check entities are created:
- `sensor.strava_coach_readiness` (0-100%)
- `sensor.strava_coach_fatigue` (ATL)
- `sensor.strava_coach_form` (TSB)
- `sensor.strava_coach_today_suggestion`

## Step 6: Set Up Morning Notifications (Optional)

Copy from `ha-strava-coach/example_automation.yaml` and customize:

```yaml
automation:
  - alias: "Strava Coach: Morning Training Suggestion"
    trigger:
      - platform: time
        at: "07:30:00"
    action:
      - service: notify.mobile_app_YOUR_DEVICE
        data:
          title: "🚴 Today's Training"
          message: >
            {{ states('sensor.strava_coach_today_suggestion') }}

            {{ state_attr('sensor.strava_coach_today_suggestion', 'rationale_short') }}

            📊 Readiness: {{ states('sensor.strava_coach_readiness') }}%
```

## Troubleshooting

### "missing_configuration" Error
- Ensure credentials are in `configuration.yaml` or `secrets.yaml`
- Restart Home Assistant after adding configuration
- Check `configuration.yaml` syntax with: Settings → System → Logs

### Integration Not Appearing
- Verify files exist in `/config/custom_components/strava_coach/`
- Check Home Assistant logs for errors
- Ensure Home Assistant version is 2024.1.0+

### OAuth Redirect Error
- Verify **Authorization Callback Domain** in Strava matches your HA domain
- Domain should be just the hostname (no `https://` or path)
- Example: `your-ha.duckdns.org` NOT `https://your-ha.duckdns.org/`

### No Activities Synced
- Check Strava authorization was successful
- Verify history window includes recent activities
- Manually trigger sync: `strava_coach.sync_now` service

## Getting Help

- Check logs: Settings → System → Logs (filter by "strava")
- Documentation: `ha-strava-coach/docs/README.md`
- Privacy policy: `ha-strava-coach/docs/PRIVACY.md`
- GitHub issues: https://github.com/yourusername/ha-strava-coach/issues

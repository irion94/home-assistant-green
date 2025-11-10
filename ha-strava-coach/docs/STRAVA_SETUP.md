# Strava API Application Setup

This guide shows you how to create a Strava API application to use with Strava Coach.

## Prerequisites

- A Strava account
- Access to your Home Assistant instance's external URL (for OAuth callback)

## Step 1: Create Strava API Application

1. Go to [Strava API Settings](https://www.strava.com/settings/api)

2. Click **"Create App"** or **"My API Application"**

3. Fill in the application details:
   - **Application Name**: `Home Assistant Strava Coach` (or your preferred name)
   - **Category**: Choose appropriate category (e.g., "Training")
   - **Club**: Leave blank (optional)
   - **Website**: Your Home Assistant URL or GitHub repo
   - **Application Description**: Brief description of your usage
   - **Authorization Callback Domain**: **IMPORTANT**
     ```
     your-ha-instance.duckdns.org
     ```
     or your Home Assistant's public domain (without `https://` or path)

4. Accept Strava API Agreement

5. Click **"Create"**

## Step 2: Get Client Credentials

After creating the app, you'll see:

- **Client ID**: A numeric ID (e.g., `123456`)
- **Client Secret**: A long alphanumeric string (e.g., `abc123def456...`)

**⚠️ Keep your Client Secret private!** Do not share it publicly.

## Step 3: Configure in Home Assistant

### Method 1: Via Application Credentials (Recommended)

1. In Home Assistant, go to: **Settings** → **Devices & Services** → **Application Credentials**

2. Click **"Add Application Credential"**

3. Select **"Strava Coach"**

4. Enter:
   - **Client ID**: Your Strava Client ID
   - **Client Secret**: Your Strava Client Secret

5. Click **"Create"**

### Method 2: Via Integration Setup

When adding the Strava Coach integration, you'll be prompted to enter:
- Client ID
- Client Secret

## Step 4: Authorize OAuth

1. Go to **Settings** → **Devices & Services** → **Add Integration**

2. Search for **"Strava Coach"**

3. Click **"Configure"**

4. You'll be redirected to Strava to authorize access

5. Click **"Authorize"** on Strava

6. You'll be redirected back to Home Assistant

7. Complete the setup with your preferences:
   - Daily sync time
   - History window
   - (Optional) LLM configuration

## Callback URL Details

The OAuth callback URL must match the pattern:
```
https://your-ha-instance.duckdns.org/auth/external/callback
```

Common setups:

### Nabu Casa
- Callback domain: `abcdef1234.ui.nabu.casa`
- Full URL: `https://abcdef1234.ui.nabu.casa/auth/external/callback`

### DuckDNS
- Callback domain: `your-ha.duckdns.org`
- Full URL: `https://your-ha.duckdns.org/auth/external/callback`

### Custom Domain
- Callback domain: `homeassistant.yourdomain.com`
- Full URL: `https://homeassistant.yourdomain.com/auth/external/callback`

## Troubleshooting

### "Redirect URI mismatch" error

**Cause**: Authorization Callback Domain doesn't match your HA URL

**Fix**:
1. Check your HA external URL: **Settings** → **System** → **Network**
2. Update Strava app settings with the correct callback domain
3. Wait a few minutes for changes to propagate
4. Try authorization again

### "Invalid client" error

**Cause**: Client ID or Secret is incorrect

**Fix**:
1. Double-check Client ID and Secret from Strava API settings
2. Re-enter credentials in Home Assistant
3. Ensure no extra spaces or characters

### "Access denied" error

**Cause**: User declined authorization or app permissions issue

**Fix**:
1. Try authorization again and click "Authorize" on Strava
2. Verify your Strava app has required scopes:
   - `read`
   - `activity:read_all`

## Rate Limits

Strava API has rate limits:
- **15-minute limit**: 100 requests
- **Daily limit**: 1000 requests

Strava Coach is designed to stay well below these limits with:
- Efficient caching
- Configurable sync intervals
- Rate limit tracking and backoff

## Revoking Access

To revoke Strava Coach access:

1. Go to [Strava Settings → My Apps](https://www.strava.com/settings/apps)
2. Find "Home Assistant Strava Coach" (or your app name)
3. Click **"Revoke Access"**

To revoke the API application entirely:

1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Find your application
3. Click **"Delete Application"** (if needed)

## Additional Resources

- [Strava API Documentation](https://developers.strava.com/docs/getting-started/)
- [Strava Rate Limits](https://developers.strava.com/docs/rate-limits/)
- [Home Assistant OAuth Setup](https://www.home-assistant.io/integrations/application_credentials/)

# Development Workflow for Strava Coach

## Overview

This integration is developed in the `ha-strava-coach/` directory and deployed to the Home Assistant `config/custom_components/` directory.

## Why Not Symlink?

Since Home Assistant runs in a container/OS environment, it can't access symlinks pointing to paths outside the mounted config directory. Therefore, we **copy** the integration files instead.

## Development Workflow

### 1. Make Changes to Integration Code

Edit files in:
```
ha-strava-coach/custom_components/strava_coach/
```

### 2. Sync Changes to Home Assistant

Run the sync script:
```bash
./scripts/sync_strava_coach.sh
```

Or manually:
```bash
rsync -av --delete \
  --exclude='__pycache__' \
  ha-strava-coach/custom_components/strava_coach/ \
  config/custom_components/strava_coach/
```

### 3. Restart Home Assistant

- **Via UI**: Settings → System → Restart
- **Via Docker**: `docker restart homeassistant`
- **Via SSH**: `ha core restart`

### 4. Test Changes

- Check logs: Settings → System → Logs
- Test integration: Settings → Devices & Services

## Quick Development Commands

```bash
# From ha-enterprise-starter root directory:

# 1. Sync integration files
./scripts/sync_strava_coach.sh

# 2. Restart HA (if using Docker)
docker restart homeassistant

# 3. Check HA logs
docker logs -f homeassistant | grep -i strava

# 4. Run tests
cd ha-strava-coach
make test

# 5. Lint code
cd ha-strava-coach
make lint
```

## File Structure

```
ha-enterprise-starter/
├── ha-strava-coach/                    # Development directory (source of truth)
│   └── custom_components/strava_coach/ # Integration source code
│
├── config/                             # Home Assistant config (mounted in container)
│   └── custom_components/strava_coach/ # Deployed integration (synced copy)
│
└── scripts/
    └── sync_strava_coach.sh            # Sync script
```

## Automated Sync on File Change (Optional)

To automatically sync on file changes, use `fswatch` (macOS) or `inotify` (Linux):

### macOS with fswatch:
```bash
# Install fswatch
brew install fswatch

# Watch for changes and auto-sync
fswatch -o ha-strava-coach/custom_components/strava_coach/ | \
  xargs -n1 -I{} ./scripts/sync_strava_coach.sh
```

### Linux with inotifywait:
```bash
# Install inotify-tools
sudo apt-get install inotify-tools

# Watch for changes and auto-sync
while inotifywait -r -e modify,create,delete ha-strava-coach/custom_components/strava_coach/; do
  ./scripts/sync_strava_coach.sh
done
```

## Deployment to Production

For production deployment, use one of these methods:

### Option 1: HACS (Recommended)
1. Create a GitHub repository
2. Add `hacs.json` (already included)
3. Add repository to HACS custom repositories
4. Install via HACS

### Option 2: Manual Installation
```bash
# Copy to any Home Assistant instance
scp -r ha-strava-coach/custom_components/strava_coach \
  user@homeassistant:/config/custom_components/
```

### Option 3: Git Pull
```bash
# On the HA host/container
cd /config/custom_components
git clone https://github.com/yourusername/ha-strava-coach.git strava_coach_repo
ln -s strava_coach_repo/custom_components/strava_coach strava_coach
```

## Testing Before Sync

Always run tests before syncing:
```bash
cd ha-strava-coach
make test
make lint
```

## Troubleshooting

### Integration Not Appearing
1. Verify files were synced: `ls config/custom_components/strava_coach/`
2. Check HA logs: Settings → System → Logs
3. Restart Home Assistant
4. Check manifest.json is valid: `cat config/custom_components/strava_coach/manifest.json`

### Changes Not Taking Effect
1. Ensure you ran sync script
2. Clear Python cache: `rm -rf config/custom_components/strava_coach/__pycache__`
3. Restart Home Assistant (config reload may not be enough)

### Syntax Errors
```bash
# Check syntax before syncing
cd ha-strava-coach
python3 -m py_compile custom_components/strava_coach/*.py
```

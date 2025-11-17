# ADR 003: Git-Based Configuration Management

## Status

**Accepted** - November 2024

## Context

Home Assistant configurations can be managed through:
- Manual editing via SSH
- UI-based configuration
- Git-based version control
- Backup/restore systems

We need a deployment strategy that provides version control, collaboration, rollback capability, and CI/CD automation while supporting UI-managed configurations.

### Alternatives Considered

1. **Manual SSH Editing**
   - Pros: Direct access, immediate changes
   - Cons: No version control, no collaboration, no rollback, error-prone

2. **UI-Only Configuration**
   - Pros: User-friendly, visual interface
   - Cons: Limited version control, hard to collaborate, difficult rollback

3. **Git + Manual Deployment**
   - Pros: Version control, collaboration
   - Cons: Manual effort, no CI validation, deployment errors

4. **GitOps with Automated Deployment** ✅
   - Pros: Full version control, CI/CD automation, validation, rollback
   - Cons: Setup complexity, requires infrastructure

## Decision

We will use a **GitOps approach** where:
1. All configuration is stored in Git
2. Changes are deployed automatically via CI/CD
3. UI-managed changes are synced back to Git
4. Pre-deployment validation prevents breaking changes
5. Automated rollback available for failures

### Implementation

```yaml
# Deployment Flow
1. Edit configuration locally or via HA UI
2. If UI edit: Run ./scripts/pull_gui_changes.sh
3. Commit and push to repository
4. CI validates configuration
5. CI deploys to Home Assistant
6. Health checks verify deployment
7. Notifications sent on success/failure
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
- Validate secrets references
- Validate HA configuration (Docker)
- Run tests
- Create config snapshot

# .github/workflows/deploy-ssh-tailscale.yml
- Check for GUI-managed drift
- Deploy via SSH (Tailscale)
- Validate deployed config
- Restart Home Assistant
- Health check (5-minute timeout)
- Send notifications
```

## Consequences

### Positive

✅ **Version Control**: Full history of all configuration changes
✅ **Collaboration**: Multiple contributors via pull requests
✅ **Validation**: CI prevents breaking changes from being deployed
✅ **Rollback**: Easy revert to previous working state
✅ **Audit Trail**: Who changed what and when
✅ **Disaster Recovery**: Repository serves as backup
✅ **Testing**: Test changes before deployment
✅ **Documentation**: Commit messages document intent
✅ **Automation**: No manual deployment steps

### Negative

❌ **Complexity**: Requires Git knowledge
❌ **Delay**: Changes not immediate (CI takes time)
❌ **Sync Required**: UI changes must be synced manually
❌ **Infrastructure**: Requires GitHub Actions, secrets management

### Mitigations

- **Git Hooks**: Automatic sync before push (optional)
- **Drift Detection**: CI checks for unsync UI changes
- **Fast CI**: Optimized with Docker caching (~2-3 min)
- **Documentation**: Clear guides for contributors
- **Emergency Access**: Direct SSH still available for emergencies

## Workflow Patterns

### Developer Workflow

```bash
# 1. Make changes locally
vim config/packages/mqtt.yaml

# 2. Test locally (optional)
docker run --rm -v "$PWD/config":/config \
  ghcr.io/home-assistant/home-assistant:2024.11.3 \
  python -m homeassistant --script check_config --config /config

# 3. Commit and push
git add config/packages/mqtt.yaml
git commit -m "config(mqtt): add new sensor"
git push

# 4. CI automatically validates and deploys
```

### UI Configuration Workflow

```bash
# 1. Make changes in HA UI (automations, dashboards, etc.)

# 2. Sync changes back to repository
./scripts/pull_gui_changes.sh

# 3. Review and commit
git diff  # Review changes
git add config/automations.yaml
git commit -m "config(automation): add motion light"
git push

# 4. CI deploys (no actual change to HA, just syncs repo)
```

## Drift Prevention

**Pre-push Hook** (optional):
```bash
# .githooks/pre-push
# Syncs HA UI changes before allowing push
# Prevents drift between HA and repository
```

**CI Drift Check**:
```yaml
# In deploy-ssh-tailscale.yml
- name: Sync-check GUI changes on HA (abort on drift)
  run: |
    bash scripts/pull_gui_changes.sh || true
    if ! git diff --quiet; then
      echo "::error::Detected GUI-managed changes"
      exit 1
    fi
```

## Related

- See: .github/workflows/ci.yml for validation pipeline
- See: .github/workflows/deploy-ssh-tailscale.yml for deployment
- See: .github/workflows/rollback.yml for rollback process
- See: scripts/pull_gui_changes.sh for UI sync
- See: CONTRIBUTING.md for developer workflow

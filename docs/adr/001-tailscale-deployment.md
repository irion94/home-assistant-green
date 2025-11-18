# ADR 001: Use Tailscale for Secure Deployment

## Status

**Accepted** - November 2024

## Context

Home Assistant runs on a local network (Home Assistant Green/OS) without direct internet exposure. We need a secure way to deploy configuration changes from GitHub Actions runners to the Home Assistant instance without:

- Exposing SSH ports to the internet
- Setting up complex port forwarding
- Managing VPN infrastructure ourselves
- Compromising security

### Alternatives Considered

1. **Webhook Deployment (Git Pull Add-on)**
   - Pros: Simple, no network access needed, built into HA
   - Cons: Limited control, no health verification, can't run remote commands

2. **Direct SSH with Port Forwarding**
   - Pros: Simple, direct connection
   - Cons: Security risk (exposed SSH), requires router configuration, not portable

3. **WireGuard VPN**
   - Pros: Secure, fast, widely used
   - Cons: Manual setup, key management, infrastructure maintenance

4. **Tailscale VPN** ✅
   - Pros: Zero-config, secure, NAT traversal, OAuth-based, no infrastructure
   - Cons: Third-party dependency, requires account

## Decision

We will use **Tailscale** as the primary deployment mechanism, with webhook deployment as a fallback option.

### Implementation

```yaml
# .github/workflows/deploy-ssh-tailscale.yml
- name: Connect to Tailscale
  uses: tailscale/github-action@v2
  with:
    oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}
    oauth-secret: ${{ secrets.TS_OAUTH_CLIENT_SECRET }}
    tags: tag:ci
```

### Rationale

- **Zero Configuration**: No router config, port forwarding, or firewall rules
- **Security**: End-to-end encrypted, OAuth-based authentication
- **NAT Traversal**: Works behind NAT without exposing ports
- **Reliability**: Established connection before deployment begins
- **Auditability**: Tailscale logs all connection attempts
- **Portability**: Works with any HA instance, any network

## Consequences

### Positive

✅ **Secure**: No exposed ports, encrypted connections, OAuth authentication
✅ **Simple**: GitHub Action handles connection automatically
✅ **Reliable**: Handles network failures gracefully
✅ **Auditable**: Full connection logs in Tailscale admin
✅ **Flexible**: Can be used for other remote operations (backups, monitoring)
✅ **Cost**: Free for personal use (up to 3 users, 100 devices)

### Negative

❌ **Third-party Dependency**: Requires Tailscale account and service availability
❌ **Initial Setup**: Requires installing Tailscale on HA and creating OAuth credentials
❌ **Network Overhead**: Slight latency compared to direct connection (negligible)

### Mitigations

- **Fallback Option**: Webhook deployment available as alternative
- **Documentation**: Clear setup instructions in docs/TAILSCALE_SETUP.md
- **Monitoring**: Deployment failures trigger notifications

## Related

- See: docs/TAILSCALE_SETUP.md for setup instructions
- See: .github/workflows/deploy-webhook.yml for fallback deployment
- Supersedes: Direct SSH deployment (security concerns)

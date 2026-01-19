# React Dashboard Multi-Client Architecture Plan

## Project ID: react-dashboard-multi-client

## Overview

Transform the react-dashboard from an embedded component in ha-enterprise-starter to a standalone repository with branch-per-client architecture, matching the home-assistant-service pattern.

## Current State
- react-dashboard lives inside ha-enterprise-starter
- Hardcoded entity configurations in `src/config/entities.ts`
- Single deployment, not scalable for multiple clients

## Target State
- Separate `react-dashboard` GitHub repository
- Branch per client (e.g., `client/wojcik_igor`)
- Dynamic configuration loaded per client
- Deployment scripts for multi-client setup

---

## 10-Phase Implementation Plan

| Phase | Name | Description | Deliverables |
|-------|------|-------------|--------------|
| 1 | Repository Setup | Create separate react-dashboard repo, migrate code | New GitHub repo with base code |
| 2 | Configuration Abstraction | Extract hardcoded configs into modular structure | `src/config/` with typed interfaces |
| 3 | Client Branch Strategy | Define branching model and client override pattern | Branch naming convention, merge strategy |
| 4 | Environment Configuration | Add env vars for client identification | `.env.example`, Vite env handling |
| 5 | API Config Endpoint | AI Gateway endpoint to serve client config | `GET /api/config` endpoint |
| 6 | Dynamic Config Loading | React dashboard fetches config at runtime | Config loader hook, fallback handling |
| 7 | Theme System | Client-specific theming (colors, branding) | Theme provider, CSS variables |
| 8 | Deployment Scripts | Init scripts to clone and checkout client branch | `init-react-dashboard.sh` |
| 9 | Docker Integration | Update docker-compose for external repo | Volume mounts, build context |
| 10 | Documentation & Testing | Docs for adding new clients, E2E tests | README, client onboarding guide |

---

## Dependencies
- home-assistant-service (existing branch-per-client pattern)
- ai-gateway (serves config API)
- GitHub repository access

## Success Criteria
- [ ] New client can be onboarded by creating branch + updating .env
- [ ] Zero code changes to react-dashboard main branch per client
- [ ] Existing functionality preserved
- [ ] < 5 minute deployment for new client

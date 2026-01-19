# Phase 1: Repository Setup

## Objective
Create a separate `react-dashboard` GitHub repository and migrate existing code from ha-enterprise-starter.

## Tasks

### 1.1 Create GitHub Repository
```bash
# Create new repo on GitHub: irion94/react-dashboard
# Initialize with README, .gitignore (Node), MIT license
```

### 1.2 Move Existing Code
```bash
# From ha-enterprise-starter/react-dashboard/ to new repo
cd ~/modules
git clone git@github.com:irion94/react-dashboard.git
cp -r ha-enterprise-starter/react-dashboard/* react-dashboard/
cd react-dashboard
git add .
git commit -m "feat: initial migration from ha-enterprise-starter"
git push origin main
```

### 1.3 Update ha-enterprise-starter
- Remove `react-dashboard/` directory from ha-enterprise-starter
- Update `.gitignore` to ignore cloned `react-dashboard/`
- Update `docker-compose.yml` to reference external path

### 1.4 Create Base Branch Structure
```bash
# main branch = base code (shared components, no client-specific config)
# client/* branches = client overrides
git checkout -b client/wojcik_igor
git push origin client/wojcik_igor
```

## Files Changed
- New repo: `react-dashboard/`
- Modified: `ha-enterprise-starter/.gitignore`
- Modified: `ha-enterprise-starter/ai-gateway/docker-compose.yml`

## Validation
- [ ] New repo accessible on GitHub
- [ ] `npm install && npm run dev` works in new repo
- [ ] docker-compose builds from external path

## Rollback
Keep original `react-dashboard/` in ha-enterprise-starter until Phase 10 complete.

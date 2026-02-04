# GitHub Actions Secrets Setup Guide

**Version**: 2.0
**Date**: 2026-02-04
**Author**: DevOps Agent
**Updated**: STORY-076 - Complete secrets template

---

## Overview

This guide describes how to configure GitHub Actions secrets and environment variables for the CI/CD pipelines of the Hybrid RAG Knowledge Platform.

---

## 1. Complete Secrets Inventory

### 1.1 Repository Secrets (Shared Across All Environments)

| Secret Name | Description | Required | Example |
|-------------|-------------|:--------:|---------|
| `SLACK_BOT_TOKEN` | Slack bot token for notifications | Yes | `xoxb-xxx-xxx-xxx` |
| `SLACK_CHANNEL_DEV` | Slack channel ID for dev notifications | Yes | `C0A9WGCD733` |
| `SLACK_CHANNEL_ALERTS` | Slack channel ID for alerts | Yes | `C0A9WGEVB97` |
| `SONAR_TOKEN` | SonarQube integration token | Optional | `squ_xxx` |
| `SENTRY_DSN` | Sentry error tracking DSN | Optional | `https://xxx@sentry.io/xxx` |
| `DOCKER_USERNAME` | Docker Hub username (if using Docker Hub) | Optional | `username` |
| `DOCKER_PASSWORD` | Docker Hub token | Optional | `dckr_pat_xxx` |

### 1.2 Staging Environment Secrets

| Secret Name | Description | Required | Min Length |
|-------------|-------------|:--------:|-----------|
| `STAGING_HOST` | Staging server hostname/IP | Yes | - |
| `STAGING_USER` | SSH username | Yes | - |
| `STAGING_SSH_KEY` | SSH private key (Ed25519) | Yes | - |
| `DB_PASSWORD` | PostgreSQL password | Yes | 16 chars |
| `NEO4J_PASSWORD` | Neo4j password | Yes | 16 chars |
| `REDIS_PASSWORD` | Redis password | Yes | 16 chars |
| `JWT_SECRET` | JWT signing secret | Yes | 32 chars |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin password | Yes | 16 chars |
| `KEYCLOAK_DB_PASSWORD` | Keycloak DB password | Yes | 16 chars |
| `DEEPSEEK_API_KEY` | DeepSeek LLM API key | Yes | - |
| `MINIO_ACCESS_KEY` | MinIO access key | Yes | 16 chars |
| `MINIO_SECRET_KEY` | MinIO secret key | Yes | 16 chars |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password | Yes | 16 chars |

### 1.3 Production Environment Secrets

| Secret Name | Description | Required | Min Length |
|-------------|-------------|:--------:|-----------|
| `PRODUCTION_HOST` | Production server hostname/IP | Yes | - |
| `PRODUCTION_USER` | SSH username | Yes | - |
| `PRODUCTION_SSH_KEY` | SSH private key (Ed25519) | Yes | - |
| `DB_PASSWORD` | PostgreSQL password | Yes | **32 chars** |
| `NEO4J_PASSWORD` | Neo4j password | Yes | **16 chars** |
| `REDIS_PASSWORD` | Redis password | Yes | **32 chars** |
| `ES_PASSWORD` | Elasticsearch password | Yes | **32 chars** |
| `JWT_SECRET` | JWT signing secret | Yes | **64 chars** |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin password | Yes | **32 chars** |
| `KEYCLOAK_DB_PASSWORD` | Keycloak DB password | Yes | **32 chars** |
| `DEEPSEEK_API_KEY` | DeepSeek LLM API key | Yes | - |
| `MINIO_ACCESS_KEY` | MinIO access key | Yes | 16 chars |
| `MINIO_SECRET_KEY` | MinIO secret key | Yes | **32 chars** |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password | Yes | **32 chars** |
| `KIBANA_PASSWORD` | Kibana password | Yes | **32 chars** |
| `SLACK_WEBHOOK_URL` | Slack webhook for alerts | Optional | - |
| `SMTP_PASSWORD` | SMTP password for email alerts | Optional | - |

---

## 2. Quick Setup Script

### 2.1 Automated Setup Script

Create and run this script to set up all GitHub secrets:

```bash
#!/bin/bash
# setup-github-secrets.sh
# Run this script after generating secrets with validate-secrets.sh

set -e

# Check GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    exit 1
fi

# Verify authentication
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI. Run: gh auth login"
    exit 1
fi

echo "Setting up GitHub Actions secrets..."
echo ""

# =============================================================================
# Repository Secrets (Shared)
# =============================================================================
echo "1. Setting repository secrets..."

# Slack Integration
gh secret set SLACK_BOT_TOKEN --body "${SLACK_BOT_TOKEN:-}"
gh secret set SLACK_CHANNEL_DEV --body "C0A9WGCD733"
gh secret set SLACK_CHANNEL_ALERTS --body "C0A9WGEVB97"

echo "   Repository secrets configured"

# =============================================================================
# Staging Environment
# =============================================================================
echo ""
echo "2. Setting staging environment secrets..."

# Create staging environment if not exists
gh api repos/{owner}/{repo}/environments/staging -X PUT \
    -F "deployment_branch_policy[custom_branch_policies]=true" \
    -F "deployment_branch_policy[protected_branches]=false" 2>/dev/null || true

# Deployment secrets
gh secret set STAGING_HOST --env staging --body "${STAGING_HOST:-}"
gh secret set STAGING_USER --env staging --body "${STAGING_USER:-deploy}"
gh secret set STAGING_SSH_KEY --env staging < "${STAGING_SSH_KEY_FILE:-/dev/null}" 2>/dev/null || \
    echo "   Warning: STAGING_SSH_KEY not set (provide STAGING_SSH_KEY_FILE)"

# Application secrets
gh secret set DB_PASSWORD --env staging --body "${STAGING_DB_PASSWORD:-}"
gh secret set NEO4J_PASSWORD --env staging --body "${STAGING_NEO4J_PASSWORD:-}"
gh secret set REDIS_PASSWORD --env staging --body "${STAGING_REDIS_PASSWORD:-}"
gh secret set JWT_SECRET --env staging --body "${STAGING_JWT_SECRET:-}"
gh secret set KEYCLOAK_ADMIN_PASSWORD --env staging --body "${STAGING_KEYCLOAK_ADMIN_PASSWORD:-}"
gh secret set KEYCLOAK_DB_PASSWORD --env staging --body "${STAGING_KEYCLOAK_DB_PASSWORD:-}"
gh secret set DEEPSEEK_API_KEY --env staging --body "${DEEPSEEK_API_KEY:-}"
gh secret set MINIO_ACCESS_KEY --env staging --body "${STAGING_MINIO_ACCESS_KEY:-}"
gh secret set MINIO_SECRET_KEY --env staging --body "${STAGING_MINIO_SECRET_KEY:-}"
gh secret set GRAFANA_ADMIN_PASSWORD --env staging --body "${STAGING_GRAFANA_ADMIN_PASSWORD:-}"

echo "   Staging secrets configured"

# =============================================================================
# Production Environment
# =============================================================================
echo ""
echo "3. Setting production environment secrets..."

# Create production environment with protection rules
gh api repos/{owner}/{repo}/environments/production -X PUT \
    -F "reviewers[][type]=User" \
    -F "reviewers[][id]=${REVIEWER_USER_ID:-1}" \
    -F "deployment_branch_policy[protected_branches]=true" 2>/dev/null || true

# Deployment secrets
gh secret set PRODUCTION_HOST --env production --body "${PRODUCTION_HOST:-}"
gh secret set PRODUCTION_USER --env production --body "${PRODUCTION_USER:-deploy}"
gh secret set PRODUCTION_SSH_KEY --env production < "${PRODUCTION_SSH_KEY_FILE:-/dev/null}" 2>/dev/null || \
    echo "   Warning: PRODUCTION_SSH_KEY not set (provide PRODUCTION_SSH_KEY_FILE)"

# Application secrets (production-strength)
gh secret set DB_PASSWORD --env production --body "${PROD_DB_PASSWORD:-}"
gh secret set NEO4J_PASSWORD --env production --body "${PROD_NEO4J_PASSWORD:-}"
gh secret set REDIS_PASSWORD --env production --body "${PROD_REDIS_PASSWORD:-}"
gh secret set ES_PASSWORD --env production --body "${PROD_ES_PASSWORD:-}"
gh secret set JWT_SECRET --env production --body "${PROD_JWT_SECRET:-}"
gh secret set KEYCLOAK_ADMIN_PASSWORD --env production --body "${PROD_KEYCLOAK_ADMIN_PASSWORD:-}"
gh secret set KEYCLOAK_DB_PASSWORD --env production --body "${PROD_KEYCLOAK_DB_PASSWORD:-}"
gh secret set DEEPSEEK_API_KEY --env production --body "${DEEPSEEK_API_KEY:-}"
gh secret set MINIO_ACCESS_KEY --env production --body "${PROD_MINIO_ACCESS_KEY:-}"
gh secret set MINIO_SECRET_KEY --env production --body "${PROD_MINIO_SECRET_KEY:-}"
gh secret set GRAFANA_ADMIN_PASSWORD --env production --body "${PROD_GRAFANA_ADMIN_PASSWORD:-}"
gh secret set KIBANA_PASSWORD --env production --body "${PROD_KIBANA_PASSWORD:-}"

# Optional alerting secrets
if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    gh secret set SLACK_WEBHOOK_URL --env production --body "${SLACK_WEBHOOK_URL}"
fi

if [[ -n "${SMTP_PASSWORD:-}" ]]; then
    gh secret set SMTP_PASSWORD --env production --body "${SMTP_PASSWORD}"
fi

echo "   Production secrets configured"

# =============================================================================
# Verification
# =============================================================================
echo ""
echo "4. Verifying secrets..."
echo ""
echo "Repository secrets:"
gh secret list

echo ""
echo "Staging environment secrets:"
gh secret list --env staging

echo ""
echo "Production environment secrets:"
gh secret list --env production

echo ""
echo "Setup complete!"
echo ""
echo "IMPORTANT: Run validate-secrets.sh before deployment:"
echo "  ./infrastructure/scripts/validate-secrets.sh staging"
echo "  ./infrastructure/scripts/validate-secrets.sh production"
```

### 2.2 Manual Setup Commands

```bash
# =============================================================================
# STEP 1: Repository Secrets
# =============================================================================

# Slack Integration
gh secret set SLACK_BOT_TOKEN --body "xoxb-your-token-here"
gh secret set SLACK_CHANNEL_DEV --body "C0A9WGCD733"
gh secret set SLACK_CHANNEL_ALERTS --body "C0A9WGEVB97"

# =============================================================================
# STEP 2: Staging Environment
# =============================================================================

# Create environment
# (Go to Settings > Environments > New environment > "staging")

# Deployment
gh secret set STAGING_HOST --env staging --body "staging.example.com"
gh secret set STAGING_USER --env staging --body "deploy"
gh secret set STAGING_SSH_KEY --env staging < staging_deploy_key

# Generate and set application secrets
openssl rand -base64 24 | gh secret set DB_PASSWORD --env staging
openssl rand -base64 24 | gh secret set NEO4J_PASSWORD --env staging
openssl rand -base64 24 | gh secret set REDIS_PASSWORD --env staging
openssl rand -base64 48 | gh secret set JWT_SECRET --env staging
openssl rand -base64 24 | gh secret set KEYCLOAK_ADMIN_PASSWORD --env staging
openssl rand -base64 24 | gh secret set KEYCLOAK_DB_PASSWORD --env staging
gh secret set DEEPSEEK_API_KEY --env staging --body "your-api-key"
openssl rand -base64 24 | gh secret set MINIO_ACCESS_KEY --env staging
openssl rand -base64 24 | gh secret set MINIO_SECRET_KEY --env staging
openssl rand -base64 24 | gh secret set GRAFANA_ADMIN_PASSWORD --env staging

# =============================================================================
# STEP 3: Production Environment
# =============================================================================

# Create environment with protection
# (Go to Settings > Environments > New environment > "production")
# Configure:
#   - Required reviewers: 1-2 team members
#   - Wait timer: 5 minutes
#   - Deployment branches: main only

# Deployment
gh secret set PRODUCTION_HOST --env production --body "prod.example.com"
gh secret set PRODUCTION_USER --env production --body "deploy"
gh secret set PRODUCTION_SSH_KEY --env production < production_deploy_key

# Generate and set application secrets (production-strength)
openssl rand -base64 48 | gh secret set DB_PASSWORD --env production
openssl rand -base64 24 | gh secret set NEO4J_PASSWORD --env production
openssl rand -base64 48 | gh secret set REDIS_PASSWORD --env production
openssl rand -base64 48 | gh secret set ES_PASSWORD --env production
openssl rand -base64 96 | gh secret set JWT_SECRET --env production
openssl rand -base64 48 | gh secret set KEYCLOAK_ADMIN_PASSWORD --env production
openssl rand -base64 48 | gh secret set KEYCLOAK_DB_PASSWORD --env production
gh secret set DEEPSEEK_API_KEY --env production --body "your-production-api-key"
openssl rand -base64 24 | gh secret set MINIO_ACCESS_KEY --env production
openssl rand -base64 48 | gh secret set MINIO_SECRET_KEY --env production
openssl rand -base64 48 | gh secret set GRAFANA_ADMIN_PASSWORD --env production
openssl rand -base64 48 | gh secret set KIBANA_PASSWORD --env production
```

---

## 3. Environment Configuration

### 3.1 Creating GitHub Environments

1. Go to your GitHub repository
2. Click **Settings** > **Environments**
3. Click **New environment**
4. Name it `staging` or `production`
5. Configure environment protection rules
6. Add environment secrets

### 3.2 Recommended Protection Rules

#### Staging Environment

| Rule | Setting | Description |
|------|---------|-------------|
| **Wait timer** | 0 minutes | No delay for staging |
| **Deployment branches** | `develop`, `feature/*` | Allow feature testing |

#### Production Environment

| Rule | Setting | Description |
|------|---------|-------------|
| **Required reviewers** | 1-2 reviewers | Manual approval before deploy |
| **Wait timer** | 5 minutes | Delay before deployment starts |
| **Deployment branches** | `main`, `release/*` | Restrict deployment sources |

---

## 4. Workflow Integration

### 4.1 Using Secrets in Workflows

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main, develop]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate Secrets
        env:
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          JWT_SECRET: ${{ secrets.JWT_SECRET }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: |
          ./infrastructure/scripts/validate-secrets.sh ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }} --ci-mode

  deploy-staging:
    needs: validate
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Staging
        env:
          SSH_KEY: ${{ secrets.STAGING_SSH_KEY }}
          HOST: ${{ secrets.STAGING_HOST }}
          USER: ${{ secrets.STAGING_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          JWT_SECRET: ${{ secrets.JWT_SECRET }}
          # ... other secrets
        run: |
          # Create .env file
          cat > .env << EOF
          DB_PASSWORD=${DB_PASSWORD}
          JWT_SECRET=${JWT_SECRET}
          # ... other variables
          EOF

          # Deploy
          ./scripts/deploy.sh staging

  deploy-production:
    needs: validate
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Production
        env:
          SSH_KEY: ${{ secrets.PRODUCTION_SSH_KEY }}
          HOST: ${{ secrets.PRODUCTION_HOST }}
          USER: ${{ secrets.PRODUCTION_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          JWT_SECRET: ${{ secrets.JWT_SECRET }}
          ES_PASSWORD: ${{ secrets.ES_PASSWORD }}
          # ... other secrets
        run: |
          ./scripts/deploy.sh production
```

### 4.2 Secret Validation Step

```yaml
- name: Validate Required Secrets
  run: |
    MISSING=""

    # Check required secrets
    [ -z "${{ secrets.DB_PASSWORD }}" ] && MISSING="$MISSING DB_PASSWORD"
    [ -z "${{ secrets.JWT_SECRET }}" ] && MISSING="$MISSING JWT_SECRET"
    [ -z "${{ secrets.DEEPSEEK_API_KEY }}" ] && MISSING="$MISSING DEEPSEEK_API_KEY"
    [ -z "${{ secrets.KEYCLOAK_ADMIN_PASSWORD }}" ] && MISSING="$MISSING KEYCLOAK_ADMIN_PASSWORD"

    if [ -n "$MISSING" ]; then
      echo "::error::Missing required secrets:$MISSING"
      exit 1
    fi

    echo "All required secrets are configured"
```

---

## 5. SSH Key Setup

### 5.1 Generate Deployment Keys

```bash
# Generate Ed25519 key (recommended)
ssh-keygen -t ed25519 -C "github-actions-$(date +%Y%m%d)" -f deploy_key -N ""

# Or RSA if Ed25519 not supported
ssh-keygen -t rsa -b 4096 -C "github-actions-$(date +%Y%m%d)" -f deploy_key -N ""
```

### 5.2 Server Configuration

```bash
# On the deployment server
# Create deploy user
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# Add public key
sudo mkdir -p /home/deploy/.ssh
sudo cat deploy_key.pub >> /home/deploy/.ssh/authorized_keys
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh

# Grant limited sudo
echo "deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose" | sudo tee /etc/sudoers.d/deploy
```

### 5.3 Add Keys to GitHub

```bash
# Staging
gh secret set STAGING_SSH_KEY --env staging < deploy_key

# Production (use separate key)
gh secret set PRODUCTION_SSH_KEY --env production < deploy_key_prod
```

---

## 6. Slack Integration

### 6.1 Creating a Slack Bot

1. Go to [Slack API](https://api.slack.com/apps)
2. Click **Create New App** > **From scratch**
3. Name your app (e.g., "GitHub Actions")
4. Select your workspace

### 6.2 Required Bot Token Scopes

| Scope | Description |
|-------|-------------|
| `chat:write` | Send messages |
| `chat:write.public` | Send to public channels without joining |

### 6.3 Install and Get Token

1. Click **Install to Workspace**
2. Authorize the app
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
4. Add as `SLACK_BOT_TOKEN` secret

### 6.4 Channel IDs

| Channel | ID |
|---------|-----|
| proj-hrkp-dev | `C0A9WGCD733` |
| proj-hrkp-alerts | `C0A9WGEVB97` |
| proj-hrkp-standup | `C0A9B7HDEUB` |
| proj-hrkp-general | `C0AABTM716U` |

---

## 7. Secrets Checklist

### 7.1 Pre-Deployment Checklist

#### Repository Level

- [ ] `SLACK_BOT_TOKEN` - Slack bot token
- [ ] `SLACK_CHANNEL_DEV` - Dev channel ID (C0A9WGCD733)
- [ ] `SLACK_CHANNEL_ALERTS` - Alerts channel ID (C0A9WGEVB97)

#### Staging Environment

- [ ] `STAGING_HOST` - Server hostname/IP
- [ ] `STAGING_USER` - SSH username (deploy)
- [ ] `STAGING_SSH_KEY` - SSH private key
- [ ] `DB_PASSWORD` - PostgreSQL password (16+ chars)
- [ ] `NEO4J_PASSWORD` - Neo4j password (16+ chars)
- [ ] `REDIS_PASSWORD` - Redis password (16+ chars)
- [ ] `JWT_SECRET` - JWT signing secret (32+ chars)
- [ ] `KEYCLOAK_ADMIN_PASSWORD` - Keycloak admin (16+ chars)
- [ ] `KEYCLOAK_DB_PASSWORD` - Keycloak DB (16+ chars)
- [ ] `DEEPSEEK_API_KEY` - DeepSeek API key
- [ ] `MINIO_ACCESS_KEY` - MinIO access key
- [ ] `MINIO_SECRET_KEY` - MinIO secret key
- [ ] `GRAFANA_ADMIN_PASSWORD` - Grafana admin (16+ chars)

#### Production Environment

- [ ] `PRODUCTION_HOST` - Server hostname/IP
- [ ] `PRODUCTION_USER` - SSH username (deploy)
- [ ] `PRODUCTION_SSH_KEY` - SSH private key
- [ ] `DB_PASSWORD` - PostgreSQL password (**32+ chars**)
- [ ] `NEO4J_PASSWORD` - Neo4j password (**16+ chars**)
- [ ] `REDIS_PASSWORD` - Redis password (**32+ chars**)
- [ ] `ES_PASSWORD` - Elasticsearch password (**32+ chars**)
- [ ] `JWT_SECRET` - JWT signing secret (**64+ chars**)
- [ ] `KEYCLOAK_ADMIN_PASSWORD` - Keycloak admin (**32+ chars**)
- [ ] `KEYCLOAK_DB_PASSWORD` - Keycloak DB (**32+ chars**)
- [ ] `DEEPSEEK_API_KEY` - DeepSeek API key
- [ ] `MINIO_ACCESS_KEY` - MinIO access key
- [ ] `MINIO_SECRET_KEY` - MinIO secret key (**32+ chars**)
- [ ] `GRAFANA_ADMIN_PASSWORD` - Grafana admin (**32+ chars**)
- [ ] `KIBANA_PASSWORD` - Kibana password (**32+ chars**)
- [ ] Environment protection rules configured

---

## 8. Security Best Practices

### 8.1 Secret Rotation Schedule

| Secret Type | Staging | Production |
|-------------|---------|------------|
| SSH Keys | 365 days | 180 days |
| Database Passwords | 180 days | 90 days |
| JWT Secret | 90 days | 30 days |
| API Tokens | 90 days | 60 days |
| Admin Credentials | 180 days | 90 days |

### 8.2 Access Control

1. **Limit who can edit secrets** - Only repository admins
2. **Use environment protection** - Require approvals for production
3. **Audit secret usage** - Review workflow runs regularly
4. **Never log secrets** - GitHub masks them, but avoid explicit logging

### 8.3 Secret Naming Convention

```
Repository: SERVICE_TYPE (e.g., SLACK_BOT_TOKEN)
Environment: TYPE (e.g., DB_PASSWORD, JWT_SECRET)
```

---

## 9. Troubleshooting

### 9.1 SSH Connection Failed

```
Error: ssh: connect to host xxx port 22: Connection timed out
```

**Solutions:**
1. Verify host is correct
2. Check firewall allows GitHub Actions IPs
3. Verify SSH key format (OpenSSH)

### 9.2 Permission Denied

```
Error: Permission denied (publickey)
```

**Solutions:**
1. Verify public key is in authorized_keys
2. Check key permissions (600)
3. Ensure private key includes headers

### 9.3 Secret Not Available

```
Error: Secret DB_PASSWORD is not set
```

**Solutions:**
1. Verify secret is set for correct environment
2. Check workflow uses correct environment
3. Run `gh secret list --env <env>` to verify

---

## 10. Quick Reference

### 10.1 GitHub CLI Commands

```bash
# List all repository secrets
gh secret list

# List environment secrets
gh secret list --env staging
gh secret list --env production

# Set repository secret
gh secret set SECRET_NAME --body "value"

# Set environment secret
gh secret set SECRET_NAME --env staging --body "value"

# Set secret from file
gh secret set SSH_KEY --env production < private_key_file

# Delete secret
gh secret delete SECRET_NAME
gh secret delete SECRET_NAME --env production
```

### 10.2 Validate Before Deploy

```bash
# Run local validation
./infrastructure/scripts/validate-secrets.sh staging --verbose
./infrastructure/scripts/validate-secrets.sh production --verbose
```

---

## Related Documents

| Document | Path |
|----------|------|
| Secrets Management Guide | `docs/06_deployment/secrets_management_guide.md` |
| Deployment Plan | `docs/06_deployment/deployment_plan.md` |
| Production Deployment Guide | `docs/06_deployment/production_deployment_guide.md` |
| Validate Secrets Script | `infrastructure/scripts/validate-secrets.sh` |

---

**Document End**

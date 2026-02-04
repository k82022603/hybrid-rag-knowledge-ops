# GitHub Actions Secrets Setup Guide

**Version**: 1.0
**Date**: 2026-02-04
**Author**: DevOps Agent

---

## Overview

This guide describes how to configure GitHub Actions secrets and environment variables for the CI/CD pipelines of the Hybrid RAG Knowledge Platform.

---

## 1. Repository Secrets

Repository secrets are available to all workflows in the repository.

### 1.1 Required Secrets

| Secret Name | Description | Required | Example |
|-------------|-------------|:--------:|---------|
| `SLACK_BOT_TOKEN` | Slack bot token for notifications | Yes | `xoxb-xxx-xxx-xxx` |
| `SLACK_CHANNEL_DEV` | Slack channel ID for dev notifications | Yes | `C0A9WGCD733` |
| `SLACK_CHANNEL_ALERTS` | Slack channel ID for alerts | Yes | `C0A9WGEVB97` |

### 1.2 How to Add Repository Secrets

1. Go to your GitHub repository
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Enter the secret name and value
5. Click **Add secret**

```bash
# Using GitHub CLI
gh secret set SLACK_BOT_TOKEN --body "xoxb-your-token-here"
gh secret set SLACK_CHANNEL_DEV --body "C0A9WGCD733"
gh secret set SLACK_CHANNEL_ALERTS --body "C0A9WGEVB97"
```

---

## 2. Environment Secrets

Environment secrets are specific to deployment environments (staging, production).

### 2.1 Staging Environment

| Secret Name | Description | Required |
|-------------|-------------|:--------:|
| `STAGING_HOST` | Staging server hostname/IP | Yes |
| `STAGING_USER` | SSH username for staging | Yes |
| `STAGING_SSH_KEY` | SSH private key for staging | Yes |

### 2.2 Production Environment

| Secret Name | Description | Required |
|-------------|-------------|:--------:|
| `PRODUCTION_HOST` | Production server hostname/IP | Yes |
| `PRODUCTION_USER` | SSH username for production | Yes |
| `PRODUCTION_SSH_KEY` | SSH private key for production | Yes |

### 2.3 How to Create Environments

1. Go to your GitHub repository
2. Click **Settings** > **Environments**
3. Click **New environment**
4. Name it `staging` or `production`
5. Configure environment protection rules (optional)
6. Add environment secrets

#### Recommended Protection Rules for Production

| Rule | Setting | Description |
|------|---------|-------------|
| **Required reviewers** | 1-2 reviewers | Manual approval before deploy |
| **Wait timer** | 5 minutes | Delay before deployment starts |
| **Deployment branches** | `main`, `v*` tags | Restrict deployment sources |

```bash
# Create SSH key for deployment
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""

# Add public key to server
cat deploy_key.pub >> ~/.ssh/authorized_keys

# Add private key as GitHub secret
gh secret set STAGING_SSH_KEY < deploy_key
```

---

## 3. Environment Variables

Environment variables can be set at the repository or workflow level.

### 3.1 Repository Variables

| Variable Name | Description | Value |
|---------------|-------------|-------|
| `REGISTRY` | Container registry | `ghcr.io` |
| `IMAGE_PREFIX` | Image name prefix | `<owner>/knowledge-platform` |

### 3.2 Setting Variables

```bash
# Using GitHub CLI
gh variable set REGISTRY --body "ghcr.io"
gh variable set IMAGE_PREFIX --body "your-org/knowledge-platform"
```

---

## 4. Container Registry Setup

### 4.1 GitHub Container Registry (ghcr.io)

GitHub Container Registry is automatically available with `GITHUB_TOKEN`.

#### Permissions Required

In your workflow, ensure the job has package write permissions:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
```

### 4.2 Alternative: Docker Hub

If using Docker Hub instead of ghcr.io:

| Secret Name | Description |
|-------------|-------------|
| `DOCKER_USERNAME` | Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub password or access token |

---

## 5. Slack Integration

### 5.1 Creating a Slack Bot

1. Go to [Slack API](https://api.slack.com/apps)
2. Click **Create New App** > **From scratch**
3. Name your app (e.g., "GitHub Actions")
4. Select your workspace

### 5.2 Bot Token Scopes

Add the following OAuth scopes under **OAuth & Permissions**:

| Scope | Description |
|-------|-------------|
| `chat:write` | Send messages |
| `chat:write.public` | Send to public channels |

### 5.3 Install App to Workspace

1. Click **Install to Workspace**
2. Authorize the app
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
4. Add as `SLACK_BOT_TOKEN` secret

### 5.4 Get Channel IDs

1. Open Slack in browser
2. Navigate to the channel
3. Channel ID is in the URL: `https://app.slack.com/client/T.../C0A9WGCD733`

---

## 6. SSH Key Setup for Deployment

### 6.1 Generate Deployment Key

```bash
# Generate Ed25519 key (recommended)
ssh-keygen -t ed25519 -C "github-actions-$(date +%Y%m%d)" -f deploy_key -N ""

# Or RSA if Ed25519 not supported
ssh-keygen -t rsa -b 4096 -C "github-actions-$(date +%Y%m%d)" -f deploy_key -N ""
```

### 6.2 Server Setup

```bash
# On the deployment server
# Create deploy user (if not exists)
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# Add public key
sudo mkdir -p /home/deploy/.ssh
sudo cat deploy_key.pub >> /home/deploy/.ssh/authorized_keys
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh

# Grant sudo for specific commands (optional)
echo "deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose" | sudo tee /etc/sudoers.d/deploy
```

### 6.3 Add Private Key to GitHub

```bash
# Using GitHub CLI
gh secret set STAGING_SSH_KEY < deploy_key
gh secret set PRODUCTION_SSH_KEY < deploy_key_prod
```

---

## 7. Secrets Checklist

### 7.1 Staging Deployment

- [ ] `STAGING_HOST` - Server hostname or IP
- [ ] `STAGING_USER` - SSH username (e.g., `deploy`)
- [ ] `STAGING_SSH_KEY` - SSH private key
- [ ] `SLACK_BOT_TOKEN` - Slack notifications
- [ ] `SLACK_CHANNEL_DEV` - Dev channel ID

### 7.2 Production Deployment

- [ ] `PRODUCTION_HOST` - Server hostname or IP
- [ ] `PRODUCTION_USER` - SSH username
- [ ] `PRODUCTION_SSH_KEY` - SSH private key
- [ ] `SLACK_CHANNEL_ALERTS` - Alerts channel ID
- [ ] Environment protection rules configured

### 7.3 Optional Secrets

- [ ] `SONAR_TOKEN` - SonarQube integration
- [ ] `SENTRY_DSN` - Error tracking
- [ ] `DEEPSEEK_API_KEY` - AI service (for integration tests)

---

## 8. Security Best Practices

### 8.1 Secret Rotation

| Secret Type | Rotation Frequency | Notes |
|-------------|-------------------|-------|
| SSH Keys | Every 6 months | Update both server and GitHub |
| API Tokens | Every 3 months | Slack, external services |
| Service Passwords | Every 3 months | Database, registry |

### 8.2 Access Control

1. **Limit who can edit secrets** - Only repository admins
2. **Use environment protection** - Require approvals for production
3. **Audit secret usage** - Review workflow runs regularly
4. **Never log secrets** - Masked by GitHub, but avoid explicit logging

### 8.3 Secret Naming Convention

```
<ENVIRONMENT>_<SERVICE>_<TYPE>

Examples:
STAGING_SSH_KEY
PRODUCTION_DB_PASSWORD
SLACK_BOT_TOKEN (shared across environments)
```

---

## 9. Troubleshooting

### 9.1 SSH Connection Failed

```
Error: ssh: connect to host xxx.xxx.xxx.xxx port 22: Connection timed out
```

**Solutions:**
1. Verify `STAGING_HOST` or `PRODUCTION_HOST` is correct
2. Check server firewall allows port 22 from GitHub Actions IPs
3. Verify SSH key is correct format (OpenSSH)

### 9.2 Permission Denied

```
Error: Permission denied (publickey)
```

**Solutions:**
1. Verify public key is in `~/.ssh/authorized_keys` on server
2. Check SSH key permissions (600)
3. Ensure private key includes headers (`-----BEGIN OPENSSH PRIVATE KEY-----`)

### 9.3 Docker Push Failed

```
Error: denied: denied
```

**Solutions:**
1. Verify `GITHUB_TOKEN` has `packages: write` permission
2. Check image name format: `ghcr.io/<owner>/<repo>/<image>`
3. Ensure package visibility settings allow the action

---

## 10. Quick Reference

### 10.1 GitHub CLI Commands

```bash
# List all secrets
gh secret list

# Set a secret
gh secret set SECRET_NAME --body "secret_value"

# Set secret from file
gh secret set SSH_KEY < private_key_file

# Delete a secret
gh secret delete SECRET_NAME

# Set environment secret
gh secret set SECRET_NAME --env staging --body "value"
```

### 10.2 Verify Secrets Are Set

```yaml
# Add this step to your workflow to verify secrets
- name: Verify Secrets
  run: |
    if [ -z "${{ secrets.STAGING_HOST }}" ]; then
      echo "::error::STAGING_HOST secret is not set"
      exit 1
    fi
    echo "All required secrets are configured"
```

---

## Related Documents

| Document | Path |
|----------|------|
| Deployment Plan | `docs/06_deployment/deployment_plan.md` |
| DevOps Design | `docs/02_design/devops_detailed_design.md` |
| CI/CD Report | `docs/06_deployment/cicd_pipeline_report.md` |

---

**Document End**

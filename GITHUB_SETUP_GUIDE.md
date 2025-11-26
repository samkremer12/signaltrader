# GitHub Repository Setup Guide

This guide will help you push your SignalTrader code to GitHub so you can deploy it to Render.

---

## 📋 Prerequisites

- GitHub account (sign up at https://github.com if you don't have one)
- Git installed locally (already available in your environment)

---

## 🚀 Step-by-Step Instructions

### Step 1: Create a New GitHub Repository

1. Go to https://github.com/new
2. Fill in the repository details:
   - **Repository name:** `signaltrader` (or any name you prefer)
   - **Description:** "Automated crypto trading platform with TradingView webhook integration"
   - **Visibility:** Private (recommended) or Public
   - **DO NOT check** "Initialize this repository with a README" (we already have code)
   - **DO NOT add** .gitignore or license (we already have these)
3. Click **"Create repository"**
4. You'll see a page with setup instructions - **copy the repository URL**
   - It will look like: `https://github.com/YOUR_USERNAME/signaltrader.git`
   - Or SSH format: `git@github.com:YOUR_USERNAME/signaltrader.git`

---

### Step 2: Push Code to GitHub

Open a terminal and run these commands:

```bash
# Navigate to the project directory
cd /home/ubuntu/crypto-trading-platform

# Add GitHub as remote origin (replace YOUR_USERNAME with your actual GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/signaltrader.git

# Verify remote was added
git remote -v

# Push the code to GitHub
git push -u origin devin/1763862731-phase-1-production-ready

# Optional: Also push to main branch if you want
# git checkout -b main
# git push -u origin main
```

**Note:** If you're using SSH instead of HTTPS, use:
```bash
git remote add origin git@github.com:YOUR_USERNAME/signaltrader.git
```

---

### Step 3: Verify Code is on GitHub

1. Go to your repository URL: `https://github.com/YOUR_USERNAME/signaltrader`
2. You should see:
   - Branch: `devin/1763862731-phase-1-production-ready`
   - Files: `crypto-trading-backend/`, `crypto-trading-frontend/`, `PRODUCTION_DEPLOYMENT.md`, `RENDER_DEPLOYMENT_GUIDE.md`, etc.
3. Click on the branch dropdown and verify `devin/1763862731-phase-1-production-ready` is listed

---

### Step 4: Authentication (If Prompted)

If Git asks for credentials when pushing:

#### Option A: Personal Access Token (Recommended)

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Configure:
   - **Note:** "SignalTrader Deployment"
   - **Expiration:** 90 days (or custom)
   - **Scopes:** Check `repo` (full control of private repositories)
4. Click **"Generate token"**
5. **Copy the token** (you won't see it again!)
6. When Git prompts for password, paste the token (not your GitHub password)

#### Option B: SSH Key (Alternative)

1. Generate SSH key:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```
2. Press Enter to accept default location
3. Press Enter twice to skip passphrase (or set one)
4. Copy public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
5. Go to https://github.com/settings/keys
6. Click **"New SSH key"**
7. Paste the public key and save
8. Use SSH remote URL: `git@github.com:YOUR_USERNAME/signaltrader.git`

---

### Step 5: Connect Repository to Render

Now that your code is on GitHub, you can connect it to Render:

1. Go to https://render.com/dashboard
2. When creating a new service (Web Service or Background Worker)
3. Click **"Connect a repository"**
4. If this is your first time:
   - Click **"Connect GitHub"**
   - Authorize Render to access your GitHub account
   - Select which repositories to grant access (choose your `signaltrader` repo)
5. Select your repository from the list
6. Choose branch: `devin/1763862731-phase-1-production-ready`
7. Continue with deployment configuration

---

## 🔄 Updating Code After Changes

If you make changes to the code and want to update the deployment:

```bash
# Navigate to project directory
cd /home/ubuntu/crypto-trading-platform

# Check current status
git status

# Add changed files
git add .

# Commit changes
git commit -m "Description of changes"

# Push to GitHub
git push origin devin/1763862731-phase-1-production-ready
```

Render will automatically detect the push and redeploy your services (if auto-deploy is enabled).

---

## 🌿 Branch Management

### Current Branch Structure

- **Branch:** `devin/1763862731-phase-1-production-ready`
- **Contains:** All Phase 1 & Phase 2 features (multi-user auth, PostgreSQL, Celery, paper trading, trailing stops, notifications)

### Creating a Main Branch (Optional)

If you want to create a `main` branch for production:

```bash
# Create and switch to main branch
git checkout -b main

# Push to GitHub
git push -u origin main

# Switch back to development branch
git checkout devin/1763862731-phase-1-production-ready
```

### Creating Feature Branches (For Future Development)

```bash
# Create a new feature branch
git checkout -b feature/new-feature-name

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push to GitHub
git push -u origin feature/new-feature-name

# Later: Merge into main branch
git checkout main
git merge feature/new-feature-name
git push origin main
```

---

## 🔒 Security Best Practices

### What to Commit

✅ **DO commit:**
- Source code (`.py`, `.tsx`, `.ts`, `.json`, etc.)
- Configuration files (`pyproject.toml`, `package.json`, `tsconfig.json`)
- Documentation (`.md` files)
- `.gitignore` file

❌ **DO NOT commit:**
- `.env` files (contains secrets)
- `node_modules/` directory
- `__pycache__/` directories
- `*.pyc` files
- Database files (`*.db`, `*.sqlite`)
- API keys or passwords
- `poetry.lock` or `package-lock.json` (optional, but can cause conflicts)

### Verify .gitignore

Check that sensitive files are ignored:

```bash
cat .gitignore
```

Should include:
```
.env
*.db
*.sqlite
__pycache__/
node_modules/
.DS_Store
```

### Check for Accidentally Committed Secrets

```bash
# Search for potential secrets in committed files
git log --all --full-history --source --pretty=format: --name-only -- .env
git log --all --full-history --source --pretty=format: --name-only -- "*.db"
```

If you find secrets in history, you'll need to remove them:
```bash
# Remove file from all commits (use with caution!)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (only if repository is private and you're the only user)
git push origin --force --all
```

---

## 🐛 Troubleshooting

### Error: "remote origin already exists"

```bash
# Remove existing remote
git remote remove origin

# Add new remote
git remote add origin https://github.com/YOUR_USERNAME/signaltrader.git
```

### Error: "failed to push some refs"

```bash
# Pull latest changes first
git pull origin devin/1763862731-phase-1-production-ready --rebase

# Then push
git push origin devin/1763862731-phase-1-production-ready
```

### Error: "Permission denied (publickey)"

You're using SSH but haven't set up SSH keys. Either:
1. Follow "Option B: SSH Key" in Step 4 above
2. Or switch to HTTPS:
   ```bash
   git remote set-url origin https://github.com/YOUR_USERNAME/signaltrader.git
   ```

### Error: "Repository not found"

- Verify the repository URL is correct
- Check you have access to the repository
- If using HTTPS, verify your username in the URL

---

## 📊 Repository Statistics

After pushing, you can view repository statistics:

```bash
# View commit history
git log --oneline

# View file changes
git diff --stat

# View repository size
git count-objects -vH

# View all branches
git branch -a
```

---

## 🎉 Next Steps

After successfully pushing to GitHub:

1. ✅ Code is backed up on GitHub
2. ✅ Ready to connect to Render for deployment
3. ✅ Can collaborate with others (if public or shared)
4. ✅ Version history is preserved
5. ✅ Can create pull requests for code reviews

Continue with the **RENDER_DEPLOYMENT_GUIDE.md** to deploy your application!

---

## 📞 Need Help?

- **GitHub Documentation:** https://docs.github.com
- **Git Basics:** https://git-scm.com/book/en/v2/Getting-Started-Git-Basics
- **Render + GitHub:** https://render.com/docs/github

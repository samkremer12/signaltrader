# SignalTrader - Complete Render Deployment Guide

This guide provides step-by-step instructions to deploy SignalTrader to production using Render (PostgreSQL + Backend + Celery) and Upstash (Redis).

## 🔑 Generated Encryption Keys

**IMPORTANT: Save these keys securely - you'll need them for environment variables**

```
API_KEY_ENCRYPTION_KEY=tvm_0zRe5RXfyU4IBXFQ7UJs1K5SE5cF
JWT_SECRET_KEY=isaijV8kcjBOsRFPBrSj2FxPoO5HIwuIrG8gEWLCxsI
```

---

## 📋 Prerequisites

Before starting, you'll need:
- GitHub account (to push code and connect to Render)
- Render account (free tier available at https://render.com)
- Upstash account (free tier available at https://upstash.com)
- Gmail account (for email notifications)

---

## 🚀 Step-by-Step Deployment

### Step 1: Push Code to GitHub

If you haven't already created a GitHub repository:

1. Go to https://github.com/new
2. Create a new repository (e.g., `signaltrader`)
3. **Do NOT initialize with README** (we already have code)
4. Copy the repository URL (e.g., `https://github.com/YOUR_USERNAME/signaltrader.git`)

Then push the code:

```bash
cd /home/ubuntu/crypto-trading-platform
git remote add origin https://github.com/YOUR_USERNAME/signaltrader.git
git push -u origin devin/1763862731-phase-1-production-ready
```

**Note:** Replace `YOUR_USERNAME` with your actual GitHub username.

---

### Step 2: Create PostgreSQL Database on Render

1. Go to https://render.com/dashboard
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name:** `signaltrader-db`
   - **Database:** `signaltrader`
   - **User:** `signaltrader` (auto-generated)
   - **Region:** Choose closest to you (e.g., `Ohio (US East)`)
   - **PostgreSQL Version:** 16 (latest)
   - **Instance Type:** `Free` (or `Starter` for production - $7/month)
4. Click **"Create Database"**
5. Wait for database to provision (~2 minutes)
6. **Copy the "Internal Database URL"** (starts with `postgresql://`)
   - Example: `postgresql://signaltrader:abc123@dpg-xyz.ohio-postgres.render.com/signaltrader`
   - **Save this URL - you'll need it for environment variables**

---

### Step 3: Create Redis Instance on Upstash

1. Go to https://upstash.com and sign up/login
2. Click **"Create Database"**
3. Configure:
   - **Name:** `signaltrader-redis`
   - **Type:** `Regional`
   - **Region:** Choose same region as Render (e.g., `us-east-1`)
   - **TLS:** Enabled (default)
4. Click **"Create"**
5. On the database page, scroll to **"REST API"** section
6. **Copy the Redis URL** (starts with `rediss://`)
   - Example: `rediss://default:abc123xyz@us1-example.upstash.io:6379`
   - **Save this URL - you'll need it for environment variables**

---

### Step 4: Generate Gmail App Password

1. Go to https://myaccount.google.com/security
2. Enable **"2-Step Verification"** if not already enabled
3. Search for **"App passwords"** in the search bar
4. Click **"App passwords"**
5. Select:
   - **App:** Mail
   - **Device:** Other (Custom name) → Enter "SignalTrader"
6. Click **"Generate"**
7. **Copy the 16-character password** (e.g., `abcd efgh ijkl mnop`)
   - Remove spaces: `abcdefghijklmnop`
   - **Save this password - you'll need it for SMTP_PASSWORD**

---

### Step 5: Deploy Backend (FastAPI) on Render

1. Go to https://render.com/dashboard
2. Click **"New +"** → **"Web Service"**
3. Click **"Connect a repository"** → Select your GitHub repository
4. Configure:
   - **Name:** `signaltrader-backend`
   - **Region:** Same as database (e.g., `Ohio (US East)`)
   - **Branch:** `devin/1763862731-phase-1-production-ready`
   - **Root Directory:** `crypto-trading-backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install poetry && poetry install`
   - **Start Command:** `poetry run uvicorn app.main:app --host 0.0.0.0 --port 10000`
   - **Instance Type:** `Free` (or `Starter` for production - $7/month)

5. Click **"Advanced"** → **"Add Environment Variable"** and add:

```
DATABASE_URL=<paste_your_postgresql_url_from_step_2>
CELERY_BROKER_URL=<paste_your_redis_url_from_step_3>
CELERY_RESULT_BACKEND=<paste_your_redis_url_from_step_3>
API_KEY_ENCRYPTION_KEY=tvm_0zRe5RXfyU4IBXFQ7UJs1K5SE5cF
JWT_SECRET_KEY=isaijV8kcjBOsRFPBrSj2FxPoO5HIwuIrG8gEWLCxsI
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<your_gmail_email>
SMTP_PASSWORD=<your_gmail_app_password_from_step_4>
```

6. Click **"Create Web Service"**
7. Wait for deployment (~5-10 minutes)
8. **Copy the backend URL** (e.g., `https://signaltrader-backend.onrender.com`)
   - **Save this URL - you'll need it for frontend deployment**

---

### Step 6: Deploy Celery Worker on Render

1. Go to https://render.com/dashboard
2. Click **"New +"** → **"Background Worker"**
3. Select your GitHub repository
4. Configure:
   - **Name:** `signaltrader-worker`
   - **Region:** Same as backend
   - **Branch:** `devin/1763862731-phase-1-production-ready`
   - **Root Directory:** `crypto-trading-backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install poetry && poetry install`
   - **Start Command:** `poetry run celery -A app.celery_app.celery_app worker --loglevel=info`
   - **Instance Type:** `Free` (or `Starter` for production)

5. Click **"Advanced"** → **"Add Environment Variable"** and add **THE SAME environment variables as Step 5**

6. Click **"Create Background Worker"**
7. Wait for deployment (~5 minutes)

---

### Step 7: Deploy Celery Beat on Render

1. Go to https://render.com/dashboard
2. Click **"New +"** → **"Background Worker"**
3. Select your GitHub repository
4. Configure:
   - **Name:** `signaltrader-beat`
   - **Region:** Same as backend
   - **Branch:** `devin/1763862731-phase-1-production-ready`
   - **Root Directory:** `crypto-trading-backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install poetry && poetry install`
   - **Start Command:** `poetry run celery -A app.celery_app.celery_app beat --loglevel=info`
   - **Instance Type:** `Free` (or `Starter` for production)

5. Click **"Advanced"** → **"Add Environment Variable"** and add **THE SAME environment variables as Step 5**

6. Click **"Create Background Worker"**
7. Wait for deployment (~5 minutes)

---

### Step 8: Deploy Frontend on Vercel (Recommended) or Netlify

#### Option A: Vercel (Recommended)

1. Go to https://vercel.com and sign up/login
2. Click **"Add New"** → **"Project"**
3. Import your GitHub repository
4. Configure:
   - **Framework Preset:** Vite
   - **Root Directory:** `crypto-trading-frontend`
   - **Build Command:** `npm install && npm run build`
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`

5. Click **"Environment Variables"** → Add:
   ```
   VITE_API_URL=<your_backend_url_from_step_5>
   ```
   Example: `VITE_API_URL=https://signaltrader-backend.onrender.com`

6. Click **"Deploy"**
7. Wait for deployment (~3-5 minutes)
8. **Copy the frontend URL** (e.g., `https://signaltrader.vercel.app`)

#### Option B: Netlify

1. Go to https://netlify.com and sign up/login
2. Click **"Add new site"** → **"Import an existing project"**
3. Connect to GitHub and select your repository
4. Configure:
   - **Branch:** `devin/1763862731-phase-1-production-ready`
   - **Base directory:** `crypto-trading-frontend`
   - **Build command:** `npm install && npm run build`
   - **Publish directory:** `crypto-trading-frontend/dist`

5. Click **"Advanced build settings"** → **"New variable"**:
   ```
   VITE_API_URL=<your_backend_url_from_step_5>
   ```

6. Click **"Deploy site"**
7. Wait for deployment (~3-5 minutes)
8. **Copy the frontend URL** (e.g., `https://signaltrader.netlify.app`)

---

## ✅ Verification Checklist

After deployment, verify everything is working:

### 1. Check Backend Health

Open in browser: `https://your-backend-url.onrender.com/system-status`

Expected response:
```json
{
  "status": "operational",
  "auto_trading_enabled": false,
  "exchange_connected": false,
  "last_trade": null
}
```

### 2. Check API Documentation

Open in browser: `https://your-backend-url.onrender.com/docs`

You should see the FastAPI Swagger documentation.

### 3. Test User Registration

1. Open your frontend URL
2. Click **"Register"**
3. Create a new account (username + password)
4. You should be redirected to the Home page

### 4. Test API Key Storage

1. On the Home page, enter test API credentials:
   - **Exchange:** Binance
   - **API Key:** `test_key_123`
   - **API Secret:** `test_secret_456`
2. Click **"Save API Keys"**
3. Refresh the page - credentials should persist (encrypted in PostgreSQL)

### 5. Test Paper Trading Mode

1. Go to **Settings** page
2. Enable **"Paper Trading Mode"**
3. Set trading parameters (position size, stop-loss, take-profit)
4. Click **"Save Settings"**
5. Copy your **Webhook URL** from the Home page
6. Send a test webhook using curl:

```bash
curl -X POST "https://your-backend-url.onrender.com/webhook/YOUR_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "buy",
    "symbol": "BTCUSDT",
    "price": "50000"
  }'
```

7. Go to **Trade Logs** page - you should see a simulated trade

### 6. Test Email Notifications

1. Go to **Settings** page
2. Enable **"Email Notifications"**
3. Enter your email address
4. Click **"Save Settings"**
5. Send another test webhook (same as step 5)
6. Check your email - you should receive a trade notification

### 7. Test Trailing Stop-Loss

1. Enable **"Trailing Stop-Loss"** in Settings
2. Set **"Trailing Stop %"** to 2%
3. Execute a paper trade (webhook)
4. Wait 30-60 seconds
5. Check Render logs for Celery Beat:
   - Go to Render dashboard → `signaltrader-beat` → Logs
   - You should see: `Monitoring trailing stops for X positions`

### 8. Test Data Persistence

1. Go to Render dashboard → `signaltrader-backend`
2. Click **"Manual Deploy"** → **"Clear build cache & deploy"**
3. Wait for backend to restart (~3 minutes)
4. Refresh your frontend
5. Login again - all your settings, trades, and API keys should still be there

---

## 🔍 Troubleshooting

### Backend won't start

**Check Render logs:**
1. Go to Render dashboard → `signaltrader-backend` → Logs
2. Look for error messages

**Common issues:**
- **Database connection error:** Verify `DATABASE_URL` is correct
- **Redis connection error:** Verify `CELERY_BROKER_URL` is correct
- **Poetry install fails:** Check `pyproject.toml` is in `crypto-trading-backend/` directory

### Celery Worker won't start

**Check Render logs:**
1. Go to Render dashboard → `signaltrader-worker` → Logs

**Common issues:**
- **Redis connection error:** Verify `CELERY_BROKER_URL` matches backend
- **Import error:** Ensure all environment variables match backend exactly

### Frontend shows "Network Error"

**Check browser console:**
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for CORS or network errors

**Common issues:**
- **CORS error:** Backend CORS is configured for all origins, but verify backend is running
- **Wrong API URL:** Check `VITE_API_URL` environment variable in Vercel/Netlify
- **Backend not responding:** Verify backend URL is accessible

### Webhooks not executing trades

**Check:**
1. Webhook token is correct (copy from Home page)
2. Webhook URL format: `https://your-backend.onrender.com/webhook/YOUR_TOKEN`
3. API keys are saved and valid
4. Auto-trading is enabled (toggle on Home page)
5. Check Trade Logs page for error messages

### Email notifications not working

**Check:**
1. Gmail App Password is correct (16 characters, no spaces)
2. Email notifications are enabled in Settings
3. Email address is entered correctly
4. Check Gmail spam folder
5. Check Render logs for SMTP errors

### Trailing stops not triggering

**Check:**
1. Celery Beat is running (Render dashboard → `signaltrader-beat` → should show "Live")
2. Trailing stop is enabled in Settings
3. You have open positions (check Trade Logs)
4. Check Celery Beat logs for monitoring messages

---

## 📊 Monitoring Your Deployment

### View Backend Logs

```
Render Dashboard → signaltrader-backend → Logs
```

### View Celery Worker Logs

```
Render Dashboard → signaltrader-worker → Logs
```

### View Celery Beat Logs

```
Render Dashboard → signaltrader-beat → Logs
```

### Check Database

1. Go to Render dashboard → `signaltrader-db`
2. Click **"Connect"** → Copy connection string
3. Use a PostgreSQL client (e.g., pgAdmin, DBeaver) to connect
4. Query tables: `users`, `trades`, `positions`, `settings`, `api_credentials`

### Check Redis

1. Go to Upstash dashboard → `signaltrader-redis`
2. Click **"CLI"** tab
3. Run commands:
   ```
   PING
   KEYS *
   ```

---

## 💰 Cost Breakdown

### Free Tier (Good for Testing)
- **Render PostgreSQL:** Free (1GB storage, 90 days)
- **Render Backend:** Free (750 hours/month, sleeps after 15min inactivity)
- **Render Worker:** Free (750 hours/month)
- **Render Beat:** Free (750 hours/month)
- **Upstash Redis:** Free (10,000 commands/day)
- **Vercel/Netlify:** Free (100GB bandwidth/month)
- **Gmail:** Free
- **Total:** $0/month

### Production Tier (Recommended for Live Trading)
- **Render PostgreSQL:** $7/month (Starter - 256MB RAM, 10GB storage)
- **Render Backend:** $7/month (Starter - 512MB RAM, always on)
- **Render Worker:** $7/month (Starter - 512MB RAM)
- **Render Beat:** $7/month (Starter - 512MB RAM)
- **Upstash Redis:** Free (or $10/month for Pro - 1M commands/day)
- **Vercel/Netlify:** Free (or $20/month for Pro)
- **Gmail:** Free
- **Total:** $28-58/month

---

## 🔒 Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Rotate encryption keys periodically** - Generate new keys every 90 days
3. **Use strong passwords** - Minimum 12 characters for user accounts
4. **Enable 2FA on Gmail** - Required for App Passwords
5. **Monitor logs regularly** - Check for suspicious activity
6. **Keep dependencies updated** - Run `poetry update` monthly
7. **Use HTTPS only** - Render provides SSL certificates automatically

---

## 🚀 Next Steps

After successful deployment:

1. **Test with real exchange API keys** (start with small amounts)
2. **Set up TradingView alerts** with your webhook URL
3. **Monitor trades daily** for the first week
4. **Adjust trading parameters** based on performance
5. **Consider Phase 3 features:**
   - 2FA authentication
   - Backtesting
   - Multi-region failover
   - Admin panel

---

## 📞 Support

If you encounter issues:

1. Check this troubleshooting guide
2. Review Render logs for error messages
3. Verify all environment variables are set correctly
4. Test each component individually (backend, worker, beat)
5. Check GitHub Issues for similar problems

---

## 🎉 Congratulations!

You now have a fully autonomous, production-ready crypto trading platform running 24/7 with:
- ✅ Multi-user authentication
- ✅ Persistent PostgreSQL storage
- ✅ Async trade execution with Celery
- ✅ Trailing stop-loss monitoring (every 30 seconds)
- ✅ Email notifications
- ✅ Paper trading mode
- ✅ Professional UI with dark mode

Happy trading! 🚀📈

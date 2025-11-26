# SignalTrader - Quick Start Guide

**Complete deployment in 30 minutes!** ⚡

This is your quick reference for deploying SignalTrader to production with Render + Upstash.

---

## 📦 What You're Deploying

**SignalTrader** - Autonomous crypto trading platform with:
- ✅ Multi-user authentication
- ✅ TradingView webhook integration
- ✅ Paper trading mode
- ✅ Trailing stop-loss (every 30s)
- ✅ Email notifications
- ✅ 24/7 autonomous operation

---

## 🔑 Your Generated Encryption Keys

**SAVE THESE - You'll need them for environment variables:**

```
API_KEY_ENCRYPTION_KEY=tvm_0zRe5RXfyU4IBXFQ7UJs1K5SE5cF
JWT_SECRET_KEY=isaijV8kcjBOsRFPBrSj2FxPoO5HIwuIrG8gEWLCxsI
```

---

## 🚀 Deployment Checklist

### ☐ Step 1: Push to GitHub (5 min)
```bash
cd /home/ubuntu/crypto-trading-platform
git remote add origin https://github.com/YOUR_USERNAME/signaltrader.git
git push -u origin devin/1763862731-phase-1-production-ready
```
📖 **Detailed guide:** `GITHUB_SETUP_GUIDE.md`

---

### ☐ Step 2: Create PostgreSQL on Render (3 min)
1. https://render.com/dashboard → **New +** → **PostgreSQL**
2. Name: `signaltrader-db`, Region: `Ohio (US East)`, Type: `Free`
3. **Copy Internal Database URL** → Save for Step 5

---

### ☐ Step 3: Create Redis on Upstash (3 min)
1. https://upstash.com → **Create Database**
2. Name: `signaltrader-redis`, Region: `us-east-1`
3. **Copy Redis URL** → Save for Step 5

---

### ☐ Step 4: Get Gmail App Password (3 min)
1. https://myaccount.google.com/security → **App passwords**
2. Generate password for "SignalTrader"
3. **Copy 16-character password** → Save for Step 5

---

### ☐ Step 5: Deploy Backend on Render (5 min)
1. https://render.com/dashboard → **New +** → **Web Service**
2. Connect GitHub repo → Branch: `devin/1763862731-phase-1-production-ready`
3. Configure:
   - **Root Directory:** `crypto-trading-backend`
   - **Build Command:** `pip install poetry && poetry install`
   - **Start Command:** `poetry run uvicorn app.main:app --host 0.0.0.0 --port 10000`
4. **Add Environment Variables:**
   ```
   DATABASE_URL=<paste_postgresql_url_from_step_2>
   CELERY_BROKER_URL=<paste_redis_url_from_step_3>
   CELERY_RESULT_BACKEND=<paste_redis_url_from_step_3>
   API_KEY_ENCRYPTION_KEY=tvm_0zRe5RXfyU4IBXFQ7UJs1K5SE5cF
   JWT_SECRET_KEY=isaijV8kcjBOsRFPBrSj2FxPoO5HIwuIrG8gEWLCxsI
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=<your_gmail_email>
   SMTP_PASSWORD=<gmail_app_password_from_step_4>
   ```
5. **Create Web Service** → Wait 5-10 min
6. **Copy backend URL** → Save for Step 8

---

### ☐ Step 6: Deploy Celery Worker on Render (3 min)
1. https://render.com/dashboard → **New +** → **Background Worker**
2. Same repo, same branch, same root directory
3. **Start Command:** `poetry run celery -A app.celery_app.celery_app worker --loglevel=info`
4. **Add same environment variables as Step 5**
5. **Create Background Worker**

---

### ☐ Step 7: Deploy Celery Beat on Render (3 min)
1. https://render.com/dashboard → **New +** → **Background Worker**
2. Same repo, same branch, same root directory
3. **Start Command:** `poetry run celery -A app.celery_app.celery_app beat --loglevel=info`
4. **Add same environment variables as Step 5**
5. **Create Background Worker**

---

### ☐ Step 8: Deploy Frontend on Vercel (5 min)
1. https://vercel.com → **Add New** → **Project**
2. Import GitHub repo
3. Configure:
   - **Root Directory:** `crypto-trading-frontend`
   - **Build Command:** `npm install && npm run build`
   - **Output Directory:** `dist`
4. **Environment Variable:**
   ```
   VITE_API_URL=<backend_url_from_step_5>
   ```
5. **Deploy** → Wait 3-5 min
6. **Copy frontend URL** → This is your app!

---

## ✅ Verification (5 min)

### 1. Check Backend Health
Open: `https://your-backend.onrender.com/system-status`

Expected: `{"status": "operational", ...}`

### 2. Test Registration
1. Open your frontend URL
2. Register a new account
3. Login successfully

### 3. Test Paper Trading
1. Go to Settings → Enable **Paper Trading Mode**
2. Save settings
3. Copy webhook URL from Home page
4. Send test webhook:
   ```bash
   curl -X POST "https://your-backend.onrender.com/webhook/YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"action":"buy","symbol":"BTCUSDT","price":"50000"}'
   ```
5. Check Trade Logs → Should see simulated trade

### 4. Test Email Notifications
1. Settings → Enable **Email Notifications**
2. Enter your email
3. Send another test webhook
4. Check email → Should receive notification

### 5. Test Persistence
1. Render dashboard → Restart backend
2. Refresh frontend → Login
3. All settings and trades should persist

---

## 🎉 You're Live!

Your SignalTrader platform is now running 24/7 with:
- ✅ Persistent PostgreSQL storage
- ✅ Async trade execution with Celery
- ✅ Trailing stops monitoring every 30 seconds
- ✅ Email notifications for all trades
- ✅ Paper trading mode for safe testing

---

## 📖 Full Documentation

- **Complete Deployment Guide:** `RENDER_DEPLOYMENT_GUIDE.md` (493 lines)
- **GitHub Setup Guide:** `GITHUB_SETUP_GUIDE.md` (326 lines)
- **Production Deployment:** `PRODUCTION_DEPLOYMENT.md` (395 lines)

---

## 🐛 Troubleshooting

**Backend won't start?**
→ Check Render logs for errors
→ Verify DATABASE_URL and CELERY_BROKER_URL are correct

**Webhooks not working?**
→ Verify webhook token is correct
→ Check API keys are saved
→ Enable auto-trading toggle on Home page

**Emails not sending?**
→ Verify Gmail App Password (16 chars, no spaces)
→ Check SMTP settings in environment variables
→ Check spam folder

**Full troubleshooting:** See `RENDER_DEPLOYMENT_GUIDE.md` section 🔍

---

## 💰 Monthly Cost

**Free Tier (Testing):** $0/month
- Render services sleep after 15min inactivity
- Good for testing and development

**Production Tier (Recommended):** $28/month
- Always-on services
- Better performance
- Suitable for live trading

---

## 🔒 Security Reminders

- ✅ Never commit `.env` files
- ✅ Rotate encryption keys every 90 days
- ✅ Use strong passwords (12+ characters)
- ✅ Keep Gmail 2FA enabled
- ✅ Monitor logs regularly

---

## 📞 Need Help?

1. Check `RENDER_DEPLOYMENT_GUIDE.md` troubleshooting section
2. Review Render logs for error messages
3. Verify all environment variables are set correctly
4. Test each component individually

---

## 🚀 Next Steps After Deployment

1. **Test with real API keys** (start small!)
2. **Set up TradingView alerts** with your webhook URL
3. **Monitor trades daily** for first week
4. **Adjust parameters** based on performance
5. **Consider Phase 3 features:**
   - 2FA authentication
   - Backtesting
   - Admin panel

---

**Happy Trading! 🎯📈**

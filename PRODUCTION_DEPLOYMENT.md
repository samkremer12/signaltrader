# SignalTrader - Production Deployment Guide

This guide explains how to deploy SignalTrader as a fully production-ready, persistent, autonomous crypto trading platform that runs 24/7 with no manual input required.

## Architecture Overview

SignalTrader consists of:
- **Backend API** (FastAPI) - Handles authentication, webhooks, and API endpoints
- **Frontend** (React + Vite) - User interface for configuration and monitoring
- **PostgreSQL** - Persistent database for users, trades, settings, positions
- **Redis** - Message broker and result backend for Celery
- **Celery Worker** - Async task execution for trades
- **Celery Beat** - Periodic task scheduler for trailing stops and monitoring

## Prerequisites

### Required Services
1. **PostgreSQL Database** (v12+)
   - Managed service: AWS RDS, Google Cloud SQL, DigitalOcean Managed Databases, or Supabase
   - Self-hosted: PostgreSQL server with public access

2. **Redis Instance** (v5+)
   - Managed service: AWS ElastiCache, Redis Cloud, DigitalOcean Managed Redis
   - Self-hosted: Redis server with public access

3. **SMTP Email Service** (for notifications)
   - Gmail, SendGrid, AWS SES, Mailgun, or any SMTP provider

### Environment Variables

Create a `.env` file in the backend directory with the following configuration:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@host:5432/signaltrader
# Example: postgresql://signaltrader:mypassword@db.example.com:5432/signaltrader

# Redis Configuration
CELERY_BROKER_URL=redis://host:6379/0
CELERY_RESULT_BACKEND=redis://host:6379/0
# Example: redis://redis.example.com:6379/0
# Example with password: redis://:password@redis.example.com:6379/0

# Security
API_KEY_ENCRYPTION_KEY=your-32-character-encryption-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Sentry Error Reporting (Optional)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# SMTP Email Configuration (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Frontend URL (for CORS)
FRONTEND_URL=https://your-frontend-url.com
```

## Deployment Steps

### 1. Database Setup

**PostgreSQL:**
```sql
-- Create database
CREATE DATABASE signaltrader;

-- Create user (if needed)
CREATE USER signaltrader WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE signaltrader TO signaltrader;
```

The database tables will be created automatically when the backend starts (via SQLAlchemy's `Base.metadata.create_all()`).

### 2. Backend Deployment

**Option A: Deploy to Fly.io (Recommended)**

1. Install Fly.io CLI: `curl -L https://fly.io/install.sh | sh`

2. Login: `fly auth login`

3. Create app: `fly launch` (in backend directory)

4. Set environment variables:
```bash
fly secrets set DATABASE_URL="postgresql://..."
fly secrets set CELERY_BROKER_URL="redis://..."
fly secrets set CELERY_RESULT_BACKEND="redis://..."
fly secrets set API_KEY_ENCRYPTION_KEY="..."
fly secrets set JWT_SECRET_KEY="..."
fly secrets set SMTP_HOST="smtp.gmail.com"
fly secrets set SMTP_PORT="587"
fly secrets set SMTP_USER="your-email@gmail.com"
fly secrets set SMTP_PASSWORD="your-app-password"
```

5. Deploy: `fly deploy`

**Option B: Deploy to any VPS/Cloud Provider**

1. Install dependencies:
```bash
cd crypto-trading-backend
poetry install
```

2. Set environment variables in `.env` file

3. Run backend:
```bash
poetry run fastapi run app/main.py --host 0.0.0.0 --port 8000
```

4. Use a process manager like systemd or supervisor to keep it running

### 3. Celery Worker Deployment

The Celery worker handles async trade execution. It must run continuously.

**Start Celery Worker:**
```bash
cd crypto-trading-backend
poetry run celery -A app.celery_app.celery_app worker --loglevel=info
```

**Systemd Service (Linux):**
Create `/etc/systemd/system/signaltrader-worker.service`:
```ini
[Unit]
Description=SignalTrader Celery Worker
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/crypto-trading-backend
Environment="PATH=/path/to/.local/bin:/usr/bin"
ExecStart=/path/to/poetry run celery -A app.celery_app.celery_app worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable signaltrader-worker
sudo systemctl start signaltrader-worker
```

### 4. Celery Beat Deployment

Celery Beat schedules periodic tasks (trailing stops, system health checks). It must run continuously.

**Start Celery Beat:**
```bash
cd crypto-trading-backend
poetry run celery -A app.celery_app.celery_app beat --loglevel=info
```

**Systemd Service (Linux):**
Create `/etc/systemd/system/signaltrader-beat.service`:
```ini
[Unit]
Description=SignalTrader Celery Beat Scheduler
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/crypto-trading-backend
Environment="PATH=/path/to/.local/bin:/usr/bin"
ExecStart=/path/to/poetry run celery -A app.celery_app.celery_app beat --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable signaltrader-beat
sudo systemctl start signaltrader-beat
```

### 5. Frontend Deployment

1. Update `.env` in frontend directory:
```bash
VITE_API_URL=https://your-backend-url.com
```

2. Build frontend:
```bash
cd crypto-trading-frontend
npm run build
```

3. Deploy the `dist` folder to:
   - Vercel: `vercel deploy`
   - Netlify: `netlify deploy --prod`
   - AWS S3 + CloudFront
   - Any static hosting service

## Production Features

### Automatic Trailing Stop-Loss
- Runs every 30 seconds via Celery Beat
- Monitors all open positions with trailing stops enabled
- Automatically adjusts stop-loss as price moves favorably
- Executes stop-loss orders when price hits trailing stop level

### Email Notifications
- Sent for all trade executions (buy, sell, close)
- Sent when trailing stop-loss is triggered
- Configurable per user in Settings page
- Requires SMTP configuration in environment variables

### System Health Monitoring
- Runs every 5 minutes via Celery Beat
- Tracks active users, trades (24h), and open positions
- Stores health metrics in database
- Available via `/system-health` API endpoint

### Paper Trading Mode
- Simulates trades without real execution
- Uses real market prices for simulation
- Tracks simulated PnL and positions
- Zero fees for paper trades
- Toggle in Settings page

## Monitoring & Maintenance

### Check Celery Worker Status
```bash
# View worker logs
poetry run celery -A app.celery_app.celery_app inspect active

# Check registered tasks
poetry run celery -A app.celery_app.celery_app inspect registered
```

### Check Celery Beat Status
```bash
# View scheduled tasks
poetry run celery -A app.celery_app.celery_app inspect scheduled
```

### Database Backups
```bash
# PostgreSQL backup
pg_dump -h host -U username signaltrader > backup.sql

# Restore
psql -h host -U username signaltrader < backup.sql
```

### Logs
- Backend logs: Check your deployment platform's logging
- Celery logs: Systemd journals or log files
- Sentry: Error tracking and performance monitoring

## Scaling

### Horizontal Scaling
- Run multiple Celery workers for increased throughput
- Use Redis Sentinel or Redis Cluster for high availability
- Use PostgreSQL read replicas for read-heavy workloads

### Vertical Scaling
- Increase worker concurrency: `--concurrency=10`
- Increase database connection pool size
- Optimize Redis memory usage

## Security Checklist

- [ ] Use strong passwords for PostgreSQL and Redis
- [ ] Enable SSL/TLS for database connections
- [ ] Use environment variables for all secrets (never commit to git)
- [ ] Enable Sentry for error tracking
- [ ] Set up database backups (daily recommended)
- [ ] Use HTTPS for all frontend/backend communication
- [ ] Enable rate limiting on API endpoints (already configured)
- [ ] Rotate JWT secret keys periodically
- [ ] Monitor Celery task queue for anomalies

## Troubleshooting

### Celery Worker Not Processing Tasks
1. Check Redis connection: `redis-cli -h host ping`
2. Check worker logs for errors
3. Verify CELERY_BROKER_URL is correct
4. Restart worker: `systemctl restart signaltrader-worker`

### Trailing Stops Not Working
1. Check Celery Beat is running: `systemctl status signaltrader-beat`
2. Check Beat logs for errors
3. Verify trailing_stop_enabled is True in user settings
4. Check open positions have highest_price set

### Email Notifications Not Sending
1. Verify SMTP credentials in environment variables
2. Check SMTP host and port are correct
3. For Gmail: Use App Password, not regular password
4. Check Celery worker logs for email errors

### Database Connection Errors
1. Verify DATABASE_URL is correct
2. Check PostgreSQL is accessible from backend server
3. Verify database user has correct permissions
4. Check PostgreSQL logs for connection errors

## Support

For issues or questions:
- Check logs first (backend, Celery worker, Celery Beat)
- Review Sentry error reports
- Verify all environment variables are set correctly
- Ensure PostgreSQL and Redis are accessible

## Architecture Diagram

```
┌─────────────┐
│  TradingView│
│   Webhooks  │
└──────┬──────┘
       │
       v
┌─────────────────────────────────────────────┐
│           FastAPI Backend                    │
│  - Authentication (JWT)                      │
│  - Webhook endpoints                         │
│  - Trading API                               │
│  - Settings management                       │
└──────┬──────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────┐
│           PostgreSQL Database                │
│  - Users, API keys (encrypted)               │
│  - Trades, positions, logs                   │
│  - Settings, system health                   │
└─────────────────────────────────────────────┘
       ^
       │
┌──────┴──────────────────────────────────────┐
│           Redis (Message Broker)             │
└──────┬──────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────┐
│         Celery Worker (Async Tasks)          │
│  - Execute trades on exchanges               │
│  - Close positions                           │
│  - Send email notifications                  │
└─────────────────────────────────────────────┘
       ^
       │
┌──────┴──────────────────────────────────────┐
│      Celery Beat (Periodic Scheduler)        │
│  - Monitor trailing stops (30s)              │
│  - System health checks (5min)               │
└─────────────────────────────────────────────┘
       ^
       │
┌──────┴──────────────────────────────────────┐
│           React Frontend                     │
│  - User dashboard                            │
│  - Settings configuration                    │
│  - Trade logs and monitoring                 │
└─────────────────────────────────────────────┘
```

## Summary

SignalTrader is now fully production-ready with:
- ✅ Persistent PostgreSQL storage (no data loss on restarts)
- ✅ Redis-backed Celery for async task processing
- ✅ Celery Beat for autonomous 24/7 operation
- ✅ Trailing stop-loss monitoring (every 30 seconds)
- ✅ Email notifications for all trades
- ✅ System health monitoring
- ✅ Paper trading mode
- ✅ Multi-user authentication with JWT
- ✅ Encrypted API key storage (AES-256)
- ✅ Sentry error reporting
- ✅ Rate limiting and security features

Once deployed with PostgreSQL and Redis, the platform will run autonomously 24/7 with no manual input required. Webhooks from TradingView will trigger trades automatically, trailing stops will adjust positions automatically, and email notifications will keep users informed of all activity.

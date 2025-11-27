from celery import Celery
from celery.schedules import crontab
import os
import ssl
from dotenv import load_dotenv

load_dotenv()

# Force low-memory settings via environment variables for Render free tier (512MB)
# These will be picked up by Celery worker even if not specified in start command
os.environ.setdefault('CELERYD_CONCURRENCY', '1')
os.environ.setdefault('CELERYD_PREFETCH_MULTIPLIER', '1')
os.environ.setdefault('CELERYD_MAX_TASKS_PER_CHILD', '50')

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "signal_trader",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks.trading_tasks", "app.tasks.periodic_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    # Memory optimization settings for low-memory environments (512MB)
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,  # Recycle worker after 50 tasks to prevent memory leaks
    worker_disable_rate_limits=True,  # Reduce overhead
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    # SSL configuration for Upstash Redis (rediss://)
    broker_use_ssl={
        "ssl_cert_reqs": ssl.CERT_NONE,
    },
    redis_backend_use_ssl={
        "ssl_cert_reqs": ssl.CERT_NONE,
    },
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'monitor-trailing-stops': {
        'task': 'monitor_trailing_stops',
        'schedule': 30.0,  # Run every 30 seconds
    },
    'system-health-check': {
        'task': 'system_health_check',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
    },
}

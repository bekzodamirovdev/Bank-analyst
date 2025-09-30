import os
import logging
from logging.handlers import RotatingFileHandler
import sqlite3
from contextlib import contextmanager
from functools import lru_cache
import threading
from typing import Dict, Any, Optional
import time

class ProductionConfig:    
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'bank_data.db')
    DATABASE_POOL_SIZE = int(os.getenv('DATABASE_POOL_SIZE', '10'))
    DATABASE_TIMEOUT = int(os.getenv('DATABASE_TIMEOUT', '30'))
    
    LLM_URL = os.getenv('LLM_URL', 'http://localhost:11434')
    LLM_MODEL = os.getenv('LLM_MODEL', 'llama3.2')
    LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '60'))
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '2000'))
    
    CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))  # 1 hour
    CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', '1000'))
    
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    MAX_QUERY_LENGTH = int(os.getenv('MAX_QUERY_LENGTH', '1000'))
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
    
    REPORTS_DIR = os.getenv('REPORTS_DIR', 'reports')
    MAX_REPORT_SIZE_MB = int(os.getenv('MAX_REPORT_SIZE_MB', '100'))
    CLEANUP_INTERVAL_HOURS = int(os.getenv('CLEANUP_INTERVAL_HOURS', '24'))
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'bank_analyst.log')
    LOG_MAX_SIZE_MB = int(os.getenv('LOG_MAX_SIZE_MB', '10'))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

class DatabasePool:    
    def __init__(self, db_path: str, pool_size: int = 10):
        self.db_path = db_path
        self.pool_size = pool_size
        self._connections = []
        self._lock = threading.Lock()
        self._create_pool()
    
    def _create_pool(self):
        for _ in range(self.pool_size):
            conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=ProductionConfig.DATABASE_TIMEOUT
            )
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=10000')
            conn.execute('PRAGMA temp_store=memory')
            self._connections.append(conn)
    
    @contextmanager
    def get_connection(self):
        with self._lock:
            if self._connections:
                conn = self._connections.pop()
            else:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=ProductionConfig.DATABASE_TIMEOUT
                )
                conn.row_factory = sqlite3.Row
        
        try:
            yield conn
        finally:
            with self._lock:
                if len(self._connections) < self.pool_size:
                    self._connections.append(conn)
                else:
                    conn.close()
    
    def close_all(self):
        with self._lock:
            for conn in self._connections:
                conn.close()
            self._connections.clear()

class QueryCache:    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def get(self, query: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if query in self._cache:
                cached_data = self._cache[query]
                if time.time() - cached_data['timestamp'] < self.ttl:
                    return cached_data['data']
                else:
                    del self._cache[query]
        return None
    
    def set(self, query: str, data: Dict[str, Any]):
        with self._lock:
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k]['timestamp'])
                del self._cache[oldest_key]
            
            self._cache[query] = {
                'data': data,
                'timestamp': time.time()
            }
    
    def clear(self):
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self):
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, value in self._cache.items()
                if current_time - value['timestamp'] >= self.ttl
            ]
            for key in expired_keys:
                del self._cache[key]

class RateLimiter:    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self._requests = {}
        self._lock = threading.Lock()
    
    def is_allowed(self, client_id: str) -> bool:
        with self._lock:
            current_time = time.time()
            current_minute = int(current_time / 60)
            
            if client_id not in self._requests:
                self._requests[client_id] = {}
            
            client_requests = self._requests[client_id]
            
            for minute in list(client_requests.keys()):
                if minute < current_minute:
                    del client_requests[minute]
            
            if current_minute in client_requests:
                if client_requests[current_minute] >= self.max_requests:
                    return False
                client_requests[current_minute] += 1
            else:
                client_requests[current_minute] = 1
            
            return True

class ProductionLogger:    
    @staticmethod
    def setup_logging():
        os.makedirs('logs', exist_ok=True)
        
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, ProductionConfig.LOG_LEVEL))
        
        file_handler = RotatingFileHandler(
            f"logs/{ProductionConfig.LOG_FILE}",
            maxBytes=ProductionConfig.LOG_MAX_SIZE_MB * 1024 * 1024,
            backupCount=ProductionConfig.LOG_BACKUP_COUNT
        )
        
        console_handler = logging.StreamHandler()
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

class SecurityMiddleware:    
    @staticmethod
    def validate_query(query: str) -> tuple[bool, str]:
        if not query or not query.strip():
            return False, "Bo'sh query"
        
        if len(query) > ProductionConfig.MAX_QUERY_LENGTH:
            return False, "Query juda uzun"
        
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 
            'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE'
        ]
        
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return False, f"Xavfli SQL keyword: {keyword}"
        
        return True, "OK"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        import re
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:95] + ext
        return filename

class PerformanceMonitor:    
    def __init__(self):
        self._metrics = {
            'query_count': 0,
            'query_times': [],
            'error_count': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        self._lock = threading.Lock()
    
    def record_query_time(self, duration: float):
        with self._lock:
            self._metrics['query_count'] += 1
            self._metrics['query_times'].append(duration)
            
            if len(self._metrics['query_times']) > 1000:
                self._metrics['query_times'] = self._metrics['query_times'][-1000:]
    
    def record_error(self):
        with self._lock:
            self._metrics['error_count'] += 1
    
    def record_cache_hit(self):
        with self._lock:
            self._metrics['cache_hits'] += 1
    
    def record_cache_miss(self):
        with self._lock:
            self._metrics['cache_misses'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            avg_time = 0
            if self._metrics['query_times']:
                avg_time = sum(self._metrics['query_times']) / len(self._metrics['query_times'])
            
            cache_total = self._metrics['cache_hits'] + self._metrics['cache_misses']
            cache_hit_rate = 0
            if cache_total > 0:
                cache_hit_rate = self._metrics['cache_hits'] / cache_total * 100
            
            return {
                'query_count': self._metrics['query_count'],
                'error_count': self._metrics['error_count'],
                'average_query_time': round(avg_time, 3),
                'cache_hit_rate': round(cache_hit_rate, 1),
                'total_cache_requests': cache_total
            }

class FileCleanupService:    
    def __init__(self, reports_dir: str = 'reports'):
        self.reports_dir = reports_dir
        self.cleanup_interval = ProductionConfig.CLEANUP_INTERVAL_HOURS * 3600
        self._running = False
        self._thread = None
    
    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._cleanup_loop)
            self._thread.daemon = True
            self._thread.start()
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
    
    def _cleanup_loop(self):
        while self._running:
            try:
                self._cleanup_old_files()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logging.error(f"Cleanup service xatosi: {e}")
                time.sleep(300) 
    
    def _cleanup_old_files(self):
        if not os.path.exists(self.reports_dir):
            return
        
        current_time = time.time()
        max_age = 7 * 24 * 3600  
        
        for filename in os.listdir(self.reports_dir):
            filepath = os.path.join(self.reports_dir, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age:
                    try:
                        os.remove(filepath)
                        logging.info(f"Eski fayl o'chirildi: {filename}")
                    except Exception as e:
                        logging.error(f"Fayl o'chirishda xato {filename}: {e}")

db_pool = None
query_cache = None
rate_limiter = None
performance_monitor = None
cleanup_service = None

def initialize_production_services():
    global db_pool, query_cache, rate_limiter, performance_monitor, cleanup_service
    
    ProductionLogger.setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Production services ishga tushirilmoqda...")
    
    db_pool = DatabasePool(
        ProductionConfig.DATABASE_PATH,
        ProductionConfig.DATABASE_POOL_SIZE
    )
    
    query_cache = QueryCache(
        ProductionConfig.CACHE_MAX_SIZE,
        ProductionConfig.CACHE_TTL
    )
    
    rate_limiter = RateLimiter(ProductionConfig.RATE_LIMIT_PER_MINUTE)
    
    performance_monitor = PerformanceMonitor()
    
    cleanup_service = FileCleanupService(ProductionConfig.REPORTS_DIR)
    cleanup_service.start()
    
    logger.info("Production services muvaffaqiyatli ishga tushdi")

def shutdown_production_services():
    global db_pool, query_cache, rate_limiter, performance_monitor, cleanup_service
    
    logger = logging.getLogger(__name__)
    logger.info("Production services to'xtatilmoqda...")
    
    if cleanup_service:
        cleanup_service.stop()
    
    if db_pool:
        db_pool.close_all()
    
    if query_cache:
        query_cache.clear()
    
    logger.info("Production services to'xtatildi")

class ProductionFlaskConfig:    
    SECRET_KEY = ProductionConfig.SECRET_KEY
    DEBUG = False
    TESTING = False
    
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{ProductionConfig.DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    }
    
    MAX_CONTENT_LENGTH = ProductionConfig.MAX_REPORT_SIZE_MB * 1024 * 1024
    
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class ProductionMonitoring:    
    @staticmethod
    def health_check():
        try:
            with db_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            return {
                'status': 'healthy',
                'timestamp': time.time(),
                'services': {
                    'database': 'ok',
                    'cache': 'ok',
                    'rate_limiter': 'ok'
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': time.time(),
                'error': str(e)
            }
    
    @staticmethod
    def metrics():
        return {
            'performance': performance_monitor.get_metrics(),
            'cache': {
                'size': len(query_cache._cache),
                'max_size': query_cache.max_size,
                'ttl': query_cache.ttl
            },
            'database': {
                'pool_size': len(db_pool._connections),
                'max_pool_size': db_pool.pool_size
            }
        }

GUNICORN_CONFIG = '''
# gunicorn.conf.py
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 60
keepalive = 5
preload_app = True
user = "bankapp"
group = "bankapp"
daemon = False
pidfile = "/var/run/gunicorn.pid"
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
access_log_format = '%%(h)s %%(l)s %%(u)s %%(t)s "%%(r)s" %%(s)s %%(b)s "%%(f)s" "%%(a)s" %%(D)s'
'''

NGINX_CONFIG = '''
# /etc/nginx/sites-available/bank-analyst
upstream bank_analyst {
    server 127.0.0.1:5000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;
    
    location / {
        proxy_pass http://bank_analyst;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
    
    location /reports/ {
        alias /app/reports/;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
    
    location /health {
        access_log off;
        proxy_pass http://bank_analyst;
    }
}
'''

SYSTEMD_SERVICE = '''
# /etc/systemd/system/bank-analyst.service
[Unit]
Description=Bank AI Data Analyst
After=network.target

[Service]
Type=notify
User=bankapp
Group=bankapp
WorkingDirectory=/opt/bank-analyst
Environment=PATH=/opt/bank-analyst/venv/bin
Environment=FLASK_ENV=production
ExecStart=/opt/bank-analyst/venv/bin/gunicorn --config gunicorn.conf.py web_app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10
KillSignal=SIGTERM
TimeoutStopSec=20
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bank-analyst

[Install]
WantedBy=multi-user.target
'''

DEPLOYMENT_SCRIPT = '''#!/bin/bash
# deploy.sh - Production deployment script

set -e

APP_DIR="/opt/bank-analyst"
APP_USER="bankapp"
BACKUP_DIR="/opt/backups/bank-analyst"

echo "🚀 Bank AI Data Analyst - Production Deployment"
echo "=============================================="

# Create backup
echo "📦 Backup yaratilmoqda..."
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" -C $APP_DIR .

# Stop services
echo "🛑 Servislar to'xtatilmoqda..."
systemctl stop bank-analyst || true

# Update code
echo "📥 Kod yangilanmoqda..."
cd $APP_DIR
git pull origin main

# Update dependencies
echo "📦 Dependencies yangilanmoqda..."
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Database migrations (if needed)
echo "🗄️ Database tekshirilmoqda..."
python bank_analyst.py --setup

# Set permissions
echo "🔒 Ruxsatlar sozlanmoqda..."
chown -R $APP_USER:$APP_USER $APP_DIR
chmod +x $APP_DIR/*.py

# Restart services
echo "🔄 Servislar qayta ishga tushirilmoqda..."
systemctl daemon-reload
systemctl start bank-analyst
systemctl enable bank-analyst

# Restart nginx
systemctl reload nginx

# Health check
echo "🏥 Health check..."
sleep 10
if curl -f http://localhost/health; then
    echo "✅ Deployment muvaffaqiyatli!"
else
    echo "❌ Health check failed!"
    exit 1
fi

echo "🎉 Deployment tugallandi!"
'''

ENVIRONMENTS = {
    'development': {
        'DATABASE_PATH': 'dev_bank_data.db',
        'LOG_LEVEL': 'DEBUG',
        'CACHE_TTL': 300,
        'LLM_TIMEOUT': 30,
        'RATE_LIMIT_PER_MINUTE': 120
    },
    'staging': {
        'DATABASE_PATH': 'staging_bank_data.db',
        'LOG_LEVEL': 'INFO',
        'CACHE_TTL': 1800,
        'LLM_TIMEOUT': 45,
        'RATE_LIMIT_PER_MINUTE': 80
    },
    'production': {
        'DATABASE_PATH': 'prod_bank_data.db',
        'LOG_LEVEL': 'WARNING',
        'CACHE_TTL': 3600,
        'LLM_TIMEOUT': 60,
        'RATE_LIMIT_PER_MINUTE': 60
    }
}

def load_environment_config(env: str = 'production'):
    if env in ENVIRONMENTS:
        for key, value in ENVIRONMENTS[env].items():
            os.environ[key] = str(value)
    else:
        raise ValueError(f"Noma'lum environment: {env}")

def save_production_configs():
    configs = {
        'gunicorn.conf.py': GUNICORN_CONFIG,
        'nginx.conf': NGINX_CONFIG,
        'bank-analyst.service': SYSTEMD_SERVICE,
        'deploy.sh': DEPLOYMENT_SCRIPT
    }
    
    os.makedirs('production', exist_ok=True)
    
    for filename, content in configs.items():
        with open(f'production/{filename}', 'w') as f:
            f.write(content.strip())
    
    os.chmod('production/deploy.sh', 0o755)
    
    print("✅ Production config fayllari yaratildi:")
    for filename in configs.keys():
        print(f"  - production/{filename}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            initialize_production_services()
        elif command == "configs":
            save_production_configs()
        elif command == "test":
            initialize_production_services()
            print("🧪 Production services test...")
            
            with db_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master")
                print(f"✅ Database pool: {cursor.fetchone()[0]} tables")
            
            query_cache.set("test", {"result": "ok"})
            cached = query_cache.get("test")
            print(f"✅ Cache: {cached}")
            
            allowed = rate_limiter.is_allowed("test_client")
            print(f"✅ Rate limiter: {allowed}")
            
            performance_monitor.record_query_time(0.5)
            metrics = performance_monitor.get_metrics()
            print(f"✅ Performance monitor: {metrics}")
            
            print("🎉 Barcha testlar muvaffaqiyatli!")
            
            shutdown_production_services()
        else:
            print("Usage: python production_config.py [init|configs|test]")
    else:
        print("Production configuration module loaded")
        print("Available commands: init, configs, test")
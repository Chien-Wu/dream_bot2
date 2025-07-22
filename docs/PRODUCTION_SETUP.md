# Production Setup Guide

This guide covers deploying Dream Line Bot v2 to production environments with proper security, monitoring, and scalability.

## 📋 Prerequisites

### Infrastructure Requirements
- **Server**: 2+ CPU cores, 4GB+ RAM, 20GB+ storage
- **Database**: MySQL 8.0+ (managed service recommended)
- **Domain**: Valid domain with SSL certificate
- **Monitoring**: Log aggregation and uptime monitoring

### Required Accounts & Services
- LINE Developers Console access
- OpenAI API account with Assistant
- Cloud provider account (AWS/GCP/Azure/DigitalOcean)
- Domain registrar and DNS management

## 🚀 Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Step 1: Server Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

#### Step 2: Application Setup
```bash
# Clone repository
git clone https://github.com/your-username/dream_line_bot_v2.git
cd dream_line_bot_v2

# Create production environment file
cp .env.example .env.production
```

#### Step 3: Configure Production Environment
Edit `.env.production`:
```bash
# Production Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=5000

# Database Configuration (Use managed MySQL service)
MYSQL_HOST=your-production-mysql-host
MYSQL_USER=dream_bot_prod
MYSQL_PASSWORD=your_secure_mysql_password
MYSQL_DATABASE=dream_bot_prod
MYSQL_ROOT_PASSWORD=your_mysql_root_password

# LINE Bot Configuration
LINE_CHANNEL_ACCESS_TOKEN=your_production_line_token
LINE_CHANNEL_SECRET=your_production_line_secret
LINE_ADMIN_USER_ID=your_admin_line_user_id

# OpenAI Configuration
OPENAI_API_KEY=your_production_openai_key
OPENAI_ASSISTANT_ID=your_production_assistant_id
OPENAI_POLL_MAX_RETRIES=120
OPENAI_POLL_INTERVAL=2.0
AI_CONFIDENCE_THRESHOLD=0.83

# Web Search Configuration
SEARCH_DEFAULT_RESULTS=5
SEARCH_MAX_RESULTS=10
SEARCH_TIMEOUT=120.0

# Message Buffer Configuration
MESSAGE_BUFFER_TIMEOUT=10.0
MESSAGE_BUFFER_MAX_SIZE=10
MESSAGE_BUFFER_MIN_LENGTH=50
```

#### Step 4: Deploy with Docker Compose
```bash
# Create production docker-compose override
cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  dream-bot:
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
    volumes:
      - ./logs:/app/logs
      - /etc/localtime:/etc/localtime:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dream-bot.rule=Host(\`your-domain.com\`)"
      - "traefik.http.routers.dream-bot.tls.certresolver=letsencrypt"

  mysql:
    restart: unless-stopped
    volumes:
      - mysql_prod_data:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=\${MYSQL_ROOT_PASSWORD}

volumes:
  mysql_prod_data:
EOF

# Deploy to production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

# Verify deployment
docker-compose logs -f dream-bot
curl http://localhost:5000/health
```

### Option 2: Cloud Platform Deployment

#### Google Cloud Run
```bash
# Build and submit to Cloud Build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/dream-bot .

# Deploy to Cloud Run
gcloud run deploy dream-bot \
  --image gcr.io/YOUR_PROJECT_ID/dream-bot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 5000 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production,LOG_LEVEL=INFO \
  --set-secrets MYSQL_PASSWORD=mysql-password:latest,OPENAI_API_KEY=openai-key:latest
```

#### AWS ECS with Fargate
```bash
# Create ECR repository
aws ecr create-repository --repository-name dream-bot

# Build and push image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker build -t dream-bot .
docker tag dream-bot:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/dream-bot:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/dream-bot:latest

# Create ECS task definition and service (use AWS Console or Terraform)
```

#### DigitalOcean App Platform
Create `.do/app.yaml`:
```yaml
name: dream-line-bot
services:
- name: web
  source_dir: /
  github:
    repo: your-username/dream_line_bot_v2
    branch: main
  build_command: pip install -r requirements.txt
  run_command: python main.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 5000
  envs:
  - key: ENVIRONMENT
    value: production
    type: STATIC
  - key: LOG_LEVEL
    value: INFO
    type: STATIC
  - key: MYSQL_HOST
    value: ${db.HOSTNAME}
    type: SECRET
  - key: MYSQL_PASSWORD
    value: ${db.PASSWORD}
    type: SECRET

databases:
- name: db
  engine: MYSQL
  version: "8"
```

### Option 3: VPS/Dedicated Server

#### Step 1: Server Setup (Ubuntu 22.04)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv mysql-server nginx certbot python3-certbot-nginx git htop curl

# Secure MySQL installation
sudo mysql_secure_installation

# Create application user
sudo adduser --system --group --home /opt/dream-bot dream-bot

# Setup application directory
sudo mkdir -p /opt/dream-bot
sudo chown dream-bot:dream-bot /opt/dream-bot
```

#### Step 2: Application Installation
```bash
# Switch to application user
sudo -u dream-bot -i

# Clone repository
cd /opt/dream-bot
git clone https://github.com/your-username/dream_line_bot_v2.git .

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create production config
cp .env.example .env
# Edit .env with production values

# Test application
python main.py
```

#### Step 3: Database Setup
```bash
# Create production database
sudo mysql -u root -p << EOF
CREATE DATABASE dream_bot_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'dream_bot_prod'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON dream_bot_prod.* TO 'dream_bot_prod'@'localhost';
FLUSH PRIVILEGES;
EOF

# Initialize database tables
mysql -u dream_bot_prod -p dream_bot_prod < scripts/init.sql
```

#### Step 4: Systemd Service Setup
Create `/etc/systemd/system/dream-bot.service`:
```ini
[Unit]
Description=Dream Line Bot
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=simple
User=dream-bot
Group=dream-bot
WorkingDirectory=/opt/dream-bot
Environment=PATH=/opt/dream-bot/venv/bin
EnvironmentFile=/opt/dream-bot/.env
ExecStart=/opt/dream-bot/venv/bin/python main.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dream-bot

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/dream-bot/logs

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable dream-bot
sudo systemctl start dream-bot
sudo systemctl status dream-bot

# Check logs
sudo journalctl -u dream-bot -f
```

#### Step 5: Nginx Reverse Proxy
Create `/etc/nginx/sites-available/dream-bot`:
```nginx
upstream dream_bot {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration (will be handled by certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Logging
    access_log /var/log/nginx/dream-bot.access.log;
    error_log /var/log/nginx/dream-bot.error.log;

    location / {
        proxy_pass http://dream_bot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://dream_bot/health;
        access_log off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/dream-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Setup SSL with Let's Encrypt
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## 🔒 Security Configuration

### 1. Firewall Setup
```bash
# Configure UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

### 2. SSL/TLS Configuration
```bash
# Auto-renewal setup
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet

# Test renewal
sudo certbot renew --dry-run
```

### 3. Environment Security
```bash
# Secure environment file
sudo chmod 600 /opt/dream-bot/.env
sudo chown dream-bot:dream-bot /opt/dream-bot/.env

# Rotate secrets regularly
# Use external secret management for production
```

### 4. Database Security
```bash
# Configure MySQL for production
sudo mysql -u root -p << EOF
# Remove test database
DROP DATABASE IF EXISTS test;

# Secure root account
ALTER USER 'root'@'localhost' IDENTIFIED BY 'strong_root_password';

# Configure logging
SET GLOBAL general_log = 'ON';
SET GLOBAL general_log_file = '/var/log/mysql/general.log';
EOF

# Configure automated backups
sudo crontab -e
# Add: 0 2 * * * mysqldump -u root -p'password' dream_bot_prod > /backup/dream_bot_$(date +%Y%m%d).sql
```

## 📊 Monitoring & Logging

### 1. Application Monitoring
```bash
# Install monitoring agent (example: New Relic)
pip install newrelic

# Configure in main.py
import newrelic.agent
newrelic.agent.initialize('/opt/dream-bot/newrelic.ini')

@newrelic.agent.wsgi_application()
def application(environ, start_response):
    # Your Flask app
    pass
```

### 2. Log Management
```bash
# Configure log rotation
sudo cat > /etc/logrotate.d/dream-bot << EOF
/opt/dream-bot/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    postrotate
        systemctl reload dream-bot
    endscript
}
EOF

# Setup centralized logging (optional)
# Configure rsyslog to forward to ELK stack or cloud logging
```

### 3. Health Checks
```bash
# Setup monitoring script
cat > /opt/dream-bot/health_check.sh << 'EOF'
#!/bin/bash
HEALTH_URL="https://your-domain.com/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): Health check passed"
else
    echo "$(date): Health check failed with code $RESPONSE"
    # Send alert (email, Slack, etc.)
fi
EOF

chmod +x /opt/dream-bot/health_check.sh

# Add to crontab
echo "*/5 * * * * /opt/dream-bot/health_check.sh >> /var/log/dream-bot-health.log" | sudo crontab -
```

## 🚀 Deployment Automation

### 1. CI/CD with GitHub Actions
The project includes automated deployment workflows in `.github/workflows/`:

- **ci.yml**: Automated testing and security scanning
- **release.yml**: Automated releases and Docker image building

### 2. Deployment Script
Create `deploy.sh`:
```bash
#!/bin/bash
set -e

echo "🚀 Deploying Dream Line Bot..."

# Pull latest changes
git pull origin main

# Backup current deployment
sudo systemctl stop dream-bot
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations (if any)
python scripts/migrate.py

# Test configuration
python -c "from config import config; print('✅ Configuration valid')"

# Restart service
sudo systemctl start dream-bot
sudo systemctl reload nginx

# Verify deployment
sleep 10
curl -f https://your-domain.com/health || {
    echo "❌ Health check failed, rolling back..."
    sudo systemctl stop dream-bot
    git checkout HEAD~1
    sudo systemctl start dream-bot
    exit 1
}

echo "✅ Deployment successful!"
```

## 🔧 LINE Bot Configuration

### 1. Update Webhook URL
1. Go to [LINE Developers Console](https://developers.line.biz/)
2. Select your channel
3. Navigate to Messaging API settings
4. Update Webhook URL to: `https://your-domain.com/callback`
5. Enable "Use webhook"
6. Verify webhook

### 2. Test Webhook
```bash
# Test from LINE console or send message to bot
# Check logs for successful processing
sudo journalctl -u dream-bot -f
```

## 📈 Performance Optimization

### 1. Database Optimization
```sql
-- Add indexes for better performance
CREATE INDEX idx_user_threads_user_id ON user_threads(user_id);
CREATE INDEX idx_message_history_user_id ON message_history(user_id);
CREATE INDEX idx_message_history_created_at ON message_history(created_at);

-- Configure MySQL for production
[mysqld]
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
max_connections = 200
query_cache_size = 64M
```

### 2. Application Scaling
```bash
# For high traffic, consider:
# - Load balancer (nginx/HAProxy)
# - Multiple app instances
# - Redis for session storage
# - Database read replicas
# - CDN for static assets
```

## 🚨 Troubleshooting

### Common Issues
1. **Database Connection**: Check MySQL credentials and firewall
2. **SSL Certificate**: Verify domain DNS and certificate renewal
3. **Memory Issues**: Monitor RAM usage and adjust instance size
4. **Rate Limiting**: Configure appropriate limits for your traffic

### Debug Commands
```bash
# Check service status
sudo systemctl status dream-bot

# View logs
sudo journalctl -u dream-bot -f
tail -f /opt/dream-bot/logs/dream_bot.log

# Test database connection
mysql -u dream_bot_prod -p dream_bot_prod -e "SELECT 1;"

# Test application health
curl -v https://your-domain.com/health
```

## 📞 Support

For production issues:
1. Check application logs first
2. Verify external service status (LINE API, OpenAI API)
3. Monitor resource usage (CPU, memory, disk)
4. Review recent changes and deployments

---

**🎉 Congratulations!** Your Dream Line Bot is now running in production with enterprise-grade security, monitoring, and scalability.
# 🚀 Production Deployment Guide

## ✅ Pre-Deployment Checklist

### 1. **Environment Setup**

- [ ] Server with Ubuntu 22.04+ or similar
- [ ] Domain name configured with DNS pointing to your server
- [ ] SSL certificate (Let's Encrypt recommended)
- [ ] Docker and Docker Compose installed

### 2. **Required Accounts & Credentials**

- [ ] LINE Channel Access Token and Secret
- [ ] OpenAI API Key with sufficient credits
- [ ] MySQL production credentials
- [ ] LINE Admin User ID

### 3. **Production Configuration**

- [ ] `.env.production` file created with production values
- [ ] All sensitive credentials secured (not in version control)
- [ ] Database connection tested
- [ ] LINE webhook URL updated to production domain

---

## 🐳 Docker Deployment (Recommended)

### Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes
```

### Step 2: Application Setup

```bash
# Clone your repository
git clone https://github.com/Chien-Wu/dream_bot2.git
cd dream_bot2

# Create production environment file
cp .env.example .env.production
```

### Step 3: Configure Production Environment

Edit `.env.production`:

```bash
# Application Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=5000

# Database Configuration
MYSQL_HOST=mysql
MYSQL_USER=dream_bot
MYSQL_PASSWORD=your_secure_mysql_password_here
MYSQL_DATABASE=dream_bot_db
MYSQL_ROOT_PASSWORD=your_mysql_root_password_here

# LINE Bot Configuration
LINE_CHANNEL_ACCESS_TOKEN=your_production_line_channel_access_token
LINE_CHANNEL_SECRET=your_production_line_channel_secret
LINE_ADMIN_USER_ID=your_line_admin_user_id

# OpenAI Configuration
OPENAI_API_KEY=your_production_openai_api_key
AI_CONFIDENCE_THRESHOLD=0.83
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=2048
OPENAI_TEMPERATURE=0.7
OPENAI_VECTOR_STORE_ID=your_vector_store_id
SHOW_AI_DEBUG_INFO=false

# Message Buffer Configuration
MESSAGE_BUFFER_TIMEOUT=10.0
MESSAGE_BUFFER_MAX_SIZE=10
MESSAGE_BUFFER_MAX_CHINESE_CHARS=1000

# Handover Configuration
HANDOVER_TIMEOUT_HOURS=1
HANDOVER_CLEANUP_INTERVAL_MINUTES=15
```

### Step 4: Deploy Application

```bash
# Build and start services
docker-compose --env-file .env.production up -d

# Check if services are running
docker-compose ps

# View logs
docker-compose logs -f dream-bot
```

### Step 5: Verify Deployment

```bash
# Test health endpoint
curl http://localhost:5000/health

# Should return: {"service":"dream-line-bot","status":"healthy"}

# Check database connection
docker-compose exec dream-bot python -c "from src.services.database_service import DatabaseService; db = DatabaseService(); print('✅ Database connected')"
```

---

## 🌐 Nginx Reverse Proxy (Production Domain)

### Step 1: Install Nginx

```bash
sudo apt install nginx certbot python3-certbot-nginx
```

### Step 2: Configure Nginx

Create `/etc/nginx/sites-available/dream-bot`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for LINE webhook
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://localhost:5000/health;
        access_log off;
    }
}
```

### Step 3: Enable Site and SSL

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/dream-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test SSL renewal
sudo certbot renew --dry-run
```

---

## 🔗 LINE Bot Configuration

### Step 1: Update Webhook URL

1. Go to [LINE Developers Console](https://developers.line.biz/)
2. Select your channel
3. Go to **Messaging API** tab
4. Update **Webhook URL** to: `https://your-domain.com/callback`
5. Enable **Use webhook**
6. Click **Verify** to test the connection

### Step 2: Test Webhook

```bash
# Monitor logs while testing
docker-compose logs -f dream-bot

# Send a test message to your LINE bot
# You should see the message processing in logs
```

---

## 🔒 Security Configuration

### Step 1: Firewall Setup

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Step 2: Secure Environment Files

```bash
sudo chmod 600 .env.production
sudo chown $USER:$USER .env.production
```

### Step 3: Regular Security Updates

```bash
# Add to crontab for automatic updates
echo "0 2 * * 0 apt update && apt upgrade -y" | sudo crontab -
```

---

## 📊 Monitoring & Maintenance

### Step 1: Health Monitoring

Create `/opt/dream-bot/health_monitor.sh`:

```bash
#!/bin/bash
HEALTH_URL="https://your-domain.com/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): ✅ Health check passed"
else
    echo "$(date): ❌ Health check failed with code $RESPONSE"
    # Restart services if health check fails
    cd /path/to/dream_bot2
    docker-compose restart dream-bot
fi
```

### Step 2: Automated Backups

```bash
# Add database backup to crontab
echo "0 3 * * * docker-compose exec mysql mysqldump -u root -p\$MYSQL_ROOT_PASSWORD dream_bot_db > /backup/dream_bot_\$(date +%Y%m%d).sql" | crontab -
```

### Step 3: Log Management

```bash
# Configure log rotation
sudo tee /etc/logrotate.d/dream-bot << EOF
/path/to/dream_bot2/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
```

---

## 🚨 Troubleshooting

### Common Issues & Solutions

**1. Docker containers won't start**

```bash
docker-compose logs dream-bot
# Check for missing environment variables or database connection issues
```

**2. LINE webhook fails**

```bash
# Check if port 5000 is accessible
sudo netstat -tulpn | grep :5000

# Test health endpoint locally
curl http://localhost:5000/health
```

**3. Database connection errors**

```bash
# Check if MySQL container is running
docker-compose ps mysql

# Test database connection
docker-compose exec mysql mysql -u dream_bot -p dream_bot_db
```

**4. SSL certificate issues**

```bash
# Check certificate status
sudo certbot certificates

# Renew certificates manually
sudo certbot renew --force-renewal
```

---

## 🔄 Updates & Deployment

### Production Update Process

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose --env-file .env.production down
docker-compose --env-file .env.production up -d --build

# Verify deployment
curl https://your-domain.com/health
```

---

## 📞 Production Support

### Essential Commands

```bash
# View application logs
docker-compose logs -f dream-bot

# Check system resources
docker stats

# Database backup
docker-compose exec mysql mysqldump -u root -p dream_bot_db > backup.sql

# Restart specific service
docker-compose restart dream-bot
```

### Monitoring Endpoints

- **Health Check**: `https://your-domain.com/health`
- **LINE Webhook**: `https://your-domain.com/callback`

---

## ✅ Final Checklist

Before going live:

- [ ] All environment variables configured correctly
- [ ] Database is accessible and tables initialized
- [ ] Health endpoint returns 200 OK
- [ ] LINE webhook verified and working
- [ ] SSL certificate installed and valid
- [ ] Firewall properly configured
- [ ] Monitoring and backup scripts in place
- [ ] Admin notifications working

**🎉 Your Dream Line Bot is now ready for production!**

# Deployment Guide for Vultr Server

## Server Details
- **IP:** 192.248.181.245
- **OS:** Ubuntu 22.04 x64
- **Port:** 9000 (verified available, to avoid conflicts)

## Step-by-Step Deployment

### 1. Connect to Your Server
```bash
ssh root@192.248.181.245
```

### 2. Install Dependencies
```bash
# Update system
apt update && apt upgrade -y

# Install Python 3 and pip
apt install python3 python3-pip python3-venv -y

# Install git (if you want to use git)
apt install git -y
```

### 3. Create Application Directory
```bash
mkdir -p /var/www/maltese-law-rag
cd /var/www/maltese-law-rag
```

### 4. Upload Your Code
**Option A: Using SCP from your Windows machine**
```powershell
# Run this on your Windows machine
scp -r "c:\Users\Jake\Downloads\maltese-law-rag\maltese-law-rag\*" root@192.248.181.245:/var/www/maltese-law-rag/
```

**Option B: Using Git**
```bash
# If your code is in a git repo
git clone <your-repo-url> .
```

### 5. Create .env File on Server
```bash
cat > /var/www/maltese-law-rag/.env << 'EOF'
VOYAGE_API_KEY=your_voyage_api_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
GOOGLE_API_KEY=your_google_api_key_here

# Anthropic API (for Citations API - verified citations)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Vertex AI Configuration
GOOGLE_CLOUD_PROJECT=divine-ceremony-482509-b8
GOOGLE_APPLICATION_CREDENTIALS=path_to_service_account.json
VERTEX_AI_LOCATION=europe-west1

# Anthropic Model
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=6267645736

# Admin Dashboard Authentication
ADMIN_KEY=your_admin_key_here

# Server Configuration
PORT=9000
FLASK_ENV=production
FLASK_DEBUG=0
EOF
```

### 6. Install Python Dependencies
```bash
cd /var/www/maltese-law-rag

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install flask flask-cors flask-limiter python-dotenv anthropic requests voyageai google-generativeai

# If you have a requirements.txt
pip install -r requirements.txt
```

### 7. Create Systemd Service (Keep it Running)
```bash
cat > /etc/systemd/system/maltese-law-rag.service << 'EOF'
[Unit]
Description=Maltese Law RAG API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/maltese-law-rag
Environment="PATH=/var/www/maltese-law-rag/venv/bin"
ExecStart=/var/www/maltese-law-rag/venv/bin/python api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service to start on boot
systemctl enable maltese-law-rag

# Start the service
systemctl start maltese-law-rag

# Check status
systemctl status maltese-law-rag
```

### 8. Configure Firewall
```bash
# Allow port 9000
ufw allow 9000/tcp

# Check firewall status
ufw status
```

### 9. Access Your Application
Your app will be available at:
- **Main Chat:** http://192.248.181.245:9000
- **Admin Dashboard:** http://192.248.181.245:9000/admin
- **RAG Verification:** http://192.248.181.245:9000/verify

**Login Credentials:**
- Username: `axis`
- Password: `1616`

## Management Commands

### View Logs
```bash
# Real-time logs
journalctl -u maltese-law-rag -f

# Last 100 lines
journalctl -u maltese-law-rag -n 100
```

### Restart Service
```bash
systemctl restart maltese-law-rag
```

### Stop Service
```bash
systemctl stop maltese-law-rag
```

### Update Application
```bash
cd /var/www/maltese-law-rag
source venv/bin/activate
git pull  # If using git
systemctl restart maltese-law-rag
```

## Optional: Set Up Nginx Reverse Proxy

If you want to use a domain name instead of IP:port:

```bash
# Install nginx
apt install nginx -y

# Create nginx config
cat > /etc/nginx/sites-available/maltese-law-rag << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # Change this to your domain

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/maltese-law-rag /etc/nginx/sites-enabled/

# Test nginx config
nginx -t

# Restart nginx
systemctl restart nginx
```

## Troubleshooting

### Service won't start
```bash
# Check for errors
journalctl -u maltese-law-rag -n 50

# Check if port is already in use
ss -tulpn | grep 9000

# Test manually
cd /var/www/maltese-law-rag
source venv/bin/activate
python api.py
```

### Database issues
```bash
# Check if database file exists
ls -la /var/www/maltese-law-rag/*.db
ls -la /var/www/maltese-law-rag/*.sqlite
```

### API Keys not working
```bash
# Check .env file
cat /var/www/maltese-law-rag/.env

# Make sure it's being loaded
cd /var/www/maltese-law-rag
source venv/bin/activate
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('ANTHROPIC_API_KEY'))"
```

## Security Recommendations

1. **Change default credentials** in production
2. **Use HTTPS** with Let's Encrypt (if using domain)
3. **Set up firewall** properly with ufw
4. **Regular backups** of the database
5. **Monitor logs** for suspicious activity

## Quick Start (Copy-Paste)

Here's everything in one go:

```bash
# 1. Connect
ssh root@192.248.181.245

# 2. Install dependencies
apt update && apt upgrade -y
apt install python3 python3-pip python3-venv git -y

# 3. Create directory
mkdir -p /var/www/maltese-law-rag
cd /var/www/maltese-law-rag

# 4. Upload code (do this from your Windows machine via SCP)

# 5. Continue on server...
# (Follow steps 5-8 above)
```



# 🚀 Quick Deployment to Vultr Server

## Option 1: Automated Deployment (Easiest)

### Step 1: Upload Files from Windows
Open PowerShell and run:
```powershell
cd "c:\Users\Jake\Downloads\maltese-law-rag\maltese-law-rag"
.\deploy.ps1
```

### Step 2: SSH into Server
```powershell
ssh root@192.248.181.245
```

### Step 3: Navigate to App Directory
```bash
cd /var/www/maltese-law-rag
```

### Step 4: Run Setup Script
```bash
chmod +x setup_server.sh
./setup_server.sh
```

**Done!** Your app will be running on port 8080.

---

## Option 2: Manual Deployment

### Step 1: Upload Files
```powershell
# From Windows PowerShell
scp -r "c:\Users\Jake\Downloads\maltese-law-rag\maltese-law-rag\*" root@192.248.181.245:/var/www/maltese-law-rag/
```

### Step 2: SSH into Server
```bash
ssh root@192.248.181.245
```

### Step 3: Install Dependencies
```bash
cd /var/www/maltese-law-rag
apt update && apt install -y python3 python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors flask-limiter python-dotenv anthropic requests voyageai google-generativeai
```

### Step 4: Start the Application

**Quick Test (temporary):**
```bash
source venv/bin/activate
python api.py
```

**Permanent (runs in background):**
```bash
chmod +x setup_server.sh
./setup_server.sh
```

---

## Access Your Application

Once deployed, access at:

- **Main Chat Interface:** http://192.248.181.245:9000
- **Admin Dashboard:** http://192.248.181.245:9000/admin
- **RAG Verification:** http://192.248.181.245:9000/verify

### Login Credentials:
- **Username:** `axis`
- **Password:** `1616`

---

## Management Commands

```bash
# View real-time logs
journalctl -u maltese-law-rag -f

# Restart service
systemctl restart maltese-law-rag

# Stop service
systemctl stop maltese-law-rag

# Check status
systemctl status maltese-law-rag
```

---

## Environment Variables (.env file)

The `.env` file is automatically created with your API keys on the server:

```bash
PORT=9000                    # Server port (changed to avoid conflicts)
FLASK_ENV=production         # Production mode
FLASK_DEBUG=0                # Debug disabled
ANTHROPIC_API_KEY=...        # Same as your local keys
TELEGRAM_BOT_TOKEN=...       # Telegram notifications
TELEGRAM_CHAT_ID=6267645736  # Your Telegram chat ID
ADMIN_KEY=your_admin_key_here           # Admin dashboard key
```

All your API keys are preserved from your local setup.

---

## Telegram Notifications

Remember to start your Telegram bot if you haven't already:

1. Open: https://t.me/MalteseLegalRagBot
2. Click **Start**
3. You'll now receive notifications when clients ask questions!

---

## Troubleshooting

### Port 9000 already in use?
```bash
# Check what's using port 9000
ss -tulpn | grep 9000

# Change port in .env file
nano /var/www/maltese-law-rag/.env
# Change PORT=9000 to another port (e.g., PORT=9001)

# Restart service
systemctl restart maltese-law-rag
```

### Service won't start?
```bash
# Check logs
journalctl -u maltese-law-rag -n 50

# Try running manually to see errors
cd /var/www/maltese-law-rag
source venv/bin/activate
python api.py
```

### Firewall blocking access?
```bash
# Allow your port through firewall
ufw allow 9000/tcp
ufw status
```

---

## Next Steps

After deployment:

1. ✅ Test the login at http://192.248.181.245:9000
2. ✅ Ask a test question to verify Telegram notifications
3. ✅ Check admin dashboard at http://192.248.181.245:9000/admin
4. ✅ Share the URL and credentials with your client

**Client Access:**
- URL: http://192.248.181.245:9000
- Username: axis
- Password: 1616

That's it! Your Maltese Law RAG is now live! 🎉


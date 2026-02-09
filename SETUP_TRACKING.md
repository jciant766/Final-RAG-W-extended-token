# User Tracking & Telegram Notifications Setup

This guide explains how to set up user tracking and Telegram notifications for monitoring client usage.

## Features

- User authentication with API tokens
- Query logging (every question asked, response length, sources used)
- Telegram notifications for new users and queries
- Admin dashboard to monitor all users and their activity
- IP address and user agent tracking

## Quick Setup

### 1. Set up Telegram Bot (Optional but Recommended)

1. **Create a Telegram Bot:**
   - Open Telegram and message [@BotFather](https://t.me/BotFather)
   - Send `/newbot` command
   - Follow the instructions (choose a name and username for your bot)
   - Copy the **bot token** (looks like: `your_telegram_bot_token_here`)

2. **Get Your Chat ID:**
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram
   - It will reply with your user ID (a number like: `123456789`)
   - This is your TELEGRAM_CHAT_ID

3. **Start Conversation with Your Bot:**
   - Search for your bot on Telegram (using the username you chose)
   - Send `/start` to your bot
   - Now it can send you messages!

4. **Update .env file:**
   ```bash
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TELEGRAM_CHAT_ID=123456789
   ADMIN_KEY=your_secure_password_here
   ```

### 2. Create Your First User

You can create users either via API or Python script:

#### Option A: Via API (using curl or Postman)

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "trial_client",
    "password": "secure_password_123",
    "email": "client@example.com",
    "notes": "Free trial - Company XYZ"
  }'
```

Response will include the API token - **save this!**

#### Option B: Via Python Script

```python
from user_tracking import tracker

result = tracker.create_user(
    username="trial_client",
    password="secure_password_123",
    email="client@example.com",
    notes="Free trial - Company XYZ"
)

print(f"API Token: {result['api_token']}")
# Save this token and give it to your client
```

### 3. Access Admin Dashboard

1. Open: http://localhost:5000/admin
2. Enter your ADMIN_KEY (from .env file)
3. View all users, their query counts, and recent questions

## How Clients Use the System

### Client Authentication

Clients need to include their API token in every request to `/api/chat`:

#### Option 1: Authorization Header (Recommended)
```javascript
fetch('/api/chat', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_API_TOKEN_HERE'
    },
    body: JSON.stringify({
        message: "What are the penalties for tax evasion?"
    })
})
```

#### Option 2: In Request Body
```javascript
fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        message: "What are the penalties for tax evasion?",
        token: "YOUR_API_TOKEN_HERE"
    })
})
```

### What Gets Tracked

Every time a client asks a question, the system logs:
- User ID and username
- Full query text
- Response length (characters)
- Number of sources cited
- IP address
- User agent (browser info)
- Timestamp

### Telegram Notifications

You'll receive real-time Telegram messages for:

1. **New User Registration:**
   ```
   🆕 New user created:
   👤 trial_client
   📧 client@example.com
   📝 Free trial - Company XYZ
   ```

2. **Every Query:**
   ```
   💬 New query from trial_client:

   ❓ What are the penalties for tax evasion in Malta?

   📊 Response: 1247 chars, 3 sources
   ```

## Admin API Endpoints

All admin endpoints require `admin_key` parameter:

### Get All Users
```bash
GET /api/admin/users?admin_key=YOUR_ADMIN_KEY
```

### Get User Stats
```bash
GET /api/admin/users/1/stats?admin_key=YOUR_ADMIN_KEY
```

### Deactivate User
```bash
POST /api/admin/users/1/deactivate?admin_key=YOUR_ADMIN_KEY
```

## Database

User data is stored in `user_tracking.db` SQLite database with three tables:

- **users**: User accounts with passwords, tokens, query counts
- **usage_logs**: Every query with full text and metadata
- **sessions**: Web session tokens (for future web login)

## Security Notes

1. **API Tokens**: 32-byte random tokens using `secrets.token_urlsafe()`
2. **Passwords**: Hashed with SHA256 (consider upgrading to bcrypt for production)
3. **Admin Key**: Change the default in .env immediately
4. **HTTPS**: Use HTTPS in production to protect tokens in transit
5. **Rate Limiting**: Already configured (30 requests/minute)

## Production Deployment

Before deploying:

1. ✅ Change ADMIN_KEY to a strong password
2. ✅ Set up Telegram bot for notifications
3. ✅ Use HTTPS (tokens in plain HTTP are insecure)
4. ✅ Consider upgrading password hashing to bcrypt
5. ✅ Set up database backups for user_tracking.db
6. ✅ Review CORS settings in api.py for your domain

## Troubleshooting

### Not receiving Telegram notifications?

1. Check bot token and chat ID are correct in .env
2. Make sure you sent `/start` to your bot
3. Check Flask logs for "Failed to send Telegram notification"

### Client getting 401 errors?

1. Verify token is being sent correctly (check request headers/body)
2. Check if user is still active (not deactivated)
3. Verify token matches exactly (no extra spaces)

### Admin dashboard not loading?

1. Verify ADMIN_KEY in .env matches what you're entering
2. Check browser console for errors
3. Ensure Flask server is running

## Example: Monitoring Your Trial Client

1. Create user and give them the API token
2. They integrate it into their application
3. You receive Telegram notification every time they ask a question
4. Check admin dashboard to see:
   - Total query count
   - Recent questions asked
   - When they last used the system
5. After trial ends, deactivate their account via admin panel

## Need Help?

Check the logs:
```bash
tail -f logs/api.log
```

Or examine the database directly:
```bash
sqlite3 user_tracking.db
SELECT * FROM users;
SELECT * FROM usage_logs ORDER BY timestamp DESC LIMIT 10;
```


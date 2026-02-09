#!/bin/bash
# Server Setup Script for Maltese Law RAG
# Run this on your Ubuntu server after uploading the files

set -e  # Exit on error

echo "======================================"
echo "Maltese Law RAG - Server Setup"
echo "======================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
apt update
apt install -y python3 python3-pip python3-venv

# Create virtual environment
echo ""
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python packages
echo ""
echo "📚 Installing Python packages..."
pip install --upgrade pip
pip install flask flask-cors flask-limiter python-dotenv anthropic requests voyageai google-generativeai

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "⚙️  Creating .env file..."
    cat > .env << 'EOF'
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
else
    echo ""
    echo "✓ .env file already exists, skipping..."
fi

# Create systemd service
echo ""
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/maltese-law-rag.service << EOF
[Unit]
Description=Maltese Law RAG API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin"
ExecStart=$SCRIPT_DIR/venv/bin/python api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo ""
echo "🚀 Enabling and starting service..."
systemctl daemon-reload
systemctl enable maltese-law-rag
systemctl start maltese-law-rag

# Check if UFW is active and configure it
if command -v ufw &> /dev/null; then
    echo ""
    echo "🔥 Configuring firewall..."
    ufw allow 9000/tcp
    echo "✓ Port 9000 opened"
fi

# Show service status
echo ""
echo "======================================"
echo "✓ Installation Complete!"
echo "======================================"
echo ""
echo "Service Status:"
systemctl status maltese-law-rag --no-pager
echo ""
echo "======================================"
echo "Your application is now running!"
echo ""
echo "Access URLs:"
echo "  • Main Chat: http://$(curl -s ifconfig.me):9000"
echo "  • Admin Dashboard: http://$(curl -s ifconfig.me):9000/admin"
echo "  • RAG Verification: http://$(curl -s ifconfig.me):9000/verify"
echo ""
echo "Login Credentials:"
echo "  • Username: axis"
echo "  • Password: 1616"
echo ""
echo "Management Commands:"
echo "  • View logs: journalctl -u maltese-law-rag -f"
echo "  • Restart: systemctl restart maltese-law-rag"
echo "  • Stop: systemctl stop maltese-law-rag"
echo "======================================"



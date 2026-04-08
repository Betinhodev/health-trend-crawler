#!/bin/bash
# Health Trend Crawler - Setup Script
# Run this once on your VPS to configure everything

set -e

echo "=================================="
echo " Health Trend Crawler - Setup"
echo "=================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 1. CREATE DIRECTORIES
echo ""
echo "[1/6] Creating directories..."
mkdir -p data/raw data/reports data/logs public/history

# 2. PYTHON VIRTUAL ENVIRONMENT
echo ""
echo "[2/6] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Virtual environment created"
else
    echo "  Virtual environment already exists"
fi

source venv/bin/activate

# 3. INSTALL DEPENDENCIES
echo ""
echo "[3/6] Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  Dependencies installed"

# 4. VERIFY CLAUDE CODE CLI
echo ""
echo "[4/6] Checking Claude Code CLI..."
if command -v claude &> /dev/null; then
    echo "  Claude Code CLI found: $(which claude)"
else
    echo "  WARNING: Claude Code CLI not found in PATH!"
    echo "  Make sure 'claude' is installed and available."
    echo "  Install: npm install -g @anthropic-ai/claude-code"
fi

# 5. INSTALL & CONFIGURE CADDY
echo ""
echo "[5/6] Setting up Caddy web server..."
if command -v caddy &> /dev/null; then
    echo "  Caddy already installed: $(caddy version)"
else
    echo "  Installing Caddy..."
    sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl 2>/dev/null || true
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list 2>/dev/null || true
    sudo apt update -q 2>/dev/null && sudo apt install -y caddy 2>/dev/null || echo "  Could not install Caddy automatically. Install manually: https://caddyserver.com/docs/install"
fi

# Create log directory for Caddy
sudo mkdir -p /var/log/caddy 2>/dev/null || true

# Set up password for dashboard
echo ""
echo "  Setting up dashboard password..."
echo "  You'll be asked to set a password for accessing the dashboard."
echo "  Username will be: gilberto"
echo ""

if command -v caddy &> /dev/null; then
    echo "  Enter a password for the dashboard (it will be hidden):"
    HASH=$(caddy hash-password 2>/dev/null) || true
    if [ -n "$HASH" ]; then
        sed -i "s|\\\$2a\\\$14\\\$REPLACE_WITH_CADDY_HASH_PASSWORD|$HASH|g" "$PROJECT_DIR/Caddyfile"
        echo "  Password configured!"
    else
        echo "  WARNING: Could not generate password hash."
        echo "  Run manually: caddy hash-password"
        echo "  Then update the Caddyfile with the hash."
    fi
fi

# Copy Caddyfile to system location or use custom path
if [ -d "/etc/caddy" ]; then
    sudo cp "$PROJECT_DIR/Caddyfile" /etc/caddy/Caddyfile
    sudo systemctl restart caddy 2>/dev/null || true
    echo "  Caddy configured and restarted"
else
    echo "  NOTE: Copy Caddyfile manually or run: caddy run --config $PROJECT_DIR/Caddyfile"
fi

# 6. SETUP CRON JOBS
echo ""
echo "[6/6] Setting up cron jobs..."
chmod +x run.sh

CURRENT_CRON=$(crontab -l 2>/dev/null || true)

if echo "$CURRENT_CRON" | grep -q "health-trend-crawler"; then
    echo "  Cron jobs already configured"
else
    NEW_CRON="$CURRENT_CRON
# Health Trend Crawler - Morning run (8:00 AM EST = 12:00 UTC)
0 12 * * * $PROJECT_DIR/run.sh >> $PROJECT_DIR/data/logs/cron_stdout.log 2>&1
# Health Trend Crawler - Evening run (6:00 PM EST = 22:00 UTC)
0 22 * * * $PROJECT_DIR/run.sh >> $PROJECT_DIR/data/logs/cron_stdout.log 2>&1"

    echo "$NEW_CRON" | crontab -
    echo "  Cron jobs added (8:00 AM and 6:00 PM EST)"
    echo "  NOTE: Times set for UTC. Adjust with 'crontab -e' if needed."
fi

# SUMMARY
echo ""
echo "=================================="
echo " Setup Complete!"
echo "=================================="
echo ""
echo " Dashboard URL: http://YOUR_VPS_IP"
echo " Username: gilberto"
echo " Password: (the one you just set)"
echo ""
echo " Quick commands:"
echo ""
echo "   # Test (1 niche, 3 articles)"
echo "   source venv/bin/activate"
echo "   python main.py --test"
echo ""
echo "   # Full pipeline"
echo "   python main.py"
echo ""
echo "   # Regenerate dashboard from latest data"
echo "   python main.py --dashboard-only"
echo ""
echo "   # Check cron"
echo "   crontab -l"
echo ""
echo "   # View logs"
echo "   tail -f data/logs/main.log"
echo ""
echo "   # Restart Caddy"
echo "   sudo systemctl restart caddy"
echo ""

#!/bin/bash

# Nginx + Let's Encrypt setup
# Usage: sudo bash install_nginx.sh smartschoolassistant.com

DOMAIN=${1:-smartschoolassistant.com}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Installing Nginx + Let's Encrypt for $DOMAIN..."

# Install Nginx & Certbot
apt-get update -qq
apt-get install -y nginx certbot python3-certbot-nginx > /dev/null 2>&1

# Copy config
sudo cp "$SCRIPT_DIR/school-assistant.conf" /etc/nginx/sites-available/school-assistant

# Enable site
sudo ln -sf /etc/nginx/sites-available/school-assistant /etc/nginx/sites-enabled/school-assistant

# Remove default
sudo rm -f /etc/nginx/sites-enabled/default

# Test config
sudo nginx -t > /dev/null 2>&1 || {
    echo "❌ Nginx config error!"
    exit 1
}

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Create certbot directories
mkdir -p /var/www/certbot

# Get SSL cert
echo "📜 Getting SSL certificate..."
sudo certbot certonly --webroot -w /var/www/certbot -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos -m admin@$DOMAIN 2>&1 | grep -E "(SUCCESS|Cert|error)" || true

# Reload Nginx
sudo nginx -s reload

echo "✅ Done!"
echo ""
echo "🔗 Domain: https://$DOMAIN"
echo "📊 Status: sudo systemctl status nginx"
echo "📋 Logs: sudo tail -f /var/log/nginx/access.log"

#!/bin/bash
set -euo pipefail

# Secrets rotation script
# Usage: ./rotate_secrets.sh [secret_name]

SECRETS_DIR="/run/secrets"
BACKUP_DIR="/var/backups/secrets"

echo "🔐 Home Assistant AI Companion - Secrets Rotation"
echo "================================================"

# Create backup directory
sudo mkdir -p "$BACKUP_DIR"
sudo chmod 700 "$BACKUP_DIR"

# Function to rotate a secret
rotate_secret() {
    local secret_name=$1
    local secret_file="$SECRETS_DIR/$secret_name"

    echo ""
    echo "Rotating secret: $secret_name"
    echo "------------------------------------"

    # Backup existing secret
    if [ -f "$secret_file" ]; then
        local backup_file="$BACKUP_DIR/${secret_name}_$(date +%Y%m%d_%H%M%S).bak"
        sudo cp "$secret_file" "$backup_file"
        echo "✅ Backed up to: $backup_file"
    fi

    # Prompt for new secret
    echo "Enter new value for $secret_name:"
    read -s new_value
    echo ""

    if [ -z "$new_value" ]; then
        echo "❌ Empty value, skipping rotation"
        return 1
    fi

    # Write new secret
    echo "$new_value" | sudo tee "$secret_file" > /dev/null
    sudo chmod 600 "$secret_file"
    sudo chown root:root "$secret_file"

    echo "✅ Secret rotated successfully"
    echo "⚠️  Remember to update the secret in:"

    case $secret_name in
        ha_token)
            echo "   - Home Assistant: Settings > Long-lived access tokens"
            ;;
        openai_api_key)
            echo "   - OpenAI Dashboard: https://platform.openai.com/api-keys"
            ;;
        brave_api_key)
            echo "   - Brave Search Dashboard"
            ;;
        postgres_password)
            echo "   - PostgreSQL database"
            ;;
    esac
}

# Main rotation logic
if [ $# -eq 0 ]; then
    echo "Available secrets to rotate:"
    echo "  1) ha_token"
    echo "  2) openai_api_key"
    echo "  3) brave_api_key"
    echo "  4) postgres_password"
    echo "  5) All secrets"
    echo ""
    echo "Select secret to rotate (1-5):"
    read -r choice

    case $choice in
        1) rotate_secret "ha_token" ;;
        2) rotate_secret "openai_api_key" ;;
        3) rotate_secret "brave_api_key" ;;
        4) rotate_secret "postgres_password" ;;
        5)
            rotate_secret "ha_token"
            rotate_secret "openai_api_key"
            rotate_secret "brave_api_key"
            rotate_secret "postgres_password"
            ;;
        *)
            echo "❌ Invalid choice"
            exit 1
            ;;
    esac
else
    rotate_secret "$1"
fi

echo ""
echo "✅ Rotation complete!"
echo "🔄 Restart services to apply changes:"
echo "   cd /home/irion94/home-assistant-green/ai-gateway"
echo "   docker-compose restart"

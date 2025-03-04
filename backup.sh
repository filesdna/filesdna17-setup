#!/bin/bash

# Master Password
MASTER_PWD="hHGdf3524DD5gs"

# Backup Directory
BACKUP_DIR="/root/backups"
mkdir -p "$BACKUP_DIR"

# API Endpoint for listing databases (assuming a fixed base domain)
LIST_DB_URL="https://bs.filesdna.com/web/database/list"

# Get list of databases
DB_LIST=$(curl -X POST "$LIST_DB_URL" \
    -H "Content-Type: application/json" \
    -d "{\"master_pwd\": \"$MASTER_PWD\"}" \
    -s | jq -r '.result[]')

# Check if database list is empty
if [ -z "$DB_LIST" ]; then
    echo "❌ Error: No databases found or incorrect master password."
    exit 1
fi

# Loop through each database, construct the domain, and create a backup
for DB_NAME in $DB_LIST; do
    DOMAIN="https://${DB_NAME}.filesdna.com"
    BACKUP_URL="$DOMAIN/web/database/backup"

    TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
    BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_$TIMESTAMP.zip"

    echo "📦 Creating backup for database: $DB_NAME on domain: $DOMAIN"

    RESPONSE=$(curl -X POST "$BACKUP_URL" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "master_pwd=$MASTER_PWD" \
        -d "name=$DB_NAME" \
        -d "backup_format=zip" \
        --output "$BACKUP_FILE" \
        -s -w "%{http_code}")

    # Check Response
    if [ "$RESPONSE" -eq 200 ]; then
        echo "✅ Backup saved: $BACKUP_FILE"
    else
        echo "❌ Error backing up '$DB_NAME' on domain '$DOMAIN'. HTTP Status Code: $RESPONSE"
        rm -f "$BACKUP_FILE"  # Remove incomplete backup
    fi
done

echo "🎉 Backup process completed!"

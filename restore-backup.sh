#!/bin/bash

# API URL
API_URL="http://localhost:8069/web/database/restore"

# Master Password
MASTER_PWD="hHGdf3524DD5gs"

# Backup File Path (Ensure the correct path)
BACKUP_DIR="/opt/filesdna17"
BACKUP_FILE=$(ls -t /root/bs_2025-02-28_07-14-00.zip 2>/dev/null | head -n1)

# Ask for Database Name
read -p "Enter the database name to restore: " DB_NAME

# Check if Backup File Exists
if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Error: No backup file found in $BACKUP_DIR"
    exit 1
fi

echo "🔍 Found Backup File: $BACKUP_FILE"

# Make API Request with Binary File Upload
RESPONSE=$(curl -X POST "$API_URL" \
    -H "Content-Type: multipart/form-data" \
    -F "master_pwd=$MASTER_PWD" \
    -F "name=$DB_NAME" \
    -F "copy=true" \
    -F "backup_file=@$BACKUP_FILE;type=application/zip" \
    -s -o /dev/null -w "%{http_code}")

# Check Response
if [ "$RESPONSE" -eq 200 ]; then
    echo "✅ Database '$DB_NAME' restored successfully!"
else
    echo "❌ Error restoring database. HTTP Status Code: $RESPONSE"
fi

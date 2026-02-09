# Deployment Script for Maltese Law RAG to Vultr Server
# Run this from PowerShell on your Windows machine

$SERVER_IP = "192.248.181.245"
$SERVER_USER = "root"
$SERVER_PATH = "/var/www/maltese-law-rag"
$LOCAL_PATH = "c:\Users\Jake\Downloads\maltese-law-rag\maltese-law-rag"

Write-Host "======================================"
Write-Host "Deploying Maltese Law RAG to Server"
Write-Host "Server: $SERVER_IP"
Write-Host "======================================"

# Upload files using SCP
Write-Host "`nUploading files..."
scp -r "$LOCAL_PATH\*" "${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/"

Write-Host "`n✓ Files uploaded successfully!"
Write-Host "`nNext steps:"
Write-Host "1. SSH into your server: ssh $SERVER_USER@$SERVER_IP"
Write-Host "2. Follow the instructions in DEPLOYMENT_GUIDE.md"
Write-Host "3. Your app will be available at: http://$SERVER_IP:9000"
Write-Host "`nLogin credentials:"
Write-Host "  Username: axis"
Write-Host "  Password: 1616"

#!/bin/bash

echo "========================================"
echo "Deploying Fixed response_generator.py"
echo "========================================"
echo

echo "Step 1: Copying file to server..."
scp src/generation/response_generator.py jake@18.133.144.105:/var/www/maltese-law-rag/src/generation/response_generator.py

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to copy file to server"
    echo
    echo "Please check:"
    echo "  - You have SSH access configured"
    echo "  - The server IP is correct: 18.133.144.105"
    echo "  - Your SSH key is loaded"
    echo
    exit 1
fi

echo
echo "Step 2: Restarting the service..."
ssh jake@18.133.144.105 "sudo systemctl restart maltese-law-rag && sudo systemctl status maltese-law-rag"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to restart service"
    exit 1
fi

echo
echo "========================================"
echo "SUCCESS! Service has been restarted."
echo "========================================"
echo
echo "The fix added Optional to the typing imports."
echo "Citations should now work with page numbers."
echo

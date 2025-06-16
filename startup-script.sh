#!/bin/bash

# Log all output from this script to a file.
LOG_FILE="/var/log/startup-script.log"
exec > >(sudo tee -a ${LOG_FILE}) 2>&1

echo "Startup script started at $(date)"

# Add a new system user named zncuser without a password
echo "Adding system user 'zncuser'..."
if id "zncuser" &>/dev/null; then
    echo "User 'zncuser' already exists."
else
    sudo adduser --disabled-password --gecos "" zncuser
    if [ $? -eq 0 ]; then
        echo "User 'zncuser' created successfully."
    else
        echo "Failed to create user 'zncuser'."
        # Optionally exit here if user creation is critical
        # exit 1
    fi
fi
echo "Home directory for zncuser should be /home/zncuser"
ls -ld /home/zncuser

# Update package lists
echo "Updating package lists..."
sudo apt-get update -y
if [ $? -eq 0 ]; then
    echo "Package lists updated successfully."
else
    echo "Failed to update package lists."
    # Optionally exit here if package update is critical
    # exit 1
fi

# Install ZNC
echo "Installing ZNC..."
sudo apt-get install znc -y
if [ $? -eq 0 ]; then
    echo "ZNC installed successfully."
else
    echo "Failed to install ZNC."
    # Optionally exit here if ZNC installation is critical
    # exit 1
fi

echo "ZNC installation process completed."

# Create systemd service file for ZNC
echo "Creating systemd service file for ZNC at /etc/systemd/system/znc.service..."
sudo tee /etc/systemd/system/znc.service > /dev/null <<EOF
[Unit]
Description=ZNC - An advanced IRC Bouncer
After=network-online.target

[Service]
User=zncuser
ExecStart=/usr/bin/znc -f
Restart=always

[Install]
WantedBy=multi-user.target
EOF

if [ $? -eq 0 ]; then
    echo "znc.service file created successfully."
    sudo chmod 644 /etc/systemd/system/znc.service
    echo "Permissions set to 644 for znc.service."
else
    echo "Failed to create znc.service file."
    # exit 1 # Critical step
fi

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
if [ $? -eq 0 ]; then
    echo "Systemd daemon reloaded successfully."
else
    echo "Failed to reload systemd daemon."
    # exit 1 # Critical step
fi

# Enable ZNC service
echo "Enabling ZNC service to start on boot..."
sudo systemctl enable znc.service
if [ $? -eq 0 ]; then
    echo "ZNC service enabled successfully."
else
    echo "Failed to enable ZNC service."
    # exit 1 # Critical step
fi

# Start ZNC service
echo "Starting ZNC service..."
sudo systemctl start znc.service
if [ $? -eq 0 ]; then
    echo "ZNC service started successfully."
else
    echo "Failed to start ZNC service."
    # exit 1 # Critical step
fi

# Check ZNC service status
echo "Checking ZNC service status..."
sudo systemctl status znc.service --no-pager # --no-pager to prevent interactive mode
echo "Status check command executed."

echo "Startup script finished at $(date)"

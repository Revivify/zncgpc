#!/bin/bash

# Log all output from this script to a file.
LOG_FILE="/var/log/startup-script.log"
exec > >(sudo tee -a ${LOG_FILE}) 2>&1

echo "Startup script started at $(date)"

# Retry function
retry_command() {
    local max_attempts=$1
    local delay=$2
    local cmd="${@:3}"
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt/$max_attempts: Running '$cmd'"
        eval "$cmd"
        if [ $? -eq 0 ]; then
            echo "Command '$cmd' succeeded."
            return 0
        fi
        echo "Command '$cmd' failed. Retrying in $delay seconds..."
        sleep $delay
        attempt=$((attempt + 1))
    done
    echo "Command '$cmd' failed after $max_attempts attempts."
    return 1
}

# Check network connectivity
echo "Checking network connectivity..."
MAX_NET_ATTEMPTS=5
NET_ATTEMPT=1
PING_HOST="8.8.8.8" # Google's public DNS

while [ $NET_ATTEMPT -le $MAX_NET_ATTEMPTS ]; do
    if ping -c 1 $PING_HOST &>/dev/null; then
        echo "Network connectivity to $PING_HOST confirmed."
        break
    fi
    echo "Network connectivity check $NET_ATTEMPT/$MAX_NET_ATTEMPTS failed. Retrying in 10 seconds..."
    sleep 10
    NET_ATTEMPT=$((NET_ATTEMPT + 1))
done

if [ $NET_ATTEMPT -gt $MAX_NET_ATTEMPTS ]; then
    echo "ERROR: Network connectivity could not be established after $MAX_NET_ATTEMPTS attempts. Apt operations might fail."
    # Proceeding, letting apt retries handle further issues.
fi

# Add a new system user named zncuser without a password
echo "Adding system user 'zncuser'..."
if id "zncuser" &>/dev/null; then
    echo "User 'zncuser' already exists."
else
    # Using retry_command for robustness, though adduser is usually reliable locally.
    retry_command 2 3 "sudo adduser --disabled-password --gecos \"\" zncuser"
    if [ $? -eq 0 ]; then
        echo "User 'zncuser' created successfully."
    else
        echo "Failed to create user 'zncuser' after retries."
        # exit 1 # Critical for ZNC service user
    fi
fi
echo "Home directory for zncuser should be /home/zncuser"
ls -ld /home/zncuser # Confirm home directory

# Update package lists
echo "Updating package lists (with retries and forcing IPv4)..."
retry_command 3 10 "sudo apt-get -o Acquire::ForceIPv4=true update -y"
if [ $? -eq 0 ]; then
    echo "Package lists updated successfully."
else
    echo "Failed to update package lists after multiple retries. Proceeding with ZNC installation attempt..."
    # Not exiting, to allow ZNC install to be attempted from cache or if partial update worked.
fi

# Install ZNC
echo "Installing ZNC (with retries and forcing IPv4)..."
retry_command 3 10 "sudo apt-get -o Acquire::ForceIPv4=true install znc -y"
ZNCAptInstallStatus=$? # Save status for later check
if [ $ZNCAptInstallStatus -eq 0 ]; then
    echo "ZNC installed successfully via apt."
else
    echo "Failed to install ZNC via apt after multiple retries. Will proceed to systemd setup, but ZNC may not be functional."
fi

echo "ZNC installation attempt completed." # Changed message to reflect it's an attempt

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
    echo "Failed to create znc.service file. ZNC will not run as a service."
    # exit 1 # Critical step for service setup
fi

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
if [ $? -eq 0 ]; then
    echo "Systemd daemon reloaded successfully."
else
    echo "Failed to reload systemd daemon."
fi

# Enable ZNC service
echo "Enabling ZNC service to start on boot..."
sudo systemctl enable znc.service
if [ $? -eq 0 ]; then
    echo "ZNC service enabled successfully."
else
    echo "Failed to enable ZNC service."
fi

# Start ZNC service - only if ZNC was installed successfully
if [ $ZNCAptInstallStatus -eq 0 ]; then
    echo "Starting ZNC service..."
    sudo systemctl start znc.service
    if [ $? -eq 0 ]; then
        echo "ZNC service started successfully."
    else
        echo "Failed to start ZNC service. Check ZNC configuration or installation."
    fi

    # Check ZNC service status
    echo "Checking ZNC service status..."
    sudo systemctl status znc.service --no-pager # --no-pager to prevent interactive mode
    echo "Status check command executed."
else
    echo "Skipping ZNC service start because ZNC package installation failed or was incomplete."
    echo "Please check /var/log/startup-script.log and apt logs for installation errors."
    echo "The znc.service file has been created and enabled; you may be able to start it manually if ZNC is correctly installed by other means."
fi

echo "Startup script finished at $(date)"

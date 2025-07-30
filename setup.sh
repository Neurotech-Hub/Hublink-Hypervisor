#!/bin/bash

set -e  # Exit on error
log_file="install.log"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Starting Hublink Hypervisor installation..." | tee -a "$log_file"

# Get the installing user
INSTALL_USER=$(logname)
if [ -z "$INSTALL_USER" ]; then
    INSTALL_USER=$SUDO_USER
fi

echo "Installing for user: $INSTALL_USER" | tee -a "$log_file"

# Remove existing directory completely and recreate fresh
echo "Preparing installation directory..." | tee -a "$log_file"
cd /
rm -rf /opt/hublink-hypervisor
mkdir -p /opt/hublink-hypervisor

# Clone the repository
echo "Downloading Hublink Hypervisor..." | tee -a "$log_file"
git clone https://github.com/Neurotech-Hub/Hublink-Hypervisor.git /opt/hublink-hypervisor 2>> "$log_file" || {
    echo "Git clone failed! See $log_file for details" | tee -a "$log_file"
    cat "$log_file"
    exit 1
}
cd /opt/hublink-hypervisor || exit 1
echo "Repository cloned successfully" | tee -a "$log_file"

# Set proper ownership
echo "Setting file permissions..." | tee -a "$log_file"
chown -R $INSTALL_USER:$INSTALL_USER /opt/hublink-hypervisor

# Create virtual environment
echo "Creating Python virtual environment..." | tee -a "$log_file"
su - $INSTALL_USER -c "cd /opt/hublink-hypervisor && python3 -m venv venv"

# Install Python dependencies
echo "Installing Python dependencies..." | tee -a "$log_file"
su - $INSTALL_USER -c "cd /opt/hublink-hypervisor && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Create logs directory
echo "Setting up logging..." | tee -a "$log_file"
mkdir -p /opt/hublink-hypervisor/logs
chown $INSTALL_USER:$INSTALL_USER /opt/hublink-hypervisor/logs

# Create systemd service file
echo "Creating systemd service..." | tee -a "$log_file"
cat > /etc/systemd/system/hublink-hypervisor.service <<EOL
[Unit]
Description=Hublink Hypervisor Flask Application
After=network.target

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_USER
WorkingDirectory=/opt/hublink-hypervisor
Environment=PATH=/opt/hublink-hypervisor/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/hublink-hypervisor/venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/hublink-hypervisor/logs/hublink-hypervisor.log
StandardError=append:/opt/hublink-hypervisor/logs/hublink-hypervisor.log

[Install]
WantedBy=multi-user.target
EOL

# Set proper permissions for service file
chmod 644 /etc/systemd/system/hublink-hypervisor.service

# Reload systemd and enable service
echo "Enabling and starting service..." | tee -a "$log_file"
systemctl daemon-reload
systemctl enable hublink-hypervisor.service
systemctl start hublink-hypervisor.service

# Wait a moment for service to start
sleep 3

# Check if service is running
if systemctl is-active --quiet hublink-hypervisor.service; then
    echo "Hublink Hypervisor service is running successfully!" | tee -a "$log_file"
else
    echo "Warning: Service may not have started properly. Check logs:" | tee -a "$log_file"
    echo "sudo journalctl -u hublink-hypervisor.service -f" | tee -a "$log_file"
fi

echo "Installation complete!" | tee -a "$log_file"
echo "Hublink Hypervisor is now running at: http://localhost:8081" | tee -a "$log_file"
echo "Logs are available at: /opt/hublink-hypervisor/logs/hublink-hypervisor.log" | tee -a "$log_file"
echo "Service status: sudo systemctl status hublink-hypervisor.service" | tee -a "$log_file" 
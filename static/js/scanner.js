/**
 * Hublink Scanner JavaScript
 * Dedicated functionality for the scanner page
 */

class HublinkScanner {
    constructor() {
        this.elements = {};
        this.isInitialized = false;
        this.init();
    }

    init() {
        this.initializeElements();
        this.bindEvents();
        this.loadInitialState();
        this.isInitialized = true;
        console.log('Hublink Scanner initialized');
    }

    initializeElements() {
        // Scanner controls
        this.elements.startScanBtn = document.getElementById('start-scan-btn');

        // Status elements
        this.elements.scannerStatusIndicator = document.getElementById('scanner-status-indicator');
        this.elements.scanningStatus = document.getElementById('scanning-status');
        this.elements.devicesFound = document.getElementById('devices-found');
        this.elements.devicesConnected = document.getElementById('devices-connected');

        // Device list
        this.elements.deviceListContent = document.getElementById('device-list-content');

        // Filter input
        this.elements.deviceNameFilter = document.getElementById('device-name-filter');



        // Modal elements
        this.elements.deviceModal = document.getElementById('device-modal');
        this.elements.deviceModalContent = document.getElementById('device-modal-content');
        this.elements.deviceModalClose = document.getElementById('device-modal-close');
    }

    bindEvents() {
        // Scanner control buttons
        this.elements.startScanBtn?.addEventListener('click', () => this.startScanner());



        // Modal events
        this.elements.deviceModalClose?.addEventListener('click', () => this.hideDeviceModal());
        this.elements.deviceModal?.addEventListener('click', (e) => {
            if (e.target === this.elements.deviceModal) {
                this.hideDeviceModal();
            }
        });
    }

    async loadInitialState() {
        try {
            await this.refreshDevices();
        } catch (error) {
            console.error('Error loading initial state:', error);
        }
    }

    async startScanner() {
        try {
            this.setLoading(true);
            this.updateStatus('Starting scan...', 'scanning');

            // Clear the discovered devices list immediately
            if (this.elements.deviceListContent) {
                this.elements.deviceListContent.innerHTML = '';
            }

            // Get device name filter
            const deviceNameFilter = this.elements.deviceNameFilter?.value || 'Hublink';

            // Start the scan with filter
            const response = await fetch('/api/scanner/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ device_name_filter: deviceNameFilter })
            });
            const result = await response.json();

            if (result.success) {
                this.updateStatus(`Scanning for devices (filter: '${deviceNameFilter}')...`, 'scanning');
                this.showNotification(`Scanner started successfully (filter: '${deviceNameFilter}')`, 'success');

                // Update button text to show scanning
                if (this.elements.startScanBtn) {
                    this.elements.startScanBtn.innerHTML = 'Scanning...';
                    this.elements.startScanBtn.disabled = true;
                }

                // Auto-stop after 10 seconds
                setTimeout(async () => {
                    await this.stopScanner();
                }, 10000);

                // Refresh device list every 2 seconds during scan
                const refreshInterval = setInterval(async () => {
                    await this.refreshDevices();

                    // Stop refreshing when scan stops
                    if (!this.elements.startScanBtn.disabled) {
                        clearInterval(refreshInterval);
                    }
                }, 2000);

            } else {
                this.updateStatus('Scan failed', 'error');
                this.showNotification(`Failed to start scanner: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error starting scanner:', error);
            this.updateStatus('Scan failed', 'error');
            this.showNotification('Error starting scanner', 'error');
        } finally {
            this.setLoading(false);
        }
    }

    async stopScanner() {
        try {
            const response = await fetch('/api/scanner/stop', { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.updateStatus('Scan completed', 'ready');

                // Reset button
                if (this.elements.startScanBtn) {
                    this.elements.startScanBtn.innerHTML = 'Start Scan';
                    this.elements.startScanBtn.disabled = false;
                }

                // Final refresh of device list
                await this.refreshDevices();
                this.showNotification('Scan completed', 'success');
            } else {
                this.showNotification(`Failed to stop scanner: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error stopping scanner:', error);
            this.showNotification('Error stopping scanner', 'error');
        }
    }

    async refreshDevices() {
        try {
            const response = await fetch('/api/scanner/devices');
            const result = await response.json();

            if (result.success) {
                this.updateDeviceList(result.devices);
                this.updateStats(result.count, result.devices.filter(d => d.connection_status === 'connected').length);
            } else {
                console.error('Failed to refresh devices:', result.error);
            }
        } catch (error) {
            console.error('Error refreshing devices:', error);
        }
    }

    async connectToDevice(address) {
        try {
            // Best-effort stop scanner before connecting (idempotent on backend)
            try { await fetch('/api/scanner/stop', { method: 'POST' }); } catch (_) { }

            // Use real endpoint
            const response = await fetch(`/api/scanner/connect/${address}`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showNotification(`Connected to ${result.device.name}`, 'success');
                this.refreshDevices();
            } else {
                this.showNotification(`Failed to connect: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error connecting to device:', error);
            this.showNotification('Error connecting to device', 'error');
        }
    }

    async disconnectFromDevice(address) {
        try {
            // Best-effort stop scanner first
            try { await fetch('/api/scanner/stop', { method: 'POST' }); } catch (_) { }

            // Use real endpoint
            const response = await fetch(`/api/scanner/disconnect/${address}`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showNotification('Device disconnected successfully', 'success');
                this.refreshDevices();
            } else {
                this.showNotification(`Failed to disconnect: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error disconnecting from device:', error);
            this.showNotification('Error disconnecting from device', 'error');
        }
    }

    updateStatus(message, status) {
        if (!this.elements) return;

        const statusText = this.elements.scannerStatusIndicator?.querySelector('.status-text');
        const statusDot = this.elements.scannerStatusIndicator?.querySelector('.status-dot');

        if (statusText) statusText.textContent = message;
        if (statusDot) {
            statusDot.className = 'status-dot ' + status;
        }
    }

    setLoading(loading) {
        if (!this.elements) return;

        const buttons = [
            this.elements.startScanBtn
        ].filter(Boolean);

        buttons.forEach(btn => {
            btn.disabled = loading;
        });
    }

    updateStats(discovered, connected) {
        if (!this.elements) return;

        if (this.elements.devicesFound) {
            this.elements.devicesFound.textContent = discovered;
        }
        if (this.elements.devicesConnected) {
            this.elements.devicesConnected.textContent = connected;
        }
    }

    updateDeviceList(devices) {
        if (!this.elements?.deviceListContent) return;

        if (devices.length === 0) {
            this.elements.deviceListContent.innerHTML = `
                <div class="no-devices-message">
                    <p>No Hublink devices discovered yet</p>
                    <p class="no-devices-hint">Start scanning to discover nearby devices</p>
                </div>
            `;
            return;
        }

        const deviceItems = devices.map(device => this.createDeviceItem(device)).join('');
        this.elements.deviceListContent.innerHTML = deviceItems;

        // Load node data for connected devices
        devices.forEach(device => {
            if (device.connection_status === 'connected') {
                this.loadNodeData(device.address);
            }
        });
    }

    createDeviceItem(device) {
        const isConnected = device.connection_status === 'connected';
        const rssiText = device.rssi ? `${device.rssi} dBm` : 'Unknown';
        const hasAnyConnection = this.hasAnyConnectedDevice();

        return `
            <div class="device-item ${isConnected ? 'connected' : ''}" data-address="${device.address}">
                <div class="device-main-content">
                    <div class="device-info">
                        <div class="device-name">${this.escapeHtml(device.name)}</div>
                        <div class="device-details">
                            <span class="device-address">${device.address}</span>
                            <span>RSSI: ${rssiText}</span>
                        </div>
                    </div>
                    <div class="device-actions">
                        ${isConnected ?
                `<button class="btn btn-sm btn-warning" onclick="window.hublinkScanner.disconnectFromDevice('${device.address}')">
                                Disconnect
                            </button>` :
                `<button class="btn btn-sm btn-primary" onclick="window.hublinkScanner.connectToDevice('${device.address}')" ${hasAnyConnection ? 'disabled' : ''}>
                                Connect
                            </button>`
            }
                    </div>
                </div>
                ${isConnected ? this.createExpandedContent(device) : ''}
            </div>
        `;
    }



    hasAnyConnectedDevice() {
        // This would need to be implemented to check current state
        // For now, we'll check the devices connected count
        const connectedCount = parseInt(this.elements.devicesConnected?.textContent || '0');
        return connectedCount > 0;
    }

    async loadNodeData(address) {
        try {
            const response = await fetch(`/api/scanner/read-node/${address}`, { method: 'POST' });
            const result = await response.json();

            const nodeDataElement = document.getElementById(`node-data-${address}`);
            if (!nodeDataElement) return;

            if (result.success) {
                nodeDataElement.innerHTML = `
                    <div class="node-data-raw">
                        <pre>${this.escapeHtml(result.data)}</pre>
                    </div>
                `;
            } else {
                nodeDataElement.innerHTML = `
                    <div class="node-data-error">
                        <p>Error loading node data: ${result.error}</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading node data:', error);
            const nodeDataElement = document.getElementById(`node-data-${address}`);
            if (nodeDataElement) {
                nodeDataElement.innerHTML = `
                    <div class="node-data-error">
                        <p>Error loading node data: ${error.message}</p>
                    </div>
                `;
            }
        }
    }

    async writeGatewayCommand(address) {
        const commandInput = document.getElementById(`command-input-${address}`);
        if (!commandInput) return;

        const command = commandInput.value.trim();
        if (!command) {
            this.showNotification('Please enter a command', 'warning');
            return;
        }

        try {
            const response = await fetch(`/api/scanner/write-gateway/${address}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command: command })
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Command sent successfully', 'success');
                commandInput.value = ''; // Clear the input
            } else {
                this.showNotification(`Failed to send command: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error writing gateway command:', error);
            this.showNotification('Error sending command', 'error');
        }
    }

    createExpandedContent(device) {
        const connectedAt = device.connected_at ? new Date(device.connected_at).toLocaleString() : 'Unknown';
        const uploadPath = device.upload_path || 'Unknown';

        return `
            <div class="device-expanded-content">
                <div class="device-node-data">
                    <h4>Node Characteristic Data</h4>
                    <div class="node-data-content" id="node-data-${device.address}">
                        <div class="loading-indicator">Loading node data...</div>
                    </div>
                </div>
                <div class="device-gateway-command">
                    <h4>Gateway Commands</h4>
                    <div class="command-input-group">
                        <textarea 
                            class="command-input" 
                            id="command-input-${device.address}" 
                            placeholder="Enter command to send to gateway..."
                            rows="3"
                        ></textarea>
                        <button 
                            class="btn btn-primary" 
                            onclick="window.hublinkScanner.writeGatewayCommand('${device.address}')"
                        >
                            Write Command
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    showDeviceModal() {
        if (this.elements?.deviceModal) {
            this.elements.deviceModal.style.display = 'flex';
        }
    }

    hideDeviceModal() {
        if (this.elements?.deviceModal) {
            this.elements.deviceModal.style.display = 'none';
        }
    }

    showNotification(message, type = 'info') {
        // Simple notification system - could be enhanced with a proper toast library
        console.log(`${type.toUpperCase()}: ${message}`);

        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;

        // Set background color based on type
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            info: '#17a2b8',
            warning: '#ffc107'
        };
        toast.style.backgroundColor = colors[type] || colors.info;

        document.body.appendChild(toast);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Add CSS animations for toast notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize scanner when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.hublinkScanner = new HublinkScanner();
});

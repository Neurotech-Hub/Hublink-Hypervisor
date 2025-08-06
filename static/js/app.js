/**
 * Hublink Hypervisor - Frontend JavaScript
 * Handles API calls, real-time updates, and user interactions
 */

class HublinkHypervisor {
    constructor() {
        this.autoRefreshInterval = null;
        this.refreshInterval = 5000; // 5 seconds
        this.isLoading = false;

        this.initializeElements();
        this.bindEvents();
        this.startAutoRefresh();
        this.loadStatus(true); // Show loading on initial load
    }

    initializeElements() {
        // Container elements
        this.elements = {
            containerState: document.getElementById('container-state'),
            containerMessage: document.getElementById('container-message'),
            containerList: document.getElementById('container-list'),
            startBtn: document.getElementById('start-btn'),
            stopBtn: document.getElementById('stop-btn'),
            restartBtn: document.getElementById('restart-btn'),

            // Internet elements
            appInternet: document.getElementById('app-internet'),
            hublinkInternet: document.getElementById('hublink-internet'),

            // Header status elements
            statusDot: document.querySelector('#overall-status .status-dot'),
            statusText: document.querySelector('#overall-status .status-text'),

            // Navigation elements
            navTabs: document.querySelectorAll('.header-nav .nav-tab'),
            tabContents: document.querySelectorAll('.tab-content'),

            // Footer elements
            lastUpdated: document.getElementById('last-updated'),
            dashboardLink: document.getElementById('dashboard-link'),

            // Gateway elements
            gatewayTag: document.getElementById('gateway-tag'),

            // Logs elements
            logsContent: document.getElementById('logs-content'),

            // Overlay elements
            loadingOverlay: document.getElementById('loading-overlay'),
            errorModal: document.getElementById('error-modal'),
            modalContent: document.getElementById('modal-content'),
            modalClose: document.getElementById('modal-close')
        };
    }

    bindEvents() {
        // Container control buttons
        this.elements.startBtn.addEventListener('click', () => this.startContainers());
        this.elements.stopBtn.addEventListener('click', () => this.stopContainers());
        this.elements.restartBtn.addEventListener('click', () => this.restartContainers());



        // Modal events
        this.elements.modalClose.addEventListener('click', () => this.hideModal());
        this.elements.errorModal.addEventListener('click', (e) => {
            if (e.target === this.elements.errorModal) {
                this.hideModal();
            }
        });



        // Navigation events
        this.elements.navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.switchTab(tab.dataset.tab);
            });
        });

        // Keyboard events
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideModal();
            }
        });
    }

    async loadStatus(showLoading = false) {
        if (this.isLoading) return;

        this.isLoading = true;
        if (showLoading) {
            this.showLoading();
        }

        try {
            console.log('Loading system status...');
            const response = await fetch('/api/status');
            const data = await response.json();

            this.updateUI(data);
            this.updateLastUpdated();

        } catch (error) {
            console.error('Error loading status:', error);
            this.showError('Failed to load system status');
        } finally {
            this.isLoading = false;
            if (showLoading) {
                this.hideLoading();
            }
        }
    }

    updateUI(data) {
        console.log('Updating UI with data:', data);

        // Update header status
        this.updateHeaderStatus(data);

        // Update container information
        if (data.container_state) {
            this.updateContainerState(data.container_state, data.errors);
        }

        // Update internet connectivity
        this.updateInternetStatus(data.internet_connected, data.hublink_internet_connected);

        // Update dashboard link
        this.updateDashboardLink(data.secret_url);

        // Update gateway tag
        this.updateGatewayTag(data.gateway_name);

        // Load logs if containers are running, clear if stopped
        if (data.container_state && data.container_state.state === 'running') {
            this.loadLogs();
        } else {
            this.clearLogs();
        }
    }

    updateHeaderStatus(data) {
        const statusDot = this.elements.statusDot;
        const statusText = this.elements.statusText;

        // Remove all status classes
        statusDot.className = 'status-dot';
        statusText.className = 'status-text';

        // Determine status based on container state, health, errors, and internet
        const containerState = data.container_state;
        const hasErrors = data.errors && Object.keys(data.errors).length > 0;
        const appInternet = data.internet_connected;
        const containerInternet = data.hublink_internet_connected;

        if (containerState.state === 'not_found' || containerState.state === 'stopped') {
            // Waiting to start
            statusDot.classList.add('waiting');
            statusText.textContent = 'Waiting to start...';
            statusText.classList.add('waiting');
        } else if (containerState.state === 'running') {
            // Container is running, check if healthy
            const isFullyHealthy = !hasErrors && appInternet && containerInternet;
            const hasContainerErrors = hasErrors && (data.errors.hublink_internet || data.errors.hublink_api);

            if (isFullyHealthy) {
                // Healthy: container running, no errors, both internet connections working
                statusDot.classList.add('healthy');
                statusText.textContent = 'Healthy';
                statusText.classList.add('healthy');
            } else if (hasContainerErrors) {
                // Container running but has connectivity/API issues
                statusDot.classList.add('warning');
                statusText.textContent = 'Partial Issues';
                statusText.classList.add('warning');
            } else {
                // Container running but has other issues
                statusDot.classList.add('warning');
                statusText.textContent = 'Unhealthy';
                statusText.classList.add('warning');
            }
        } else {
            // Default loading state
            statusDot.classList.add('loading');
            statusText.textContent = 'Loading...';
            statusText.classList.add('loading');
        }
    }



    updateContainerState(containerState, containerErrors = null) {
        if (containerState.error) {
            this.elements.containerState.textContent = 'Error';
            this.elements.containerState.className = 'status-value error';
            this.elements.containerMessage.textContent = containerState.error;
            this.updateContainerButtons(false, false, false);
            return;
        }

        const state = containerState.state;
        const message = containerState.message;

        this.elements.containerState.textContent = this.capitalizeFirst(state);

        // Build detailed status message
        let detailedMessage = message;

        if (state === 'running') {
            const containers = containerState.containers || [];
            if (containers.length > 0) {
                const container = containers[0];
                const status = container.status;

                // Check if container is healthy
                if (status.includes('unhealthy')) {
                    // Provide more meaningful explanation of unhealthy status
                    if (containerErrors && Object.keys(containerErrors).length > 0) {
                        const errorMessages = [];
                        for (const [category, error] of Object.entries(containerErrors)) {
                            if (category === 'hublink_internet') {
                                errorMessages.push('No internet connectivity');
                            } else if (category === 'hublink_api') {
                                errorMessages.push('API communication failed');
                            } else {
                                errorMessages.push(`${category}: ${error}`);
                            }
                        }
                        detailedMessage = `Container health check failed: ${errorMessages.join(', ')}`;
                    } else {
                        detailedMessage = `Container health check is failing - the container may have internal issues or be unable to respond to health checks`;
                    }
                } else if (status.includes('healthy')) {
                    detailedMessage = `Container is healthy`;

                    // Add specific issues if container is healthy but system has problems
                    if (containerErrors && Object.keys(containerErrors).length > 0) {
                        const errorMessages = [];
                        for (const [category, error] of Object.entries(containerErrors)) {
                            if (category === 'hublink_internet') {
                                errorMessages.push('Container internet connectivity issue');
                            } else if (category === 'hublink_api') {
                                errorMessages.push('Container API communication issue');
                            } else {
                                errorMessages.push(`${category}: ${error}`);
                            }
                        }
                        if (errorMessages.length > 0) {
                            detailedMessage += ` - System issues: ${errorMessages.join(', ')}`;
                        }
                    }
                } else {
                    detailedMessage = `Container status: ${status}`;
                }
            }
        } else if (state === 'not_found') {
            detailedMessage = "No Hublink containers found. Use the Start button to launch containers.";
        } else if (state === 'stopped') {
            detailedMessage = "All Hublink containers are stopped. Use the Start button to launch containers.";
        }

        this.elements.containerMessage.textContent = detailedMessage;

        // Update state styling
        this.elements.containerState.className = 'status-value';
        switch (state) {
            case 'running':
                this.elements.containerState.classList.add('healthy');
                break;
            case 'stopped':
                this.elements.containerState.classList.add('warning');
                break;
            case 'not_found':
                // No special class - will use default black text
                break;
        }

        // Update container list
        this.updateContainerList(containerState.containers || []);

        // Show/hide container details row and update header
        const containerDetailsRow = document.getElementById('container-details-row');
        const containerDetailsHeader = document.getElementById('container-details-header');

        if (containerState.containers && containerState.containers.length > 0) {
            containerDetailsRow.style.display = 'block';
            const count = containerState.containers.length;
            const containerText = count === 1 ? 'container' : 'containers';
            containerDetailsHeader.textContent = `${count} ${containerText} running`;
        } else {
            containerDetailsRow.style.display = 'none';
        }

        // Update buttons
        this.updateContainerButtons(
            containerState.can_start || false,
            containerState.can_stop || false,
            containerState.can_restart || false
        );
    }

    updateContainerList(containers) {
        const containerList = this.elements.containerList;
        containerList.innerHTML = '';

        if (containers.length === 0) {
            containerList.innerHTML = '<div class="no-containers">No Hublink containers found</div>';
            return;
        }

        containers.forEach(container => {
            const containerItem = document.createElement('div');
            containerItem.className = 'container-item';
            containerItem.innerHTML = `
                <div class="container-header">
                    <div class="container-name">${container.name}</div>
                    <div class="container-status">${container.status}</div>
                </div>
                <div class="container-info">
                    <div class="info-item">
                        <span class="info-label">Image:</span>
                        <span class="info-value">${container.image}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Ports:</span>
                        <span class="info-value">${container.ports || 'None'}</span>
                    </div>
                </div>
            `;
            containerList.appendChild(containerItem);
        });
    }

    updateContainerButtons(canStart, canStop, canRestart) {
        this.elements.startBtn.disabled = !canStart;
        this.elements.stopBtn.disabled = !canStop;
        this.elements.restartBtn.disabled = !canRestart;
    }

    updateInternetStatus(appInternet, hublinkInternet) {
        this.updateStatusElement(this.elements.appInternet, appInternet, 'Hypervisor');
        this.updateStatusElement(this.elements.hublinkInternet, hublinkInternet, 'Hublink Container');
    }

    updateDashboardLink(secretUrl) {
        if (secretUrl) {
            this.elements.dashboardLink.href = secretUrl;
            this.elements.dashboardLink.classList.remove('dashboard-link-disabled');
        } else {
            this.elements.dashboardLink.href = '#';
            this.elements.dashboardLink.classList.add('dashboard-link-disabled');
        }
    }

    updateGatewayTag(gatewayName) {
        if (gatewayName) {
            this.elements.gatewayTag.textContent = gatewayName;
            this.elements.gatewayTag.style.display = 'inline';
        } else {
            this.elements.gatewayTag.style.display = 'none';
        }
    }

    updateStatusElement(element, isConnected, label) {
        if (isConnected) {
            element.textContent = 'Connected';
            element.className = 'status-value healthy';
        } else {
            element.textContent = 'Disconnected';
            element.className = 'status-value error';
        }
    }





    async startContainers() {
        await this.performContainerAction('start', 'Starting containers... This may take a few minutes.');
    }

    async stopContainers() {
        await this.performContainerAction('stop', 'Stopping containers... This may take a few minutes.');
    }

    async restartContainers() {
        await this.performContainerAction('restart', 'Restarting containers... This may take a few minutes.');
    }

    async performContainerAction(action, loadingMessage) {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading(loadingMessage);

        try {
            console.log(`${action} containers...`);
            const response = await fetch(`/api/containers/${action}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                console.log(`${action} successful:`, data.message);
                this.showSuccess(`${action} successful`);

                // Wait for docker-compose to complete, then refresh
                // For start/stop actions, wait longer as containers need time to fully start/stop
                const waitTime = action === 'start' ? 5000 : 3000;
                setTimeout(() => {
                    this.loadStatus();
                }, waitTime);
            } else {
                console.error(`${action} failed:`, data.error);
                this.showError(`${action} failed: ${data.error}`);
            }

        } catch (error) {
            console.error(`Error during ${action}:`, error);
            this.showError(`Failed to ${action} containers`);
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }



    showErrorDetails(category, message, timestamp) {
        const timestampStr = timestamp ? new Date(timestamp * 1000).toLocaleString() : 'Unknown';
        const content = `
            <div style="margin-bottom: 1rem;">
                <strong>Category:</strong> ${category}
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Message:</strong><br>
                ${message}
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Timestamp:</strong> ${timestampStr}
            </div>
        `;

        this.showModal('Error Details', content);
    }

    showModal(title, content) {
        const modal = this.elements.errorModal;
        const modalContent = this.elements.modalContent;

        // Update modal title
        const modalTitle = modal.querySelector('.modal-header h3');
        modalTitle.textContent = title;

        // Update modal content
        modalContent.innerHTML = content;

        // Show modal
        modal.classList.add('show');
    }

    hideModal() {
        this.elements.errorModal.classList.remove('show');
    }

    showLoading(message = 'Starting up...') {
        const loadingText = this.elements.loadingOverlay.querySelector('.loading-text');
        loadingText.textContent = message;
        this.elements.loadingOverlay.classList.add('show');
    }

    hideLoading() {
        this.elements.loadingOverlay.classList.remove('show');
    }

    showSuccess(message) {
        // Simple success notification - could be enhanced with a toast library
        console.log('Success:', message);
        // For now, just log to console. In a real app, you might want to show a toast notification
    }

    showError(message) {
        // Simple error notification - could be enhanced with a toast library
        console.error('Error:', message);
        // For now, just log to console. In a real app, you might want to show a toast notification
    }

    updateLastUpdated() {
        const now = new Date();
        this.elements.lastUpdated.textContent = now.toLocaleTimeString();
    }

    async loadLogs() {
        try {
            console.log('Loading container logs...');
            const response = await fetch('/api/logs');
            const data = await response.json();

            if (data.success) {
                this.updateLogs(data.logs);
            } else {
                console.error('Failed to load logs:', data.error);
                this.updateLogs(`Error loading logs: ${data.error}`);
            }
        } catch (error) {
            console.error('Error loading logs:', error);
            this.updateLogs(`Error loading logs: ${error.message}`);
        }
    }

    updateLogs(logs) {
        const logsContent = this.elements.logsContent;

        if (!logs || logs === 'No logs available') {
            logsContent.innerHTML = '<div class="log-line">No logs available</div>';
            return;
        }

        // Add timestamp header
        const now = new Date();
        const timestampHeader = `<div class="log-line timestamp-header">Logs fetched at: ${now.toLocaleString()}</div>`;

        // Split logs into lines and create log line elements
        const lines = logs.split('\n');
        const logLines = lines.map(line => {
            if (!line.trim()) return '';

            // Clean the log line (strip ANSI codes and container prefix)
            const cleanLine = this.cleanLogLine(line);

            let className = '';
            if (cleanLine.toLowerCase().includes('error') || cleanLine.toLowerCase().includes('failed')) {
                className = 'error';
            } else if (cleanLine.toLowerCase().includes('warning') || cleanLine.toLowerCase().includes('warn')) {
                className = 'warning';
            } else if (cleanLine.toLowerCase().includes('info') || cleanLine.toLowerCase().includes('success')) {
                className = 'info';
            }

            return `<div class="log-line ${className}">${this.escapeHtml(cleanLine)}</div>`;
        }).filter(line => line !== '');

        logsContent.innerHTML = timestampHeader + logLines.join('');

        // Scroll to bottom
        logsContent.scrollTop = logsContent.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    stripAnsiCodes(text) {
        // Remove ANSI color codes and formatting
        return text.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');
    }

    cleanLogLine(text) {
        // Strip ANSI codes first
        let cleanLine = this.stripAnsiCodes(text);

        // Remove container name prefix (e.g., "hublink-hublink-gateway-1  | ")
        cleanLine = cleanLine.replace(/^[a-zA-Z0-9\-_]+\s*\|\s*/, '');

        return cleanLine;
    }

    clearLogs() {
        this.elements.logsContent.innerHTML = '<div class="log-line">No logs available - containers are not running</div>';
    }

    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            this.loadStatus(false); // Don't show loading for auto-refresh
        }, this.refreshInterval);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    switchTab(tabName) {
        // Remove active class from all tabs and contents
        this.elements.navTabs.forEach(tab => {
            tab.classList.remove('active');
        });
        this.elements.tabContents.forEach(content => {
            content.classList.remove('active');
        });

        // Add active class to selected tab and content
        const selectedTab = document.querySelector(`[data-tab="${tabName}"]`);
        const selectedContent = document.getElementById(`${tabName}-tab`);

        if (selectedTab && selectedContent) {
            selectedTab.classList.add('active');
            selectedContent.classList.add('active');
        }
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Hublink Hypervisor...');
    window.hublinkHypervisor = new HublinkHypervisor();
});

// Handle page visibility changes to pause/resume auto-refresh
document.addEventListener('visibilitychange', () => {
    if (window.hublinkHypervisor) {
        if (document.hidden) {
            window.hublinkHypervisor.stopAutoRefresh();
        } else {
            window.hublinkHypervisor.startAutoRefresh();
        }
    }
}); 
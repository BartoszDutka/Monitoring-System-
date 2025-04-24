class DashboardUpdater {
    constructor() {
        this.graylogInterval = 30000; // 30 seconds
        this.zabbixInterval = 120000; // 2 minutes
        this.setupAutoRefresh();
        this.setupManualRefresh();
    }

    setupAutoRefresh() {
        // Graylog auto-refresh
        setInterval(() => {
            this.refreshGraylogData();
        }, this.graylogInterval);

        // Zabbix auto-refresh
        setInterval(() => {
            this.refreshZabbixData();
        }, this.zabbixInterval);
    }

    setupManualRefresh() {
        // GLPI manual refresh button
        document.getElementById('refresh-glpi').addEventListener('click', () => {
            this.refreshGLPIData();
        });
    }

    async refreshGraylogData() {
        try {
            const response = await fetch('/api/graylog/refresh');
            const data = await response.json();
            this.updateGraylogUI(data);
        } catch (error) {
            console.error('Error refreshing Graylog data:', error);
        }
    }

    async refreshZabbixData() {
        try {
            const response = await fetch('/api/zabbix/refresh');
            const data = await response.json();
            this.updateZabbixUI(data);
        } catch (error) {
            console.error('Error refreshing Zabbix data:', error);
        }
    }

    async refreshGLPIData() {
        try {
            const button = document.getElementById('refresh-glpi');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-sync fa-spin"></i> Refreshing...';
            }

            const response = await fetch('/api/glpi/force_refresh');
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            
            const data = await response.json();
            this.updateGLPIUI(data);
            
            // Add notification for user
            if (data.status === 'success') {
                // Show success notification if available
                if (typeof showNotification === 'function') {
                    showNotification('GLPI data refreshed successfully', 'success');
                } else {
                    console.log('GLPI data refreshed successfully');
                }
            }

        } catch (error) {
            console.error('Error refreshing GLPI data:', error);
            // Show error notification if available
            if (typeof showNotification === 'function') {
                showNotification('Error refreshing GLPI data: ' + error.message, 'error');
            }
        } finally {
            const button = document.getElementById('refresh-glpi');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-sync"></i> Refresh GLPI';
            }
        }
    }

    updateGraylogUI(data) {
        // Update Graylog section of the dashboard
        // Implementation depends on your HTML structure
        console.log('Updating Graylog UI with:', data);
    }

    updateZabbixUI(data) {
        // Update Zabbix section of the dashboard
        // Implementation depends on your HTML structure
        console.log('Updating Zabbix UI with:', data);
    }

    updateGLPIUI(data) {
        // Update GLPI section of the dashboard
        if (!data || !data.category_counts) return;
        
        // Update device counts in the UI
        const categories = ['workstations', 'terminals', 'servers', 'network', 'printers', 'monitors', 'racks', 'other'];
        
        categories.forEach(category => {
            const countElement = document.querySelector(`.glpi-category-${category} .count`);
            if (countElement) {
                countElement.textContent = data.category_counts[category] || 0;
            }
        });
        
        // Update total count if element exists
        const totalElement = document.querySelector('.glpi-total-count');
        if (totalElement && data.total_count !== undefined) {
            totalElement.textContent = data.total_count;
        }
        
        // Refresh current page if we're on a GLPI page
        if (window.location.pathname.startsWith('/glpi/')) {
            window.location.reload();
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardUpdater = new DashboardUpdater();
});

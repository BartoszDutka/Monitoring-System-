class DashboardUpdater {
    constructor() {
        this.graylogInterval = 30000; // 30 seconds
        this.zabbixInterval = 120000; // 2 minutes
        this.setupAutoRefresh();
        this.setupManualRefresh();
        
        // Add initialization for GLPI cards on dashboard
        this.updateGLPICardCounts();
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
                
                // Update GLPI card counts
                this.updateGLPICardCounts();
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
            const countElement = document.querySelector(`.dashboard-nav-link[href*="/glpi/${category}"] .count`);
            if (countElement) {
                countElement.textContent = data.category_counts[category] || 0;
                
                // Update visual indicator based on count
                const linkElement = countElement.closest('.dashboard-nav-link');
                if (linkElement) {
                    if (parseInt(countElement.textContent) === 0) {
                        linkElement.classList.add('empty-category');
                    } else {
                        linkElement.classList.remove('empty-category');
                    }
                }
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
        
        this.updateGLPICardCounts();
    }

    updateGLPICardCounts() {
        // Update GLPI category counts on dashboard cards
        const glpiLinks = document.querySelectorAll('.glpi-card .dashboard-nav-link');
        
        glpiLinks.forEach(link => {
            // Check if the link has a count span
            const countSpan = link.querySelector('.count');
            if (countSpan && countSpan.textContent) {
                // If count is 0, add a class to highlight it's empty
                if (countSpan.textContent === '0') {
                    link.classList.add('empty-category');
                } else {
                    link.classList.remove('empty-category');
                }
            }
        });
        
        console.log('GLPI card counts updated');
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardUpdater = new DashboardUpdater();
    
    // If we're on the index page after login, check GLPI data
    if (window.location.pathname === '/') {
        // Update GLPI card counts
        if (window.dashboardUpdater) {
            window.dashboardUpdater.updateGLPICardCounts();
        }
    }
});

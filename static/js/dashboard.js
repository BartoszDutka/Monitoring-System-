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
            button.disabled = true;
            button.textContent = 'Refreshing...';

            const response = await fetch('/api/glpi/force_refresh');
            const data = await response.json();
            this.updateGLPIUI(data);

        } catch (error) {
            console.error('Error refreshing GLPI data:', error);
        } finally {
            const button = document.getElementById('refresh-glpi');
            button.disabled = false;
            button.textContent = 'Refresh GLPI';
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
        // Implementation depends on your HTML structure
        console.log('Updating GLPI UI with:', data);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardUpdater = new DashboardUpdater();
});

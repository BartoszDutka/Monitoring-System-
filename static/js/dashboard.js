class DashboardUpdater {
    constructor() {
        this.graylogInterval = 30000; // 30 seconds
        this.zabbixInterval = 120000; // 2 minutes
        this.setupAutoRefresh();
        this.setupManualRefresh();
        
        // Add initialization for GLPI cards on dashboard
        this.updateGLPICardCounts();
        
        // Add listener for language changes
        this.setupLanguageChangeListener();
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

    setupLanguageChangeListener() {
        // Listen for language change events
        document.addEventListener('languageChanged', (e) => {
            // Refresh Zabbix content when language changes
            this.refreshZabbixData();
            
            // Also refresh Graylog content if needed
            this.refreshGraylogData();
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
        // Get current language setting
        const currentLanguage = document.documentElement.getAttribute('data-language') || 'en';
        console.log('Updating Zabbix UI with:', data, 'Language:', currentLanguage);
        
        // Apply translations to static Zabbix UI elements
        this.translateZabbixStaticElements(currentLanguage);
        
        // Process and display Zabbix data with proper translations
        if (data && data.hosts) {
            this.displayZabbixHosts(data.hosts, currentLanguage);
        }
    }
    
    translateZabbixStaticElements(lang) {
        // Translate static elements in the Zabbix section
        const translations = {
            'en': {
                'hostStatus': 'Host Status',
                'available': 'Available',
                'unavailable': 'Unavailable',
                'unknown': 'Unknown',
                'noProblems': 'No problems',
                'problems': 'Problems detected',
                'lastUpdate': 'Last updated',
                'refreshing': 'Refreshing...'
            },
            'pl': {
                'hostStatus': 'Status hosta',
                'available': 'Dostępny',
                'unavailable': 'Niedostępny',
                'unknown': 'Nieznany',
                'noProblems': 'Brak problemów',
                'problems': 'Wykryto problemy',
                'lastUpdate': 'Ostatnia aktualizacja',
                'refreshing': 'Odświeżanie...'
            }
        };
        
        // Find all elements with data-translation attribute in the Zabbix section
        const zabbixSection = document.querySelector('.zabbix-section') || document.querySelector('[data-section="zabbix"]');
        if (zabbixSection) {
            const translatableElements = zabbixSection.querySelectorAll('[data-translation]');
            
            translatableElements.forEach(element => {
                const translationKey = element.getAttribute('data-translation');
                if (translations[lang] && translations[lang][translationKey]) {
                    element.textContent = translations[lang][translationKey];
                }
            });
        }
    }
    
    displayZabbixHosts(hosts, lang) {
        // Display hosts with the correct language
        const hostContainer = document.querySelector('.zabbix-hosts-container') || document.querySelector('[data-container="zabbix-hosts"]');
        if (!hostContainer) return;
        
        // Clear the container before adding new host information
        // hostContainer.innerHTML = '';
        
        // Process each host and update/create elements with the correct language
        hosts.forEach(host => {
            // Find or create host element
            let hostElement = document.getElementById(`zabbix-host-${host.hostid}`);
            
            // Apply translations based on the current language
            if (hostElement) {
                // Update existing host element with the correct language
                this.updateHostElementLanguage(hostElement, host, lang);
            }
            // If you need to create new elements, do it here
        });
    }
    
    updateHostElementLanguage(element, host, lang) {
        // Update host element with the correct language
        const statusTexts = {
            'en': {
                '0': 'Available',
                '1': 'Unavailable',
                '2': 'Unknown'
            },
            'pl': {
                '0': 'Dostępny',
                '1': 'Niedostępny',
                '2': 'Nieznany'
            }
        };
        
        // Update status text
        const statusElement = element.querySelector('.host-status');
        if (statusElement && host.status) {
            statusElement.textContent = statusTexts[lang][host.status] || statusTexts['en'][host.status];
        }
        
        // Update other language-dependent elements
        const problemsElement = element.querySelector('.host-problems');
        if (problemsElement) {
            if (host.problems && host.problems.length > 0) {
                problemsElement.textContent = lang === 'pl' ? 
                    `Wykryto ${host.problems.length} problem(ów)` : 
                    `${host.problems.length} problem(s) detected`;
            } else {
                problemsElement.textContent = lang === 'pl' ? 'Brak problemów' : 'No problems';
            }
        }
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

function updateHostCard(host) {
    const availability = host.availability || 'Unknown';
    
    // Group alerts by status
    const alertsByStatus = host.alerts ? {
        'Critical': host.alerts.filter(a => a.description.toLowerCase().includes('critical')),
        'Warning': host.alerts.filter(a => a.description.toLowerCase().includes('warning')),
        'Other': host.alerts.filter(a => !a.description.toLowerCase().includes('critical') && !a.description.toLowerCase().includes('warning'))
    } : {};

    return `
        <div class="host-card">
            <h3>${host.name}</h3>
            <div class="status-indicator ${availability === 'Available' ? 'available' : availability === 'Unknown' ? 'unknown' : 'unavailable'}">
                Status: ${availability}
            </div>
            
            <h4>System Metrics:</h4>
            <ul>
                <li>CPU Usage: ${host.metrics.cpu}</li>
                <li>Memory: ${host.metrics.memory}</li>
                <li>Disk Space: ${host.metrics.disk}</li>
                <li>Network Traffic: ${host.metrics.network}</li>
                <li>Ping Status: ${host.metrics.ping}</li>
                <li>Uptime: ${host.metrics.uptime}</li>
            </ul>

            ${host.alerts ? `
                <div class="alerts-container">
                    ${Object.entries(alertsByStatus).map(([status, alerts]) => 
                        alerts.length ? `
                            <details class="alerts-details ${status.toLowerCase()}">
                                <summary>${status} Alerts (${alerts.length})</summary>
                                <ul class="alerts">
                                    ${alerts.map(alert => `
                                        <li class="alert">
                                            ${alert.description}
                                            <span class="alert-count">(${alert.count}x)</span>
                                            <br>
                                            <span class="alert-timestamp">Last occurred: ${alert.last_occurrence}</span>
                                        </li>
                                    `).join('')}
                                </ul>
                            </details>
                        ` : ''
                    ).join('')}
                </div>
            ` : ''}
        </div>
    `;
}

function updateGraylogInfo(graylog) {
    return `
        <li>Cluster ID: ${graylog.cluster_id}</li>
        <li>Node ID: ${graylog.node_id}</li>
        <li>Version: ${graylog.version}</li>
        <li>Tagline: ${graylog.tagline}</li>
    `;
}

function filterHosts(searchTerm, hostsGroup) {
    const cards = hostsGroup.querySelectorAll('.host-card');
    cards.forEach(card => {
        const hostName = card.querySelector('h3').textContent.toLowerCase();
        if (hostName.includes(searchTerm.toLowerCase())) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// Add function to update unknown hosts container
function updateUnknownHosts(data) {
    const container = document.getElementById('unknown-hosts');
    if (!container) return;

    const unknownHosts = data.unknown || [];
    
    if (unknownHosts.length === 0) {
        container.innerHTML = '<div class="host-card"><p>No unknown hosts found</p></div>';
        return;
    }

    container.innerHTML = unknownHosts.map(host => `
        <div class="host-card">
            <h3>${host.name}</h3>
            <div class="status-indicator unknown">
                Status: Unknown
            </div>
            <div class="host-details">
                <p><strong>Host ID:</strong> ${host.hostid}</p>
                <p><strong>Last Check:</strong> N/A</p>
                <p><strong>Status Details:</strong> Status cannot be determined</p>
            </div>
        </div>
    `).join('');
}

function updateDashboard() {
    const currentPage = window.location.pathname;
    
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            if (currentPage === '/') {
                // Aktualizuj informacje z Grayloga
                const graylogContainer = document.querySelector('#graylog-info');
                if (data.graylog && graylogContainer) {
                    graylogContainer.innerHTML = updateGraylogInfo(data.graylog);
                }
            }
            
            // Aktualizuj dane Zabbix dla wszystkich stron z hostami
            if (data.zabbix && data.zabbix.result) {
                const hosts = data.zabbix.result;
                const hostsContainer = document.querySelector('.hosts-container');
                
                if (hostsContainer) {
                    let filteredHosts = [];
                    
                    if (currentPage === '/available-hosts') {
                        filteredHosts = hosts.filter(h => h.availability === 'Available');
                    } else if (currentPage === '/unavailable-hosts') {
                        filteredHosts = hosts.filter(h => h.availability === 'Unavailable');
                    } else if (currentPage === '/unknown-hosts') {
                        filteredHosts = data.unknown || [];
                    }
                    
                    if (filteredHosts.length > 0) {
                        hostsContainer.innerHTML = filteredHosts.map(updateHostCard).join('');
                    }
                }
            }
        })
        .catch(error => console.error('Error updating dashboard:', error));
}

// Funkcja do aktualizacji liczników GLPI na stronie głównej
function updateGLPICounts(glpiData) {
    if (!glpiData || !glpiData.category_counts) return;
    
    const counts = document.querySelectorAll('.glpi-card .count');
    counts.forEach(countElement => {
        const category = countElement.closest('.dashboard-nav-link').getAttribute('href').split('/').pop();
        if (category === 'workstations') countElement.textContent = glpiData.category_counts.workstations;
        if (category === 'terminals') countElement.textContent = glpiData.category_counts.terminals;
        if (category === 'servers') countElement.textContent = glpiData.category_counts.servers;
        if (category === 'network') countElement.textContent = glpiData.category_counts.network;
        if (category === 'printers') countElement.textContent = glpiData.category_counts.printers;
    });
}

// Add GLPI search functionality
function filterGLPIDevices(searchTerm) {
    const cards = document.querySelectorAll('.host-card');
    cards.forEach(card => {
        const deviceName = card.querySelector('h3').textContent.toLowerCase();
        const details = card.querySelector('.device-details').textContent.toLowerCase();
        if (deviceName.includes(searchTerm.toLowerCase()) || details.includes(searchTerm.toLowerCase())) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('.host-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            if (window.location.pathname.startsWith('/glpi/')) {
                filterGLPIDevices(e.target.value);
            } else {
                filterHosts(e.target.value, document.querySelector('.hosts-container'));
            }
        });
    }
    
    // Uruchamiaj updateDashboard co 2 minuty tylko dla stron non-GLPI
    const currentPage = window.location.pathname;
    
    if (!currentPage.startsWith('/glpi/')) {
        updateDashboard(); // Pierwsze wywołanie
        setInterval(updateDashboard, 120000); // Co 2 minuty
    }
});

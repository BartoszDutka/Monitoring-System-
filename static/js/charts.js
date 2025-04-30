function updateHostCard(host) {
    const availability = host.availability || 'Unknown';
    const language = document.documentElement.getAttribute('data-language') || 'en';
    
    // Tłumaczenia statusów
    const translations = {
        'status': { 'en': 'Status', 'pl': 'Status' },
        'available': { 'en': 'Available', 'pl': 'Dostępny' },
        'unavailable': { 'en': 'Unavailable', 'pl': 'Niedostępny' },
        'unknown': { 'en': 'Unknown', 'pl': 'Nieznany' },
        'system_metrics': { 'en': 'System Metrics', 'pl': 'Metryki systemowe' },
        'cpu_usage': { 'en': 'CPU Usage', 'pl': 'Użycie CPU' },
        'memory': { 'en': 'Memory', 'pl': 'Pamięć' },
        'disk_space': { 'en': 'Disk Space', 'pl': 'Przestrzeń dyskowa' },
        'network_traffic': { 'en': 'Network Traffic', 'pl': 'Ruch sieciowy' },
        'ping_status': { 'en': 'Ping Status', 'pl': 'Status pingu' },
        'uptime': { 'en': 'Uptime', 'pl': 'Czas działania' },
        'critical': { 'en': 'Critical', 'pl': 'Krytyczny' },
        'warning': { 'en': 'Warning', 'pl': 'Ostrzeżenie' },
        'other': { 'en': 'Other', 'pl': 'Inne' },
        'alerts': { 'en': 'Alerts', 'pl': 'Alerty' },
        'last_occurred': { 'en': 'Last occurred', 'pl': 'Ostatnie wystąpienie' },
        'host_id': { 'en': 'Host ID', 'pl': 'ID hosta' },
        'last_check': { 'en': 'Last Check', 'pl': 'Ostatnie sprawdzenie' },
        'status_details': { 'en': 'Status Details', 'pl': 'Szczegóły statusu' },
        'status_cannot_be_determined': { 'en': 'Status cannot be determined', 'pl': 'Status nie może zostać określony' },
        'no_unknown_hosts': { 'en': 'No unknown hosts found', 'pl': 'Nie znaleziono nieznanych hostów' },
        'loading': { 'en': 'Loading', 'pl': 'Ładowanie' },
        'online': { 'en': 'Online', 'pl': 'Online' },
        'offline': { 'en': 'Offline', 'pl': 'Offline' },
        'summary': { 'en': 'Summary', 'pl': 'Podsumowanie' },
        'details': { 'en': 'Details', 'pl': 'Szczegóły' },
        'messages_over_time': { 'en': 'Messages Over Time', 'pl': 'Wiadomości w czasie' },
        'system_logs': { 'en': 'System Logs', 'pl': 'Logi systemowe' },
        'system_logs_monitor': { 'en': 'System Logs Monitor', 'pl': 'Monitor logów systemowych' },
        'high': { 'en': 'High', 'pl': 'Wysoki' },
        'medium': { 'en': 'Medium', 'pl': 'Średni' },
        'low': { 'en': 'Low', 'pl': 'Niski' },
        'na': { 'en': 'N/A', 'pl': 'Brak danych' },
        'priority': { 'en': 'Priority', 'pl': 'Priorytet' },
        'total_messages': { 'en': 'Total Messages', 'pl': 'Łączna liczba wiadomości' },
        'errors': { 'en': 'Errors', 'pl': 'Błędy' },
        'warnings': { 'en': 'Warnings', 'pl': 'Ostrzeżenia' },
        'info': { 'en': 'Info', 'pl': 'Informacje' },
        'period': { 'en': 'Period', 'pl': 'Okres' },
        'monitored_hosts': { 'en': 'Monitored Hosts', 'pl': 'Monitorowane hosty' },
        'host_status': { 'en': 'Host Status', 'pl': 'Status hosta' },
        'available_hosts': { 'en': 'Available Hosts', 'pl': 'Dostępne hosty' },
        'unavailable_hosts': { 'en': 'Unavailable Hosts', 'pl': 'Niedostępne hosty' },
        'unknown_hosts': { 'en': 'Unknown Hosts', 'pl': 'Nieznane hosty' },
        'refresh': { 'en': 'Refresh', 'pl': 'Odśwież' },
        'redirecting': { 'en': 'Redirecting...', 'pl': 'Przekierowywanie...' },
        // Additional translations for Graylog sections
        'session_details': { 'en': 'Session Details', 'pl': 'Szczegóły sesji' },
        'session_name': { 'en': 'Session Name', 'pl': 'Nazwa sesji' },
        'db_session_id': { 'en': 'DB Session ID', 'pl': 'ID sesji bazy danych' },
        'critical_events': { 'en': 'Critical Events', 'pl': 'Zdarzenia krytyczne' },
        'time_range': { 'en': 'Time Range', 'pl': 'Zakres czasu' },
        'show_entries': { 'en': 'Show entries', 'pl': 'Pokaż wpisy' },
        'system_error': { 'en': 'System Error', 'pl': 'Błąd systemowy' },
        'security_alert': { 'en': 'Security Alert', 'pl': 'Alert bezpieczeństwa' },
        'performance_issue': { 'en': 'Performance Issue', 'pl': 'Problem wydajności' },
        'service_status': { 'en': 'Service Status', 'pl': 'Status usługi' },
        // GLPI component translations
        'serial': { 'en': 'Serial', 'pl': 'Nr seryjny' },
        'other_serial': { 'en': 'Other S/N', 'pl': 'Drugi nr seryjny' },
        'owner': { 'en': 'Owner', 'pl': 'Właściciel' },
        'location': { 'en': 'Location', 'pl': 'Lokalizacja' },
        'notice': { 'en': 'Notice', 'pl': 'Uwaga' },
        'no_detailed_info': { 'en': 'This device has no detailed information available', 'pl': 'To urządzenie nie ma dostępnych szczegółowych informacji' },
        'comments': { 'en': 'Comments', 'pl': 'Komentarze' },
        'last_modified': { 'en': 'Last Modified', 'pl': 'Ostatnia modyfikacja' },
        'os': { 'en': 'OS', 'pl': 'System operacyjny' },
        'ip_address': { 'en': 'IP Address', 'pl': 'Adres IP' },
        'mac': { 'en': 'MAC', 'pl': 'MAC' },
        // Messages over time translations
        'minutes': { 'en': 'Minutes', 'pl': 'Minuty' },
        'hours': { 'en': 'Hours', 'pl': 'Godziny' },
        'days': { 'en': 'Days', 'pl': 'Dni' },
        'interval': { 'en': 'Interval', 'pl': 'Interwał' },
        // Task priority translations
        'task_priority_high': { 'en': 'High Priority', 'pl': 'Wysoki priorytet' },
        'task_priority_medium': { 'en': 'Medium Priority', 'pl': 'Średni priorytet' },
        'task_priority_low': { 'en': 'Low Priority', 'pl': 'Niski priorytet' },
        'task_status_pending': { 'en': 'Pending', 'pl': 'Oczekujące' },
        'task_status_in_progress': { 'en': 'In Progress', 'pl': 'W toku' },
        'task_status_completed': { 'en': 'Completed', 'pl': 'Ukończone' },
        'task_status_delayed': { 'en': 'Delayed', 'pl': 'Opóźnione' },
        'task_status_cancelled': { 'en': 'Cancelled', 'pl': 'Anulowane' },
        // Inventory related translations
        'no_products_found': { 'en': 'No products found in the invoice. Try the alternative method.', 'pl': 'Nie znaleziono produktów na fakturze. Spróbuj alternatywnej metody.' },
        'no_equipment_assigned': { 'en': 'No equipment assigned to this department', 'pl': 'Brak sprzętu przypisanego do tego działu' },
        'failed_to_load': { 'en': 'Failed to load equipment data', 'pl': 'Nie udało się załadować danych o sprzęcie' },
        'remove_confirm': { 'en': 'Are you sure you want to remove this item?', 'pl': 'Czy na pewno chcesz usunąć ten element?' },
        // Additional message timeline translations
        'today': { 'en': 'Today', 'pl': 'Dzisiaj' },
        'yesterday': { 'en': 'Yesterday', 'pl': 'Wczoraj' },
        'last_7_days': { 'en': 'Last 7 Days', 'pl': 'Ostatnie 7 dni' },
        'last_30_days': { 'en': 'Last 30 Days', 'pl': 'Ostatnie 30 dni' },
        'custom_range': { 'en': 'Custom Range', 'pl': 'Niestandardowy zakres' },
        'apply': { 'en': 'Apply', 'pl': 'Zastosuj' },
        'cancel': { 'en': 'Cancel', 'pl': 'Anuluj' },
        'from': { 'en': 'From', 'pl': 'Od' },
        'to': { 'en': 'To', 'pl': 'Do' },
        'source': { 'en': 'Source', 'pl': 'Źródło' },
        'message': { 'en': 'Message', 'pl': 'Wiadomość' },
        'level': { 'en': 'Level', 'pl': 'Poziom' },
        'timestamp': { 'en': 'Timestamp', 'pl': 'Znacznik czasu' },
        'facility': { 'en': 'Facility', 'pl': 'Obiekt' },
        'host': { 'en': 'Host', 'pl': 'Host' },
        'all': { 'en': 'All', 'pl': 'Wszystkie' },
        'search': { 'en': 'Search', 'pl': 'Szukaj' },
        'no_messages_found': { 'en': 'No messages found for the selected criteria', 'pl': 'Nie znaleziono wiadomości dla wybranych kryteriów' },
        'loading_messages': { 'en': 'Loading messages...', 'pl': 'Ładowanie wiadomości...' },
        // Confirmation dialog translations
        'delete_confirm_title': { 'en': 'Confirm Deletion', 'pl': 'Potwierdź usunięcie' },
        'delete_confirm_task': { 'en': 'Are you sure you want to delete this task?', 'pl': 'Czy na pewno chcesz usunąć to zadanie?' },
        'delete_confirm_task_permanent': { 'en': 'This action cannot be undone.', 'pl': 'Ta akcja nie może być cofnięta.' },
        'delete_confirm_yes': { 'en': 'Yes, delete it', 'pl': 'Tak, usuń' },
        'delete_confirm_no': { 'en': 'Cancel', 'pl': 'Anuluj' },
        'operation_successful': { 'en': 'Operation successful', 'pl': 'Operacja zakończona sukcesem' },
        'operation_failed': { 'en': 'Operation failed', 'pl': 'Operacja zakończona niepowodzeniem' },
        // Additional translations for alerts
        'error_loading_data': { 'en': 'Error loading data', 'pl': 'Błąd ładowania danych' },
        'no_data_available': { 'en': 'No data available', 'pl': 'Brak dostępnych danych' },
        'session_expired': { 'en': 'Your session has expired. Please log in again.', 'pl': 'Twoja sesja wygasła. Zaloguj się ponownie.' },
        'permission_denied': { 'en': 'Permission denied', 'pl': 'Odmowa dostępu' }
    };
    
    function t(key) {
        if (!key) return '';
        const lowerKey = key.toLowerCase();
        // Look for exact matches first
        if (translations[key]) {
            return translations[key][language] || translations[key]['en'] || key;
        }
        // Look for case-insensitive matches
        for (const transKey in translations) {
            if (transKey.toLowerCase() === lowerKey) {
                return translations[transKey][language] || translations[transKey]['en'] || key;
            }
        }
        return key;
    }
    
    // Group alerts by status and translate alert descriptions if possible
    const alertsByStatus = host.alerts ? {
        [t('critical')]: host.alerts.filter(a => a.description.toLowerCase().includes('critical')).map(a => ({
            ...a,
            description: translateAlertDescription(a.description)
        })),
        [t('warning')]: host.alerts.filter(a => a.description.toLowerCase().includes('warning')).map(a => ({
            ...a,
            description: translateAlertDescription(a.description)
        })),
        [t('other')]: host.alerts.filter(a => !a.description.toLowerCase().includes('critical') && 
                                           !a.description.toLowerCase().includes('warning')).map(a => ({
            ...a,
            description: translateAlertDescription(a.description)
        }))
    } : {};

    // Helper function to translate common alert description patterns
    function translateAlertDescription(desc) {
        if (!desc || language === 'en') return desc;
        
        // Common translations for alert descriptions
        const alertTranslations = {
            'Host became unavailable': 'Host stał się niedostępny',
            'High CPU usage': 'Wysokie użycie CPU',
            'Disk space is low': 'Mało miejsca na dysku',
            'Memory usage': 'Użycie pamięci',
            'Service is down': 'Usługa nie działa'
        };
        
        // Try to match and replace parts of the description
        let translated = desc;
        Object.entries(alertTranslations).forEach(([en, pl]) => {
            if (desc.includes(en) && language === 'pl') {
                translated = translated.replace(en, pl);
            }
        });
        
        return translated;
    }

    // Tłumaczenie statusu dostępności
    let translatedAvailability;
    if (availability === 'Available') {
        translatedAvailability = t('available');
    } else if (availability === 'Unavailable') {
        translatedAvailability = t('unavailable');
    } else {
        translatedAvailability = t('unknown');
    }

    return `
        <div class="host-card">
            <h3>${host.name}</h3>
            <div class="status-indicator ${availability === 'Available' ? 'available' : availability === 'Unknown' ? 'unknown' : 'unavailable'}">
                ${t('status')}: ${translatedAvailability}
            </div>
            
            <h4>${t('system_metrics')}:</h4>
            <ul>
                <li>${t('cpu_usage')}: ${host.metrics.cpu}</li>
                <li>${t('memory')}: ${host.metrics.memory}</li>
                <li>${t('disk_space')}: ${host.metrics.disk}</li>
                <li>${t('network_traffic')}: ${host.metrics.network}</li>
                <li>${t('ping_status')}: ${host.metrics.ping}</li>
                <li>${t('uptime')}: ${host.metrics.uptime}</li>
            </ul>

            ${host.alerts ? `
                <div class="alerts-container">
                    ${Object.entries(alertsByStatus).map(([status, alerts]) => 
                        alerts.length ? `
                            <details class="alerts-details ${status.toLowerCase()}">
                                <summary>${status} ${t('alerts')} (${alerts.length})</summary>
                                <ul class="alerts">
                                    ${alerts.map(alert => `
                                        <li class="alert">
                                            ${alert.description}
                                            <span class="alert-count">(${alert.count}x)</span>
                                            <br>
                                            <span class="alert-timestamp">${t('last_occurred')}: ${alert.last_occurrence}</span>
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
    const language = document.documentElement.getAttribute('data-language') || 'en';
    const translations = {
        'cluster_id': { 'en': 'Cluster ID', 'pl': 'ID klastra' },
        'node_id': { 'en': 'Node ID', 'pl': 'ID węzła' },
        'version': { 'en': 'Version', 'pl': 'Wersja' },
        'tagline': { 'en': 'Tagline', 'pl': 'Slogan' }
    };

    function t(key) {
        return translations[key] ? (translations[key][language] || translations[key]['en']) : key;
    }

    return `
        <li>${t('cluster_id')}: ${graylog.cluster_id}</li>
        <li>${t('node_id')}: ${graylog.node_id}</li>
        <li>${t('version')}: ${graylog.version}</li>
        <li>${t('tagline')}: ${graylog.tagline}</li>
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

    const language = document.documentElement.getAttribute('data-language') || 'en';
    const translations = {
        'status': { 'en': 'Status', 'pl': 'Status' },
        'unknown': { 'en': 'Unknown', 'pl': 'Nieznany' },
        'host_id': { 'en': 'Host ID', 'pl': 'ID hosta' },
        'last_check': { 'en': 'Last Check', 'pl': 'Ostatnie sprawdzenie' },
        'status_details': { 'en': 'Status Details', 'pl': 'Szczegóły statusu' },
        'status_cannot_be_determined': { 'en': 'Status cannot be determined', 'pl': 'Status nie może zostać określony' },
        'no_unknown_hosts': { 'en': 'No unknown hosts found', 'pl': 'Nie znaleziono nieznanych hostów' },
        'na': { 'en': 'N/A', 'pl': 'Brak danych' }
    };

    function t(key) {
        return translations[key] ? (translations[key][language] || translations[key]['en']) : key;
    }

    const unknownHosts = data.unknown || [];
    
    if (unknownHosts.length === 0) {
        container.innerHTML = `<div class="host-card"><p>${t('no_unknown_hosts')}</p></div>`;
        return;
    }

    container.innerHTML = unknownHosts.map(host => `
        <div class="host-card">
            <h3>${host.name}</h3>
            <div class="status-indicator unknown">
                ${t('status')}: ${t('unknown')}
            </div>
            <div class="host-details">
                <p><strong>${t('host_id')}:</strong> ${host.hostid}</p>
                <p><strong>${t('last_check')}:</strong> ${t('na')}</p>
                <p><strong>${t('status_details')}:</strong> ${t('status_cannot_be_determined')}</p>
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

// Function to set chart options with proper translations
function getTranslatedChartOptions(chartType, customOptions = {}) {
    const language = document.documentElement.getAttribute('data-language') || 'en';
    
    // Base options for all charts
    let options = {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 1000
        },
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    font: {
                        family: "'Nunito', sans-serif",
                        size: 12
                    }
                }
            },
            tooltip: {
                titleFont: {
                    family: "'Nunito', sans-serif"
                },
                bodyFont: {
                    family: "'Nunito', sans-serif"
                },
                callbacks: {}
            }
        }
    };
    
    // Chart type specific translations
    if (chartType === 'messagesOverTime') {
        options.scales = {
            x: {
                title: {
                    display: true,
                    text: t('time_period'),
                    font: {
                        family: "'Nunito', sans-serif",
                        size: 14
                    }
                }
            },
            y: {
                title: {
                    display: true,
                    text: t('total_messages'),
                    font: {
                        family: "'Nunito', sans-serif",
                        size: 14
                    }
                },
                beginAtZero: true
            }
        };
        options.plugins.tooltip.callbacks.title = function(context) {
            return t('time_period') + ': ' + context[0].label;
        };
        options.plugins.tooltip.callbacks.label = function(context) {
            return context.dataset.label + ': ' + context.raw;
        };
    } else if (chartType === 'hostStatus') {
        options.plugins.tooltip.callbacks.label = function(context) {
            const label = context.label || '';
            const value = context.raw || 0;
            return label + ': ' + value;
        };
    }
    
    // Merge with custom options
    return { ...options, ...customOptions };
}

// Use this function when initializing charts
function initializeMessagesOverTimeChart(ctx, data) {
    const language = document.documentElement.getAttribute('data-language') || 'en';
    
    // Translate dataset labels
    const datasets = data.datasets.map(dataset => {
        if (dataset.label === 'Errors' || dataset.label === 'Błędy') {
            dataset.label = t('errors');
        } else if (dataset.label === 'Warnings' || dataset.label === 'Ostrzeżenia') {
            dataset.label = t('warnings');
        } else if (dataset.label === 'Info' || dataset.label === 'Informacje') {
            dataset.label = t('info');
        }
        return dataset;
    });
    
    const chartData = {
        labels: data.labels,
        datasets: datasets
    };
    
    const options = getTranslatedChartOptions('messagesOverTime');
    
    return new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: options
    });
}

function initializeHostStatusChart(ctx, data) {
    const language = document.documentElement.getAttribute('data-language') || 'en';
    
    // Translate labels
    const translatedLabels = data.labels.map(label => {
        if (label === 'Available' || label === 'Dostępny') {
            return t('available');
        } else if (label === 'Unavailable' || label === 'Niedostępny') {
            return t('unavailable');
        } else if (label === 'Unknown' || label === 'Nieznany') {
            return t('unknown');
        }
        return label;
    });
    
    const chartData = {
        labels: translatedLabels,
        datasets: data.datasets
    };
    
    const options = getTranslatedChartOptions('hostStatus');
    
    return new Chart(ctx, {
        type: 'pie',
        data: chartData,
        options: options
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

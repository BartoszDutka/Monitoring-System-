/**
 * System monitoringu - moduł inwentaryzacji
 * wersja naprawiona z lepszą obsługą języka polskiego
 * i ochroną przed zawieszaniem
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicjalne tłumaczenie - wykonane bezpiecznie
    try {
        setTimeout(() => {
            translateUIElements();
        }, 100);
    } catch (err) {
        console.error('Błąd podczas początkowego tłumaczenia:', err);
    }
      // Konfiguracja obserwerów
    setupMutationObserver();
    
    const methodBtns = document.querySelectorAll('.method-btn');
    const sections = {
        manual: document.querySelector('.manual-section'),
        invoice: document.querySelector('.invoice-section'),
        equipment: document.querySelector('.equipment-section')
    };

    methodBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            methodBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            const method = this.dataset.method;
            Object.keys(sections).forEach(key => {
                if (sections[key]) {
                    sections[key].style.display = key === method ? 'block' : 'none';
                }
            });
            
            // Perform translations again when changing sections - bezpiecznie
            try {
                setTimeout(() => {
                    translateUIElements();
                }, 100);
            } catch (err) {
                console.error('Błąd podczas tłumaczenia po zmianie sekcji:', err);
            }
            
            // If equipment section is selected, immediately translate its content
            if (method === 'equipment') {
                const departmentSelect = document.getElementById('departmentSelect');
                if (departmentSelect && departmentSelect.value) {
                    try {
                        // Reload equipment data to ensure translations are applied
                        loadDepartmentEquipment(departmentSelect.value);
                    } catch (err) {
                        console.error('Błąd podczas ładowania wyposażenia działu:', err);
                    }
                }
            }
        });
    });

    // File upload preview for manual form
    const fileInput = document.getElementById('itemAttachments');
    const fileDisplay = document.getElementById('selectedFiles');
    
    fileInput?.addEventListener('change', function() {
        if (this.files.length > 0) {
            let fileNames = Array.from(this.files).map(file => file.name).join(', ');
            fileDisplay.textContent = fileNames;
        } else {
            // Get current language
            const language = document.documentElement.getAttribute('data-language') || 'en';
            fileDisplay.textContent = language === 'pl' ? 'Nie wybrano plików' : 'No files selected';
        }
    });
    
    // File upload preview for invoice form
    const invoiceInput = document.getElementById('invoicePdf');
    const invoiceFileDisplay = document.getElementById('selectedInvoiceFile');
    
    invoiceInput?.addEventListener('change', function() {
        if (this.files.length > 0) {
            invoiceFileDisplay.textContent = this.files[0].name;
        } else {
            // Get current language
            const language = document.documentElement.getAttribute('data-language') || 'en';
            invoiceFileDisplay.textContent = language === 'pl' ? 'Nie wybrano pliku' : 'No file selected';
        }
    });
    
    // Add active class to first button by default
    window.addEventListener('DOMContentLoaded', function() {
        try {
            // First click the manual button to show that section
            const firstBtn = document.querySelector('.method-btn[data-method="manual"]');
            if (firstBtn) firstBtn.click();
        } catch (err) {
            console.error('Błąd podczas inicjalizacji pierwszego przycisku:', err);
        }
    });    const departmentSelect = document.getElementById('departmentSelect');
    if (departmentSelect) {
        // Uproszczona obsługa zmiany departamentu - teraz niestandardowa kontrolka select
        // zajmuje się samą interakcją użytkownika, więc możemy skupić się tylko na obsłudze zmiany
        
        departmentSelect.addEventListener('change', function() {
            const department = this.value;
            if (department) {
                // Wczytaj dane departamentu tylko jeśli wartość nie jest pusta
                loadDepartmentEquipment(department);
            } else {
                const equipmentList = document.getElementById('departmentEquipmentList');
                if (equipmentList) {
                    equipmentList.style.display = 'none';
                }
            }
        });

        // Load equipment for initial selection if any
        if (departmentSelect.value) {
            try {
                loadDepartmentEquipment(departmentSelect.value);
            } catch (err) {
                console.error('Błąd podczas początkowego ładowania wyposażenia działu:', err);
            }
        }
    }
});

// Funkcja tłumacząca elementy interfejsu w zależności od języka
function translateUIElements() {
    try {
        const language = document.documentElement.getAttribute('data-language') || 'en';
        if (language !== 'pl') return; // Tłumaczenie tylko na polski
        
        // Ograniczamy zakres zapytań do konkretnych kontenerów zamiast całego dokumentu
        const containers = [
            document.getElementById('equipmentTableBody')?.parentNode,
            document.querySelector('.inventory-container')
        ].filter(el => el); // Filtrujemy puste elementy
        
        // Jeśli nie ma żadnych kontenerów, przerywamy
        if (containers.length === 0) return;
        
        // Osobna obsługa elementu select dla departamentów 
        // Tylko tłumaczenie opcji, kontrolka wizualna jest obsługiwana przez custom-select.js
        const departmentSelect = document.getElementById('departmentSelect');
        if (departmentSelect) {
            try {
                Array.from(departmentSelect.options).forEach(option => {
                    try {
                        if (option.text?.includes(' items)')) {
                            option.text = option.text.replace(' items)', ' elementów)');
                        }
                        
                        // Handle "Choose a department..." text
                        if (option.text === 'Choose a department...') {
                            option.text = 'Wybierz dział...';
                        }
                    } catch (err) {
                        console.error('Błąd przy tłumaczeniu opcji select:', err);
                    }
                });
                
                // Po zmianie tłumaczeń w oryginalnym selekcie, 
                // zaktualizuj również niestandardową kontrolkę
                if (typeof updateCustomSelectLabels === 'function') {
                    updateCustomSelectLabels();
                }
            } catch (err) {
                console.error('Błąd przy tłumaczeniu departmentSelect:', err);
            }
        }
        
        // Tłumaczenie "items" w opcjach wyboru departamentu - ograniczone do kontenerów
        containers.forEach(container => {
            try {
                container.querySelectorAll('select:not(#departmentSelect) option').forEach(option => {
                    try {
                        if (option.text?.includes(' items)')) {
                            option.text = option.text.replace(' items)', ' elementów)');
                        }
                        
                        // Handle "Choose a department..." text
                        if (option.text === 'Choose a department...') {
                            option.text = 'Wybierz dział...';
                        }
                    } catch (err) {
                        console.error('Błąd przy tłumaczeniu opcji select:', err);
                    }
                });
                
                // Tłumaczenie wartości w komórkach tabeli - ograniczone do kontenerów
                container.querySelectorAll('td').forEach(cell => {
                    try {
                        const text = cell.textContent?.trim() || '';
                        if (text.toLowerCase() === 'hardware') {
                            cell.textContent = 'sprzęt';
                        } else if (text.toLowerCase() === 'network') {
                            cell.textContent = 'urz. sieciowe';
                        } else if (text === 'N/A') {
                            cell.textContent = 'Brak danych';
                        }
                    } catch (err) {
                        console.error('Błąd przy tłumaczeniu komórki tabeli:', err);
                    }
                });
                
                // Translate buttons and headings if needed - ograniczone do kontenerów
                container.querySelectorAll('[data-en][data-pl]').forEach(el => {
                    try {
                        const translation = el.getAttribute('data-pl');
                        if (translation) {
                            el.textContent = translation;
                        }
                    } catch (err) {
                        console.error('Błąd przy tłumaczeniu elementu z data-*:', err);
                    }
                });
                
                // Translate button titles - ograniczone do kontenerów
                container.querySelectorAll('[data-en-title][data-pl-title]').forEach(el => {
                    try {
                        const translation = el.getAttribute('data-pl-title');
                        if (translation) {
                            el.title = translation;
                        }
                    } catch (err) {
                        console.error('Błąd przy tłumaczeniu title:', err);
                    }
                });
            } catch (containerErr) {
                console.error('Błąd przetwarzania kontenera:', containerErr);
            }
        });
    } catch (error) {
        console.error('Błąd podczas tłumaczenia interfejsu:', error);
    }
}

// Dodanie funkcji do wywoływania przy zmianach w DOM
function setupMutationObserver() {
    try {
        const language = document.documentElement.getAttribute('data-language') || 'en';
        if (language !== 'pl') return; // Obserwacja tylko dla polskiego języka
        
        // Dodajemy mechanizm zabezpieczający przed zbyt częstym wywoływaniem tłumaczeń
        let translateDebounceTimer;
        const debouncedTranslate = function() {
            clearTimeout(translateDebounceTimer);
            translateDebounceTimer = setTimeout(function() {
                try {
                    translateUIElements();
                } catch (err) {
                    console.error('Błąd podczas tłumaczenia elementów:', err);
                }
            }, 200); // Większe opóźnienie 200ms dla bezpieczeństwa
        };
        
        // Obserwuj zmiany w tabeli sprzętu
        const equipmentTableBody = document.getElementById('equipmentTableBody');
        if (equipmentTableBody) {
            const observer = new MutationObserver(debouncedTranslate);
            observer.observe(equipmentTableBody, { childList: true, subtree: true });
        }
        
        // Obserwuj też zmiany w dropdown departamentów
        const departmentSelect = document.getElementById('departmentSelect');
        if (departmentSelect) {
            const observer = new MutationObserver(debouncedTranslate);
            observer.observe(departmentSelect, { childList: true, subtree: true });
        }
    } catch (err) {
        console.error('Błąd podczas konfiguracji obserwatora mutacji:', err);
    }
}

// Zmienna do kontrolowania czy jest w toku ładowanie
let isLoadingEquipment = false;

// Główna funkcja ładująca wyposażenie działu
function loadDepartmentEquipment(departmentName) {
    // Zabezpieczenie przed wielokrotnym wywołaniem
    if (isLoadingEquipment) return;
    isLoadingEquipment = true;
    
    const equipmentList = document.getElementById('departmentEquipmentList');
    if (!equipmentList) {
        isLoadingEquipment = false;
        return;
    }
    
    equipmentList.style.display = 'block';
    
    // Usuń poprzedni spinner jeśli istnieje
    const existingSpinner = equipmentList.querySelector('.loading-spinner');
    if (existingSpinner) existingSpinner.remove();
    
    const loadingSpinner = document.createElement('div');
    loadingSpinner.className = 'loading-spinner';
    
    // Get current language for translation
    const language = document.documentElement.getAttribute('data-language') || 'en';
    loadingSpinner.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + 
                              (language === 'pl' ? 'Ładowanie...' : 'Loading...');
    equipmentList.appendChild(loadingSpinner);

    // Get current language
    const noDataText = language === 'pl' ? 'Brak danych' : 'N/A';

    fetch(`/api/department_equipment/${encodeURIComponent(departmentName)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const tbody = document.getElementById('equipmentTableBody');
            if (!tbody) {
                console.error('Element equipmentTableBody not found');
                return;
            }
            
            try {
                if (data.equipment && data.equipment.length > 0) {
                    // Użyj dokumentu fragmentu dla lepszej wydajności
                    const fragment = document.createDocumentFragment();
                    
                    // Create rows for each equipment item
                    data.equipment.forEach(item => {
                        try {
                            // Always translate hardware to sprzęt in Polish
                            let typeValue = item.type || noDataText;
                            if (language === 'pl') {
                                if (typeValue.toLowerCase() === 'hardware') {
                                    typeValue = 'sprzęt';
                                } else if (typeValue.toLowerCase() === 'network') {
                                    typeValue = 'urz. sieciowe';
                                } else if (typeValue.toLowerCase() === 'software') {
                                    typeValue = 'oprogramowanie';  
                                } else if (typeValue.toLowerCase() === 'accessories') {
                                    typeValue = 'akcesoria';
                                } else if (typeValue.toLowerCase() === 'furniture') {
                                    typeValue = 'meble';
                                } else if (typeValue.toLowerCase() === 'other') {
                                    typeValue = 'inne';
                                }
                            }

                            // Always replace N/A with proper Polish text
                            let serialNumber = item.serial_number;
                            if (language === 'pl') {
                                if (!serialNumber || serialNumber === 'N/A') {
                                    serialNumber = noDataText;
                                }
                            } else {
                                serialNumber = serialNumber || noDataText;
                            }
                            
                            // Format dates and other fields
                            let assignedDate = item.assigned_date || noDataText;
                            if (language === 'pl' && (assignedDate === 'N/A' || !item.assigned_date)) {
                                assignedDate = noDataText;
                            }
                            
                            let status = item.status || noDataText;
                            if (language === 'pl') {
                                // Translate status values
                                if (status.toLowerCase() === 'available') {
                                    status = 'dostępny';
                                } else if (status.toLowerCase() === 'in-use') {
                                    status = 'w użyciu';
                                } else if (status.toLowerCase() === 'maintenance') {
                                    status = 'konserwacja';
                                } else if (status.toLowerCase() === 'disposed') {
                                    status = 'zutylizowany';
                                } else if (status === 'N/A') {
                                    status = noDataText;
                                }
                            }

                            // Tworzenie wiersza tabeli
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${item.name || noDataText}</td>
                                <td>${typeValue}</td>
                                <td>${serialNumber}</td>
                                <td>${item.quantity || 1}</td>
                                <td>${assignedDate}</td>
                                <td><span class="status-badge ${item.status}">${status}</span></td>
                                <td></td>
                                <td>
                                    <button class="btn-icon" onclick="unassignFromDepartment(${item.id})">
                                        <i class="fas fa-unlink"></i>
                                    </button>
                                    <button class="btn-icon" onclick="editEquipment(${item.id})">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                </td>
                            `;
                            
                            fragment.appendChild(row);
                        } catch (itemErr) {
                            console.error('Error processing equipment item:', itemErr, item);
                        }
                    });
                    
                    // Clear table and add all rows at once
                    tbody.innerHTML = '';
                    tbody.appendChild(fragment);
                    
                    // Apply translations after loading equipment in a safer way
                    if (language === 'pl') {
                        try {
                            // Używamy setTimeout, żeby dać przeglądarce czas na renderowanie
                            setTimeout(() => {
                                translateUIElements();
                            }, 100);
                        } catch (err) {
                            console.error('Błąd podczas tłumaczenia elementów tabeli:', err);
                        }
                    }
                } else {
                    const noEquipmentText = language === 'pl' ? 'Brak sprzętu przypisanego do tego działu' : 'No equipment assigned to this department';
                    tbody.innerHTML = `<tr><td colspan="8">${noEquipmentText}</td></tr>`;
                }
            } catch (err) {
                console.error('Error processing equipment data:', err);
                tbody.innerHTML = `<tr><td colspan="8">${language === 'pl' ? 'Błąd przetwarzania danych' : 'Error processing data'}</td></tr>`;
            }
            
            // Bezpieczne usunięcie loadingSpinnera
            if (loadingSpinner && loadingSpinner.parentNode) {
                loadingSpinner.remove();
            }
        })        .catch(error => {
            console.error('Error:', error);
            const errorText = language === 'pl' ? 'Nie udało się załadować danych sprzętu' : 'Failed to load equipment data';
            if (equipmentList) {
                equipmentList.innerHTML = `<div class="error-message">${errorText}</div>`;
            }
            
            // Bezpieczne usunięcie loadingSpinnera
            if (loadingSpinner && loadingSpinner.parentNode) {
                loadingSpinner.remove();
            }
        })
        .finally(() => {
            // Zawsze resetujemy flagę po zakończeniu
            isLoadingEquipment = false;
        });
}

// Add function to unassign equipment from department
function unassignFromDepartment(equipmentId) {
    // Get current language for confirmation message
    const language = document.documentElement.getAttribute('data-language') || 'en';
    const confirmMessage = language === 'pl' ? 
        'Czy na pewno chcesz cofnąć przypisanie tego sprzętu do działu?' : 
        'Are you sure you want to unassign this equipment from the department?';
    
    if (confirm(confirmMessage)) {
        fetch('/api/equipment/unassign', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ equipment_id: equipmentId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload equipment list to reflect changes
                const departmentSelect = document.getElementById('departmentSelect');
                if (departmentSelect && departmentSelect.value) {
                    loadDepartmentEquipment(departmentSelect.value);
                }
            } else {
                const errorMessage = language === 'pl' ? 
                    'Wystąpił błąd przy cofaniu przypisania: ' + (data.error || 'Nieznany błąd') : 
                    'Error unassigning equipment: ' + (data.error || 'Unknown error');
                alert(errorMessage);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            const errorMessage = language === 'pl' ? 
                'Nie udało się cofnąć przypisania sprzętu. Spróbuj ponownie.' : 
                'Failed to unassign equipment. Please try again.';
            alert(errorMessage);
        });
    }
}

// Add function to edit equipment
function editEquipment(equipmentId) {
    // Get current language
    const language = document.documentElement.getAttribute('data-language') || 'en';
    
    // First get equipment details
    fetch(`/api/equipment/${equipmentId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Switch to manual input tab
            const tabButton = document.querySelector('.method-btn[data-method="manual"]');
            if (tabButton) tabButton.click();
            
            // Populate form with equipment data
            const form = document.getElementById('itemForm');
            if (form && data.equipment) {
                // Store equipment ID in hidden field or as a data attribute on the form
                form.dataset.equipmentId = equipmentId;
                
                // Update form action to indicate editing mode
                form.dataset.mode = 'edit';
                
                // Populate form fields
                document.getElementById('itemName').value = data.equipment.name || '';
                document.getElementById('itemCategory').value = data.equipment.type || 'hardware';
                document.getElementById('itemStatus').value = data.equipment.status || 'available';
                document.getElementById('itemQuantity').value = data.equipment.quantity || 1;
                document.getElementById('assignTo').value = data.equipment.assigned_to_department || '';
                
                // Additional fields if available
                if (document.getElementById('itemSerial')) {
                    document.getElementById('itemSerial').value = data.equipment.serial_number || '';
                }
                if (document.getElementById('itemValue')) {
                    document.getElementById('itemValue').value = data.equipment.value || '';
                }
                if (document.getElementById('itemDescription')) {
                    document.getElementById('itemDescription').value = data.equipment.description || '';
                }
                if (document.getElementById('itemManufacturer')) {
                    document.getElementById('itemManufacturer').value = data.equipment.manufacturer || '';
                }
                if (document.getElementById('itemModel')) {
                    document.getElementById('itemModel').value = data.equipment.model || '';
                }
                if (document.getElementById('itemNotes')) {
                    document.getElementById('itemNotes').value = data.equipment.notes || '';
                }
                if (document.getElementById('acquisitionDate')) {
                    document.getElementById('acquisitionDate').value = data.equipment.acquisition_date || '';
                }
                
                // Update save button text to reflect editing mode
                const saveButton = document.getElementById('saveItemBtn');
                if (saveButton) {
                    if (language === 'pl') {
                        saveButton.textContent = 'Aktualizuj element';
                        saveButton.dataset.pl = 'Aktualizuj element';
                    } else {
                        saveButton.textContent = 'Update Item';
                        saveButton.dataset.en = 'Update Item';
                    }
                }
                
                // Scroll to the form
                form.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            const errorMessage = language === 'pl' ? 
                'Nie udało się pobrać danych sprzętu do edycji.' : 
                'Failed to retrieve equipment data for editing.';
            alert(errorMessage);
        });
}

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
    
    // Listen for language changes and update inventory-specific elements
    document.addEventListener('languageChanged', function(e) {
        const newLanguage = e.detail.language;
        
        // Update any inventory-specific elements that need translation
        setTimeout(() => {
            if (typeof updateInventoryTranslations === 'function') {
                updateInventoryTranslations(newLanguage);
            }
        }, 10);
    });
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

    // Invoice processing logic with enhanced display and error handling
    const invoiceForm = document.getElementById('invoiceForm');
    const processingIndicator = document.getElementById('processingIndicator');
    const invoicePreview = document.getElementById('invoicePreview');
    
    invoiceForm?.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get the language for error messages
        const language = document.documentElement.getAttribute('data-language') || 'en';
        const noFileMsg = language === 'pl' ? 'Proszę wybrać plik PDF.' : 'Please select a PDF file.';
        
        const formData = new FormData(this);
        if (!formData.get('invoice_pdf')?.name) {
            alert(noFileMsg);
            return;
        }
        
        // Show processing indicator
        if (processingIndicator) {
            processingIndicator.style.display = 'flex';
        }
        if (invoicePreview) {
            invoicePreview.style.display = 'none';
        }
        
        // Add debugging console logs to track request
        console.log('Sending invoice processing request...');
        
        fetch('/api/invoice/process', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('Received response:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide processing indicator
            if (processingIndicator) {
                processingIndicator.style.display = 'none';
            }
            
            console.log('Received data:', data);
            
            if (data.error) {
                const errorMsg = language === 'pl' ? 
                    'Błąd: ' + data.error : 
                    'Error: ' + data.error;
                alert(errorMsg);
                return;
            }
            
            // Store invoice products in window for reference
            window.invoiceProducts = data.products || [];
            
            // Display invoice data
            document.getElementById('invoiceNumber').textContent = data.invoice_number || 
                (language === 'pl' ? 'Nie wykryto' : 'Not detected');
            document.getElementById('invoiceDate').textContent = data.invoice_date || 
                (language === 'pl' ? 'Nie wykryto' : 'Not detected');
            document.getElementById('invoiceVendor').textContent = data.vendor || 
                (language === 'pl' ? 'Nie wykryto' : 'Not detected');
            
            // Resize the container to accommodate the products
            const invoiceFormContainer = document.getElementById('invoiceFormContainer');
            if (invoiceFormContainer) {
                // Ensure container is large enough for content
                if (data.products && data.products.length > 10) {
                    invoiceFormContainer.style.maxWidth = '95%';
                    invoiceFormContainer.style.width = '1400px';
                }
            }
            
            // Display products with enhanced layout
            const productTableBody = document.getElementById('productTableBody');
            if (productTableBody) {
                productTableBody.innerHTML = '';
                
                if (data.products && data.products.length > 0) {
                    data.products.forEach((product, index) => {
                        // Guess product category
                        let category = guessProductCategory(product.name);
                        
                        const row = document.createElement('tr');
                        row.dataset.category = category.toLowerCase();
                        row.dataset.productIndex = index;
                        
                        // Store full product name for tooltip
                        const fullProductName = product.name;
                        
                        // Create a more detailed row with better spacing
                        row.innerHTML = `
                            <td data-full-text="${escapeHtml(fullProductName)}">${escapeHtml(fullProductName)}</td>                            <td>
                                <select class="product-category-select">
                                    <option value="hardware" ${category === 'Hardware' ? 'selected' : ''}>${language === 'pl' ? 'Sprzęt' : 'Hardware'}</option>
                                    <option value="software" ${category === 'Software' ? 'selected' : ''}>${language === 'pl' ? 'Oprogramowanie' : 'Software'}</option>
                                    <option value="furniture" ${category === 'Furniture' ? 'selected' : ''}>${language === 'pl' ? 'Meble' : 'Furniture'}</option>
                                    <option value="accessories" ${category === 'Accessories' ? 'selected' : ''}>${language === 'pl' ? 'Akcesoria' : 'Accessories'}</option>
                                    <option value="other" ${category === 'Other' ? 'selected' : ''}>${language === 'pl' ? 'Inne' : 'Other'}</option>
                                </select>
                            </td>
                            <td>
                                <input type="number" class="form-control quantity-input" value="${product.quantity || 1}" min="1">
                            </td>
                            <td>${product.unit_price ? product.unit_price.toFixed(2) : '0.00'} PLN</td>
                            <td>${product.total_price ? product.total_price.toFixed(2) : '0.00'} PLN</td>
                            <td>
                                <select class="assign-to-select form-control">
                                    <option value="">${language === 'pl' ? 'Wybierz dział...' : 'Select Department'}</option>
                                    ${Array.from(document.querySelectorAll('#departmentSelect option'))
                                        .filter(opt => opt.value)
                                        .map(opt => `
                                            <option value="${opt.value}" ${opt.selected ? 'selected' : ''}>
                                                ${opt.text}
                                            </option>
                                        `).join('')}
                                </select>
                            </td>
                            <td>
                                <button class="btn-icon import-product" title="${language === 'pl' ? 'Importuj do inwentarza' : 'Import to inventory'}">
                                    <i class="fas fa-plus"></i>
                                </button>
                                <button class="btn-icon edit-product" title="${language === 'pl' ? 'Edytuj element' : 'Edit item'}">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn-icon delete-product" title="${language === 'pl' ? 'Usuń element' : 'Delete item'}">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>
                        `;                        
                        productTableBody.appendChild(row);
                        
                        // Update translations for newly added row
                        if (typeof updateInventoryTranslations === 'function') {
                            const currentLang = document.documentElement.getAttribute('data-language') || 'en';
                            updateInventoryTranslations(currentLang);
                        }
                        
                        // Add click handler to show full product name
                        const nameCell = row.querySelector('td:first-child');
                        nameCell.addEventListener('click', function() {
                            showProductDetails(product, category);
                        });
                    });
                    
                    // Add event listeners for import buttons
                    document.querySelectorAll('.import-product').forEach((btn) => {
                        btn.addEventListener('click', function() {
                            const row = this.closest('tr');
                            const productIndex = row.dataset.productIndex;
                            const product = {...window.invoiceProducts[productIndex]};
                            
                            // Update with any user changes
                            product.quantity = parseFloat(row.querySelector('.quantity-input').value) || 1;
                            product.category = row.querySelector('.product-category-select').value;
                            product.assignTo = row.querySelector('.assign-to-select').value;
                            
                            importProductToInventory(product);
                            
                            // Mark as imported
                            row.classList.add('imported');
                            this.disabled = true;
                            this.innerHTML = '<i class="fas fa-check"></i>';
                        });
                    });
                    
                    // Add event listeners for edit product
                    document.querySelectorAll('.edit-product').forEach((btn) => {
                        btn.addEventListener('click', function() {
                            const row = this.closest('tr');
                            const productIndex = row.dataset.productIndex;
                            const product = window.invoiceProducts[productIndex];
                            
                            // Populate manual form with product data
                            document.getElementById('itemName').value = product.name;
                            document.getElementById('itemQuantity').value = product.quantity || 1;
                            document.getElementById('itemValue').value = product.unit_price || 0;
                            document.getElementById('itemCategory').value = row.querySelector('.product-category-select').value;
                            document.getElementById('assignTo').value = row.querySelector('.assign-to-select').value;
                            
                            // Switch to manual input tab
                            const manualTabBtn = document.querySelector('.method-btn[data-method="manual"]');
                            if (manualTabBtn) {
                                manualTabBtn.click();
                            }
                        });
                    });
                    
                    // Add event listeners for delete buttons
                    document.querySelectorAll('.delete-product').forEach((btn) => {
                        btn.addEventListener('click', function() {
                            const row = this.closest('tr');
                            const confirmMsg = language === 'pl' ? 
                                'Czy na pewno chcesz usunąć ten element?' : 
                                'Are you sure you want to remove this item?';
                            
                            if (confirm(confirmMsg)) {
                                row.remove();
                            }
                        });
                    });
                    
                    // Update category visuals when select changes
                    document.querySelectorAll('.product-category-select').forEach(select => {
                        select.addEventListener('change', function() {
                            const row = this.closest('tr');
                            row.dataset.category = this.value;
                        });
                    });
                    
                    // Show import all button
                    const importAllBtn = document.getElementById('importAllProducts');
                    if (importAllBtn) {
                        importAllBtn.style.display = 'inline-flex';
                    }
                } else {
                    const noProductsMsg = language === 'pl' ? 
                        'Nie znaleziono produktów w fakturze. Spróbuj metody alternatywnej.' : 
                        'No products found in the invoice. Try the alternative method.';
                    productTableBody.innerHTML = `<tr><td colspan="7">${noProductsMsg}</td></tr>`;
                }
            }
            
            // Show preview
            if (invoicePreview) {
                invoicePreview.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (processingIndicator) {
                processingIndicator.style.display = 'none';
            }
            const errorMsg = language === 'pl' ? 
                'Nie udało się przetworzyć faktury. Spróbuj ponownie lub użyj wprowadzania ręcznego.' : 
                'Failed to process invoice. Please try again or use manual input.';
            alert(errorMsg);
        });
    });
      // Obsługa przycisku "Dodaj brakujące pozycje"
    document.getElementById('addMissingProduct')?.addEventListener('click', function() {
        // Pobierz język interfejsu
        const language = document.documentElement.getAttribute('data-language') || 'en';
        
        // Sprawdź, czy faktura została przetworzona
        if (!window.invoiceProducts) {
            const errorMsg = language === 'pl' ? 
                'Najpierw przetwórz fakturę, aby móc dodać brakujące pozycje.' : 
                'Please process an invoice first to add missing items.';
            alert(errorMsg);
            return;
        }
        
        // Utwórz nowy pusty produkt
        const newProductIndex = window.invoiceProducts.length;
        const newProduct = {
            name: language === 'pl' ? 'Nowa pozycja' : 'New item',
            quantity: 1,
            unit_price: 0,
            total_price: 0
        };
        
        // Dodaj produkt do listy
        window.invoiceProducts.push(newProduct);
        
        // Dodaj nowy wiersz do tabeli
        const productTableBody = document.getElementById('productTableBody');
        if (productTableBody) {
            let category = 'Other';
            
            const row = document.createElement('tr');
            row.dataset.category = category.toLowerCase();
            row.dataset.productIndex = newProductIndex;
            
            // Utwórz wiersz z edytowalną zawartością
            row.innerHTML = `
                <td>
                    <input type="text" class="form-control" value="${newProduct.name}" placeholder="${language === 'pl' ? 'Wprowadź nazwę' : 'Enter name'}" onchange="window.invoiceProducts[${newProductIndex}].name = this.value">
                </td>
                <td>                    <select class="product-category-select">
                        <option value="hardware">${language === 'pl' ? 'Sprzęt' : 'Hardware'}</option>
                        <option value="software">${language === 'pl' ? 'Oprogramowanie' : 'Software'}</option>
                        <option value="furniture">${language === 'pl' ? 'Meble' : 'Furniture'}</option>
                        <option value="accessories">${language === 'pl' ? 'Akcesoria' : 'Accessories'}</option>
                        <option value="other" selected>${language === 'pl' ? 'Inne' : 'Other'}</option>
                    </select>
                </td>
                <td>
                    <input type="number" class="form-control quantity-input" value="${newProduct.quantity}" min="1" onchange="window.invoiceProducts[${newProductIndex}].quantity = this.value">
                </td>
                <td>
                    <input type="number" class="form-control" value="${newProduct.unit_price}" min="0" step="0.01" onchange="window.invoiceProducts[${newProductIndex}].unit_price = parseFloat(this.value); window.invoiceProducts[${newProductIndex}].total_price = parseFloat(this.value) * window.invoiceProducts[${newProductIndex}].quantity;">
                </td>
                <td>
                    <input type="number" class="form-control" value="${newProduct.total_price}" min="0" step="0.01" onchange="window.invoiceProducts[${newProductIndex}].total_price = parseFloat(this.value)">
                </td>
                <td>
                    <select class="assign-to-select form-control">
                        <option value="">${language === 'pl' ? 'Wybierz dział...' : 'Select Department'}</option>
                        ${Array.from(document.querySelectorAll('#departmentSelect option'))
                            .filter(opt => opt.value)
                            .map(opt => `
                                <option value="${opt.value}" ${opt.selected ? 'selected' : ''}>
                                    ${opt.text}
                                </option>
                            `).join('')}
                    </select>
                </td>
                <td>
                    <button class="btn-icon import-product" title="${language === 'pl' ? 'Importuj do inwentarza' : 'Import to inventory'}">
                        <i class="fas fa-plus"></i>
                    </button>
                    <button class="btn-icon delete-product" title="${language === 'pl' ? 'Usuń element' : 'Delete item'}">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;            
            productTableBody.appendChild(row);
            
            // Update translations for newly added row
            if (typeof updateInventoryTranslations === 'function') {
                const currentLang = document.documentElement.getAttribute('data-language') || 'en';
                updateInventoryTranslations(currentLang);
            }
            
            // Dodaj obsługę przycisków do nowego wiersza
            const importBtn = row.querySelector('.import-product');
            if (importBtn) {
                importBtn.addEventListener('click', function() {
                    const row = this.closest('tr');
                    const productIndex = row.dataset.productIndex;
                    const product = {...window.invoiceProducts[productIndex]};
                    
                    // Aktualizuj z wartościami z formularza
                    product.category = row.querySelector('.product-category-select').value;
                    product.assignTo = row.querySelector('.assign-to-select').value;
                    
                    importProductToInventory(product);
                    
                    // Oznacz jako zaimportowany
                    row.classList.add('imported');
                    this.disabled = true;
                    this.innerHTML = '<i class="fas fa-check"></i>';
                });
            }
            
            // Dodaj obsługę przycisku usuwania
            const deleteBtn = row.querySelector('.delete-product');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', function() {
                    const row = this.closest('tr');
                    const confirmMsg = language === 'pl' ? 
                        'Czy na pewno chcesz usunąć ten element?' : 
                        'Are you sure you want to remove this item?';
                    
                    if (confirm(confirmMsg)) {
                        row.remove();
                    }
                });
            }
            
            // Aktualizuj kategorię przy zmianie
            const categorySelect = row.querySelector('.product-category-select');
            if (categorySelect) {
                categorySelect.addEventListener('change', function() {
                    const row = this.closest('tr');
                    row.dataset.category = this.value;
                });
            }
        }
    });
    
    // Import all products button handler
    document.getElementById('importAllProducts')?.addEventListener('click', function() {
        const language = document.documentElement.getAttribute('data-language') || 'en';
        const rows = document.querySelectorAll('#productTableBody tr:not(.imported)');
        let importCount = 0;
        
        rows.forEach(row => {
            // Skip hidden rows (filtered out by category)
            if (row.style.display === 'none') return;
            
            const productIndex = row.dataset.productIndex;
            if (productIndex) {
                const product = JSON.parse(JSON.stringify(window.invoiceProducts[productIndex]));
                
                // Update with any user changes
                product.quantity = parseFloat(row.querySelector('.quantity-input').value) || 1;
                product.category = row.querySelector('.product-category-select').value;
                product.assignTo = row.querySelector('.assign-to-select').value;
                
                importProductToInventory(product, false); // Don't show individual alerts
                
                // Mark as imported
                row.classList.add('imported');
                const importBtn = row.querySelector('.import-product');
                if (importBtn) {
                    importBtn.disabled = true;
                    importBtn.innerHTML = '<i class="fas fa-check"></i>';
                }
                
                importCount++;
            }
        });
        
        if (importCount > 0) {
            const successMsg = language === 'pl' ? 
                `Pomyślnie zaimportowano ${importCount} produktów do inwentarza.` :
                `Successfully imported ${importCount} products to inventory.`;
            alert(successMsg);
        } else {
            const noItemsMsg = language === 'pl' ? 
                'Nie wybrano produktów do importu.' :
                'No products selected for import.';
            alert(noItemsMsg);
        }
    });

    // Handle form submissions for manual form
    const manualForm = document.getElementById('itemForm');
    
    if (manualForm) {
        // Remove existing event listener if any
        const newManualForm = manualForm.cloneNode(true);
        manualForm.parentNode.replaceChild(newManualForm, manualForm);
        
        newManualForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            // Check if we're editing or adding new
            const isEditing = this.dataset.mode === 'edit';
            const equipmentId = this.dataset.equipmentId;
            
            if (isEditing && equipmentId) {
                // Add equipment ID to form data
                formData.append('equipment_id', equipmentId);
                
                fetch('/api/equipment/update', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Get current language
                        const language = document.documentElement.getAttribute('data-language') || 'en';
                        const successMessage = language === 'pl' ? 
                            'Sprzęt został pomyślnie zaktualizowany!' : 
                            'Equipment updated successfully!';
                        alert(successMessage);
                        
                        // Reset form state
                        newManualForm.reset();
                        delete newManualForm.dataset.mode;
                        delete newManualForm.dataset.equipmentId;
                        
                        // Update save button text
                        const saveButton = document.getElementById('saveItemBtn');
                        if (saveButton) {
                            if (language === 'pl') {
                                saveButton.textContent = 'Zapisz element';
                                saveButton.dataset.pl = 'Zapisz element';
                            } else {
                                saveButton.textContent = 'Save Item';
                                saveButton.dataset.en = 'Save Item';
                            }
                        }
                        
                        // Refresh equipment list if we're viewing the correct department
                        const departmentSelect = document.getElementById('departmentSelect');
                        if (departmentSelect && departmentSelect.value) {
                            loadDepartmentEquipment(departmentSelect.value);
                        }
                    } else {
                        const language = document.documentElement.getAttribute('data-language') || 'en';
                        const errorMessage = language === 'pl' ?
                            'Błąd podczas aktualizacji: ' + (data.error || 'Nieznany błąd') :
                            'Error updating equipment: ' + (data.error || 'Unknown error');
                        alert(errorMessage);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    const language = document.documentElement.getAttribute('data-language') || 'en';
                    const errorMessage = language === 'pl' ?
                        'Błąd podczas aktualizacji. Spróbuj ponownie.' :
                        'Error updating equipment. Please try again.';
                    alert(errorMessage);
                });
            } else {
                // Adding new equipment
                fetch('/api/equipment/add', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Get current language
                        const language = document.documentElement.getAttribute('data-language') || 'en';
                        const successMessage = language === 'pl' ?
                            'Nowy sprzęt został pomyślnie dodany!' :
                            'New equipment added successfully!';
                        alert(successMessage);
                        
                        // Reset form
                        newManualForm.reset();
                        
                        // Refresh equipment list if we're viewing the department it was assigned to
                        const departmentSelect = document.getElementById('departmentSelect');
                        const assignTo = formData.get('assignTo');
                        if (departmentSelect && departmentSelect.value === assignTo) {
                            loadDepartmentEquipment(assignTo);
                        }
                    } else {
                        const language = document.documentElement.getAttribute('data-language') || 'en';
                        const errorMessage = language === 'pl' ?
                            'Błąd podczas dodawania: ' + (data.error || 'Nieznany błąd') :
                            'Error adding equipment: ' + (data.error || 'Unknown error');
                        alert(errorMessage);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    const language = document.documentElement.getAttribute('data-language') || 'en';
                    const errorMessage = language === 'pl' ?
                        'Błąd podczas dodawania. Spróbuj ponownie.' :
                        'Error adding equipment. Please try again.';
                    alert(errorMessage);
                });
            }
        });
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
                            } else if (assignedDate !== noDataText) {
                                // Format date to only show YYYY-MM-DD without time
                                try {
                                    // If there's a space in the date string, it contains time
                                    if (assignedDate.includes(' ')) {
                                        assignedDate = assignedDate.split(' ')[0];
                                    }
                                } catch (dateErr) {
                                    console.error('Error formatting date:', dateErr);
                                }
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
                                    <button class="btn-icon" onclick="deleteEquipment(${item.id})">
                                        <i class="fas fa-trash"></i>
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

// Function to unassign equipment from a department
function unassignFromDepartment(equipmentId) {
    // Get current language
    const language = document.documentElement.getAttribute('data-language') || 'en';
    
    const confirmMessage = language === 'pl' ? 
        'Czy na pewno chcesz cofnąć przypisanie tego elementu do działu?' : 
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
                'Wystąpił błąd przy cofaniu przypisania. Spróbuj ponownie.' : 
                'Error unassigning equipment. Please try again.';
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

// Add this function if it's not already defined
function guessProductCategory(name) {
    if (!name) return 'Other';
    
    name = name.toLowerCase();
    
    // Keywords that suggest hardware
    const hardwareKeywords = ['laptop', 'monitor', 'komputer', 'pc', 'desktop', 'server', 
                             'printer', 'drukarka', 'klawiatura', 'myszka', 'mouse', 'keyboard',
                             'dysk', 'drive', 'ssd', 'hdd', 'ram', 'procesor', 'cpu', 'motherboard',
                             'karta graficzna', 'gpu', 'pamięć', 'płyta główna'];
                             
    // Keywords that suggest software
    const softwareKeywords = ['licencja', 'license', 'software', 'system', 'windows', 'office',
                             'program', 'application', 'app', 'subskrypcja', 'subscription',
                             'oprogramowanie', 'antywirus', 'adobe', 'autocad'];
                             
    // Keywords that suggest furniture
    const furnitureKeywords = ['biurko', 'desk', 'krzesło', 'chair', 'fotel', 'armchair', 
                              'szafka', 'cabinet', 'półka', 'shelf', 'lampa', 'lamp',
                              'stół', 'table', 'meble', 'furniture'];
                              
    // Keywords that suggest accessories
    const accessoriesKeywords = ['kabel', 'cable', 'adapter', 'przejściówka', 'torba', 'bag',
                                'etui', 'case', 'słuchawki', 'headphones', 'głośnik', 'speaker',
                                'ładowarka', 'charger', 'power bank', 'powerbank', 'bateria', 'battery',
                                'dock', 'stacja', 'pamięć usb', 'pendrive'];
    
    // Check for category matches
    if (hardwareKeywords.some(keyword => name.includes(keyword))) {
        return 'Hardware';
    }
    
    if (softwareKeywords.some(keyword => name.includes(keyword))) {
        return 'Software';
    }
    
    if (furnitureKeywords.some(keyword => name.includes(keyword))) {
        return 'Furniture';
    }
    
    if (accessoriesKeywords.some(keyword => name.includes(keyword))) {
        return 'Accessories';
    }
    
    return 'Other';
}

// Function to import product to inventory system
function importProductToInventory(product, showAlert = true) {
    const language = document.documentElement.getAttribute('data-language') || 'en';
    
    const formData = new FormData();
    formData.append('itemName', product.name);
    formData.append('itemCategory', product.category || 'hardware');
    formData.append('itemStatus', 'available');
    formData.append('itemQuantity', product.quantity || 1);
    formData.append('itemValue', product.unit_price || product.price || 0);
    formData.append('assignTo', product.assignTo || ''); // Make sure department is included

    // Add other necessary fields
    const invoiceNumber = document.getElementById('invoiceNumber')?.textContent;
    const invoiceDate = document.getElementById('invoiceDate')?.textContent;
    const vendor = document.getElementById('invoiceVendor')?.textContent;

    if (vendor && vendor !== 'Not detected' && vendor !== 'Nie wykryto') {
        formData.append('itemManufacturer', vendor);
    }

    // Add notes with invoice reference
    const notesPlaceholder = language === 'pl' ? 
        `Zaimportowano z faktury ${invoiceNumber || 'bez numeru'} z dnia ${invoiceDate || new Date().toLocaleDateString()}` : 
        `Imported from invoice ${invoiceNumber || 'unnumbered'} dated ${invoiceDate || new Date().toLocaleDateString()}`;
    formData.append('itemNotes', notesPlaceholder);
    
    // Handle acquisition date
    if (invoiceDate && invoiceDate !== 'Not detected' && invoiceDate !== 'Nie wykryto') {
        formData.append('acquisitionDate', invoiceDate);
    } else {
        formData.append('acquisitionDate', new Date().toISOString().split('T')[0]);
    }

    // Handle serial number if available
    if (product.serial_number) {
        formData.append('itemSerial', product.serial_number);
    }

    // Handle model if available
    if (product.model) {
        formData.append('itemModel', product.model);
    }

    // Send request
    fetch('/api/equipment/add', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            if (showAlert) {
                const successMsg = language === 'pl' ?
                    `Produkt "${product.name}" dodany pomyślnie!` :
                    `Product "${product.name}" added successfully!`;
                alert(successMsg);
            }
            // Refresh equipment list if we're viewing the department it was assigned to
            const departmentSelect = document.getElementById('departmentSelect');
            if (departmentSelect && departmentSelect.value === product.assignTo) {
                loadDepartmentEquipment(product.assignTo);
            }
        } else {
            if (showAlert) {
                const errorMsg = language === 'pl' ?
                    'Błąd: ' + (data.error || 'Nieznany błąd') :
                    'Error: ' + (data.error || 'Unknown error');
                alert(errorMsg);
            }
            console.error('Error adding product:', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (showAlert) {
            const errorMsg = language === 'pl' ?
                'Nie udało się dodać produktu. Sprawdź szczegóły w konsoli.' :
                'Failed to add product. Check console for details.';
            alert(errorMsg);
        }
    });
}

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add function to delete equipment from inventory
function deleteEquipment(equipmentId) {
    // Get current language for confirmation message
    const language = document.documentElement.getAttribute('data-language') || 'en';
    const confirmMessage = language === 'pl' ? 
        'Czy na pewno chcesz usunąć ten element z inwentarza?' : 
        'Are you sure you want to delete this equipment from inventory?';
    
    console.log(`Próba usunięcia elementu z ID: ${equipmentId}`);
    
    if (confirm(confirmMessage)) {
        console.log(`Usuwanie zatwierdzone przez użytkownika, wysyłanie żądania...`);
        
        // Używamy FormData zamiast JSON - bardziej niezawodne
        const formData = new FormData();
        formData.append('equipment_id', equipmentId);
        formData.append('action', 'delete'); // Dodajemy akcję usunięcia
        
        fetch('/api/equipment/update', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload equipment list to reflect changes
                const departmentSelect = document.getElementById('departmentSelect');
                if (departmentSelect && departmentSelect.value) {
                    loadDepartmentEquipment(departmentSelect.value);
                }
                
                // Show success message
                const successMsg = language === 'pl' ? 
                    'Element został pomyślnie usunięty' : 
                    'Equipment successfully deleted';
                alert(successMsg);
            } else {
                // Show error message
                const errorMsg = language === 'pl' ? 
                    'Błąd: ' + (data.error || 'Nieznany błąd') : 
                    'Error: ' + (data.error || 'Unknown error');
                alert(errorMsg);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            const errorMsg = language === 'pl' ? 
                'Nie udało się usunąć elementu. Spróbuj ponownie.' : 
                'Failed to delete equipment. Please try again.';
            alert(errorMsg);
        });
    }
}

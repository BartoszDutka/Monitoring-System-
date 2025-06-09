// Zmienna do przechowywania zaznaczonych produktów
let selectedProductsToImport = new Set();

// Funkcja aktualizująca licznik zaznaczonych produktów
function updateSelectedCounter() {
    const counter = document.getElementById('selectedProductsCounter');
    if (counter) {
        const count = selectedProductsToImport.size;
        const language = document.documentElement.getAttribute('data-language') || 'en';
        counter.textContent = language === 'pl' 
            ? `Wybrano: ${count}` 
            : `Selected: ${count}`;
        
        // Pokaż lub ukryj przycisk importu zaznaczonych
        const importSelectedBtn = document.getElementById('importSelectedProducts');
        if (importSelectedBtn) {
            importSelectedBtn.style.display = count > 0 ? 'inline-flex' : 'none';
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Inicjalne tłumaczenie
    translateUIElements();
    
    // Konfiguracja obserwerów
    setupMutationObserver();
    
    // Listen for language changes and update inventory-specific elements
    document.addEventListener('languageChanged', function(e) {
        const newLanguage = e.detail.language;
        updateSelectedCounter(); // Update counter text
        
        // Update any other inventory-specific elements that need translation
        setTimeout(() => {
            updateInventoryTranslations(newLanguage);
        }, 10);
    });
      const methodBtns = document.querySelectorAll('.method-btn');
    const sections = {
        manual: document.querySelector('.manual-section'),
        invoice: document.querySelector('.invoice-section'),
        equipment: document.querySelector('.equipment-section')
    };

    // Remove null sections for users without permissions
    Object.keys(sections).forEach(key => {
        if (!sections[key]) {
            delete sections[key];
        }
    });

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
            
            // Perform translations again when changing sections
            translateUIElements();
            
            // If equipment section is selected, immediately translate its content
            if (method === 'equipment') {
                const departmentSelect = document.getElementById('departmentSelect');
                if (departmentSelect && departmentSelect.value) {
                    // Reload equipment data to ensure translations are applied
                    loadDepartmentEquipment(departmentSelect.value);
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
            fileDisplay.textContent = 'No files selected';
        }
    });
    
    // File upload preview for invoice form
    const invoiceInput = document.getElementById('invoicePdf');
    const invoiceFileDisplay = document.getElementById('selectedInvoiceFile');
    
    invoiceInput?.addEventListener('change', function() {
        if (this.files.length > 0) {
            invoiceFileDisplay.textContent = this.files[0].name;
        } else {
            invoiceFileDisplay.textContent = 'No file selected';
        }
    });
    
    // Invoice processing logic with enhanced display
    const invoiceForm = document.getElementById('invoiceForm');
    const processingIndicator = document.getElementById('processingIndicator');
    const invoicePreview = document.getElementById('invoicePreview');
    
    invoiceForm?.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        if (!formData.get('invoice_pdf').name) {
            alert('Please select a PDF file.');
            return;
        }
        
        // Show processing indicator
        processingIndicator.style.display = 'flex';
        invoicePreview.style.display = 'none';
        
        fetch('/api/invoice/process', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide processing indicator
            processingIndicator.style.display = 'none';
            
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }
            
            // Store invoice products in window for reference
            window.invoiceProducts = data.products || [];
            
            // Display invoice data
            document.getElementById('invoiceNumber').textContent = data.invoice_number || 'Not detected';
            document.getElementById('invoiceDate').textContent = data.invoice_date || 'Not detected';
            document.getElementById('invoiceVendor').textContent = data.vendor || 'Not detected';
            
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
            productTableBody.innerHTML = '';
            
            // Get language for translations
            const language = document.documentElement.getAttribute('data-language') || 'en';
            
            // For each product, create a table row
            window.invoiceProducts.forEach((product, index) => {
                // Skip products with invalid or empty names
                if (!product.name || product.name.trim() === '') return;
                
                // Determine the most likely category
                let category = guessProductCategory(product.name);
                
                const row = document.createElement('tr');
                row.dataset.category = category.toLowerCase();
                row.dataset.productIndex = index;
                
                // Create checkbox for selection
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.classList.add('product-selection-checkbox');
                checkbox.addEventListener('change', function() {
                    const productId = row.dataset.productIndex;
                    if (this.checked) {
                        selectedProductsToImport.add(productId);
                    } else {
                        selectedProductsToImport.delete(productId);
                    }
                    updateSelectedCounter();
                });
                
                // Create cells
                const checkboxCell = document.createElement('td');
                checkboxCell.appendChild(checkbox);
                row.appendChild(checkboxCell);
                
                row.innerHTML += `
                    <td>${escapeHtml(product.name || '')}</td>
                    <td>                        <select class="product-category-select">
                            <option value="hardware" ${category === 'Hardware' ? 'selected' : ''}>${language === 'pl' ? 'Sprzęt' : 'Hardware'}</option>
                            <option value="software" ${category === 'Software' ? 'selected' : ''}>${language === 'pl' ? 'Oprogramowanie' : 'Software'}</option>
                            <option value="furniture" ${category === 'Furniture' ? 'selected' : ''}>${language === 'pl' ? 'Meble' : 'Furniture'}</option>
                            <option value="accessories" ${category === 'Accessories' ? 'selected' : ''}>${language === 'pl' ? 'Akcesoria' : 'Accessories'}</option>
                            <option value="other" ${category === 'Other' ? 'selected' : ''}>${language === 'pl' ? 'Inne' : 'Other'}</option>
                        </select>
                    </td>
                    <td><input type="number" class="quantity-input form-control" value="${product.quantity || 1}" min="1"></td>
                    <td>${product.unit_price ? parseFloat(product.unit_price).toFixed(2) : '0.00'}</td>
                    <td>${product.total_price ? parseFloat(product.total_price).toFixed(2) : '0.00'}</td>
                    <td>                    <select class="assign-to-select form-control">
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
                        <button class="btn-icon select-product" title="Select for import">
                            <i class="fas fa-plus"></i>
                        </button>
                        <button class="btn-icon edit-product" title="Edit item">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-icon delete-product" title="Delete item">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>`;                
                productTableBody.appendChild(row);
                
                // Update translations for newly added row
                if (typeof updateInventoryTranslations === 'function') {
                    const currentLang = document.documentElement.getAttribute('data-language') || 'en';
                    updateInventoryTranslations(currentLang);
                }
                
                // Add click handler to show full product name
                const nameCell = row.querySelector('td:nth-child(2)');
                nameCell.addEventListener('click', function() {
                    showProductDetails(product, category);
                });
            });
            
            // Add event listeners for import buttons
            document.querySelectorAll('.select-product').forEach((btn) => {
                btn.addEventListener('click', function() {
                    const row = this.closest('tr');
                    const productIndex = row.dataset.productIndex;
                    const checkbox = row.querySelector('.product-select-checkbox');
                    
                    // Toggle selection
                    if (row.classList.contains('selected')) {
                        // Unselect product
                        row.classList.remove('selected');
                        this.innerHTML = '<i class="fas fa-plus"></i>';
                        this.title = language === 'pl' ? 'Wybierz do importu' : 'Select for import';
                        
                        if (checkbox) checkbox.checked = false;
                        selectedProductsToImport.delete(productIndex);
                    } else {
                        // Select product
                        row.classList.add('selected');
                        this.innerHTML = '<i class="fas fa-check"></i>';
                        this.title = language === 'pl' ? 'Wybrano do importu' : 'Selected for import';
                        
                        if (checkbox) checkbox.checked = true;
                        selectedProductsToImport.add(productIndex);
                    }
                    
                    // Update the counter
                    updateSelectedCounter();
                });
            });
            
            // Add event listeners for checkboxes
            document.querySelectorAll('.product-select-checkbox').forEach((checkbox) => {
                checkbox.addEventListener('change', function() {
                    const row = this.closest('tr');
                    const productIndex = row.dataset.productIndex;
                    const selectBtn = row.querySelector('.select-product');
                    
                    if (this.checked) {
                        // Select product
                        row.classList.add('selected');
                        if (selectBtn) {
                            selectBtn.innerHTML = '<i class="fas fa-check"></i>';
                            selectBtn.title = language === 'pl' ? 'Wybrano do importu' : 'Selected for import';
                        }
                        selectedProductsToImport.add(productIndex);
                    } else {
                        // Unselect product
                        row.classList.remove('selected');
                        if (selectBtn) {
                            selectBtn.innerHTML = '<i class="fas fa-plus"></i>';
                            selectBtn.title = language === 'pl' ? 'Wybierz do importu' : 'Select for import';
                        }
                        selectedProductsToImport.delete(productIndex);
                    }
                    
                    // Update the counter
                    updateSelectedCounter();
                });
            });
            
            // Add event listener for select all checkbox
            const selectAllCheckbox = document.getElementById('selectAllProducts');
            if (selectAllCheckbox) {
                selectAllCheckbox.addEventListener('change', function() {
                    const checkboxes = document.querySelectorAll('.product-select-checkbox');
                    
                    checkboxes.forEach(checkbox => {
                        // Only affect visible rows (not filtered out)
                        const row = checkbox.closest('tr');
                        if (row.style.display !== 'none') {
                            checkbox.checked = this.checked;
                            checkbox.dispatchEvent(new Event('change'));
                        }
                    });
                });
            }
            
            // Add selectAllProducts event handler
            document.getElementById('selectAllProducts')?.addEventListener('change', function() {
                const checkboxes = document.querySelectorAll('#productTableBody .product-selection-checkbox');
                const language = document.documentElement.getAttribute('data-language') || 'en';
                
                checkboxes.forEach(checkbox => {
                    // Only affect visible rows (not filtered out)
                    const row = checkbox.closest('tr');
                    if (row && row.style.display !== 'none') {
                        checkbox.checked = this.checked;
                        
                        const productIndex = row.dataset.productIndex;
                        const selectBtn = row.querySelector('.select-product');
                        
                        if (this.checked) {
                            // Select product
                            row.classList.add('selected');
                            if (selectBtn) {
                                selectBtn.innerHTML = '<i class="fas fa-check"></i>';
                                selectBtn.title = language === 'pl' ? 'Wybrano do importu' : 'Selected for import';
                            }
                            selectedProductsToImport.add(productIndex);
                        } else {
                            // Unselect product
                            row.classList.remove('selected');
                            if (selectBtn) {
                                selectBtn.innerHTML = '<i class="fas fa-plus"></i>';
                                selectBtn.title = language === 'pl' ? 'Wybierz do importu' : 'Select for import';
                            }
                            selectedProductsToImport.delete(productIndex);
                        }
                    }
                });
                
                // Update the counter
                updateSelectedCounter();
            });
            
            // Add event listeners for other buttons
            document.querySelectorAll('.edit-product').forEach((btn, index) => {
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
                    document.querySelector('.method-btn[data-method="manual"]').click();
                });
            });
              // Add event listeners for delete buttons
            document.querySelectorAll('.delete-product').forEach((btn, index) => {
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
            document.getElementById('importAllProducts').style.display = 'inline-flex';
            
            // Show preview
            invoicePreview.style.display = 'block';
            
            // Remove any horizontal scroll that might have been added
            document.querySelectorAll('.invoice-data-table').forEach(table => {
                table.style.overflowX = 'visible';
            });
            
            // Resize container based on content width
            setTimeout(adjustContainerWidth, 100);
        })
        .catch(error => {
            console.error('Error:', error);
            processingIndicator.style.display = 'none';
            alert('Failed to process invoice. Please try again or use manual input.');
        });
    });
    
    // Category filter functionality
    document.getElementById('toggleHardware')?.addEventListener('change', function() {
        updateProductVisibility();
    });
    
    document.getElementById('toggleSoftware')?.addEventListener('change', function() {
        updateProductVisibility();
    });
    
    document.getElementById('toggleFurniture')?.addEventListener('change', function() {
        updateProductVisibility();
    });
    
    document.getElementById('toggleAccessories')?.addEventListener('change', function() {
        updateProductVisibility();
    });
    
    document.getElementById('toggleOther')?.addEventListener('change', function() {
        updateProductVisibility();
    });
      function updateProductVisibility() {
        const showHardware = document.getElementById('toggleHardware').checked;
        const showSoftware = document.getElementById('toggleSoftware').checked;
        const showFurniture = document.getElementById('toggleFurniture').checked;
        const showAccessories = document.getElementById('toggleAccessories').checked;
        const showOther = document.getElementById('toggleOther').checked;
        const hideImported = document.getElementById('hideImportedItems')?.checked || false;
        
        document.querySelectorAll('#productTableBody tr').forEach(row => {
            const category = row.dataset.category;
            const isImported = row.classList.contains('imported');
            
            // First check if this is an imported item that should be hidden
            if (isImported && hideImported) {
                row.style.display = 'none';
                return;
            }
            
            // Then apply category filters
            if ((category === 'hardware' && showHardware) ||
                (category === 'software' && showSoftware) ||
                (category === 'furniture' && showFurniture) ||
                (category === 'accessories' && showAccessories) ||
                (category !== 'hardware' && category !== 'software' && 
                 category !== 'furniture' && category !== 'accessories' && showOther)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
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
            
            // Create checkbox for selection
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.classList.add('product-selection-checkbox');
            checkbox.addEventListener('change', function() {
                const productId = row.dataset.productIndex;
                if (this.checked) {
                    selectedProductsToImport.add(productId);
                } else {
                    selectedProductsToImport.delete(productId);
                }
                updateSelectedCounter();
            });
            
            // Create cells
            const checkboxCell = document.createElement('td');
            checkboxCell.appendChild(checkbox);
            row.appendChild(checkboxCell);
            
            // Utwórz wiersz z edytowalną zawartością
            row.innerHTML += `
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
                    <button class="btn-icon select-product" title="${language === 'pl' ? 'Wybierz do importu' : 'Select for import'}">
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
            const selectBtn = row.querySelector('.select-product');
            if (selectBtn) {
                selectBtn.addEventListener('click', function() {
                    const row = this.closest('tr');
                    const productIndex = row.dataset.productIndex;
                    const checkbox = row.querySelector('.product-selection-checkbox');
                    
                    // Toggle selection
                    if (row.classList.contains('selected')) {
                        // Unselect product
                        row.classList.remove('selected');
                        this.innerHTML = '<i class="fas fa-plus"></i>';
                        this.title = language === 'pl' ? 'Wybierz do importu' : 'Select for import';
                        
                        if (checkbox) checkbox.checked = false;
                        selectedProductsToImport.delete(productIndex);
                    } else {
                        // Select product
                        row.classList.add('selected');
                        this.innerHTML = '<i class="fas fa-check"></i>';
                        this.title = language === 'pl' ? 'Wybrano do importu' : 'Selected for import';
                        
                        if (checkbox) checkbox.checked = true;
                        selectedProductsToImport.add(productIndex);
                    }
                    
                    // Update the counter
                    updateSelectedCounter();
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
    
    // Try alternative method button
    document.getElementById('tryAlternativeMethod')?.addEventListener('click', function() {
        const fileInput = document.getElementById('invoicePdf');
        if (!fileInput.files[0]) {
            alert('Please select a PDF file first.');
            return;
        }
        
        // Show processing indicator
        processingIndicator.style.display = 'flex';
        invoicePreview.style.display = 'none';
        
        // Create a new FormData with the same file but alternative flag
        const formData = new FormData();
        formData.append('invoice_pdf', fileInput.files[0]);
        formData.append('alternative_method', 'true');
        
        // Same endpoint but with flag for alternative processing
        fetch('/api/invoice/process', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Process response as before
            processingIndicator.style.display = 'none';
            
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }
            
            // Update UI with new data
            // ...same as above code...
            
            invoicePreview.style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            processingIndicator.style.display = 'none';
            alert('Alternative method failed. Please try manual input.');
        });
    });
    // Import all products button
    document.getElementById('importAllProducts')?.addEventListener('click', function() {
        const rows = document.querySelectorAll('#productTableBody tr:not(.imported)');
        let importCount = 0;
        let importPromises = [];
        
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
                
                // Store the import promise
                importPromises.push(importProductToInventory(product, false)); // Don't show individual alerts
                
                // Mark as imported
                row.classList.add('imported');
                const importBtn = row.querySelector('.import-product');
                if (importBtn) {
                    importBtn.disabled = true;
                    importBtn.innerHTML = '<i class="fas fa-check"></i>';
                }
                
                // Disable the checkbox if it exists
                const checkbox = row.querySelector('.product-selection-checkbox');
                if (checkbox) {
                    checkbox.disabled = true;
                    checkbox.checked = false;
                }
                
                importCount++;
            }
        });
        
        // Clear the selected products
        if (typeof selectedProductsToImport !== 'undefined') {
            selectedProductsToImport.clear();
            updateSelectedCounter();
        }
        
        const language = document.documentElement.getAttribute('data-language') || 'en';
        
        // Wait for all imports to finish
        Promise.all(importPromises)
            .then(results => {                if (importCount > 0) {
                    const message = language === 'pl' ? 
                        `Pomyślnie zaimportowano ${importCount} produktów do inwentarza.` : 
                        `Successfully imported ${importCount} products to inventory.`;
                    alert(message);
                    
                    // Automatically clear the invoice form after successful import
                    clearInvoicePreviewAndForm();
                } else {
                    const message = language === 'pl' ? 
                        'Nie zaimportowano żadnych produktów.' : 
                        'No products were imported.';
                    alert(message);
                }
            })
            .catch(error => {
                console.error('Error during batch import:', error);
                const errorMessage = language === 'pl' ? 
                    'Wystąpił błąd podczas importowania produktów.' :
                    'An error occurred while importing products.';
                alert(errorMessage);
            });
    });// Import selected products button handler
    document.getElementById('importSelectedProducts')?.addEventListener('click', function() {
        if (selectedProductsToImport.size === 0) {
            const language = document.documentElement.getAttribute('data-language') || 'en';
            const message = language === 'pl' ? 
                'Nie wybrano żadnych produktów do importu.' : 
                'No products selected for import.';
            alert(message);
            return;
        }
        
        let importCount = 0;
        let importPromises = [];
        
        // Get all rows that have selected checkboxes
        selectedProductsToImport.forEach(productIndex => {
            const row = document.querySelector(`#productTableBody tr[data-product-index="${productIndex}"]`);
            if (row && !row.classList.contains('imported') && row.style.display !== 'none') {
                const product = JSON.parse(JSON.stringify(window.invoiceProducts[productIndex]));
                
                // Update with any user changes
                product.quantity = parseFloat(row.querySelector('.quantity-input').value) || 1;
                product.category = row.querySelector('.product-category-select').value;
                product.assignTo = row.querySelector('.assign-to-select').value;
                
                // Store the import promise
                importPromises.push(importProductToInventory(product, false)); // Don't show individual alerts
                
                // Mark as imported
                row.classList.add('imported');
                const importBtn = row.querySelector('.import-product');
                if (importBtn) {
                    importBtn.disabled = true;
                    importBtn.innerHTML = '<i class="fas fa-check"></i>';
                }
                
                // Also mark the checkbox as disabled
                const checkbox = row.querySelector('.product-selection-checkbox');
                if (checkbox) {
                    checkbox.disabled = true;
                    checkbox.checked = false;
                }
                
                importCount++;
            }
        });
        
        // Clear the selected products set
        selectedProductsToImport.clear();
        updateSelectedCounter();
        
        const language = document.documentElement.getAttribute('data-language') || 'en';
        
        // Wait for all imports to finish
        Promise.all(importPromises)
            .then(results => {
                if (importCount > 0) {
                    const message = language === 'pl' ? 
                        `Pomyślnie zaimportowano ${importCount} produktów do inwentarza.` : 
                        `Successfully imported ${importCount} products to inventory.`;
                    alert(message);
                    
                    // Hide imported items
                    const hideImportedCheckbox = document.getElementById('hideImportedItems');
                    if (hideImportedCheckbox && hideImportedCheckbox.checked) {
                        document.querySelectorAll('#productTableBody tr.imported').forEach(row => {
                            row.style.display = 'none';
                        });
                    }
                    
                    // Ask user if they want to clear the form for a new invoice
                    const confirmClear = language === 'pl' ? 
                        'Czy chcesz wyczyścić formularz, aby przetworzyć kolejną fakturę?' :
                        'Do you want to clear the form to process another invoice?';
                        
                    if (confirm(confirmClear)) {
                        // Clear the invoice preview and form
                        clearInvoicePreviewAndForm();
                    }
                } else {
                    const message = language === 'pl' ? 
                        'Nie zaimportowano żadnych produktów.' : 
                        'No products were imported.';
                    alert(message);
                }
            })
            .catch(error => {
                console.error('Error during batch import:', error);
                const errorMessage = language === 'pl' ? 
                    'Wystąpił błąd podczas importowania produktów.' :
                    'An error occurred while importing products.';
                alert(errorMessage);
            });
    });

    // Add user equipment functionality
    const userSelect = document.getElementById('userSelect');
    const equipmentList = document.getElementById('userEquipmentList');
    
    // Load equipment for current user if selected
    if (userSelect && userSelect.value) {
        loadUserEquipment(userSelect.value);
    }
    
    userSelect?.addEventListener('change', function() {
        const userId = this.value;
        if (!userId) {
            equipmentList.style.display = 'none';
            return;
        }
        loadUserEquipment(userId);
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
                            'Błąd: ' + (data.error || 'Nieznany błąd') : 
                            'Error: ' + (data.error || 'Unknown error');
                        alert(errorMessage);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    const language = document.documentElement.getAttribute('data-language') || 'en';
                    const errorMessage = language === 'pl' ? 
                        'Nie udało się zaktualizować elementu. Spróbuj ponownie.' : 
                        'Failed to update item. Please try again.';
                    alert(errorMessage);
                });
            } else {
                // Original code for adding new items
                fetch('/api/equipment/add', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const language = document.documentElement.getAttribute('data-language') || 'en';
                        const successMessage = language === 'pl' ? 
                            'Element dodany pomyślnie!' : 
                            'Item added successfully!';
                        alert(successMessage);
                        newManualForm.reset();
                    } else {
                        const language = document.documentElement.getAttribute('data-language') || 'en';
                        const errorMessage = language === 'pl' ? 
                            'Błąd: ' + (data.error || 'Nieznany błąd') : 
                            'Error: ' + (data.error || 'Unknown error');
                        alert(errorMessage);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    const language = document.documentElement.getAttribute('data-language') || 'en';
                    const errorMessage = language === 'pl' ? 
                        'Nie udało się dodać elementu. Spróbuj ponownie.' : 
                        'Failed to add item. Please try again.';
                    alert(errorMessage);
                });
            }
        });
    }    // Add active class to first button by default
    window.addEventListener('DOMContentLoaded', function() {
        // Click first available method button to show that section
        const firstBtn = document.querySelector('.method-btn');
        if (firstBtn) {
            firstBtn.click();
        }
    });

    const departmentSelect = document.getElementById('departmentSelect');
    if (departmentSelect) {
        departmentSelect.addEventListener('change', function() {
            const department = this.value;
            if (department) {
                loadDepartmentEquipment(department);
            } else {
                document.getElementById('departmentEquipmentList').style.display = 'none';
            }
        });

        // Load equipment for initial selection if any
        if (departmentSelect.value) {
            loadDepartmentEquipment(departmentSelect.value);
        }
    }

    // Add event handler for hide imported items checkbox
    document.getElementById('hideImportedItems')?.addEventListener('change', function() {
        const importedRows = document.querySelectorAll('#productTableBody tr.imported');
        importedRows.forEach(row => {
            row.style.display = this.checked ? 'none' : '';
            
            // If the row is hidden, also update product visibility according to category filters
            if (!this.checked) {
                const category = row.dataset.category;
                const showHardware = document.getElementById('toggleHardware').checked;
                const showSoftware = document.getElementById('toggleSoftware').checked;
                const showFurniture = document.getElementById('toggleFurniture').checked;
                const showAccessories = document.getElementById('toggleAccessories').checked;
                const showOther = document.getElementById('toggleOther').checked;
                
                if ((category === 'hardware' && showHardware) ||
                    (category === 'software' && showSoftware) ||
                    (category === 'furniture' && showFurniture) ||
                    (category === 'accessories' && showAccessories) ||
                    (category !== 'hardware' && category !== 'software' && 
                     category !== 'furniture' && category !== 'accessories' && showOther)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            }
        });
    });
});

// Funkcja tłumacząca elementy interfejsu w zależności od języka
function translateUIElements() {
    try {
        const language = document.documentElement.getAttribute('data-language') || 'en';
        if (language === 'en') return; // Tylko dla języka polskiego
        
        document.querySelectorAll('[data-pl]').forEach(element => {
            const translatedText = element.getAttribute('data-pl');
            if (translatedText) {
                element.innerHTML = translatedText;
            }
        });
        
        // Tłumaczenie placeholderów i innych atrybutów
        document.querySelectorAll('[data-placeholder-pl]').forEach(element => {
            const translatedPlaceholder = element.getAttribute('data-placeholder-pl');
            if (translatedPlaceholder) {
                element.setAttribute('placeholder', translatedPlaceholder);
            }
        });
    } catch (error) {
        console.error('Translation error:', error);
    }
}

// Dodanie funkcji do wywoływania przy zmianach w DOM
function setupMutationObserver() {
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
        }, 100); // Opóźnienie 100ms
    };
    
    // Obserwuj zmiany w tabeli sprzętu
    const equipmentTableBody = document.getElementById('equipmentTableBody');
    if (equipmentTableBody) {
        const observer = new MutationObserver(function(mutations) {
            // Używamy debounce zamiast wywoływać tłumaczenie dla każdej mutacji
            debouncedTranslate();
        });
        
        observer.observe(equipmentTableBody, { childList: true, subtree: true });
    }
    
    // Obserwuj też zmiany w dropdown departamentów
    const departmentSelect = document.getElementById('departmentSelect');
    if (departmentSelect) {
        const observer = new MutationObserver(debouncedTranslate);
        observer.observe(departmentSelect, { childList: true, subtree: true });
    }
}

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
    
    // Enhanced matching with weighted scoring
    let scores = {
        hardware: 0,
        software: 0,
        furniture: 0,
        accessories: 0
    };
    
    // Check for matches in each category and add to score
    hardwareKeywords.forEach(keyword => {
        if (name.includes(keyword)) {
            scores.hardware += 1;
            // Give extra points for strong indicators
            if (['laptop', 'komputer', 'monitor', 'pc', 'desktop', 'server'].includes(keyword)) {
                scores.hardware += 2;
            }
        }
    });
    
    softwareKeywords.forEach(keyword => {
        if (name.includes(keyword)) {
            scores.software += 1;
            // Give extra points for strong indicators
            if (['licencja', 'license', 'software', 'windows', 'office'].includes(keyword)) {
                scores.software += 2;
            }
        }
    });
    
    furnitureKeywords.forEach(keyword => {
        if (name.includes(keyword)) {
            scores.furniture += 1;
            // Give extra points for strong indicators
            if (['biurko', 'desk', 'krzesło', 'chair', 'fotel', 'meble', 'furniture'].includes(keyword)) {
                scores.furniture += 2;
            }
        }
    });
    
    accessoriesKeywords.forEach(keyword => {
        if (name.includes(keyword)) {
            scores.accessories += 1;
            // Give extra points for strong indicators
            if (['kabel', 'cable', 'adapter', 'słuchawki', 'headphones', 'ładowarka', 'charger'].includes(keyword)) {
                scores.accessories += 2;
            }
        }
    });
    
    // Find category with highest score
    const highestScore = Math.max(...Object.values(scores));
    
    // If we have a clear match with score > 0
    if (highestScore > 0) {
        for (const [category, score] of Object.entries(scores)) {
            if (score === highestScore) {
                return category.charAt(0).toUpperCase() + category.slice(1);
            }
        }
    }
    
    // Default matching for backward compatibility
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

// Poprawiona funkcja do importowania produktu z faktury do inwentarza
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

function loadUserEquipment(userId) {
    const equipmentList = document.getElementById('userEquipmentList');
    
    // Get current language
    const language = document.documentElement.getAttribute('data-language') || 'en';
    const noDataText = language === 'pl' ? 'Brak danych' : 'N/A';
    
    fetch(`/api/person_equipment/${userId}`)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('equipmentTableBody');
            equipmentList.style.display = 'block';
            
            tbody.innerHTML = data.equipment.map(item => {
                // Translate type value correctly for Polish language
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
                
                // Replace N/A with Brak danych for Polish
                let serialNumber = item.serial_number;
                if (language === 'pl') {
                    if (!serialNumber || serialNumber === 'N/A') {
                        serialNumber = noDataText;
                    }
                } else {
                    serialNumber = serialNumber || noDataText;
                }
                
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
                
                return `
                <tr>
                    <td>${item.name || noDataText}</td>
                    <td>${typeValue}</td>
                    <td>${serialNumber}</td>
                    <td>${item.quantity || 1}</td>
                    <td>${assignedDate}</td>
                    <td><span class="status-badge ${item.status}">${status}</span></td>
                    <td>
                        <button class="btn-icon" onclick="unassignEquipment(${item.id})">
                            <i class="fas fa-unlink"></i>
                        </button>
                    </td>
                </tr>
            `}).join('') || `<tr><td colspan="7">${language === 'pl' ? 'Brak przypisanego sprzętu' : 'No equipment assigned'}</td></tr>`;
            
            // Apply translations after loading
            if (language === 'pl') {
                translateUIElements();
            }
        })
        .catch(error => console.error('Error:', error));
}

function unassignEquipment(equipmentId) {
    if (confirm('Are you sure you want to unassign this equipment?')) {
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
                document.getElementById('userSelect').dispatchEvent(new Event('change'));
            }
        })
        .catch(error => console.error('Error:', error));
    }
}

function loadDepartmentEquipment(departmentName) {
    const equipmentList = document.getElementById('departmentEquipmentList');
    equipmentList.style.display = 'block';
    
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
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('equipmentTableBody');
            
            if (data.equipment && data.equipment.length > 0) {
                tbody.innerHTML = data.equipment.map(item => {
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
                    }                    // Check if user has manage_inventory permission or is admin
                    const hasManagePermission = (window.userPermissions && window.userPermissions.includes('manage_inventory')) || 
                                              (window.userRole === 'admin');
                    console.log('Checking manage_inventory permission:', { 
                        userPermissions: window.userPermissions,
                        userRole: window.userRole,
                        hasManagePermission: hasManagePermission
                    });
                      let actionsColumn = '';
                    if (hasManagePermission) {
                        actionsColumn = `
                        <td>
                            <button class="btn-icon" onclick="changeDepartment(${item.id}, '${item.name}')" title="${language === 'pl' ? 'Przepisz do innego działu' : 'Assign to another department'}">
                                <i class="fas fa-exchange-alt"></i>
                            </button>
                            <button class="btn-icon" onclick="editEquipment(${item.id})" title="${language === 'pl' ? 'Edytuj' : 'Edit'}">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-icon" onclick="deleteEquipment(${item.id})" title="${language === 'pl' ? 'Usuń' : 'Delete'}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>`;
                    }

                    return `
                    <tr>
                        <td>${item.name || noDataText}</td>
                        <td>${typeValue}</td>
                        <td>${serialNumber}</td>
                        <td>${item.quantity || 1}</td>
                        <td>${assignedDate}</td>
                        <td><span class="status-badge ${item.status}">${status}</span></td>
                        <td></td>
                        ${actionsColumn}
                    </tr>
                    `;
                }).join('');
                  // Apply translations after loading equipment in a safer way
                if (language === 'pl') {
                    try {
                        // Używamy setTimeout, żeby dać przeglądarce czas na renderowanie
                        setTimeout(() => {
                            translateUIElements();
                        }, 10);
                    } catch (err) {
                        console.error('Błąd podczas tłumaczenia elementów tabeli:', err);
                    }
                }            } else {                // Check if user has manage_inventory permission or is admin for correct colspan
                const hasManagePermission = (window.userPermissions && window.userPermissions.includes('manage_inventory')) || 
                                          (window.userRole === 'admin');
                const colspan = hasManagePermission ? 8 : 7;
                const noEquipmentText = language === 'pl' ? 'Brak sprzętu przypisanego do tego działu' : 'No equipment assigned to this department';
                tbody.innerHTML = `<tr><td colspan="${colspan}">${noEquipmentText}</td></tr>`;
            }
            
            // Bezpieczne usunięcie loadingSpinnera
            if (loadingSpinner && loadingSpinner.parentNode) {
                loadingSpinner.remove();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            const errorText = language === 'pl' ? 'Nie udało się załadować danych sprzętu' : 'Failed to load equipment data';
            equipmentList.innerHTML = `<div class="error-message">${errorText}</div>`;
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
    
    console.log(`[EDIT] Loading equipment details for ID: ${equipmentId}`);
    
    // First get equipment details
    fetch(`/api/equipment/${equipmentId}`)
        .then(response => {
            if (!response.ok) {
                console.error(`[EDIT ERROR] Network response error: ${response.status}`);
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log(`[EDIT] Received data:`, data);
            
            // Switch to manual input tab
            document.querySelector('.method-btn[data-method="manual"]').click();
            
            // Populate form with equipment data
            const form = document.getElementById('itemForm');
            if (form && data.equipment) {
                // Store equipment ID in hidden field or as a data attribute on the form
                form.dataset.equipmentId = equipmentId;
                
                // Update form action to indicate editing mode
                form.dataset.mode = 'edit';
                
                // Log all received fields to help with debugging
                console.log('[EDIT] Available fields:', Object.keys(data.equipment));
                
                // Populate form fields
                document.getElementById('itemName').value = data.equipment.name || '';
                document.getElementById('itemCategory').value = data.equipment.type || 'hardware';
                document.getElementById('itemStatus').value = data.equipment.status || 'available';
                document.getElementById('itemQuantity').value = data.equipment.quantity || 1;
                document.getElementById('assignTo').value = data.equipment.assigned_to_department || '';
                
                // Handle location field with extra logging
                const locationField = document.getElementById('itemLocation');
                if (locationField) {
                    console.log(`[EDIT] Location value from API: "${data.equipment.location}"`);
                    locationField.value = data.equipment.location || '';
                    console.log(`[EDIT] Set itemLocation field to: "${locationField.value}"`);
                } else {
                    console.error('[EDIT ERROR] itemLocation field not found in the form');
                }
                
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

// Function to delete equipment from inventory
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
        
        // Dodajemy nagłówek X-Requested-With dla lepszej kompatybilności
        fetch('/api/equipment/update', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
        .then(response => {
            console.log(`Odpowiedź otrzymana, status: ${response.status}`);
            if (!response.ok) {
                console.error(`Błąd HTTP: ${response.status} ${response.statusText}`);
                throw new Error(`HTTP Error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(`Dane odpowiedzi:`, data);
            if (data.success) {
                // Reload equipment list to reflect changes
                const departmentSelect = document.getElementById('departmentSelect');
                if (departmentSelect && departmentSelect.value) {
                    console.log(`Odświeżanie listy dla działu: ${departmentSelect.value}`);
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
                console.error(`Błąd usuwania: ${data.error}`);
                alert(errorMsg);
            }
        })
        .catch(error => {
            console.error('Error during delete operation:', error);
            const errorMsg = language === 'pl' ? 
                'Nie udało się usunąć elementu. Spróbuj ponownie.' : 
                'Failed to delete equipment. Please try again.';
            alert(errorMsg);
        });
    }
}

// Add this function to handle department selection
document.getElementById('departmentSelect')?.addEventListener('change', function() {
    const department = this.value;
    if (department) {
        loadDepartmentEquipment(department);
    } else {
        document.getElementById('departmentEquipmentList').style.display = 'none';
    }
});

// Add function to adjust container width based on content
function adjustContainerWidth() {
    const table = document.querySelector('.invoice-data-table');
    const container = document.getElementById('invoiceFormContainer');
    
    if (table && container) {
        const tableWidth = table.scrollWidth;
        if (tableWidth > window.innerWidth * 0.9) {
            // If table is very wide, expand container to 95% of window
            container.style.maxWidth = '95%';
            container.style.width = '1400px';
        }
    }
}

// Remove the resize event listener that adds compact mode
window.removeEventListener('resize', function() {
    const invoiceTable = document.querySelector('.invoice-data-table');
    if (invoiceTable) {
        if (window.innerWidth < 1200) {
            invoiceTable.classList.add('compact-mode');
        } else {
            invoiceTable.classList.remove('compact-mode');
        }
    }
});

// Instead add a new one that ensures container width
window.addEventListener('resize', adjustContainerWidth);

// Helper function to escape HTML for security
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Function to toggle fullscreen invoice view
function toggleInvoiceFullscreen() {
    const invoicePreview = document.getElementById('invoicePreview');
    if (invoicePreview.classList.contains('fullscreen')) {
        invoicePreview.classList.remove('fullscreen');
        this.innerHTML = '<i class="fas fa-expand"></i>';
        document.body.style.overflow = '';
    } else {
        invoicePreview.classList.add('fullscreen');
        this.innerHTML = '<i class="fas fa-compress"></i>';
        document.body.style.overflow = 'hidden'; // Prevent scrolling behind the fullscreen view
    }
}

// Show detailed product information in a modal
function showProductDetails(product, category) {
    // Check if modal exists, create it if not
    let modal = document.getElementById('productDetailModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'productDetailModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close-modal">&times;</span>
                <h3>Product Details</h3>
                <div class="product-detail-content"></div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Add modal styles if they don't exist
        if (!document.getElementById('modalStyles')) {
            const style = document.createElement('style');
            style.id = 'modalStyles';
            style.textContent = `
                .modal {
                    display: none;
                    position: fixed;
                    z-index: 9999;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.5);
                }
                .modal-content {
                    background-color: white;
                    margin: 10% auto;
                    padding: 2rem;
                    border-radius: var(--radius);
                    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                    width: 80%;
                    max-width: 700px;
                    position: relative;
                }
                .close-modal {
                    position: absolute;
                    top: 1rem;
                    right: 1.5rem;
                    font-size: 1.5rem;
                    cursor: pointer;
                }
                .product-detail-content {
                    margin-top: 1rem;
                }
                .product-detail-row {
                    display: flex;
                    margin-bottom: 1rem;
                    border-bottom: 1px solid var(--border-color-light);
                    padding-bottom: 0.5rem;
                }
                .product-detail-label {
                    width: 30%;
                    font-weight: 500;
                    color: var(--primary-color);
                }
                .product-detail-value {
                    width: 70%;
                }
                .category-badge {
                    display: inline-block;
                    padding: 0.3rem 0.6rem;
                    border-radius: 4px;
                    font-size: 0.9rem;
                    font-weight: 500;
                }
            `;
            document.head.appendChild(style);
        }
        
        // Add close functionality
        const closeBtn = modal.querySelector('.close-modal');
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        // Close when clicking outside the modal
        window.addEventListener('click', (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    // Populate modal with product details
    const content = modal.querySelector('.product-detail-content');
    content.innerHTML = '';
    
    // Add product details with formatting
    const categoryColorClass = {
        'Hardware': 'hardware',
        'Software': 'software',
        'Furniture': 'furniture',
        'Accessories': 'accessories',
        'Other': 'other'
    }[category] || 'other';
    
    const details = [
        { label: 'Product Name', value: escapeHtml(product.name) },
        { 
            label: 'Category', 
            value: `<span class="category-badge ${categoryColorClass.toLowerCase()}">${category}</span>`
        },
        { label: 'Quantity', value: product.quantity || 1 },
        { label: 'Unit Price', value: `${(product.unit_price || 0).toFixed(2)} PLN` },
        { label: 'Total Price', value: `${(product.total_price || 0).toFixed(2)} PLN` }
    ];
    
    details.forEach(detail => {
        const row = document.createElement('div');
        row.className = 'product-detail-row';
        row.innerHTML = `
            <div class="product-detail-label">${detail.label}</div>
            <div class="product-detail-value">${detail.value}</div>
        `;
        content.appendChild(row);
    });
    
    // Add action buttons to modal
    const actionRow = document.createElement('div');
    actionRow.style.marginTop = '1.5rem';
    actionRow.style.display = 'flex';
    actionRow.style.gap = '0.5rem';
    actionRow.style.justifyContent = 'flex-end';
    
    const importBtn = document.createElement('button');
    importBtn.className = 'btn primary';
    importBtn.innerHTML = '<i class="fas fa-plus"></i> Import Item';
    importBtn.addEventListener('click', () => {
        // Find and trigger the import button for this product
        const productIndex = product.index || 0;
        const row = document.querySelector(`tr[data-product-index="${productIndex}"]`);
        if (row) {
            const importButton = row.querySelector('.import-product');
            if (importButton && !importButton.disabled) {
                importButton.click();
            }
        }
        modal.style.display = 'none';
    });
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'btn secondary';
    closeBtn.textContent = 'Close';
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    
    actionRow.appendChild(importBtn);
    actionRow.appendChild(closeBtn);
    content.appendChild(actionRow);
    
    // Show the modal
    modal.style.display = 'block';
}

// Function to change department assignment
function changeDepartment(equipmentId, itemName) {
    // Get current language for UI
    const language = document.documentElement.getAttribute('data-language') || 'en';
    
    // Create a selection dialog
    let modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.style.position = 'fixed';
    modal.style.zIndex = '1000';
    modal.style.left = '0';
    modal.style.top = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.backgroundColor = 'rgba(0,0,0,0.4)';
    
    // Create modal content
    let modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    modalContent.style.backgroundColor = '#fff';
    modalContent.style.margin = '10% auto';
    modalContent.style.padding = '20px';
    modalContent.style.border = '1px solid #888';
    modalContent.style.width = '50%';
    modalContent.style.borderRadius = '5px';
    
    // Get department options from the existing select
    const departmentOptions = Array.from(
        document.querySelectorAll('#departmentSelect option')
    ).filter(option => option.value).map(option => 
        `<option value="${option.value}">${option.text}</option>`
    ).join('');
    
    // Modal header and content
    modalContent.innerHTML = `
        <h3>${language === 'pl' ? 'Zmień dział dla elementu' : 'Change Department Assignment'}</h3>
        <p>${language === 'pl' ? `Element: <strong>${itemName}</strong>` : `Item: <strong>${itemName}</strong>`}</p>
        <div class="form-group">
            <label for="newDepartment">${language === 'pl' ? 'Wybierz nowy dział:' : 'Select new department:'}</label>
            <select id="newDepartment" class="form-control">
                ${departmentOptions}
            </select>
        </div>
        <div class="form-actions" style="margin-top: 20px; text-align: right;">
            <button id="cancelDeptChange" class="btn secondary">
                ${language === 'pl' ? 'Anuluj' : 'Cancel'}
            </button>
            <button id="confirmDeptChange" class="btn primary">
                ${language === 'pl' ? 'Zapisz zmiany' : 'Save Changes'}
            </button>
        </div>
    `;
    
    // Add modal to document
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    // Handle cancel button
    document.getElementById('cancelDeptChange').addEventListener('click', function() {
        modal.remove();
    });
    
    // Handle confirm button
    document.getElementById('confirmDeptChange').addEventListener('click', function() {
        const newDepartment = document.getElementById('newDepartment').value;
        if (!newDepartment) {
            alert(language === 'pl' ? 'Proszę wybrać dział.' : 'Please select a department.');
            return;
        }
        
        // Create form data for the request
        const formData = new FormData();
        formData.append('equipment_id', equipmentId);
        formData.append('department', newDepartment);
        
        // Send the request to assign equipment to new department
        fetch('/api/equipment/assign', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                equipment_id: equipmentId,
                department: newDepartment
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Remove the modal
                modal.remove();
                
                // Show success message
                const successMsg = language === 'pl' ? 
                    `Element został przypisany do działu ${newDepartment}` : 
                    `Equipment has been assigned to ${newDepartment} department`;
                alert(successMsg);
                
                // Refresh the equipment list
                const departmentSelect = document.getElementById('departmentSelect');
                if (departmentSelect) {
                    loadDepartmentEquipment(departmentSelect.value);
                }
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
                'Nie udało się przepisać elementu do nowego działu. Spróbuj ponownie.' : 
                'Failed to assign equipment to new department. Please try again.';
            alert(errorMsg);
        });
    });
    
    // Close modal when clicking outside of it
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.remove();
        }
    }
}

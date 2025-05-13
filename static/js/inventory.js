document.addEventListener('DOMContentLoaded', function() {
    // Inicjalne tłumaczenie
    translateUIElements();
    
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
                sections[key].style.display = key === method ? 'block' : 'none';
            });
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
                        <td data-full-text="${escapeHtml(fullProductName)}">${escapeHtml(fullProductName)}</td>
                        <td>
                            <select class="product-category-select">
                                <option value="hardware" ${category === 'Hardware' ? 'selected' : ''}>Hardware</option>
                                <option value="software" ${category === 'Software' ? 'selected' : ''}>Software</option>
                                <option value="furniture" ${category === 'Furniture' ? 'selected' : ''}>Furniture</option>
                                <option value="accessories" ${category === 'Accessories' ? 'selected' : ''}>Accessories</option>
                                <option value="other" ${category === 'Other' ? 'selected' : ''}>Other</option>
                            </select>
                        </td>
                        <td>
                            <input type="number" class="form-control quantity-input" value="${product.quantity || 1}" min="1">
                        </td>
                        <td>${product.unit_price ? product.unit_price.toFixed(2) : '0.00'} PLN</td>
                        <td>${product.total_price ? product.total_price.toFixed(2) : '0.00'} PLN</td>
                        <td>
                            <select class="assign-to-select form-control">
                                <option value="">Select Department</option>
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
                            <button class="btn-icon import-product" title="Import to inventory">
                                <i class="fas fa-plus"></i>
                            </button>
                            <button class="btn-icon edit-product" title="Edit item">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-icon delete-product" title="Delete item">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    `;
                    
                    productTableBody.appendChild(row);
                    
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
                        if (confirm('Are you sure you want to remove this item?')) {
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
            } else {
                productTableBody.innerHTML = '<tr><td colspan="7">No products found in the invoice. Try the alternative method.</td></tr>';
            }
            
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
        
        document.querySelectorAll('#productTableBody tr').forEach(row => {
            const category = row.dataset.category;
            
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
            alert(`Successfully imported ${importCount} products to inventory.`);
        } else {
            alert('No products selected for import.');
        }
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
    manualForm?.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        fetch('/api/equipment/add', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Item added successfully!');
                manualForm.reset();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to add item. Please try again.');
        });
    });

    // Add active class to first button by default
    window.addEventListener('DOMContentLoaded', function() {
        // First click the manual button to show that section
        document.querySelector('.method-btn[data-method="manual"]').click();
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
});

// Funkcja tłumacząca elementy interfejsu w zależności od języka
function translateUIElements() {
    const language = document.documentElement.getAttribute('data-language') || 'en';
    if (language !== 'pl') return; // Tłumaczenie tylko na polski
    
    // Tłumaczenie "items" w opcjach wyboru departamentu
    document.querySelectorAll('select option').forEach(option => {
        if (option.text.includes(' items)')) {
            option.text = option.text.replace(' items)', ' elementów)');
        }
    });
    
    // Tłumaczenie wartości w komórkach tabeli
    document.querySelectorAll('td').forEach(cell => {
        const text = cell.textContent.trim();
        if (text.toLowerCase() === 'hardware') {
            cell.textContent = 'sprzęt';
        } else if (text.toLowerCase() === 'network') {
            cell.textContent = 'urz. sieciowe';
        } else if (text === 'N/A') {
            cell.textContent = 'Brak danych';
        }
    });
}

// Dodanie funkcji do wywoływania przy zmianach w DOM
function setupMutationObserver() {
    const language = document.documentElement.getAttribute('data-language') || 'en';
    if (language !== 'pl') return; // Obserwacja tylko dla polskiego języka
    
    // Obserwuj zmiany w tabeli sprzętu
    const equipmentTableBody = document.getElementById('equipmentTableBody');
    if (equipmentTableBody) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    // Tłumaczenie nowo dodanych elementów
                    translateUIElements();
                }
            });
        });
        
        observer.observe(equipmentTableBody, { childList: true, subtree: true });
    }
    
    // Obserwuj też zmiany w dropdown departamentów
    const departmentSelect = document.getElementById('departmentSelect');
    if (departmentSelect) {
        const observer = new MutationObserver(translateUIElements);
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

function importProductToInventory(product, showAlert = true) {
    const formData = new FormData();
    formData.append('itemName', product.name);
    formData.append('itemCategory', product.category || 'hardware');
    formData.append('itemStatus', 'available');
    formData.append('itemQuantity', product.quantity);
    formData.append('itemValue', product.unit_price || product.price || 0);
    formData.append('assignTo', product.assignTo || ''); // Make sure department is included

    // Add other necessary fields
    const invoiceNumber = document.getElementById('invoiceNumber')?.textContent;
    const invoiceDate = document.getElementById('invoiceDate')?.textContent;
    const vendor = document.getElementById('invoiceVendor')?.textContent;

    if (vendor && vendor !== 'Not detected') {
        formData.append('itemManufacturer', vendor);
    }

    formData.append('itemNotes', `Imported from invoice ${invoiceNumber} dated ${invoiceDate}`);
    
    if (invoiceDate && invoiceDate !== 'Not detected') {
        formData.append('acquisitionDate', invoiceDate);
    } else {
        formData.append('acquisitionDate', new Date().toISOString().split('T')[0]);
    }

    // Send request
    fetch('/api/equipment/add', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (showAlert) {
                alert(`Product "${product.name}" added successfully!`);
            }
            // Refresh equipment list if we're viewing the department it was assigned to
            const departmentSelect = document.getElementById('departmentSelect');
            if (departmentSelect && departmentSelect.value === product.assignTo) {
                loadDepartmentEquipment(product.assignTo);
            }
        } else {
            if (showAlert) {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (showAlert) {
            alert('Failed to add item. Please try again.');
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
                // Translate type value if it's "hardware" for Polish language
                let typeValue = item.type || noDataText;
                if (language === 'pl') {
                    if (typeValue.toLowerCase() === 'hardware') {
                        typeValue = 'sprzęt';
                    } else if (typeValue.toLowerCase() === 'network') {
                        typeValue = 'urz. sieciowe';
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
                if (language === 'pl' && (status === 'N/A' || !item.status)) {
                    status = noDataText;
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
            
            // Po załadowaniu sprzętu przetłumacz elementy
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
    loadingSpinner.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    equipmentList.appendChild(loadingSpinner);

    // Get current language
    const language = document.documentElement.getAttribute('data-language') || 'en';
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
                    
                    const assignedDate = item.assigned_date || noDataText;
                    const status = item.status || noDataText;

                    return `
                    <tr>
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
                    </tr>
                    `;
                }).join('');
                
                // Po załadowaniu sprzętu przetłumacz elementy
                if (language === 'pl') {
                    translateUIElements();
                }
            } else {
                const noEquipmentText = language === 'pl' ? 'Brak sprzętu przypisanego do tego działu' : 'No equipment assigned to this department';
                tbody.innerHTML = `<tr><td colspan="8">${noEquipmentText}</td></tr>`;
            }
            
            loadingSpinner.remove();
        })
        .catch(error => {
            console.error('Error:', error);
            const errorText = language === 'pl' ? 'Nie udało się załadować danych sprzętu' : 'Failed to load equipment data';
            equipmentList.innerHTML = `<div class="error-message">${errorText}</div>`;
        });
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
    actionRow.className = 'product-detail-actions';
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

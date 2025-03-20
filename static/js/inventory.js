document.addEventListener('DOMContentLoaded', function() {
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
    
    // Invoice processing logic
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
            
            // Display products
            const productTableBody = document.getElementById('productTableBody');
            productTableBody.innerHTML = '';
            
            if (data.products && data.products.length > 0) {
                data.products.forEach((product, index) => {
                    // Guess product category
                    let category = guessProductCategory(product.name);
                    
                    const row = document.createElement('tr');
                    row.dataset.category = category.toLowerCase();
                    row.dataset.productIndex = index;
                    row.innerHTML = `
                        <td>${product.name}</td>
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
                            <button class="btn-icon delete-product" title="Remove item">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    `;
                    productTableBody.appendChild(row);
                });
                
                // Add event listeners for import buttons
                document.querySelectorAll('.import-product').forEach((btn, index) => {
                    btn.addEventListener('click', function() {
                        const row = this.closest('tr');
                        const productIndex = row.dataset.productIndex;
                        const product = {...data.products[productIndex]};
                        
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
                
                // Add event listeners for edit buttons
                document.querySelectorAll('.edit-product').forEach((btn, index) => {
                    btn.addEventListener('click', function() {
                        const row = this.closest('tr');
                        const productIndex = row.dataset.productIndex;
                        const product = data.products[productIndex];
                        
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
                
                // Show import all button
                document.getElementById('importAllProducts').style.display = 'inline-flex';
            } else {
                productTableBody.innerHTML = '<tr><td colspan="7">No products found in the invoice. Try the alternative method.</td></tr>';
            }
            
            // Show preview
            invoicePreview.style.display = 'block';
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

function guessProductCategory(name) {
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
    
    // Check for matches
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
    
    fetch(`/api/person_equipment/${userId}`)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('equipmentTableBody');
            equipmentList.style.display = 'block';
            
            tbody.innerHTML = data.equipment.map(item => `
                <tr>
                    <td>${item.name}</td>
                    <td>${item.type}</td>
                    <td>${item.serial_number || 'N/A'}</td>
                    <td>${item.quantity || 1}</td>
                    <td>${item.assigned_date || 'N/A'}</td>
                    <td><span class="status-badge ${item.status}">${item.status}</span></td>
                    <td>
                        <button class="btn-icon" onclick="unassignEquipment(${item.id})">
                            <i class="fas fa-unlink"></i>
                        </button>
                    </td>
                </tr>
            `).join('') || '<tr><td colspan="7">No equipment assigned</td></tr>';
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

    fetch(`/api/department_equipment/${encodeURIComponent(departmentName)}`)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('equipmentTableBody');
            
            if (data.equipment && data.equipment.length > 0) {
                tbody.innerHTML = data.equipment.map(item => `
                    <tr>
                        <td>${item.name || 'N/A'}</td>
                        <td>${item.type || 'N/A'}</td>
                        <td>${item.serial_number || 'N/A'}</td>
                        <td>${item.quantity || 1}</td>
                        <td>${item.assigned_date || 'N/A'}</td>
                        <td><span class="status-badge ${item.status}">${item.status || 'N/A'}</span></td>
                        <td>
                            <button class="btn-icon" onclick="unassignFromDepartment(${item.id})">
                                <i class="fas fa-unlink"></i>
                            </button>
                            <button class="btn-icon" onclick="editEquipment(${item.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="7">No equipment assigned to this department</td></tr>';
            }
            
            loadingSpinner.remove();
        })
        .catch(error => {
            console.error('Error:', error);
            equipmentList.innerHTML = '<div class="error-message">Failed to load equipment data</div>';
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

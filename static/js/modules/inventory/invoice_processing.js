/**
 * Shared functions for invoice processing functionality
 * Used across different modules and files in the inventory system
 */

// Import this file from other modules to ensure consistent functionality

/**
 * Updates the count of selected products in the UI
 * @returns {void}
 */
function updateSelectedCounter() {
    const counter = document.getElementById('selectedProductsCounter');
    if (counter) {
        const count = selectedProductsToImport.size;
        const language = document.documentElement.getAttribute('data-language') || 'en';
        counter.textContent = language === 'pl' 
            ? `Wybrano: ${count}` 
            : `Selected: ${count}`;
        
        // Show or hide import selected button based on selection count
        const importSelectedBtn = document.getElementById('importSelectedProducts');
        if (importSelectedBtn) {
            importSelectedBtn.style.display = count > 0 ? 'inline-flex' : 'none';
        }
    }
}

/**
 * Updates the visibility of products in the product table based on active filters
 * @returns {void}
 */
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

/**
 * Imports a product to the inventory system
 * @param {Object} product - The product to import
 * @param {boolean} showAlert - Whether to show alert on completion
 * @returns {Promise<boolean>} - Promise resolving to success status
 */
function importProductToInventory(product, showAlert = true) {
    return new Promise((resolve, reject) => {
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
                resolve(true);
            } else {
                if (showAlert) {
                    const errorMsg = language === 'pl' ?
                        'Błąd: ' + (data.error || 'Nieznany błąd') :
                        'Error: ' + (data.error || 'Unknown error');
                    alert(errorMsg);
                }
                console.error('Error adding product:', data.error);
                resolve(false);
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
            reject(error);
        });
    });
}

/**
 * Determines the most likely category for a product based on its name
 * @param {string} name - Product name
 * @returns {string} - Category name with capitalized first letter
 */
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

/**
 * Escapes HTML content for security purposes
 * @param {string} text - Text to escape
 * @returns {string} - Escaped HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Clears the invoice preview and resets the invoice form
 * Called after successfully importing products
 * @returns {void}
 */
function clearInvoicePreviewAndForm() {
    // Clear the invoice preview
    const invoicePreview = document.getElementById('invoicePreview');
    if (invoicePreview) {
        invoicePreview.style.display = 'none';
    }
    
    // Reset the product table
    const productTableBody = document.getElementById('productTableBody');
    if (productTableBody) {
        productTableBody.innerHTML = '';
    }
    
    // Clear invoice details
    const invoiceNumber = document.getElementById('invoiceNumber');
    const invoiceDate = document.getElementById('invoiceDate');
    const invoiceVendor = document.getElementById('invoiceVendor');
    
    if (invoiceNumber) invoiceNumber.textContent = '';
    if (invoiceDate) invoiceDate.textContent = '';
    if (invoiceVendor) invoiceVendor.textContent = '';
    
    // Reset form fields
    const invoiceForm = document.getElementById('invoiceForm');
    if (invoiceForm) {
        invoiceForm.reset();
    }
    
    // Reset the file selection display
    const invoiceFileDisplay = document.getElementById('selectedInvoiceFile');
    if (invoiceFileDisplay) {
        const language = document.documentElement.getAttribute('data-language') || 'en';
        invoiceFileDisplay.textContent = language === 'pl' ? 'Nie wybrano pliku' : 'No file selected';
    }
    
    // Clear the selected products set
    if (typeof selectedProductsToImport !== 'undefined') {
        selectedProductsToImport.clear();
        updateSelectedCounter();
    }
    
    // Hide the import buttons
    const importAllBtn = document.getElementById('importAllProducts');
    const importSelectedBtn = document.getElementById('importSelectedProducts');
    
    if (importAllBtn) importAllBtn.style.display = 'none';
    if (importSelectedBtn) importSelectedBtn.style.display = 'none';
    
    // Clear window.invoiceProducts
    window.invoiceProducts = [];
    
    // Reset container width if it was expanded
    const invoiceFormContainer = document.getElementById('invoiceFormContainer');
    if (invoiceFormContainer) {
        invoiceFormContainer.style.maxWidth = '';
        invoiceFormContainer.style.width = '';
    }
    
    // Show a confirmation message
    const language = document.documentElement.getAttribute('data-language') || 'en';
    const message = language === 'pl' ? 
        'Formularz faktury został wyczyszczony. Możesz teraz przetworzyć kolejną fakturę.' : 
        'Invoice form has been cleared. You can now process another invoice.';
    alert(message);
}

// Export the functions - will be ignored in browser environment but useful for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        updateSelectedCounter,
        updateProductVisibility,
        importProductToInventory,
        guessProductCategory,
        escapeHtml,
        clearInvoicePreviewAndForm
    };
}

/**
 * Integration tests for the inventory invoice processing module
 * 
 * These tests cover the complete workflow for invoice processing:
 * - Selecting products from an invoice
 * - Importing selected products
 * - Hiding imported products
 * - Clearing the invoice form after import
 */

describe('Invoice Processing Workflow', () => {
    beforeEach(() => {
        // Set up a mock invoice processing environment
        document.body.innerHTML = `
            <div id="invoiceFormContainer">
                <form id="invoiceForm">
                    <input type="file" id="invoicePdf">
                    <div id="selectedInvoiceFile">No file selected</div>
                    <button type="submit">Process</button>
                </form>
                <div id="processingIndicator" style="display: none">Processing...</div>
                <div id="invoicePreview" style="display: block">
                    <div id="invoiceNumber">INV-12345</div>
                    <div id="invoiceDate">2025-05-21</div>
                    <div id="invoiceVendor">Test Vendor</div>
                    <div class="product-categories">
                        <div class="category-toggle">
                            <input type="checkbox" id="toggleHardware" checked>
                            <input type="checkbox" id="toggleSoftware" checked>
                            <input type="checkbox" id="toggleFurniture" checked>
                            <input type="checkbox" id="toggleAccessories" checked>
                            <input type="checkbox" id="toggleOther" checked>
                            <input type="checkbox" id="hideImportedItems">
                        </div>
                        <div class="selected-counter">
                            <span id="selectedProductsCounter">Selected: 0</span>
                        </div>
                    </div>
                    <table class="invoice-data-table">
                        <thead>
                            <tr>
                                <th><input type="checkbox" id="selectAllProducts"></th>
                                <th>Name</th>
                                <th>Category</th>
                                <th>Quantity</th>
                                <th>Unit Price</th>
                                <th>Total Price</th>
                                <th>Assign To</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody id="productTableBody"></tbody>
                    </table>
                    <div class="form-actions">
                        <button id="importSelectedProducts">Import Selected</button>
                        <button id="importAllProducts">Import All Items</button>
                        <button id="addMissingProduct">Add Missing Item</button>
                    </div>
                </div>
            </div>
            <select id="departmentSelect">
                <option value="dept1">Department 1</option>
                <option value="dept2">Department 2</option>
            </select>
        `;
        `;

        // Mock the fetch API for product import
        global.fetch = jest.fn().mockImplementation(() => 
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ success: true })
            })
        );

        // Create a mock for the product data
        window.invoiceProducts = [
            { 
                name: 'Laptop Dell XPS 13', 
                quantity: 1, 
                unit_price: 5499.99, 
                total_price: 5499.99 
            },
            { 
                name: 'Microsoft Office License', 
                quantity: 5, 
                unit_price: 699.99, 
                total_price: 3499.95 
            },
            { 
                name: 'Monitor 24"', 
                quantity: 2, 
                unit_price: 899.50, 
                total_price: 1799.00 
            }
        ];

        // Create a spy for alert
        global.alert = jest.fn();

        // Initialize the global set for selected products
        window.selectedProductsToImport = new Set();
    });

    test('Product selection adds IDs to the selectedProductsToImport set', () => {
        // Populate the product table
        populateProductTable();

        // Select a product
        const productCheckbox = document.querySelector('.product-selection-checkbox');
        productCheckbox.click();

        // Check if the product was added to the set
        expect(window.selectedProductsToImport.size).toBe(1);
        expect(window.selectedProductsToImport.has('0')).toBe(true);
    });

    test('Selecting all products with the header checkbox selects all visible products', () => {
        // Populate the product table
        populateProductTable();

        // Select all products
        const selectAllCheckbox = document.getElementById('selectAllProducts');
        selectAllCheckbox.click();

        // Check if all products were added to the set
        expect(window.selectedProductsToImport.size).toBe(3);
        expect(window.selectedProductsToImport.has('0')).toBe(true);
        expect(window.selectedProductsToImport.has('1')).toBe(true);
        expect(window.selectedProductsToImport.has('2')).toBe(true);
    });

    test('Importing selected products marks them as imported and clears selection', () => {
        // Populate the product table
        populateProductTable();

        // Select products
        document.querySelectorAll('.product-selection-checkbox').forEach(checkbox => {
            checkbox.click();
        });

        // Import selected products
        const importSelectedBtn = document.getElementById('importSelectedProducts');
        importSelectedBtn.click();

        // Check if products are marked as imported
        const importedRows = document.querySelectorAll('#productTableBody tr.imported');
        expect(importedRows.length).toBe(3);

        // Check if selection was cleared
        expect(window.selectedProductsToImport.size).toBe(0);
    });

    test('Hiding imported items hides rows with imported class', () => {
        // Populate the product table
        populateProductTable();

        // Select and import products
        document.querySelectorAll('.product-selection-checkbox').forEach(checkbox => {
            checkbox.click();
        });
        document.getElementById('importSelectedProducts').click();

        // Enable hiding imported items
        const hideImportedCheckbox = document.getElementById('hideImportedItems');
        hideImportedCheckbox.click();

        // Check if imported rows are hidden
        const importedRows = document.querySelectorAll('#productTableBody tr.imported');
        importedRows.forEach(row => {
            expect(row.style.display).toBe('none');
        });
    });

    test('Adding missing product creates a new product row', () => {
        // Initial count of products
        const initialProductCount = window.invoiceProducts.length;
        
        // Click the Add Missing Product button
        const addMissingButton = document.getElementById('addMissingProduct');
        addMissingButton.click();
        
        // Check if a new product was added
        expect(window.invoiceProducts.length).toBe(initialProductCount + 1);
        
        // Check if a new row was added to the table
        const rows = document.querySelectorAll('#productTableBody tr');
        expect(rows.length).toBe(initialProductCount + 1);
    });

    test('Category filter hides products from unselected categories', () => {
        // Populate the product table with categorized products
        populateProductTable();
        
        // Uncheck the Hardware category
        const hardwareToggle = document.getElementById('toggleHardware');
        hardwareToggle.checked = false;
        const event = new Event('change');
        hardwareToggle.dispatchEvent(event);
        
        // Check if hardware products are hidden
        const hardwareRow = document.querySelector('tr[data-category="hardware"]');
        if (hardwareRow) {
            expect(hardwareRow.style.display).toBe('none');
        }
        
        // Software products should still be visible
        const softwareRow = document.querySelector('tr[data-category="software"]');
        if (softwareRow) {
            expect(softwareRow.style.display).not.toBe('none');
        }
    });

    // Helper function to populate the product table for testing
    function populateProductTable() {
        const productTableBody = document.getElementById('productTableBody');
        
        window.invoiceProducts.forEach((product, index) => {
            // Set product category based on name
            let category = 'other';
            if (product.name.toLowerCase().includes('laptop')) {
                category = 'hardware';
            } else if (product.name.toLowerCase().includes('license')) {
                category = 'software';
            } else if (product.name.toLowerCase().includes('monitor')) {
                category = 'hardware';
            }
            
            const row = document.createElement('tr');
            row.dataset.category = category;
            row.dataset.productIndex = index.toString();
            
            // Create selection checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.classList.add('product-selection-checkbox');
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    window.selectedProductsToImport.add(row.dataset.productIndex);
                } else {
                    window.selectedProductsToImport.delete(row.dataset.productIndex);
                }
                updateSelectedCounter();
            });
            
            // Create cells
            const checkboxCell = document.createElement('td');
            checkboxCell.appendChild(checkbox);
            
            // Create the rest of the cells
            row.appendChild(checkboxCell);
            row.innerHTML += `
                <td>${product.name}</td>
                <td>${category}</td>
                <td>${product.quantity}</td>
                <td>${product.unit_price}</td>
                <td>${product.total_price}</td>
                <td>
                    <select class="assign-to-select">
                        <option value="IT">IT Department</option>
                        <option value="Marketing">Marketing</option>
                    </select>
                </td>
                <td>
                    <button class="btn-icon select-product">
                        <i class="fas fa-plus"></i>
                    </button>
                </td>
            `;
            
            productTableBody.appendChild(row);
        });
    }

    // Mock function for updateSelectedCounter
    function updateSelectedCounter() {
        const counter = document.getElementById('selectedProductsCounter');
        if (counter) {
            counter.textContent = `Selected: ${window.selectedProductsToImport.size}`;
        }
    }
});

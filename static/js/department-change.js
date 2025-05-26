// Enhanced function to change department with proper quantity updates
function changeDepartment(equipmentId, itemName) {
    // Get current language for UI
    const language = document.documentElement.getAttribute('data-language') || 'en';
    
    // Get current department before making changes
    const departmentSelect = document.getElementById('departmentSelect');
    const currentDepartment = departmentSelect ? departmentSelect.value : '';
    
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
          console.log(`Changing equipment ${equipmentId} from department ${currentDepartment} to ${newDepartment}`);
        
        // First fetch the current equipment details to get the quantity
        fetch(`/api/equipment/${equipmentId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch equipment details');
                }
                return response.json();
            })
            .then(equipmentData => {
                console.log(`Current quantity: ${equipmentData.equipment.quantity}`);
                
                // Send the request to assign equipment to new department with the current quantity
                return fetch('/api/equipment/assign', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        equipment_id: equipmentId,
                        department: newDepartment,
                        quantity: equipmentData.equipment.quantity // Preserve the current quantity
                    })
                });
            })        .then(response => {
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
                
                // Force refresh equipment lists for both departments
                
                // 1. If we're viewing the source department, refresh it
                if (departmentSelect && departmentSelect.value === currentDepartment) {
                    console.log(`Refreshing source department: ${currentDepartment}`);
                    loadDepartmentEquipment(currentDepartment);
                }
                
                // 2. If we assigned to a different department, pre-fetch that data too
                if (newDepartment !== currentDepartment) {
                    console.log(`Pre-fetching target department: ${newDepartment}`);
                    
                    // Store the selected department option text to show in the success message
                    let newDeptFullName = '';
                    const newDepartmentOption = Array.from(document.querySelectorAll('#departmentSelect option'))
                        .find(option => option.value === newDepartment);
                    if (newDepartmentOption) {
                        newDeptFullName = newDepartmentOption.text;
                    }
                    
                    // Create a notification to indicate that data is refreshing
                    const notification = document.createElement('div');
                    notification.className = 'notification';
                    notification.style.position = 'fixed';
                    notification.style.bottom = '20px';
                    notification.style.right = '20px';
                    notification.style.backgroundColor = '#4CAF50';
                    notification.style.color = 'white';
                    notification.style.padding = '10px 20px';
                    notification.style.borderRadius = '4px';
                    notification.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
                    notification.style.zIndex = '1000';
                    notification.innerHTML = `
                        <div>${language === 'pl' ? 'Odświeżanie danych...' : 'Refreshing data...'}</div>
                        <div>${language === 'pl' ? `Element przeniesiony do: ${newDeptFullName}` : `Item moved to: ${newDeptFullName}`}</div>
                    `;
                    document.body.appendChild(notification);
                    
                    // This makes a background request to update our cache with the new department data
                    fetch(`/api/department_equipment/${encodeURIComponent(newDepartment)}`)
                        .then(response => response.json())
                        .then(data => {
                            console.log(`Updated data for target department ${newDepartment}`);
                            
                            // Update notification
                            notification.innerHTML = `
                                <div>${language === 'pl' ? 'Dane zaktualizowane!' : 'Data updated!'}</div>
                                <div>${language === 'pl' ? `Element przeniesiony do: ${newDeptFullName}` : `Item moved to: ${newDeptFullName}`}</div>
                            `;
                            
                            // If the user switched to view the target department, refresh it
                            if (departmentSelect.value === newDepartment) {
                                loadDepartmentEquipment(newDepartment);
                            }
                            
                            // Remove the notification after 3 seconds
                            setTimeout(() => {
                                notification.style.opacity = '0';
                                notification.style.transition = 'opacity 0.5s';
                                setTimeout(() => notification.remove(), 500);
                            }, 3000);
                        })
                        .catch(error => {
                            console.error('Error refreshing target department:', error);
                            // Update notification for error
                            notification.style.backgroundColor = '#F44336';
                            notification.innerHTML = `
                                <div>${language === 'pl' ? 'Błąd odświeżania danych!' : 'Error refreshing data!'}</div>
                            `;
                            // Remove the notification after 3 seconds
                            setTimeout(() => notification.remove(), 3000);
                        });
                }
            } else {
                // Show error message
                const errorMsg = language === 'pl' ? 
                    'Błąd: ' + (data.error || 'Nieznany błąd') : 
                    'Error: ' + (data.error || 'Unknown error');
                alert(errorMsg);
            }
        })        .catch(error => {
            console.error('Error:', error);
            const errorMsg = language === 'pl' ? 
                'Nie udało się przepisać elementu do nowego działu. Spróbuj ponownie.' : 
                'Failed to assign equipment to new department. Please try again.';
            alert(errorMsg);
            modal.remove(); // Make sure to remove the modal on error
        });
    });
    
    // Close modal when clicking outside of it
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.remove();
        }
    }
}

// Add a function to refresh all department data in background on page load
document.addEventListener('DOMContentLoaded', function() {
    // Wait for the page to finish loading
    setTimeout(() => {
        refreshAllDepartmentCounts();
    }, 1000);
});

// Function to refresh equipment counts for all departments in the background
function refreshAllDepartmentCounts() {
    console.log('Refreshing all department equipment counts...');
    
    // Get all departments from the select
    const departmentSelect = document.getElementById('departmentSelect');
    if (!departmentSelect) return;
    
    const departments = Array.from(departmentSelect.options)
        .filter(option => option.value)
        .map(option => option.value);
    
    // Create a queue of departments to refresh
    let queue = [...departments];
    let currentDept = departmentSelect.value;
    
    // Process each department sequentially with a small delay
    function processNextDepartment() {
        if (queue.length === 0) {
            console.log('All department data refreshed');
            return;
        }
        
        const dept = queue.shift();
        // Skip the current department as it's already loaded
        if (dept === currentDept) {
            processNextDepartment();
            return;
        }
        
        console.log(`Background refreshing data for: ${dept}`);
        
        // Fetch department data in background
        fetch(`/api/department_equipment/${encodeURIComponent(dept)}`)
            .then(response => response.json())
            .then(() => {
                console.log(`Updated equipment count for: ${dept}`);
                // Process next after a small delay
                setTimeout(processNextDepartment, 200);
            })
            .catch(error => {
                console.error(`Error updating ${dept}:`, error);
                // Continue with next department even if error
                setTimeout(processNextDepartment, 200);
            });
    }
    
    // Start processing the queue
    processNextDepartment();
}
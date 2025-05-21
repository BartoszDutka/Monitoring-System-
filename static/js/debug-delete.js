// Enhanced debug version of deleteEquipment function
function deleteEquipment(equipmentId) {
    // Get current language for confirmation message
    const language = document.documentElement.getAttribute('data-language') || 'en';
    const confirmMessage = language === 'pl' ? 
        'Czy na pewno chcesz usunąć ten element z inwentarza?' : 
        'Are you sure you want to delete this equipment from inventory?';
    
    console.log(`Próba usunięcia elementu z ID: ${equipmentId}`);
    
    if (confirm(confirmMessage)) {
        console.log(`Usuwanie zatwierdzone przez użytkownika, wysyłanie żądania...`);
        
        // Use FormData instead of JSON for better reliability
        const formData = new FormData();
        formData.append('equipment_id', equipmentId);
        formData.append('action', 'delete'); // Add delete action
        
        // Log form data before sending
        console.log(`Form data prepared for equipment ID: ${equipmentId}`);
        console.log(`Action: ${formData.get('action')}`);
        
        // Add debug request header
        fetch('/api/equipment/update', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-Debug': 'true'
            },
            body: formData
        })
        .then(response => {
            console.log(`Response received, status: ${response.status}`);
            // Log response headers
            console.log('Response headers:');
            response.headers.forEach((value, key) => {
                console.log(`${key}: ${value}`);
            });
            
            if (!response.ok) {
                console.error(`HTTP Error: ${response.status} ${response.statusText}`);
                throw new Error(`HTTP Error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(`Response data:`, data);
            if (data.success) {
                // Reload equipment list to reflect changes
                const departmentSelect = document.getElementById('departmentSelect');
                if (departmentSelect && departmentSelect.value) {
                    console.log(`Refreshing list for department: ${departmentSelect.value}`);
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
                console.error(`Deletion error: ${data.error}`);
                alert(errorMsg);
            }
        })
        .catch(error => {
            console.error('Error during delete operation:', error);
            const errorMsg = language === 'pl' ? 
                'Nie udało się usunąć elementu. Sprawdź konsolę, aby uzyskać więcej informacji.' : 
                'Failed to delete equipment. Check console for more information.';
            alert(errorMsg);
        });
    }
}

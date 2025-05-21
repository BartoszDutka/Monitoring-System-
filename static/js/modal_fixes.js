/**
 * Modal system fixes
 * This script adds additional handling for modal closing buttons
 * to avoid JavaScript errors.
 */
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners after the page has fully loaded
    const modalCloseBtn = document.getElementById('modal-close');
    const modalBg = document.getElementById('modal-bg');
    const modal = document.getElementById('modal');
    
    if (modalCloseBtn) {
        console.log('Adding event listener to close button');
        modalCloseBtn.addEventListener('click', function(e) {
            e.preventDefault();
            closeModalSafely();
        });
    }
    
    function closeModalSafely() {
        console.log('Closing modal safely');
        if (modalBg) modalBg.style.display = 'none';
        if (modal) modal.style.display = 'none';
    }
    
    // Global helper to close modals from anywhere
    window.closeModalSafely = closeModalSafely;
});

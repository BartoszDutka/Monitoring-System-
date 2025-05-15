/**
 * System monitoringu - własna implementacja listy rozwijanej
 * Rozwiązanie problemów z przeskakującym kursorem w polskim interfejsie
 */

document.addEventListener('DOMContentLoaded', function() {
    // Znajdujemy wszystkie selekty które wymagają zastąpienia
    setTimeout(() => {
        replaceNativeSelects();
    }, 300);

    // Nasłuchujemy na zdarzenie zmiany języka
    document.addEventListener('languageChanged', function() {
        // Odczekajmy chwilę aż dokument zostanie przetłumaczony
        setTimeout(() => {
            updateCustomSelectLabels();
        }, 300);
    });
});

// Funkcja zastępująca natywne selekty niestandardowymi kontrolkami
function replaceNativeSelects() {
    const selects = document.querySelectorAll('#departmentSelect');
    
    selects.forEach(select => {
        // Tworzenie kontenera dla naszej kontrolki
        const customSelect = document.createElement('div');
        customSelect.className = 'custom-select-container';
        customSelect.dataset.for = select.id;
        
        // Ukryj oryginalny select (ale pozostaw go w DOM dla submit formularzy)
        select.style.display = 'none';
        select.dataset.replaced = 'true';
        
        // Aktualna wartość / wyświetlany tekst
        const selectedValue = document.createElement('div');
        selectedValue.className = 'custom-select-value';
        selectedValue.textContent = select.options[select.selectedIndex]?.textContent || 'Wybierz opcję';
        selectedValue.setAttribute('tabindex', '0');
        
        // Strzałka rozwijania
        const arrow = document.createElement('div');
        arrow.className = 'custom-select-arrow';
        arrow.innerHTML = '<i class="fas fa-chevron-down"></i>';
        
        // Opcje rozwijane
        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'custom-select-options';
        
        // Dodaj opcje z oryginalnego selecta
        Array.from(select.options).forEach((option, index) => {
            const customOption = document.createElement('div');
            customOption.className = 'custom-select-option';
            customOption.dataset.value = option.value;
            customOption.textContent = option.textContent;
            customOption.setAttribute('tabindex', '0');
            
            if (index === select.selectedIndex) {
                customOption.classList.add('selected');
            }
            
            // Obsługa kliknięcia na opcję
            customOption.addEventListener('mousedown', function(e) {
                e.preventDefault(); // Zapobiega utracie focusu
            });
            
            customOption.addEventListener('click', function() {
                // Aktualizuj wyświetlany tekst
                selectedValue.textContent = this.textContent;
                
                // Ustaw wybraną opcję w oryginalnym selekcie
                select.value = this.dataset.value;
                
                // Wywołaj zdarzenie change
                const event = new Event('change', { bubbles: true });
                select.dispatchEvent(event);
                
                // Zamknij dropdown
                optionsContainer.classList.remove('active');
                selectedValue.focus();
                
                // Usuń klasę selected ze wszystkich opcji
                optionsContainer.querySelectorAll('.custom-select-option').forEach(opt => {
                    opt.classList.remove('selected');
                });
                
                // Dodaj klasę selected do klikniętej opcji
                this.classList.add('selected');
            });
            
            optionsContainer.appendChild(customOption);
        });
        
        // Obsługa kliknięcia na główny element
        selectedValue.addEventListener('click', function(e) {
            e.stopPropagation();
            const isActive = optionsContainer.classList.contains('active');
            
            // Zamknij wszystkie inne aktywne selekty
            document.querySelectorAll('.custom-select-options.active').forEach(container => {
                if (container !== optionsContainer) {
                    container.classList.remove('active');
                }
            });
              // Przełącz stan aktywnego
            optionsContainer.classList.toggle('active');
            
            // Nie przewijamy już do wybranej opcji, aby uniknąć przesuwania strony
            // Zamiast tego, po prostu upewniamy się, że opcje są widoczne
            if (!isActive) {
                // Sprawdzamy czy lista jest już widoczna, jeśli nie, 
                // pozycjonujemy ją tak, aby nie przesuwać strony
                optionsContainer.style.maxHeight = '300px';
            }
        });
        
        // Zamknij dropdown po kliknięciu poza nim
        document.addEventListener('click', function(e) {
            if (!customSelect.contains(e.target)) {
                optionsContainer.classList.remove('active');
            }
        });
        
        // Nawigacja klawiaturą
        selectedValue.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
                e.preventDefault();
                optionsContainer.classList.add('active');
                
                // Ustaw focus na opcję bez przewijania strony
                const selectedOption = optionsContainer.querySelector('.selected') || 
                                   optionsContainer.querySelector('.custom-select-option');
                if (selectedOption) {
                    // Focus bez przewijania strony
                    selectedOption.focus({preventScroll: true});
                }
            }
        });
        
        optionsContainer.addEventListener('keydown', function(e) {
            const options = Array.from(this.querySelectorAll('.custom-select-option'));
            const currentIndex = options.findIndex(opt => opt === document.activeElement);
            
            if (e.key === 'ArrowDown' && currentIndex < options.length - 1) {
                e.preventDefault();
                options[currentIndex + 1].focus();
            } else if (e.key === 'ArrowUp' && currentIndex > 0) {
                e.preventDefault();
                options[currentIndex - 1].focus();
            } else if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                document.activeElement.click();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                optionsContainer.classList.remove('active');
                selectedValue.focus();
            }
        });
        
        // Dodaj elementy do kontenera
        customSelect.appendChild(selectedValue);
        customSelect.appendChild(arrow);
        customSelect.appendChild(optionsContainer);
        
        // Wstaw niestandardowy select po oryginalnym
        select.parentNode.insertBefore(customSelect, select.nextSibling);
        
        // Synchronizacja gdy oryginalna kontrolka zmienia wartość
        select.addEventListener('change', function() {
            // Aktualizuje wyświetlany tekst
            selectedValue.textContent = this.options[this.selectedIndex]?.textContent || 'Wybierz opcję';
            
            // Aktualizuje zaznaczenie opcji
            const options = optionsContainer.querySelectorAll('.custom-select-option');
            options.forEach(opt => opt.classList.remove('selected'));
            
            const selectedOption = Array.from(options).find(opt => opt.dataset.value === this.value);
            if (selectedOption) {
                selectedOption.classList.add('selected');
            }
        });
    });
}

// Aktualizacja etykiet w custom selektach
function updateCustomSelectLabels() {
    document.querySelectorAll('.custom-select-container').forEach(customSelect => {
        const selectId = customSelect.dataset.for;
        const originalSelect = document.getElementById(selectId);
        
        if (originalSelect) {
            const selectedValue = customSelect.querySelector('.custom-select-value');
            selectedValue.textContent = originalSelect.options[originalSelect.selectedIndex]?.textContent || 'Wybierz opcję';
            
            // Aktualizuj wszystkie opcje
            const options = customSelect.querySelectorAll('.custom-select-option');
            options.forEach((option, index) => {
                if (index < originalSelect.options.length) {
                    option.textContent = originalSelect.options[index].textContent;
                }
            });
        }
    });
}

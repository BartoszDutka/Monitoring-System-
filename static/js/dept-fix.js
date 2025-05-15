/**
 * System monitoringu - dodatkowy moduł naprawczy dla formatu działów
 * Ten skrypt uruchamia się jako pierwszy i naprawia formatowanie nazw działów
 */

document.addEventListener('DOMContentLoaded', function() {
    // Poczekaj na pełne załadowanie strony
    setTimeout(function() {
        fixDepartmentFormat();
    }, 200);
});

// Dodatkowe nasłuchiwanie na zmiany języka
document.addEventListener('languageChanged', function(e) {
    // Poczekaj chwilę zanim system dokona właściwych zmian językowych
    setTimeout(function() {
        fixDepartmentFormat();
    }, 250);
});

function fixDepartmentFormat() {
    try {
        // Sprawdź czy jesteśmy w polskiej wersji
        const language = document.documentElement.getAttribute('data-language') || 'en';
        if (language !== 'pl') return;

        // Pobierz wszystkie listy rozwijane z działami
        const departmentSelects = document.querySelectorAll('#departmentSelect, select[name="assignTo"]');
        
        // Tablica tłumaczeń działów
        const departmentTranslations = {
            'Information Technology Department': 'Dział Technologii Informacyjnej',
            'Human Resources': 'Zasoby Ludzkie',
            'Administration Department': 'Dział Administracji',
            'Research and Development': 'Badania i Rozwój',
            'Finance Department': 'Dział Finansowy',
            'Marketing Department': 'Dział Marketingu',
            'Sales Department': 'Dział Sprzedaży',
            'Operations Department': 'Dział Operacyjny', 
            'Technical Support': 'Wsparcie Techniczne',
            'Software Development': 'Rozwój Oprogramowania',
            'IT': 'Dział Technologii Informacyjnej',
            'Development': 'Rozwój Oprogramowania',
            'Finance': 'Dział Finansowy', 
            'HR': 'Zasoby Ludzkie',
            'Marketing': 'Dział Marketingu',
            'Sales': 'Dział Sprzedaży',
            'Operations': 'Dział Operacyjny',
            'Research': 'Badania i Rozwój',
            'Support': 'Wsparcie Techniczne'
        };
        
        departmentSelects.forEach(select => {
            if (!select) return;
            
            Array.from(select.options).forEach(option => {
                if (!option.value || option.value === '') return; // Pomijamy "Wybierz dział..."
                
                const deptName = option.value;
                // Sprawdź czy już ma formatowanie "(Tłumaczenie)"
                if (!option.textContent.match(/\([^)]+\) \(\d+/)) {
                    // Dopasuj liczbę elementów (jeśli istnieje)
                    let itemCount = '0';
                    let itemText = 'elementów';
                    
                    const countMatch = option.textContent.match(/\((\d+) (items|elementów)\)/);
                    if (countMatch) {
                        itemCount = countMatch[1];
                        itemText = countMatch[2] === 'items' ? 'elementów' : countMatch[2];
                    }
                    
                    // Znajdź tłumaczenie lub użyj oryginalnej nazwy
                    const translation = departmentTranslations[deptName] || deptName;
                    
                    // Formatuj tekst opcji: "Development (Rozwój Oprogramowania) (5 elementów)"
                    option.textContent = `${deptName} (${translation}) (${itemCount} ${itemText})`;
                }
            });
        });
    } catch (error) {
        console.error('Błąd przy naprawianiu formatu działów:', error);
    }
}

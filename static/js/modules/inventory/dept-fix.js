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
        // Sprawdź język
        const language = document.documentElement.getAttribute('data-language') || 'en';
        
        // W angielskiej wersji nie robimy nic - zachowujemy oryginalne nazwy
        if (language !== 'pl') return;

        // Pobierz wszystkie listy rozwijane z działami
        const departmentSelects = document.querySelectorAll('#departmentSelect, select[name="assignTo"]');
        
        // Tablica tłumaczeń działów
        const departmentTranslations = {
            'Information Technology Department': 'Dział Technologii Informacyjnej',
            'Human Resources': 'Zasoby Ludzkie',
            'Administration Department': 'Dział Administracji',
            'Administration': 'Administracja',
            'Research and Development': 'Badania i Rozwój',
            'Finance Department': 'Dział Finansowy',
            'Marketing Department': 'Dział Marketingu',
            'Sales Department': 'Dział Sprzedaży',
            'Operations Department': 'Dział Operacyjny', 
            'Technical Support': 'Wsparcie Techniczne',
            'Software Development': 'Rozwój Oprogramowania',
            'IT': 'Dział IT',
            'Development': 'Rozwój Oprogramowania',
            'Finance': 'Dział Finansowy', 
            'HR': 'Dział HR',
            'Marketing': 'Dział Marketingu',
            'Sales': 'Dział Sprzedaży',
            'Operations': 'Dział Operacyjny',
            'Research': 'Dział Badań',
            'Support': 'Wsparcie Techniczne'
        };
        
        departmentSelects.forEach(select => {
            if (!select) return;
            
            Array.from(select.options).forEach(option => {
                if (!option.value || option.value === '') return; // Pomijamy "Wybierz dział..."
                
                const deptName = option.value;
                
                // W polskiej wersji używamy tylko polskich nazw
                const translation = departmentTranslations[deptName] || deptName;
                option.textContent = translation;
            });
        });
    } catch (error) {
        console.error('Błąd przy naprawianiu formatu działów:', error);
    }
}

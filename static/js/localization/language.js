/**
 * System monitoringu - moduł obsługi wielojęzyczności
 * Language switcher and translation handler
 */

// Obsługiwane języki / Supported languages
const LANGUAGES = {
    'en': 'English',
    'pl': 'Polski'
};

// Inicjalizacja modułu języka / Initialize language module
document.addEventListener('DOMContentLoaded', () => {
    initializeLanguageSystem();
});

// Inicjalizacja systemu językowego / Initialize language system
function initializeLanguageSystem() {
    const languageToggleBtn = document.getElementById('language-toggle');
    if (!languageToggleBtn) return;

    const html = document.documentElement;
      // Sprawdź czy mamy ustawiony język na serwerze (w meta tagu)
    const serverLanguageMeta = document.querySelector('meta[name="server-language"]');
    const serverLanguage = serverLanguageMeta ? serverLanguageMeta.getAttribute('content') : null;
    
    // Sprawdź język z localStorage
    const localLanguage = localStorage.getItem('language');
    
    // Załaduj zapisany język: najpierw sprawdź serwer, potem localStorage, lub użyj domyślnego (angielski)
    const savedLanguage = serverLanguage || localLanguage || 'en';
    
    // Zapisz do localStorage jeśli różni się od obecnego
    if (localStorage.getItem('language') !== savedLanguage) {
        localStorage.setItem('language', savedLanguage);
    }
    
    // Jeśli język w localStorage różni się od języka serwera, synchronizuj
    if (localLanguage && serverLanguage && localLanguage !== serverLanguage) {
        syncLanguageWithServer(localLanguage);
    }
    
    // Sprawdź czy to jest odświeżenie strony po zmianie języka
    const justChanged = sessionStorage.getItem('language_just_changed');
    if (justChanged) {
        // Usuń flagę, aby nie wpaść w pętlę
        sessionStorage.removeItem('language_just_changed');
        updateLanguageWithoutRefresh(savedLanguage);
    } else {
        // Normalne uruchomienie
        updateLanguageWithoutRefresh(savedLanguage);
    }
      // Obsługa kliknięcia przycisku zmiany języka
    languageToggleBtn.addEventListener('click', () => {
        const currentLang = html.getAttribute('data-language') || 'en';
        const newLang = currentLang === 'en' ? 'pl' : 'en';
        
        // Ustaw języki w storage
        localStorage.setItem('language', newLang);
        sessionStorage.setItem('language_just_changed', 'true');
        
        // Synchronizuj język z sesją serwera i odśwież po zakończeniu
        syncLanguageWithServer(newLang, () => {
            // Po zakończeniu synchronizacji, odśwież stronę
            window.location.reload();
        });
    });
}

// Synchronizuje wybór języka z serwerem / Sync language choice with server
function syncLanguageWithServer(lang, callback) {
    try {
        fetch('/api/set_language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ language: lang }),
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            console.log('Language synchronized with server:', data);
            if (callback && typeof callback === 'function') {
                callback();
            }
        })
        .catch(error => {
            console.error('Error syncing language with server:', error);
            // Still call the callback even if there was an error
            if (callback && typeof callback === 'function') {
                callback();
            }
        });
    } catch (e) {
        console.error('Failed to sync language with server:', e);
        // Still call the callback even if there was an error
        if (callback && typeof callback === 'function') {
            callback();
        }
    }
}

// Aktualizacja języka bez odświeżania / Update language without refresh
function updateLanguageWithoutRefresh(lang) {
    if (!Object.keys(LANGUAGES).includes(lang)) {
        console.error(`Unsupported language: ${lang}`);
        lang = 'en'; // Fallback to English
    }
    
    const html = document.documentElement;
    const languageToggleBtn = document.getElementById('language-toggle');
      // Aktualizuj atrybuty HTML
    html.setAttribute('lang', lang);
    html.setAttribute('data-language', lang);
    
    // Aktualizuj przycisk przełączania
    if (languageToggleBtn) {
        const langSpan = languageToggleBtn.querySelector('span');
        if (langSpan) {
            langSpan.textContent = lang.toUpperCase();
        }
    }
      // Przetłumacz wszystkie elementy
    translatePage(lang);
    
    // Update department translations
    translateDepartments(lang);
    
    // Dodatkowe ustawienie fokusa dla stabilizacji interfejsu
    // przy przełączaniu języków w inwentarzu
    setTimeout(() => {
        try {
            const activeElement = document.activeElement;
            // Jeśli focus jest na liście rozwijanej, przywróć go na inny element
            if (activeElement && activeElement.id === 'departmentSelect') {
                activeElement.blur();
            }
        } catch (e) {
            console.error('Błąd przy stabilizacji fokusa po zmianie języka:', e);
        }
    }, 100);
}

// Tłumaczenie strony / Translate page content
function translatePage(lang) {
    // Znajdź wszystkie elementy z atrybutami data-en i data-pl
    const elements = document.querySelectorAll('[data-en][data-pl]');
    
    elements.forEach(element => {
        const translation = element.getAttribute(`data-${lang}`);
        if (translation) {
            element.textContent = translation;
        }
    });
    
    // Znajdź i zaktualizuj wszystkie placeholdery
    const inputElements = document.querySelectorAll('input[data-en-placeholder][data-pl-placeholder]');
    inputElements.forEach(input => {
        const placeholderTranslation = input.getAttribute(`data-${lang}-placeholder`);
        if (placeholderTranslation) {
            input.placeholder = placeholderTranslation;
        }
    });
    
    // Dispatch event that language has changed (for other components)
    document.dispatchEvent(new CustomEvent('languageChanged', { 
        detail: { language: lang } 
    }));
}

// Funkcja tłumacząca opisy działów / Function to translate department descriptions
function translateDepartments(lang) {
    // Find all department dropdowns and update descriptions
    document.querySelectorAll('select option').forEach(option => {
        // Check if this option contains department description (has format "Name (Description)")
        const match = option.textContent.match(/(.*) \((.*)\)/);
        if (match) {
            const deptName = match[1];
            
            // Check if we have translation data attributes
            if (option.hasAttribute(`data-desc-${lang}`)) {
                const translatedDesc = option.getAttribute(`data-desc-${lang}`);
                option.textContent = `${deptName} (${translatedDesc})`;
            }
            // Check if this is an option with a dept-description span
            else if (option.querySelector('.dept-description')) {
                const descSpan = option.querySelector('.dept-description');
                if (descSpan && option.hasAttribute(`data-dept-${lang}`)) {
                    descSpan.textContent = option.getAttribute(`data-dept-${lang}`);
                }
            }
        }
    });
      // Find all department descriptions in dynamic content (table cells, spans, etc.)
    const departmentTranslations = {
        'en': {
            'Information Technology Department': 'Information Technology Department',
            'Human Resources': 'Human Resources',
            'Administration Department': 'Administration Department',
            'Administration': 'Administration',
            'Research and Development': 'Research and Development',
            'Finance Department': 'Finance Department',
            'Finance': 'Finance',
            'Marketing Department': 'Marketing Department',
            'Sales Department': 'Sales Department',
            'Operations Department': 'Operations Department',
            'Technical Support': 'Technical Support',
            'Software Development': 'Software Development',
            'Development': 'Development'
        },
        'pl': {
            'Information Technology Department': 'Dział Technologii Informacyjnej',
            'Human Resources': 'Zasoby Ludzkie',
            'Administration Department': 'Dział Administracji',
            'Administration': 'Administracja',
            'Research and Development': 'Badania i Rozwój',
            'Finance Department': 'Dział Finansowy',
            'Finance': 'Dział Finansowy',
            'Marketing Department': 'Dział Marketingu',
            'Sales Department': 'Dział Sprzedaży',
            'Operations Department': 'Dział Operacyjny', 
            'Technical Support': 'Wsparcie Techniczne',
            'Software Development': 'Rozwój Oprogramowania',
            'Development': 'Rozwój Oprogramowania'
        }
    };    // Bezpośrednie tłumaczenie nazw departamentów w opcjach wyboru - uproszczony format
    const departmentSelect = document.getElementById('departmentSelect');
    if (departmentSelect) {
        Array.from(departmentSelect.options).forEach(option => {
            if (!option.value) return; // Pomijamy opcję "Wybierz dział..."
            
            // Sprawdź czy nazwa departamentu jest kluczem w słowniku tłumaczeń
            const deptName = option.value;
            
            // W polskiej wersji pokazujemy tylko polskie nazwy, w angielskiej - angielskie
            if (departmentTranslations.en[deptName] && lang === 'pl') {
                // W polskiej wersji tylko polska nazwa
                option.textContent = departmentTranslations[lang][deptName];
            } else {
                // W angielskiej wersji lub dla działów bez tłumaczenia - oryginalna nazwa
                option.textContent = deptName;
            }
        });
    }
      // Replace department descriptions in text nodes
    document.querySelectorAll('span, td, div').forEach(el => {
        if (!el.children.length && el.textContent && el.closest('table')) {
            // Check if this element contains a department name directly
            Object.keys(departmentTranslations.en).forEach(engDesc => {
                // Bezpośrednie dopasowanie nazwy departamentu (nie w nawiasach)
                if (el.textContent.trim() === engDesc && lang === 'pl') {
                    el.textContent = departmentTranslations.pl[engDesc];
                }
                
                // Dopasowanie w nawiasach też obsługujemy dla zgodności z innymi częściami interfejsu
                const pattern = new RegExp(`\\(${engDesc}\\)`, 'g');
                if (pattern.test(el.textContent) && lang === 'pl') {
                    el.textContent = el.textContent.replace(
                        pattern, 
                        `(${departmentTranslations.pl[engDesc]})`
                    );
                }
            });
        }
    });
}

// Funkcja pomocnicza do tłumaczenia tekstu / Helper function for text translation
function translateText(key, lang = null) {
    if (!lang) {
        lang = document.documentElement.getAttribute('data-language') || 'en';
    }
    
    // Dla prostych przypadków - elementy z data-en i data-pl
    const translations = {
        'en': {
            'dashboard': 'Dashboard',
            'available': 'Available',
            'unavailable': 'Unavailable',
            'unknown': 'Unknown',
            'logout': 'Logout',
            'reports': 'Reports',
            'inventory': 'Item Inventory',
            'tasks': 'Task Management',
            'monitors': 'Monitors',
            'printers': 'Printers',
            'servers': 'Servers',
            'network_devices': 'Network Devices',
            'workstations': 'Workstations (KS)',
            'terminals': 'Terminals (KT)',
            'racks': 'Racks',
            'other_devices': 'Other Devices',
            'recent_logs': 'Recent Logs',
            'messages_over_time': 'Messages Over Time',
            'main_menu': 'Main Menu',
            'tools': 'Tools',
            'functions': 'Functions',
            'glpi_inventory': 'GLPI Inventory',
            
            // Department translations
            'Information Technology Department': 'Information Technology Department',
            'Human Resources': 'Human Resources',
            'Administration Department': 'Administration Department',
            'Research and Development': 'Research and Development',
            'Finance Department': 'Finance Department',
            'Marketing Department': 'Marketing Department',
            'Sales Department': 'Sales Department',
            'Operations Department': 'Operations Department', 
            'Technical Support': 'Technical Support',
            'Software Development': 'Software Development'
        },
        'pl': {
            'dashboard': 'Pulpit',
            'available': 'Dostępne',
            'unavailable': 'Niedostępne',
            'unknown': 'Nieznane',
            'logout': 'Wyloguj',
            'reports': 'Raporty',
            'inventory': 'Inwentaryzacja',
            'tasks': 'Zarządzanie zadaniami',
            'monitors': 'Monitory',
            'printers': 'Drukarki',
            'servers': 'Serwery',
            'network_devices': 'Urządzenia sieciowe',
            'workstations': 'Stacje robocze (KS)',
            'terminals': 'Terminale (KT)',
            'racks': 'Szafy serwerowe',
            'other_devices': 'Inne urządzenia',
            'recent_logs': 'Ostatnie logi',
            'messages_over_time': 'Wiadomości w czasie',
            'main_menu': 'Menu Główne',
            'tools': 'Narzędzia',
            'functions': 'Funkcje',
            'glpi_inventory': 'Inwentaryzacja GLPI',
            
            // Department translations
            'Information Technology Department': 'Dział Technologii Informacyjnej',
            'Human Resources': 'Zasoby Ludzkie',
            'Administration Department': 'Dział Administracji',
            'Research and Development': 'Badania i Rozwój',
            'Finance Department': 'Dział Finansowy',
            'Marketing Department': 'Dział Marketingu',
            'Sales Department': 'Dział Sprzedaży',
            'Operations Department': 'Dział Operacyjny', 
            'Technical Support': 'Wsparcie Techniczne',
            'Software Development': 'Rozwój Oprogramowania'
        }
    };
    
    return translations[lang]?.[key] || translations['en'][key] || key;
}
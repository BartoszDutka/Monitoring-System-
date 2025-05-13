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
    
    // Załaduj zapisany język lub użyj domyślnego (angielski)
    const savedLanguage = localStorage.getItem('language') || 'en';
    
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
        
        // Po prostu odśwież stronę
        window.location.reload();
    });
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
            'glpi_inventory': 'GLPI Inventory'
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
            'glpi_inventory': 'Inwentaryzacja GLPI'
        }
    };
    
    return translations[lang]?.[key] || translations['en'][key] || key;
}
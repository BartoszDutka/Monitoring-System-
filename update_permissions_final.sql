-- ==================================================
-- FINALNA REORGANIZACJA UPRAWNIEŃ SYSTEMU MONITORINGU
-- ==================================================
-- Ten skrypt reorganizuje strukturę uprawnień zgodnie z nowymi wymaganiami
-- i przypisuje odpowiednie uprawnienia do ról

START TRANSACTION;

-- 1. USUWANIE STARYCH/NIEPOTRZEBNYCH UPRAWNIEŃ
-- ==================================================

-- Usuń duplikat tasks_create (zostanie tylko create_tasks)
DELETE rp FROM role_permissions rp
JOIN permissions p ON rp.permission_id = p.permission_id
WHERE p.permission_key = 'tasks_create';

DELETE FROM permissions WHERE permission_key = 'tasks_create';

-- Usuń inne nieużywane uprawnienia
DELETE rp FROM role_permissions rp
JOIN permissions p ON rp.permission_id = p.permission_id
WHERE p.permission_key IN ('export_reports', 'acknowledge_alerts', 'assign_assets');

DELETE FROM permissions WHERE permission_key IN ('export_reports', 'acknowledge_alerts', 'assign_assets');

-- 2. AKTUALIZACJA ISTNIEJĄCYCH UPRAWNIEŃ
-- ==================================================

-- Kategoria: inventory
UPDATE permissions SET 
    category = 'inventory',
    name_en = 'View Inventory',
    name_pl = 'Podgląd inwentarza',
    description_en = 'Allows viewing inventory items, equipment assignments, and departmental equipment lists. Users can browse through all inventory data but cannot make changes.',
    description_pl = 'Pozwala na przeglądanie elementów inwentarza, przypisań sprzętu i list sprzętu działów. Użytkownicy mogą przeglądać wszystkie dane inwentarzowe, ale nie mogą wprowadzać zmian.'
WHERE permission_key = 'view_inventory';

UPDATE permissions SET 
    category = 'inventory',
    name_en = 'Manage Inventory',
    name_pl = 'Zarządzanie inwentarzem',
    description_en = 'Full inventory management including adding, editing, deleting equipment, managing assignments, processing invoices, and updating equipment status.',
    description_pl = 'Pełne zarządzanie inwentarzem obejmujące dodawanie, edycję, usuwanie sprzętu, zarządzanie przypisaniami, przetwarzanie faktur i aktualizację statusu sprzętu.'
WHERE permission_key = 'manage_inventory';

-- Kategoria: monitoring  
UPDATE permissions SET 
    category = 'monitoring',
    name_en = 'View Monitoring',
    name_pl = 'Podgląd monitoringu',
    description_en = 'Access to monitoring dashboards, system status views, real-time metrics, and performance indicators. Includes viewing Zabbix data and system health.',
    description_pl = 'Dostęp do pulpitów monitoringu, widoków statusu systemu, metryk w czasie rzeczywistym i wskaźników wydajności. Obejmuje przeglądanie danych Zabbix i kondycji systemu.'
WHERE permission_key = 'view_monitoring';

-- Kategoria: reports
UPDATE permissions SET 
    category = 'reports',
    name_en = 'View Reports',
    name_pl = 'Podgląd raportów',
    description_en = 'Access to view existing reports, browse report history, and download generated reports. Read-only access to reporting system.',
    description_pl = 'Dostęp do przeglądania istniejących raportów, przeglądania historii raportów i pobierania wygenerowanych raportów. Dostęp tylko do odczytu do systemu raportowania.'
WHERE permission_key = 'view_reports';

UPDATE permissions SET 
    category = 'reports',
    name_en = 'Manage Reports',
    name_pl = 'Zarządzanie raportami',
    description_en = 'Full report management including creating, editing, deleting reports, configuring report parameters, and managing report scheduling.',
    description_pl = 'Pełne zarządzanie raportami obejmujące tworzenie, edycję, usuwanie raportów, konfigurację parametrów raportów i zarządzanie harmonogramem raportów.'
WHERE permission_key = 'manage_reports';

-- Kategoria: system
UPDATE permissions SET 
    category = 'system',
    name_en = 'Manage Users',
    name_pl = 'Zarządzanie użytkownikami',
    description_en = 'User administration including creating, editing, deleting user accounts, managing roles and permissions, and configuring user access levels.',
    description_pl = 'Administracja użytkownikami obejmująca tworzenie, edycję, usuwanie kont użytkowników, zarządzanie rolami i uprawnieniami oraz konfigurację poziomów dostępu.'
WHERE permission_key = 'manage_users';

-- Kategoria: tasks
UPDATE permissions SET 
    category = 'tasks',
    name_en = 'Create Tasks',
    name_pl = 'Tworzenie zadań',
    description_en = 'Ability to create new tasks, set task parameters, assign tasks to users, and initiate task workflows.',
    description_pl = 'Możliwość tworzenia nowych zadań, ustawiania parametrów zadań, przypisywania zadań użytkownikom i inicjowania przepływów pracy zadań.'
WHERE permission_key = 'create_tasks';

UPDATE permissions SET 
    category = 'tasks',
    name_en = 'View Tasks',
    name_pl = 'Wyświetlanie zadań',
    description_en = 'Access to view assigned tasks, task details, task history, and progress tracking. Read-only access to task management system.',
    description_pl = 'Dostęp do przeglądania przypisanych zadań, szczegółów zadań, historii zadań i śledzenia postępów. Dostęp tylko do odczytu do systemu zarządzania zadaniami.'
WHERE permission_key = 'view_tasks';

UPDATE permissions SET 
    category = 'tasks',
    name_en = 'Manage All Tasks',
    name_pl = 'Zarządzanie wszystkimi zadaniami',
    description_en = 'Administrative access to all tasks in the system, including viewing, editing, deleting any task regardless of assignment, and managing task workflows.',
    description_pl = 'Dostęp administracyjny do wszystkich zadań w systemie, w tym przeglądanie, edycja, usuwanie dowolnego zadania niezależnie od przypisania i zarządzanie przepływami pracy zadań.'
WHERE permission_key = 'manage_all_tasks';

-- Kategoria: GLPI
UPDATE permissions SET 
    category = 'GLPI',
    name_en = 'VNC Connect',
    name_pl = 'Połączenia VNC',
    description_en = 'Ability to establish VNC connections to remote devices, access remote desktops, and perform remote administration tasks.',
    description_pl = 'Możliwość nawiązywania połączeń VNC z urządzeniami zdalnymi, dostęp do zdalnych pulpitów i wykonywanie zdalnych zadań administracyjnych.'
WHERE permission_key = 'vnc_connect';

-- Kategoria: Graylog
UPDATE permissions SET 
    category = 'Graylog',
    name_en = 'View Logs',
    name_pl = 'Podgląd logów',
    description_en = 'Access to system logs, log analysis tools, log filtering and searching capabilities, and log data refresh operations.',
    description_pl = 'Dostęp do logów systemowych, narzędzi analizy logów, możliwości filtrowania i wyszukiwania logów oraz operacji odświeżania danych logów.'
WHERE permission_key = 'view_logs';

-- 3. DODAWANIE NOWYCH UPRAWNIEŃ
-- ==================================================

-- Kategoria: reports - nowe uprawnienia
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES 
('create_reports', 'reports', 'Create Reports', 'Tworzenie raportów', 
 'Ability to create new reports, define report templates, configure data sources, and set up automated report generation.',
 'Możliwość tworzenia nowych raportów, definiowania szablonów raportów, konfiguracji źródeł danych i konfiguracji automatycznego generowania raportów.'),

('delete_reports', 'reports', 'Delete Reports', 'Usuwanie raportów', 
 'Permission to delete existing reports, remove report templates, and clean up report archives and temporary files.',
 'Uprawnienie do usuwania istniejących raportów, usuwania szablonów raportów i czyszczenia archiwów raportów oraz plików tymczasowych.');

-- Kategoria: system - nowe uprawnienie
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES 
('manage_profile', 'system', 'Manage Profile', 'Zarządzanie profilem', 
 'User can edit their own profile information, change password, update personal settings, and configure notification preferences.',
 'Użytkownik może edytować informacje swojego profilu, zmieniać hasło, aktualizować ustawienia osobiste i konfigurować preferencje powiadomień.');

-- Kategoria: tasks - nowe uprawnienia
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES 
('tasks_update', 'tasks', 'Update Tasks', 'Aktualizacja zadań', 
 'Ability to update task status, modify task details, change task assignments, and update task progress and completion status.',
 'Możliwość aktualizacji statusu zadań, modyfikacji szczegółów zadań, zmiany przypisań zadań oraz aktualizacji postępu i statusu zakończenia zadań.'),

('tasks_comment', 'tasks', 'Comment Tasks', 'Komentowanie zadań', 
 'Permission to add comments to tasks, participate in task discussions, provide updates, and communicate within task context.',
 'Uprawnienie do dodawania komentarzy do zadań, uczestniczenia w dyskusjach dotyczących zadań, dostarczania aktualizacji i komunikacji w kontekście zadań.'),

('tasks_delete', 'tasks', 'Delete Tasks', 'Usuwanie zadań', 
 'Permission to delete tasks, remove task assignments, and clean up completed or cancelled tasks from the system.',
 'Uprawnienie do usuwania zadań, usuwania przypisań zadań i czyszczenia zakończonych lub anulowanych zadań z systemu.');

-- Kategoria: GLPI - nowe uprawnienie
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES 
('view_glpi', 'GLPI', 'View GLPI Equipment', 'Podgląd sprzętu w GLPI', 
 'Access to GLPI equipment database, device information, hardware specifications, network devices, and asset management data from GLPI system.',
 'Dostęp do bazy danych sprzętu GLPI, informacji o urządzeniach, specyfikacji sprzętu, urządzeń sieciowych i danych zarządzania zasobami z systemu GLPI.');

-- 4. PRZYPISANIE UPRAWNIEŃ DO RÓL
-- ==================================================

-- Sprawdź i utwórz role jeśli nie istnieją
INSERT IGNORE INTO roles (role_key, description_en, description_pl) VALUES 
('admin', 'System Administrator', 'Administrator systemu'),
('manager', 'Department Manager', 'Kierownik działu'),
('user', 'Standard User', 'Użytkownik standardowy'),
('viewer', 'Read-only Viewer', 'Użytkownik z dostępem tylko do odczytu');

-- ROLA: admin - pełny dostęp do wszystkich funkcji
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id 
FROM roles r, permissions p 
WHERE r.role_key = 'admin';

-- ROLA: manager - zarządzanie w swoim zakresie
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id 
FROM roles r, permissions p 
WHERE r.role_key = 'manager' 
AND p.permission_key IN (
    'view_inventory', 'manage_inventory',
    'view_monitoring', 
    'view_reports', 'manage_reports', 'create_reports', 'delete_reports',
    'manage_profile',
    'create_tasks', 'tasks_update', 'tasks_comment', 'tasks_delete', 'view_tasks',
    'view_glpi', 'vnc_connect',
    'view_logs'
);

-- ROLA: user - podstawowe funkcje operacyjne
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id 
FROM roles r, permissions p 
WHERE r.role_key = 'user' 
AND p.permission_key IN (
    'view_inventory',
    'view_monitoring',
    'view_reports',
    'manage_profile',
    'create_tasks', 'tasks_update', 'tasks_comment', 'view_tasks',
    'view_glpi',
    'view_logs'
);

-- ROLA: viewer - tylko podgląd
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id 
FROM roles r, permissions p 
WHERE r.role_key = 'viewer' 
AND p.permission_key IN (
    'view_inventory',
    'view_monitoring',
    'view_reports',
    'manage_profile',
    'view_tasks',
    'view_glpi',
    'view_logs'
);

-- 5. CZYSZCZENIE NIEPOTRZEBNYCH PRZYPISAŃ
-- ==================================================

-- Usuń wszystkie przypisania dla nieistniejących uprawnień
DELETE rp FROM role_permissions rp 
LEFT JOIN permissions p ON rp.permission_id = p.permission_id 
WHERE p.permission_id IS NULL;

-- Usuń wszystkie przypisania dla nieistniejących ról
DELETE rp FROM role_permissions rp 
LEFT JOIN roles r ON rp.role_id = r.role_id 
WHERE r.role_id IS NULL;

-- 6. WERYFIKACJA WYNIKÓW
-- ==================================================

-- Pokaż wszystkie uprawnienia według kategorii
SELECT 'UPRAWNIENIA WEDŁUG KATEGORII:' as info;
SELECT 
    category as 'Kategoria',
    permission_key as 'Klucz_uprawnienia',
    name_pl as 'Nazwa_PL',
    name_en as 'Nazwa_EN'
FROM permissions 
ORDER BY category, permission_key;

-- Pokaż przypisania uprawnień do ról
SELECT 'PRZYPISANIA UPRAWNIEŃ DO RÓL:' as info;
SELECT 
    r.role_key as 'Rola',
    p.category as 'Kategoria',
    p.permission_key as 'Uprawnienie',
    p.name_pl as 'Nazwa'
FROM roles r
JOIN role_permissions rp ON r.role_id = rp.role_id
JOIN permissions p ON rp.permission_id = p.permission_id
ORDER BY r.role_key, p.category, p.permission_key;

-- Pokaż liczbę uprawnień dla każdej roli
SELECT 'LICZBA UPRAWNIEŃ NA ROLĘ:' as info;
SELECT 
    r.role_key as 'Rola',
    COUNT(rp.permission_id) as 'Liczba_uprawnień'
FROM roles r
LEFT JOIN role_permissions rp ON r.role_id = rp.role_id
GROUP BY r.role_key
ORDER BY r.role_key;

COMMIT;

-- ==================================================
-- SKRYPT ZAKOŃCZONY POMYŚLNIE
-- Struktura uprawnień została zaktualizowana zgodnie z wymaganiami
-- ==================================================

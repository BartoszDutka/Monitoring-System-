-- Skrypt do reorganizacji struktury uprawnień i naprawy ról
-- Data: 2025-05-30
-- Cel: Ustanowienie nowej struktury uprawnień z właściwymi opisami i naprawienie ról

START TRANSACTION;

-- ==================================================
-- CZĘŚĆ 1: USUWANIE STARYCH/NIEPOTRZEBNYCH UPRAWNIEŃ
-- ==================================================

-- Usuń niepotrzebne uprawnienie tasks_create (duplikat create_tasks)
DELETE rp FROM role_permissions rp 
JOIN permissions p ON rp.permission_id = p.permission_id 
WHERE p.permission_key = 'tasks_create';

DELETE FROM permissions WHERE permission_key = 'tasks_create';

-- Usuń inne stare uprawnienia, które już nie są używane
DELETE rp FROM role_permissions rp 
JOIN permissions p ON rp.permission_id = p.permission_id 
WHERE p.permission_key IN ('refresh_data', 'view_assets', 'assign_equipment', 'generate_reports', 'export_reports');

DELETE FROM permissions WHERE permission_key IN ('refresh_data', 'view_assets', 'assign_equipment', 'generate_reports', 'export_reports');

-- ==================================================
-- CZĘŚĆ 2: AKTUALIZACJA/DODANIE NOWYCH UPRAWNIEŃ
-- ==================================================

-- KATEGORIA: inventory
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('view_inventory', 'inventory', 'View Inventory', 'Podgląd inwentarza', 
 'Allows viewing inventory items, equipment lists, and asset information. Users can browse through equipment assigned to departments and view basic inventory statistics.',
 'Pozwala na przeglądanie elementów inwentarza, list sprzętu i informacji o aktywach. Użytkownicy mogą przeglądać sprzęt przypisany do działów i wyświetlać podstawowe statystyki inwentarza.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl), 
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('manage_inventory', 'inventory', 'Manage Inventory', 'Zarządzanie inwentarzem',
 'Full inventory management including adding, editing, deleting equipment, assigning assets to users/departments, processing invoices, and managing equipment lifecycle.',
 'Pełne zarządzanie inwentarzem obejmujące dodawanie, edycję, usuwanie sprzętu, przypisywanie aktywów do użytkowników/działów, przetwarzanie faktur i zarządzanie cyklem życia sprzętu.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

-- KATEGORIA: monitoring
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('view_monitoring', 'monitoring', 'View Monitoring', 'Podgląd monitoringu',
 'Access to monitoring dashboards, system status displays, server health information, and real-time monitoring data from Zabbix and other monitoring systems.',
 'Dostęp do pulpitów monitoringu, wyświetlania statusu systemu, informacji o kondycji serwerów i danych monitoringu w czasie rzeczywistym z Zabbix i innych systemów monitoringu.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

-- KATEGORIA: reports
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('view_reports', 'reports', 'View Reports', 'Podgląd raportów',
 'Ability to view existing reports, browse report archives, and access generated reports from various system modules including inventory, monitoring, and task reports.',
 'Możliwość przeglądania istniejących raportów, przeglądania archiwów raportów i dostępu do wygenerowanych raportów z różnych modułów systemu, w tym raportów inwentarza, monitoringu i zadań.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('manage_reports', 'reports', 'Manage Reports', 'Zarządzanie raportami',
 'Full report management including generating new reports, modifying report parameters, scheduling automated reports, and managing report templates and configurations.',
 'Pełne zarządzanie raportami obejmujące generowanie nowych raportów, modyfikację parametrów raportów, planowanie zautomatyzowanych raportów oraz zarządzanie szablonami i konfiguracjami raportów.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('create_reports', 'reports', 'Create Reports', 'Tworzenie raportów',
 'Permission to create new reports from scratch, design custom report layouts, set up data sources, and configure report parameters for specific business needs.',
 'Uprawnienie do tworzenia nowych raportów od podstaw, projektowania niestandardowych układów raportów, konfigurowania źródeł danych i ustawiania parametrów raportów dla konkretnych potrzeb biznesowych.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('delete_reports', 'reports', 'Delete Reports', 'Usuwanie raportów',
 'Ability to delete reports, clean up old report files, manage report retention policies, and remove obsolete or incorrect reports from the system.',
 'Możliwość usuwania raportów, czyszczenia starych plików raportów, zarządzania politykami przechowywania raportów i usuwania przestarzałych lub niepoprawnych raportów z systemu.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

-- KATEGORIA: system
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('manage_profile', 'system', 'Manage Profile', 'Zarządzanie profilem',
 'Users can manage their own profile settings, update personal information, change passwords, set language preferences, and configure personal dashboard settings.',
 'Użytkownicy mogą zarządzać własnymi ustawieniami profilu, aktualizować informacje osobiste, zmieniać hasła, ustawiać preferencje językowe i konfigurować osobiste ustawienia pulpitu.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('manage_users', 'system', 'Manage Users', 'Zarządzanie użytkownikami',
 'Administrative permission to create, edit, delete user accounts, manage user roles and permissions, reset passwords, and configure user access levels across the system.',
 'Uprawnienie administracyjne do tworzenia, edycji, usuwania kont użytkowników, zarządzania rolami i uprawnieniami użytkowników, resetowania haseł i konfigurowania poziomów dostępu użytkowników w całym systemie.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

-- KATEGORIA: tasks
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('tasks_update', 'tasks', 'Update Tasks', 'Aktualizacja zadań',
 'Permission to modify existing tasks, update task status, change task priorities, edit task descriptions, and modify task assignments and deadlines.',
 'Uprawnienie do modyfikowania istniejących zadań, aktualizowania statusu zadań, zmiany priorytetów zadań, edycji opisów zadań oraz modyfikowania przypisań zadań i terminów.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('tasks_comment', 'tasks', 'Comment on Tasks', 'Komentowanie zadań',
 'Ability to add comments to tasks, participate in task discussions, provide updates on task progress, and communicate with other team members about task-related matters.',
 'Możliwość dodawania komentarzy do zadań, uczestniczenia w dyskusjach o zadaniach, dostarczania aktualizacji postępu zadań i komunikowania się z innymi członkami zespołu w sprawach związanych z zadaniami.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('create_tasks', 'tasks', 'Create Tasks', 'Tworzenie zadań',
 'Permission to create new tasks, set task parameters, assign tasks to users, define task priorities and deadlines, and establish task workflows.',
 'Uprawnienie do tworzenia nowych zadań, ustawiania parametrów zadań, przypisywania zadań użytkownikom, definiowania priorytetów i terminów zadań oraz ustanawiania przepływów pracy zadań.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('tasks_delete', 'tasks', 'Delete Tasks', 'Usuwanie zadań',
 'Ability to delete tasks, remove completed or cancelled tasks from the system, and clean up task databases while maintaining proper audit trails.',
 'Możliwość usuwania zadań, usuwania ukończonych lub anulowanych zadań z systemu oraz czyszczenia baz danych zadań przy zachowaniu właściwych ścieżek audytu.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('tasks_view', 'tasks', 'View Tasks', 'Wyświetlanie zadań',
 'Basic permission to view tasks assigned to the user, browse task lists, check task status, and access task details within their scope of responsibility.',
 'Podstawowe uprawnienie do przeglądania zadań przypisanych użytkownikowi, przeglądania list zadań, sprawdzania statusu zadań i dostępu do szczegółów zadań w zakresie ich odpowiedzialności.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('manage_all_tasks', 'tasks', 'Manage All Tasks', 'Zarządzanie wszystkimi zadaniami',
 'Administrative permission to view and manage all tasks in the system regardless of assignment, oversee project workflows, and coordinate task management across departments.',
 'Uprawnienie administracyjne do przeglądania i zarządzania wszystkimi zadaniami w systemie niezależnie od przypisania, nadzorowania przepływów pracy projektów i koordynowania zarządzania zadaniami między działami.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

-- KATEGORIA: GLPI
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('vnc_connect', 'GLPI', 'VNC Connections', 'Połączenia VNC',
 'Permission to establish VNC connections to remote computers and servers, access remote desktops for maintenance and support purposes through the GLPI interface.',
 'Uprawnienie do nawiązywania połączeń VNC z zdalnymi komputerami i serwerami, dostępu do zdalnych pulpitów w celach konserwacyjnych i wsparcia przez interfejs GLPI.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('view_glpi', 'GLPI', 'View GLPI Equipment', 'Podgląd sprzętu w GLPI',
 'Access to view equipment information from GLPI system, browse computer assets, network devices, servers, and other hardware managed through GLPI inventory system.',
 'Dostęp do przeglądania informacji o sprzęcie z systemu GLPI, przeglądania aktywów komputerowych, urządzeń sieciowych, serwerów i innego sprzętu zarządzanego przez system inwentarza GLPI.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

-- KATEGORIA: Graylog
INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl) VALUES
('view_logs', 'Graylog', 'View Logs', 'Podgląd logów',
 'Access to view system logs through Graylog interface, search through log entries, analyze system events, and monitor application and system activity logs.',
 'Dostęp do przeglądania logów systemowych przez interfejs Graylog, przeszukiwania wpisów logów, analizowania zdarzeń systemowych i monitorowania logów aktywności aplikacji i systemu.')
ON DUPLICATE KEY UPDATE
name_en = VALUES(name_en), name_pl = VALUES(name_pl),
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

-- ==================================================
-- CZĘŚĆ 3: KONFIGURACJA RÓL I PRZYPISANIE UPRAWNIEŃ
-- ==================================================

-- Upewnij się, że wszystkie potrzebne role istnieją
INSERT INTO roles (role_key, description_en, description_pl) VALUES
('admin', 'System Administrator - Full access to all system functions and settings', 'Administrator systemu - Pełny dostęp do wszystkich funkcji i ustawień systemu'),
('manager', 'Department Manager - Extended access for department management', 'Kierownik działu - Rozszerzony dostęp do zarządzania działem'),
('user', 'Standard User - Basic system access for daily operations', 'Użytkownik standardowy - Podstawowy dostęp do systemu dla codziennych operacji'),
('viewer', 'Read-only User - Limited access for viewing information only', 'Użytkownik tylko do odczytu - Ograniczony dostęp tylko do przeglądania informacji')
ON DUPLICATE KEY UPDATE
description_en = VALUES(description_en), description_pl = VALUES(description_pl);

-- Wyczyść istniejące przypisania uprawnień do ról
DELETE FROM role_permissions;

-- ==================================================
-- ROLA: ADMIN - Pełny dostęp do wszystkich funkcji
-- ==================================================
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r, permissions p
WHERE r.role_key = 'admin'
AND p.permission_key IN (
    -- Inventory
    'view_inventory', 'manage_inventory',
    -- Monitoring
    'view_monitoring',
    -- Reports
    'view_reports', 'manage_reports', 'create_reports', 'delete_reports',
    -- System
    'manage_profile', 'manage_users',
    -- Tasks
    'tasks_update', 'tasks_comment', 'create_tasks', 'tasks_delete', 'tasks_view', 'manage_all_tasks',
    -- GLPI
    'vnc_connect', 'view_glpi',
    -- Graylog
    'view_logs'
);

-- ==================================================
-- ROLA: MANAGER - Zarządzanie działem i rozszerzone uprawnienia
-- ==================================================
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r, permissions p
WHERE r.role_key = 'manager'
AND p.permission_key IN (
    -- Inventory
    'view_inventory', 'manage_inventory',
    -- Monitoring
    'view_monitoring',
    -- Reports
    'view_reports', 'manage_reports', 'create_reports',
    -- System
    'manage_profile',
    -- Tasks
    'tasks_update', 'tasks_comment', 'create_tasks', 'tasks_delete', 'tasks_view', 'manage_all_tasks',
    -- GLPI
    'view_glpi',
    -- Graylog
    'view_logs'
);

-- ==================================================
-- ROLA: USER - Standardowy użytkownik z podstawowymi uprawnieniami
-- ==================================================
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r, permissions p
WHERE r.role_key = 'user'
AND p.permission_key IN (
    -- Inventory
    'view_inventory',
    -- Monitoring
    'view_monitoring',
    -- Reports
    'view_reports',
    -- System
    'manage_profile',
    -- Tasks
    'tasks_comment', 'create_tasks', 'tasks_view',
    -- GLPI
    'view_glpi',
    -- Graylog
    'view_logs'
);

-- ==================================================
-- ROLA: VIEWER - Tylko odczyt, ograniczone uprawnienia
-- ==================================================
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r, permissions p
WHERE r.role_key = 'viewer'
AND p.permission_key IN (
    -- Monitoring
    'view_monitoring',
    -- Reports
    'view_reports',
    -- System
    'manage_profile',
    -- Tasks
    'tasks_view',
    -- GLPI
    'view_glpi'
);

-- ==================================================
-- CZĘŚĆ 4: WERYFIKACJA I PODSUMOWANIE
-- ==================================================

-- Wyświetl podsumowanie uprawnień dla każdej roli
SELECT 'PODSUMOWANIE UPRAWNIEŃ PO KATEGORIACH:' as info;

SELECT 
    r.role_key as 'Rola',
    p.category as 'Kategoria',
    GROUP_CONCAT(p.permission_key ORDER BY p.permission_key SEPARATOR ', ') as 'Uprawnienia'
FROM roles r
JOIN role_permissions rp ON r.role_id = rp.role_id
JOIN permissions p ON rp.permission_id = p.permission_id
GROUP BY r.role_key, p.category
ORDER BY 
    FIELD(r.role_key, 'admin', 'manager', 'user', 'viewer'),
    FIELD(p.category, 'system', 'inventory', 'tasks', 'reports', 'monitoring', 'GLPI', 'Graylog');

-- Wyświetl liczbę uprawnień dla każdej roli
SELECT 'LICZBA UPRAWNIEŃ DLA KAŻDEJ ROLI:' as info;

SELECT 
    r.role_key as 'Rola',
    r.description_pl as 'Opis',
    COUNT(rp.permission_id) as 'Liczba_uprawnień'
FROM roles r
LEFT JOIN role_permissions rp ON r.role_id = rp.role_id
GROUP BY r.role_key, r.description_pl
ORDER BY FIELD(r.role_key, 'admin', 'manager', 'user', 'viewer');

-- Wyświetl wszystkie uprawnienia z opisami
SELECT 'WSZYSTKIE UPRAWNIENIA Z OPISAMI:' as info;

SELECT 
    p.category as 'Kategoria',
    p.permission_key as 'Klucz_uprawnienia',
    p.name_pl as 'Nazwa',
    p.description_pl as 'Opis'
FROM permissions p
ORDER BY 
    FIELD(p.category, 'system', 'inventory', 'tasks', 'reports', 'monitoring', 'GLPI', 'Graylog'),
    p.permission_key;

COMMIT;

SELECT 'AKTUALIZACJA STRUKTURY UPRAWNIEŃ ZAKOŃCZONA POMYŚLNIE!' as status;

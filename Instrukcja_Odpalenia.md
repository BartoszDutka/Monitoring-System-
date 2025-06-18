## 📋 **KOMPLETNA INSTRUKCJA URUCHOMIENIA SYSTEMU MONITORINGU**

### ⚙️ **WYMAGANIA SYSTEMOWE:**
- **Python 3.8+** (zalecany Python 3.10+)
- **Node.js** (do instalacji Firebase)
- **MySQL Server 5.7+** (lub MariaDB)
- **wkhtmltopdf** (opcjonalnie, do generowania PDF)

### 🗄️ **KONFIGURACJA BAZY DANYCH:**
```sql
-- 1. Utwórz bazę danych MySQL
CREATE DATABASE monitoring_system;
CREATE USER 'root'@'localhost' IDENTIFIED BY 'root';
GRANT ALL PRIVILEGES ON monitoring_system.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

### 🔧 **KONFIGURACJA APLIKACJI:**

#### 1. **Skopiuj plik konfiguracyjny:**
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

#### 2. **Skonfiguruj plik .env** (dostosuj do swoich systemów):
```bash
# Zabbix Configuration
ZABBIX_URL=https://twoj-zabbix.com/zabbix/api_jsonrpc.php
ZABBIX_TOKEN=twoj_token_zabbix

# Graylog Configuration  
GRAYLOG_URL=http://twoj-graylog.com:9000
GRAYLOG_USERNAME=admin
GRAYLOG_PASSWORD=twoje_haslo

# GLPI Configuration
GLPI_URL=http://twoj-glpi.com/glpi
GLPI_USER_TOKEN=twoj_user_token
GLPI_APP_TOKEN=twoj_app_token

# LDAP Configuration (opcjonalne)
LDAP_SERVER=twoj.ldap.server
LDAP_PORT=389
LDAP_BASE_DN=DC=example,DC=com
LDAP_DOMAIN=example.com
LDAP_SERVICE_USER=ldap_user
LDAP_SERVICE_PASSWORD=ldap_password
```

### 🚀 **URUCHOMIENIE PROJEKTU:**

#### 1. **Przygotuj środowisko:**
```bash
# Utwórz środowisko wirtualne
python -m venv venv

# Aktywuj środowisko
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate
```

#### 2. **Zainstaluj zależności:**
```bash
# Python dependencies
pip install -r requirements.txt

# JavaScript dependencies (Firebase)
npm install
```

#### 3. **Uruchom aplikację:**
```bash
python app.py
```

### 🌐 **DOSTĘP DO APLIKACJI:**
- **URL:** http://localhost:5000
- **Domyślne konto admin** zostanie utworzone automatycznie przy pierwszym uruchomieniu

---

## ✅ **AUTOMATYCZNE TWORZENIE FOLDERÓW:**

**TAK!** Wszystkie niezbędne foldery tworzą się automatycznie:
- `static/avatars/` - avatary użytkowników  
- `static/attachments/` - załączniki zadań
- `data/` - dane aplikacji
- `modules/reports/` - generowane raporty

**Kod automatycznie tworzy foldery podczas startu aplikacji.**

---

## 🛠️ **OPCJONALNE ULEPSZENIA:**

### PDF Generation (dla raportów):
```bash
# Windows - pobierz i zainstaluj wkhtmltopdf
# https://wkhtmltopdf.org/downloads.html

# Ubuntu/Debian:
sudo apt-get install wkhtmltopdf

# MacOS:
brew install wkhtmltopdf
```

---

## 🔍 **ROZWIĄZYWANIE PROBLEMÓW:**

### Problem z MySQL:
```bash
# Sprawdź czy MySQL działa
mysql --version
mysql -u root -p

# Jeśli nie ma MySQL - zainstaluj:
# Windows: https://dev.mysql.com/downloads/installer/
# Ubuntu: sudo apt install mysql-server
# MacOS: brew install mysql
```

### Problem z Python pakietami:
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Zainstaluj ponownie
pip install -r requirements.txt --force-reinstall
```

### Problem z uprawnieniami Windows:
```bash
# Uruchom PowerShell jako Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📋 **DANE TESTOWE:**
Po pierwszym uruchomieniu system utworzy:
- Podstawowe role użytkowników
- Domyślne uprawnienia  
- Przykładowe departamenty
- Strukturę bazy danych

**System jest gotowy do pracy od razu po uruchomieniu!**
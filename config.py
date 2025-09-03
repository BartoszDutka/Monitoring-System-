import os
from dotenv import load_dotenv

# Ładowanie zmiennych środowiskowych z pliku .env
load_dotenv()

# Konfiguracja Zabbix
ZABBIX_URL = os.getenv("ZABBIX_URL")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN")

# Konfiguracja Graylog
GRAYLOG_URL = os.getenv("GRAYLOG_URL")
GRAYLOG_USERNAME = os.getenv("GRAYLOG_USERNAME")
GRAYLOG_PASSWORD = os.getenv("GRAYLOG_PASSWORD")

# Konfiguracja GLPI
GLPI_URL = os.getenv("GLPI_URL")
GLPI_USER_TOKEN = os.getenv("GLPI_USER_TOKEN")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")

# Konfiguracja LDAP
LDAP_SERVER = os.getenv("LDAP_SERVER")
LDAP_PORT = int(os.getenv("LDAP_PORT", 389))
LDAP_BASE_DN = os.getenv("LDAP_BASE_DN")
LDAP_DOMAIN = os.getenv("LDAP_DOMAIN")
LDAP_SERVICE_USER = os.getenv("LDAP_SERVICE_USER")
LDAP_SERVICE_PASSWORD = os.getenv("LDAP_SERVICE_PASSWORD")




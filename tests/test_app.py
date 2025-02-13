import sys
import os

# Dodanie ścieżki głównego katalogu projektu do sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.zabbix import get_hosts
from modules.graylog import get_logs

def test_zabbix():
    print(get_hosts())

def test_graylog():
    print(get_logs())

# Uruchamianie testów
if __name__ == "__main__":
    test_zabbix()
    test_graylog()

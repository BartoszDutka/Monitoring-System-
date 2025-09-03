"""
Test configuration and fixtures for the monitoring system integration tests.
"""
import pytest
import json
import os
import sys
from unittest.mock import patch, Mock

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import app after setting path
from app import app
from modules.external.zabbix import get_hosts
from modules.external.graylog import get_logs
from modules.external.glpi import get_glpi_data


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['CACHE_TYPE'] = 'SimpleCache'  # Use simple cache for testing
    
    with app.test_client() as client:
        with app.app_context():
            # Clear cache before each test
            from app import cache
            cache.clear()
            
            # Mock authentication for tests
            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['username'] = 'test_user'
                sess['user_info'] = {
                    'username': 'test_user',
                    'role': 'admin',
                    'permissions': ['view_monitoring', 'view_logs', 'view_glpi', 'vnc_connect']
                }
                sess['user_permissions'] = ['view_monitoring', 'view_logs', 'view_glpi', 'vnc_connect']
            yield client


@pytest.fixture
def mock_zabbix_response():
    """Mock successful Zabbix API response."""
    return {
        "jsonrpc": "2.0",
        "result": [
            {
                "hostid": "10001",
                "name": "test-server-01",
                "status": "0",
                "interfaces": [
                    {
                        "ip": "192.168.1.100",
                        "type": "1",
                        "available": "1"
                    }
                ],
                "items": [
                    {
                        "name": "CPU utilization",
                        "key_": "system.cpu.util",
                        "lastvalue": "25.5",
                        "units": "%"
                    },
                    {
                        "name": "Total memory",
                        "key_": "vm.memory.size[total]",
                        "lastvalue": "8589934592",
                        "units": "B"
                    }
                ],
                "triggers": [
                    {
                        "description": "High CPU usage",
                        "status": "0",
                        "state": "1",
                        "lastchange": "1625097600"
                    }
                ]
            }
        ],
        "id": 1
    }


@pytest.fixture
def mock_graylog_response():
    """Mock successful Graylog API response."""
    return {
        "messages": [
            {
                "id": "msg1",
                "timestamp": "2024-06-07T10:00:00.000Z",
                "level": 3,
                "message": "Test log message",
                "source": "test-app",
                "fields": {
                    "severity": "INFO",
                    "category": "APPLICATION",
                    "host": "test-server"
                }
            },
            {
                "id": "msg2", 
                "timestamp": "2024-06-07T10:01:00.000Z",
                "level": 1,
                "message": "Error occurred",
                "source": "test-app",
                "fields": {
                    "severity": "ERROR",
                    "category": "SYSTEM",
                    "host": "test-server"
                }
            }
        ],
        "total_results": 2
    }


@pytest.fixture
def mock_glpi_response():
    """Mock successful GLPI API response."""
    return {
        "computers": [
            {
                "id": 1,
                "name": "KS-WORKSTATION-01",
                "serial": "SN123456",
                "computermodels_id": 1,
                "manufacturers_id": 1,
                "location_name": "Office A",
                "ip_address": "192.168.1.101"
            },
            {
                "id": 2,
                "name": "SRV-DATABASE-01", 
                "serial": "SN789012",
                "computermodels_id": 2,
                "manufacturers_id": 1,
                "location_name": "Server Room",
                "ip_address": "192.168.1.201"
            }
        ],
        "categorized": {
            "workstations": [
                {
                    "id": 1,
                    "name": "KS-WORKSTATION-01",
                    "serial": "SN123456"
                }
            ],
            "terminals": [],
            "servers": [
                {
                    "id": 2,
                    "name": "SRV-DATABASE-01",
                    "serial": "SN789012"
                }
            ],
            "other": []
        },
        "network_devices": [],
        "printers": [],
        "monitors": [],
        "racks": [],
        "total_count": 2,
        "category_counts": {
            "workstations": 1,
            "terminals": 0,
            "servers": 1,
            "network": 0,
            "printers": 0,
            "monitors": 0,
            "racks": 0,
            "other": 0
        }
    }


@pytest.fixture
def mock_timeout_error():
    """Mock timeout error response."""
    from requests.exceptions import Timeout
    return Timeout("Connection timed out")


@pytest.fixture
def mock_auth_error():
    """Mock authentication error response."""
    response = Mock()
    response.status_code = 401
    response.json.return_value = {"error": "Authentication failed"}
    return response


@pytest.fixture
def mock_forbidden_error():
    """Mock forbidden error response."""
    response = Mock()
    response.status_code = 403
    response.json.return_value = {"error": "Access forbidden"}
    return response


@pytest.fixture
def mock_glpi_data():
    """Mock comprehensive GLPI asset data for testing."""
    return {
        "computers": [
            {
                "id": 1,
                "name": "KS-WORKSTATION-01",
                "serial": "SN123456",
                "computermodels_id": 1,
                "manufacturers_id": 1,
                "location_name": "Office A",
                "ip_address": "192.168.1.101",
                "mac_address": "00:11:22:33:44:55",
                "status": "active",
                "type": "workstation"
            },
            {
                "id": 2,
                "name": "KS-WORKSTATION-02",
                "serial": "SN123457",
                "computermodels_id": 1,
                "manufacturers_id": 1,
                "location_name": "Office A",
                "ip_address": "192.168.1.102",
                "mac_address": "00:11:22:33:44:56",
                "status": "active",
                "type": "workstation"
            },
            {
                "id": 3,
                "name": "KT-TERMINAL-01",
                "serial": "SN789012",
                "computermodels_id": 2,
                "manufacturers_id": 1,
                "location_name": "Office B",
                "ip_address": "192.168.1.103",
                "mac_address": "00:11:22:33:44:57",
                "status": "active",
                "type": "terminal"
            },
            {
                "id": 4,
                "name": "SRV-DATABASE-01",
                "serial": "SN345678",
                "computermodels_id": 3,
                "manufacturers_id": 2,
                "location_name": "Server Room",
                "ip_address": "192.168.1.201",
                "mac_address": "00:11:22:33:44:58",
                "status": "active",
                "type": "server"
            }
        ],
        "categorized": {
            "workstations": [
                {
                    "id": 1,
                    "name": "KS-WORKSTATION-01",
                    "serial": "SN123456",
                    "location_name": "Office A",
                    "ip_address": "192.168.1.101"
                },
                {
                    "id": 2,
                    "name": "KS-WORKSTATION-02",
                    "serial": "SN123457",
                    "location_name": "Office A",
                    "ip_address": "192.168.1.102"
                }
            ],
            "terminals": [
                {
                    "id": 3,
                    "name": "KT-TERMINAL-01",
                    "serial": "SN789012",
                    "location_name": "Office B",
                    "ip_address": "192.168.1.103"
                }
            ],
            "servers": [
                {
                    "id": 4,
                    "name": "SRV-DATABASE-01",
                    "serial": "SN345678",
                    "location_name": "Server Room",
                    "ip_address": "192.168.1.201"
                }
            ],
            "other": []
        },
        "network_devices": [
            {
                "id": 5,
                "name": "SWITCH-CORE-01",
                "serial": "NET001",
                "type": "network",
                "location_name": "Server Room",
                "ip_address": "192.168.1.250"
            }
        ],
        "printers": [
            {
                "id": 6,
                "name": "PRINTER-OFFICE-01",
                "serial": "PRT001",
                "type": "printer",
                "location_name": "Office A",
                "ip_address": "192.168.1.150"
            }
        ],
        "monitors": [],
        "racks": [],
        "total_count": 7,
        "category_counts": {
            "workstations": 2,
            "terminals": 1,
            "servers": 1,
            "other": 0,
            "network": 1,
            "printers": 1,
            "monitors": 0,
            "racks": 0
        }
    }

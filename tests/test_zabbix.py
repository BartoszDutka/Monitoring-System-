"""
Integration tests for Zabbix API endpoints.
Tests the /api/zabbix/refresh endpoint with various scenarios.
"""
import pytest
import json
from unittest.mock import patch, Mock
import requests
from requests.exceptions import Timeout, ConnectionError


class TestZabbixAPI:
    """Test cases for Zabbix API integration."""

    def test_zabbix_hosts_success(self, client, mock_zabbix_response):
        """Test successful retrieval of Zabbix hosts."""
        with patch('modules.external.zabbix.requests.post') as mock_post:
            # Configure mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_zabbix_response
            mock_post.return_value = mock_response
            
            # Make request to API endpoint
            response = client.get('/api/zabbix/refresh')
            
            # Assertions
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify response structure
            assert 'result' in data
            assert len(data['result']) == 1
            
            host = data['result'][0]
            assert host['hostid'] == "10001"
            assert host['name'] == "test-server-01"
            assert host['availability'] == 'Available'
            assert 'metrics' in host
            assert 'alerts' in host
            
            # Verify metrics are processed
            assert 'cpu' in host['metrics']
            assert 'memory' in host['metrics']
            
            # Verify API was called with correct parameters
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]['json']['method'] == 'host.get'
            assert 'auth' in call_args[1]['json']

    def test_zabbix_hosts_unauthorized(self, client, mock_auth_error):
        """Test Zabbix API with invalid authentication token."""
        with patch('modules.external.zabbix.requests.post') as mock_post:
            mock_post.return_value = mock_auth_error
            
            response = client.get('/api/zabbix/refresh')
            
            # Should still return 200 but with error in data
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Should contain error information
            assert 'error' in data or 'result' in data
            
    def test_zabbix_hosts_forbidden(self, client, mock_forbidden_error):
        """Test Zabbix API with insufficient permissions."""
        with patch('modules.external.zabbix.requests.post') as mock_post:
            mock_post.return_value = mock_forbidden_error
            
            response = client.get('/api/zabbix/refresh')
            
            # Should still return 200 but with error in data
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Should handle the error gracefully
            assert 'error' in data or 'result' in data

    def test_zabbix_hosts_malformed_host_data(self, client):
        """Test Zabbix API with malformed host data."""
        malformed_response = {
            "jsonrpc": "2.0",
            "result": [
                {
                    "hostid": "10001",
                    # Missing required fields like 'name'
                    "status": "0"
                }
            ],
            "id": 1
        }
        
        with patch('modules.external.zabbix.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = malformed_response
            mock_post.return_value = mock_response
            
            response = client.get('/api/zabbix/refresh')
            
            # Should handle gracefully
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'result' in data

    def test_zabbix_hosts_data_format_validation(self, client, mock_zabbix_response):
        """Test that Zabbix host data conforms to expected format."""
        with patch('modules.external.zabbix.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_zabbix_response
            mock_post.return_value = mock_response
            
            response = client.get('/api/zabbix/refresh')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Validate data format
            assert isinstance(data, dict)
            assert 'result' in data
            assert isinstance(data['result'], list)
            
            if data['result']:
                host = data['result'][0]
                
                # Required fields
                assert 'hostid' in host
                assert 'name' in host
                assert 'availability' in host
                
                # Check metrics structure
                if 'metrics' in host:
                    metrics = host['metrics']
                    assert isinstance(metrics, dict)
                    # Common metric fields
                    expected_metrics = ['cpu', 'memory', 'disk', 'network', 'ping', 'uptime']
                    for metric in expected_metrics:
                        assert metric in metrics
                
                # Check alerts structure
                if 'alerts' in host:
                    alerts = host['alerts']
                    assert isinstance(alerts, list)
                    for alert in alerts:
                        assert isinstance(alert, dict)
                        assert 'description' in alert

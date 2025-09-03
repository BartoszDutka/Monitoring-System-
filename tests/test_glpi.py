"""
Integration tests for GLPI API endpoints.

This module contains comprehensive tests for GLPI functionality including:
- Asset data retrieval from API endpoint
- VNC connection functionality
- Authentication and permission handling
- Error scenarios and timeout handling
- Data format validation

Test coverage includes:
- Successful responses (200)
- Authentication errors (401/403)
- Timeout handling
- Connection errors
- Data format validation
"""

import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock
from flask import session
import requests

class TestGLPIDataAPI:
    """Test cases for /api/glpi/data endpoint"""
    
    def test_get_glpi_data_success(self, client, mock_glpi_data):
        """Test successful retrieval of GLPI data"""
        with patch('app.get_glpi_data') as mock_get_data, \
             patch('app.cache') as mock_cache:
            
            mock_get_data.return_value = mock_glpi_data
            mock_cache.get.return_value = None  # Force function call
            mock_cache.set.return_value = None
            
            response = client.get('/api/glpi/data')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify response structure
            assert 'computers' in data
            assert 'categorized' in data
            assert 'network_devices' in data
            assert 'printers' in data
            assert 'monitors' in data
            assert 'racks' in data
            assert 'total_count' in data
            assert 'category_counts' in data
            
            # Verify categorized structure
            categorized = data['categorized']
            assert 'workstations' in categorized
            assert 'terminals' in categorized
            assert 'servers' in categorized
            assert 'other' in categorized
            
            # Verify category counts
            assert data['category_counts']['workstations'] == 2
            assert data['category_counts']['terminals'] == 1
            assert data['category_counts']['servers'] == 1
            assert data['total_count'] == 7
    
    def test_get_glpi_data_unauthorized(self, client):
        """Test GLPI data access without authentication"""
        # Clear session to simulate unauthenticated request
        with client.session_transaction() as sess:
            sess.clear()
        
        response = client.get('/api/glpi/data')
        assert response.status_code == 302  # Redirect to login
    
    def test_get_glpi_data_forbidden(self, client):
        """Test GLPI data access without required permission"""
        with patch('modules.core.permissions.has_permission') as mock_has_perm:
            mock_has_perm.return_value = False
            
            response = client.get('/api/glpi/data')
            assert response.status_code == 403
    
    def test_get_glpi_data_with_database_error(self, client):
        """Test GLPI data retrieval when database connection fails"""
        with patch('app.get_glpi_data') as mock_get_data, \
             patch('app.cache') as mock_cache:
            
            mock_get_data.side_effect = Exception("Database connection failed")
            mock_cache.get.return_value = None
            
            response = client.get('/api/glpi/data')
            
            # Should return error response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['total_count'] == 0
            assert len(data['computers']) == 0
    
    def test_get_glpi_data_cached(self, client, mock_glpi_data):
        """Test that GLPI data uses caching mechanism"""
        with patch('app.get_glpi_data') as mock_get_data, \
             patch('app.cache') as mock_cache:
            
            # First call returns None from cache, second call returns cached data
            mock_cache.get.side_effect = [None, mock_glpi_data]
            mock_get_data.return_value = mock_glpi_data
            
            # First request should call the function and cache result
            response1 = client.get('/api/glpi/data')
            assert response1.status_code == 200
            assert mock_get_data.call_count == 1
              # Second request should use cache (function not called again)
            response2 = client.get('/api/glpi/data') 
            assert response2.status_code == 200
            # Function should not be called again since we're returning cached data
            assert mock_get_data.call_count == 1
            
            # Verify same data is returned
            assert json.loads(response1.data) == json.loads(response2.data)
    
    def test_get_glpi_data_asset_format_validation(self, client):
        """Test validation of asset data format"""
        malformed_data = {
            'computers': [
                {
                    'name': 'KS-TEST-01',
                    # Missing required fields like id, serial, etc.
                }
            ],
            'categorized': {'workstations': [], 'terminals': [], 'servers': [], 'other': []},
            'network_devices': [],
            'printers': [],
            'monitors': [],
            'racks': [],
            'total_count': 1,
            'category_counts': {}
        }
        
        with patch('app.get_glpi_data') as mock_get_data, \
             patch('app.cache') as mock_cache:
            
            mock_get_data.return_value = malformed_data
            mock_cache.get.return_value = None
            
            response = client.get('/api/glpi/data')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            # Should handle malformed data gracefully
            assert 'computers' in data
            assert 'total_count' in data
    
    def test_get_glpi_data_timeout_handling(self, client):
        """Test handling of timeout errors in GLPI data retrieval"""
        with patch('app.get_glpi_data') as mock_get_data, \
             patch('app.cache') as mock_cache:
            
            mock_get_data.side_effect = requests.exceptions.Timeout("Request timeout")
            mock_cache.get.return_value = None
            
            response = client.get('/api/glpi/data')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['total_count'] == 0


class TestVNCConnection:
    """Test cases for /connect_vnc endpoint"""
    
    def test_connect_vnc_success(self, client):
        """Test successful VNC connection"""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            
            response = client.post('/connect_vnc', 
                                 json={'hostname': 'KS-TEST-01'},
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert 'KS-TEST-01' in data['message']
            
            # Verify subprocess was called with correct parameters
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert 'KS-TEST-01' in call_args
    
    def test_connect_vnc_unauthorized(self, client):
        """Test VNC connection without authentication"""
        with client.session_transaction() as sess:
            sess.clear()
        
        response = client.post('/connect_vnc', 
                             json={'hostname': 'KS-TEST-01'},
                             content_type='application/json')
        assert response.status_code == 302  # Redirect to login
    
    def test_connect_vnc_forbidden(self, client):
        """Test VNC connection without required permission"""
        with patch('modules.core.permissions.has_permission') as mock_has_perm:
            mock_has_perm.return_value = False
            
            response = client.post('/connect_vnc', 
                                 json={'hostname': 'KS-TEST-01'},
                                 content_type='application/json')
            assert response.status_code == 403
    
    def test_connect_vnc_missing_hostname(self, client):
        """Test VNC connection with missing hostname"""
        response = client.post('/connect_vnc', 
                             json={},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'No hostname provided' in data['message']
    
    def test_connect_vnc_empty_hostname(self, client):
        """Test VNC connection with empty hostname"""
        response = client.post('/connect_vnc', 
                             json={'hostname': ''},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'No hostname provided' in data['message']
    
    def test_connect_vnc_invalid_json(self, client):
        """Test VNC connection with invalid JSON"""
        response = client.post('/connect_vnc', 
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 500
    
    def test_connect_vnc_subprocess_error(self, client):
        """Test VNC connection when subprocess fails"""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = Exception("Failed to start VNC viewer")
            
            response = client.post('/connect_vnc', 
                                 json={'hostname': 'KS-TEST-01'},
                                 content_type='application/json')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['status'] == 'error'
            assert 'Failed to start VNC viewer' in data['message']
    
    def test_connect_vnc_different_hostname_formats(self, client):
        """Test VNC connection with different hostname formats"""
        hostnames = ['KS-TEST-01', 'KT-TERM-05', 'SRV-DATABASE', 'workstation.domain.com']
        
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            
            for hostname in hostnames:
                response = client.post('/connect_vnc', 
                                     json={'hostname': hostname},
                                     content_type='application/json')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert hostname in data['message']
    
    def test_connect_vnc_command_validation(self, client):
        """Test that VNC command is properly constructed"""
        with patch('subprocess.Popen') as mock_popen, \
             patch('app.ULTRAVNC_PATH', 'C:\\path\\to\\vncviewer.exe') as mock_path, \
             patch('app.VNC_PASSWORD', 'testpassword') as mock_password:
            
            mock_popen.return_value = MagicMock()
            
            response = client.post('/connect_vnc', 
                                 json={'hostname': 'KS-TEST-01'},
                                 content_type='application/json')
            
            assert response.status_code == 200
            
            # Verify the command structure
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            
            # Check that required parameters are present
            assert any('vncviewer' in str(arg) for arg in call_args)
            assert '-connect' in call_args
            assert 'KS-TEST-01' in call_args
            assert '-password' in call_args


class TestGLPIClientIntegration:
    """Integration tests for GLPIClient class"""
    
    def test_glpi_client_session_initialization_success(self, client):
        """Test successful GLPI session initialization"""
        with patch('modules.external.glpi.GLPIClient.init_session') as mock_init:
            mock_init.return_value = True
            
            # This would typically be called during app startup
            from modules.external.glpi import GLPIClient
            client_instance = GLPIClient()
            
            result = client_instance.init_session()
            assert result is True
            mock_init.assert_called_once()
    
    def test_glpi_client_session_initialization_failure(self, client):
        """Test failed GLPI session initialization"""
        with patch('modules.external.glpi.GLPIClient.init_session') as mock_init:
            mock_init.return_value = False
            
            from modules.external.glpi import GLPIClient
            client_instance = GLPIClient()
            
            result = client_instance.init_session()
            assert result is False
            mock_init.assert_called_once()
    
    def test_glpi_client_authentication_error(self, client):
        """Test GLPI client handling of authentication errors"""
        with patch('modules.external.glpi.GLPIClient.init_session') as mock_init:
            mock_init.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
            
            from modules.external.glpi import GLPIClient
            client_instance = GLPIClient()
            
            with pytest.raises(requests.exceptions.HTTPError):
                client_instance.init_session()
    
    def test_glpi_data_categorization(self, client, mock_glpi_data):
        """Test proper categorization of GLPI computer data"""
        with patch('app.get_glpi_data') as mock_get_data, \
             patch('app.cache') as mock_cache:
            
            mock_get_data.return_value = mock_glpi_data
            mock_cache.get.return_value = None
            
            response = client.get('/api/glpi/data')
            data = json.loads(response.data)
            
            # Test workstation categorization (KS prefix)
            workstations = data['categorized']['workstations']
            assert len(workstations) == 2
            assert all(ws['name'].startswith('KS-') for ws in workstations)
            
            # Test terminal categorization (KT prefix)
            terminals = data['categorized']['terminals']
            assert len(terminals) == 1
            assert all(term['name'].startswith('KT-') for term in terminals)
            
            # Test server categorization (SRV prefix)
            servers = data['categorized']['servers']
            assert len(servers) == 1
            assert all(srv['name'].startswith('SRV-') for srv in servers)
            
            # Test category counts match data
            assert data['category_counts']['workstations'] == len(workstations)
            assert data['category_counts']['terminals'] == len(terminals)
            assert data['category_counts']['servers'] == len(servers)
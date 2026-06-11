def test_health_check(client):
    """Test the /api/health endpoint returns 200 and expected JSON structure."""
    response = client.get('/api/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['version'] == '2.0.0'
    assert data['data']['status'] == 'healthy'
    assert data['message'] == 'Skolaz API is running'

def test_home_page(client):
    """Test the home page loads successfully."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Skolaz' in response.data
    assert b'Global Admissions' in response.data

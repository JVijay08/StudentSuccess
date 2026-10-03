from tests.account_helpers import create, csrf


def test_login_keeps_same_origin_forms_usable(app):
    client = app.test_client()
    credentials, _ = create(client)
    client.post('/logout')
    response = client.get('/login')
    assert response.headers['Referrer-Policy'] == 'same-origin'
    response = client.post('/login', data={**credentials, 'csrf_token': csrf(client)},
                           headers={'Origin': 'http://localhost', 'Sec-Fetch-Site': 'same-origin'})
    assert response.status_code == 302
    assert response.location.endswith('/dashboard')


def test_login_still_rejects_cross_site_and_invalid_token(app):
    client = app.test_client()
    credentials, _ = create(client)
    client.post('/logout')
    token = csrf(client)
    assert client.post('/login', data={**credentials, 'csrf_token': token}, headers={
        'Origin': 'https://attacker.example', 'Sec-Fetch-Site': 'cross-site'}).status_code == 400
    assert client.post('/login', data={**credentials, 'csrf_token': 'invalid'}, headers={
        'Origin': 'http://localhost', 'Sec-Fetch-Site': 'same-origin'}).status_code == 400
    with client.session_transaction() as session:
        assert 'user_id' not in session

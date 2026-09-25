import secrets

PASSWORD = 'quiet notebooks beside windows'


def csrf(client, path='/login'):
    client.get(path)
    with client.session_transaction() as session:
        return session['access_csrf']


def register(client, username=None, **extra):
    credentials = dict(username=username or 'learner-' + secrets.token_hex(4), password=PASSWORD)
    response = client.post('/register', data={**credentials, 'confirm_password': PASSWORD,
        'understood': 'yes', 'csrf_token': csrf(client, '/register'), **extra})
    return credentials, response


def setup(client, **extra):
    return client.post('/onboarding', data={'csrf_token': csrf(client, '/onboarding'),
        'nonpersonal_confirmed':'yes', 'academic_context':'high_school', 'grade':'11',
        'study_hours':'10', 'timezone_name':'America/New_York', **extra})


def create(client):
    credentials, response = register(client)
    assert response.status_code == 302
    assert setup(client).status_code == 302
    return credentials, response


def login(client, credentials):
    return client.post('/login', data={**credentials, 'csrf_token':csrf(client)})

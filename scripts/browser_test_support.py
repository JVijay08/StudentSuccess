"""Seed a disposable practice account through the normal CSRF-protected form."""
import re


def start_demo(client, origin=''):
    response = client.get(origin + '/login')
    html = response.get_data(as_text=True) if hasattr(response, 'get_data') else response.text()
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    form = {'csrf_token': token}
    if hasattr(response, 'get_data'):
        return client.post(origin + '/demo', data=form)
    return client.post(origin + '/demo', form=form)

import json
import re
from xml.etree import ElementTree
from routes.seo_routes import PAGES


def test_public_metadata_and_canonical_host(app):
    client=app.test_client()
    titles=[]
    for path in ['/', '/features', '/updates']:
        response=client.get(path+'?campaign=example',base_url='https://untrusted.example')
        html=response.get_data(as_text=True)
        assert response.status_code==200
        assert 'noindex' not in response.headers.get('X-Robots-Tag','')
        assert html.count('name="description"')==1
        assert html.count('rel="canonical"')==1
        assert f'href="https://studentsuccess.onrender.com{path}"' in html
        assert 'property="og:image"' in html and 'name="twitter:card"' in html
        titles.append(re.search(r'<title>(.*?)</title>',html).group(1))
    assert len(set(titles))==3
    image = re.search(r'property="og:image" content="([^"]+)"', html).group(1)
    assert image == 'https://studentsuccess.onrender.com/static/images/studentsuccess-social-preview.png'
    assert 'property="og:image:alt" content="StudentSuccess — Plan less. Start sooner."' in html
    preview = client.get('/static/images/studentsuccess-social-preview.png')
    assert preview.status_code == 200
    assert preview.mimetype == 'image/png'
    html=client.get('/').get_data(as_text=True)
    schema=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',html,re.S).group(1))
    assert schema['@graph'][0]['@type']=='WebSite'
    assert 'aggregateRating' not in str(schema)


def test_sitemap_only_public_pages_and_robots(app):
    client=app.test_client()
    response=client.get('/sitemap.xml')
    assert response.mimetype=='application/xml'
    root=ElementTree.fromstring(response.data)
    locations=[node.text for node in root.findall('.//{*}loc')]
    assert set(locations)=={'https://studentsuccess.onrender.com'+p for p in ['/','/features','/updates']}
    robots=client.get('/robots.txt')
    assert robots.mimetype=='text/plain'
    assert b'Sitemap: https://studentsuccess.onrender.com/sitemap.xml' in robots.data


def test_private_auth_export_errors_and_json_not_indexable(app):
    client=app.test_client()
    for path in ['/login','/register','/tasks','/settings/calendar.ics','/time','/not-a-page','/planner/catalogs.json']:
        response=client.get(path)
        assert 'noindex' in response.headers.get('X-Robots-Tag',''),path
    client.post('/demo')
    for path in ['/dashboard','/tasks','/settings/export','/updates']:
        response=client.get(path)
        assert 'noindex' in response.headers.get('X-Robots-Tag',''),path
    assert client.get('/sitemap.xml').status_code==200


def test_custom_domain_and_optional_verification(app):
    app.config['PUBLIC_SITE_URL']='https://planner.example'
    app.config['GOOGLE_SITE_VERIFICATION']='verification-example'
    response=app.test_client().get('/')
    assert b'rel="canonical" href="https://planner.example/"' in response.data
    assert b'name="google-site-verification" content="verification-example"' in response.data

"""Public discovery metadata; private workspace URLs are never in the sitemap."""
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring
from flask import Blueprint, Response, current_app, render_template, request, session, url_for

seo_bp=Blueprint('seo',__name__)
PAGES={
    'main.home':('StudentSuccess | Student Planner for Tasks & Courses',
        'Plan assignments, break projects into subtasks, and organize high-school, dual-enrollment, and college courses. Try the interactive StudentSuccess tutorial.'),
    'seo.features':('Student Planner Features & FAQ | StudentSuccess',
        'Explore task prioritization, repeating assignments, course planning, dual enrollment, and Google Calendar deadline copies in StudentSuccess.'),
    'main.updates':('StudentSuccess Updates | Planner Features & Fixes',
        'See the latest StudentSuccess improvements to task planning, course selection, accessibility, and the interactive tutorial.'),
}


def public_url(path):
    origin=current_app.config['PUBLIC_SITE_URL']
    parsed=urlsplit(origin)
    if parsed.scheme not in {'http','https'} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'','/'}:
        raise ValueError('PUBLIC_SITE_URL must be an http(s) origin without a path, query or credentials.')
    return origin.rstrip('/')+path


@seo_bp.app_context_processor
def metadata():
    values=PAGES.get(request.endpoint)
    if not values:
        return {'seo':None}
    title,description=values
    canonical=public_url(url_for(request.endpoint))
    schema=None
    if request.endpoint=='main.home':
        schema={'@context':'https://schema.org','@graph':[
            {'@type':'WebSite','@id':public_url('/#website'),'name':'StudentSuccess','url':public_url('/')},
            {'@type':'WebApplication','name':'StudentSuccess','url':public_url('/'),
             'applicationCategory':'EducationalApplication','operatingSystem':'Any',
             'description':description,'browserRequirements':'A modern web browser'}]}
    return {'seo':dict(title=title,description=description,canonical=canonical,
        image=public_url('/static/images/studentsuccess-social-preview.png'),schema=schema)}


@seo_bp.after_app_request
def indexing_policy(response):
    public=request.endpoint in PAGES and response.status_code==200 and request.method in {'GET','HEAD'} and not session.get('user_id')
    infrastructure=request.endpoint in {'static','seo.robots','seo.sitemap'} and response.status_code==200
    if not public and not infrastructure:
        response.headers['X-Robots-Tag']='noindex, nofollow'
    return response


@seo_bp.get('/features')
def features():
    return render_template('features.html')


@seo_bp.get('/robots.txt')
def robots():
    # Allow crawling so engines can read noindex headers. Authentication protects data.
    return Response('User-agent: *\nAllow: /\n\nSitemap: '+public_url('/sitemap.xml')+'\n',mimetype='text/plain')


@seo_bp.get('/sitemap.xml')
def sitemap():
    root=Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for endpoint in PAGES:
        SubElement(SubElement(root,'url'),'loc').text=public_url(url_for(endpoint))
    return Response(tostring(root,encoding='utf-8',xml_declaration=True),mimetype='application/xml')

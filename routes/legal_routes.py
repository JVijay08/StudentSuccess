"""Public notices remain available before sign-in and during onboarding."""
from flask import Blueprint, render_template

legal_bp = Blueprint('legal', __name__)

PAGES = {
    'privacy': ('Privacy policy', 'privacy'),
    'terms-of-service': ('Terms of service', 'terms'),
    'cookies': ('Cookies & browser storage', 'cookies'),
    'data-deletion': ('Your data & deletion', 'deletion'),
    'accessibility': ('Accessibility', 'accessibility'),
}


@legal_bp.get('/<any("privacy","terms-of-service","cookies","data-deletion","accessibility"):page>')
def notice(page):
    title, content = PAGES[page]
    return render_template('legal.html', title=title, content=content)

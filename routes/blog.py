from flask import Blueprint, render_template, request, redirect, url_for

blog_bp = Blueprint('blog', __name__, url_prefix='/blog')

TRANSLATIONS = {
    'id': {
        'nav_home': 'Beranda',
        'nav_features': 'Fitur',
        'nav_guide': 'Panduan',
        'nav_roadmap': 'Roadmap',
        'nav_about': 'Tentang',
        'nav_faq': 'FAQ',
        'lang_toggle': 'EN',
        'lang_code': 'en',
    },
    'en': {
        'nav_home': 'Home',
        'nav_features': 'Features',
        'nav_guide': 'Guide',
        'nav_roadmap': 'Roadmap',
        'nav_about': 'About',
        'nav_faq': 'FAQ',
        'lang_toggle': 'ID',
        'lang_code': 'id',
    }
}


def get_lang():
    lang = request.args.get('lang', 'id')
    if lang not in TRANSLATIONS:
        lang = 'id'
    return lang


def get_t():
    return TRANSLATIONS[get_lang()]


@blog_bp.route('/')
def home():
    lang = get_lang()
    t = get_t()
    return render_template('blog/home.html', lang=lang, t=t)


@blog_bp.route('/features')
def features():
    lang = get_lang()
    t = get_t()
    return render_template('blog/features.html', lang=lang, t=t)


@blog_bp.route('/guide')
def guide():
    lang = get_lang()
    t = get_t()
    return render_template('blog/guide.html', lang=lang, t=t)


@blog_bp.route('/about')
def about():
    lang = get_lang()
    t = get_t()
    return render_template('blog/about.html', lang=lang, t=t)


@blog_bp.route('/faq')
def faq():
    lang = get_lang()
    t = get_t()
    return render_template('blog/faq.html', lang=lang, t=t)


@blog_bp.route('/roadmap')
def roadmap():
    lang = get_lang()
    t = get_t()
    return render_template('blog/roadmap.html', lang=lang, t=t)

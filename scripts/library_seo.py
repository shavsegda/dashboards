#!/usr/bin/env python3
"""Обновляет SEO публичной библиотеки. Запуск: python3 scripts/library_seo.py."""

import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / 'biblioteka'
MANIFEST = LIBRARY / 'seo.json'


class PageInfo(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1_parts = []
        self.in_h1 = False
        self.description = ''
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h1':
            self.in_h1 = True
        if tag == 'meta' and attrs.get('name') == 'description':
            self.description = attrs.get('content', '')
        if tag == 'a' and 'href' in attrs:
            self.hrefs.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag == 'h1':
            self.in_h1 = False

    def handle_data(self, data):
        if self.in_h1:
            self.h1_parts.append(data)

    @property
    def name(self):
        return ' '.join(' '.join(self.h1_parts).split()).rstrip('.')


def replace_meta(source, key, content, property_tag=False):
    attr = 'property' if property_tag else 'name'
    pattern = rf'<meta\b(?=[^>]*\b{attr}=[\"\']{re.escape(key)}[\"\'])[^>]*>\s*'
    source = re.sub(pattern, '', source, flags=re.I)
    tag = f'<meta {attr}="{key}" content="{html.escape(content, quote=True)}">\n'
    return source.replace('</head>', tag + '</head>', 1)


def write_changed(path, source):
    if not path.exists() or path.read_text() != source:
        path.write_text(source)


def add_head(source, canonical, schema):
    source = re.sub(r'<link\b(?=[^>]*\brel=[\"\']canonical[\"\'])[^>]*>\s*', '', source, flags=re.I)
    source = re.sub(r'\n?<!-- library-seo:start -->.*?<!-- library-seo:end -->\n?', '\n', source, flags=re.S)
    data = json.dumps(schema, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    block = f'<!-- library-seo:start -->\n<link rel="canonical" href="{canonical}">\n<script type="application/ld+json">{data}</script>\n<!-- library-seo:end -->\n'
    return source.replace('</head>', block + '</head>', 1)


RELATED_STYLE = '''
<style>
  .library-related { box-sizing:border-box; width:calc(100% - 40px); max-width:680px; margin:0 auto 40px; font:17px/1.65 -apple-system,BlinkMacSystemFont,"Helvetica Neue",system-ui,sans-serif; }
  .library-related h2 { font-size:23px; line-height:1.3; margin:0 0 16px; padding:0; border:0; color:inherit; }
  .library-related ul { padding-left:22px; margin:0; }
  .library-related li { margin-bottom:10px; }
  .library-related a { color:inherit; text-underline-offset:3px; }
  @media(max-width:480px) { .library-related { width:calc(100% - 32px); } }
  @media print { .library-related { display:none; } }
</style>
'''



def add_tracking(source, slug, entry, settings):
    if not settings:
        return source
    source = re.sub(r'\n?<!-- library-tracking:start -->.*?<!-- library-tracking:end -->\n?', '\n', source, flags=re.S)
    counter = int(settings['counter_id'])
    block = f'<!-- library-tracking:start -->\n<script defer src="/biblioteka/library-tracking.js" data-library-counter="{counter}" data-library-book="{slug}"></script>\n<!-- library-tracking:end -->\n'
    source = source.replace('</head>', block + '</head>', 1)
    if not entry:
        return source
    # Название книги записывается в поле «Книги подписки» существующей базы.
    field = settings['book_field']
    name = entry['name'].replace(';', ',')
    tag = html.escape('Библиотека;' + name, quote=True)
    draft = 'Здравствуйте, Алексей! Пришёл из библиотеки, со страницы «' + name + '».\nХочу обсудить: '
    telegram = 'https://t.me/shapovalov_vsegda?text=' + quote(draft, safe='')
    def update_connect(match):
        section = match[0]
        section = re.sub(r'<input\b(?=[^>]*name="' + re.escape(field) + r'")[^>]*>\s*', '', section)
        hidden = f'<input type="hidden" name="{field}" value="{tag}">\n    '
        section = re.sub(r'(<input\b(?=[^>]*name="list_id")[^>]*>\s*)', lambda m: m[0] + hidden, section, count=1)
        section = re.sub(r'<a\b[^>]*href="https://t\.me/shapovalov_vsegda(?:\?[^"\n]*)?"[^>]*>', lambda m: '<a href="' + html.escape(telegram, quote=True) + '" data-library-action="telegram">', section, count=1)
        section = section.replace('Адрес хранится в DashaMail и используется для рассылки.', 'Адрес и название материала сохраняются в DashaMail для рассылки и учёта источника подписки.')
        section = section.replace('подтвердите подписку. Адрес и название', 'подтвердите подписку. Если письма нет, проверьте папку «Спам». Адрес и название')
        return section
    return re.sub(r'<!-- author-connect:start -->.*?<!-- author-connect:end -->', update_connect, source, count=1, flags=re.S)


def main():
    manifest = json.loads(MANIFEST.read_text())
    base = manifest['base_url'].rstrip('/')
    entries = manifest['pages']
    shelf_path = LIBRARY / 'index.html'
    shelf = shelf_path.read_text()
    # Новые материалы попадают в карту после добавления ссылки на публичную полку.
    info = PageInfo()
    info.feed(shelf)
    for href in info.hrefs:
        match = re.fullmatch(r'([a-z0-9-]+)/', href)
        if not match or match[1] in entries:
            continue
        slug = match[1]
        path = LIBRARY / slug / 'index.html'
        if not path.exists():
            raise ValueError(f'Ссылка полки без страницы: {slug}')
        page = PageInfo()
        page.feed(path.read_text())
        entries[slug] = {'name': page.name, 'title': f'{page.name} — краткое содержание и основные идеи', 'description': page.description, 'original_authors': '', 'related': []}

    author = {'@type':'Person','@id':base+'/#author','name':'Алексей Шаповалов','url':base+'/'}
    for slug, entry in entries.items():
        path = LIBRARY / slug / 'index.html'
        original = path.read_text()
        canonical = f'{base}/biblioteka/{slug}/'
        source = re.sub(r'<title>.*?</title>', '<title>'+html.escape(entry['title'])+'</title>', original, count=1, flags=re.S)
        for key, value, prop in [('description',entry['description'],False),('og:title',entry['title'],True),('og:description',entry['description'],True),('og:url',canonical,True),('og:locale','ru_RU',True)]:
            source = replace_meta(source,key,value,prop)
        article = {'@type':'Article','@id':canonical+'#article','headline':entry['name'],'description':entry['description'],'url':canonical,'mainEntityOfPage':canonical,'inLanguage':'ru','author':author,'isAccessibleForFree':True}
        date = re.search(r'Пересказ подготовил Алексей Шаповалов,\s*(\d{4}-\d{2}-\d{2})', original)
        if date:
            article['datePublished'] = date[1]
        elif slug == 'cci-self-esteem':
            article['datePublished'] = '2026-11-10'
        if entry.get('source_type','Book'):
            about = {'@type':entry.get('source_type','Book'),'name':entry['name']}
            if entry['original_authors']:
                about['author'] = [{'@type':'Organization' if name.strip() == 'Winning by Design' else 'Person','name':name.strip()} for name in entry['original_authors'].split(',')]
            article['about'] = about
        breadcrumb = {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Главная','item':base+'/'},{'@type':'ListItem','position':2,'name':'Пересказы книг','item':base+'/biblioteka/'},{'@type':'ListItem','position':3,'name':entry['name'],'item':canonical}]}
        source = add_head(source,canonical,{'@context':'https://schema.org','@graph':[article,breadcrumb]})
        source = re.sub(r'\n*<!-- library-related:start -->.*?<!-- library-related:end -->\n*', '\n', source, flags=re.S)
        related = entry.get('related',[])
        if related:
            links = '\n'.join(f'    <li><a href="../{target}/">{html.escape(entries[target]["name"])}</a></li>' for target in related)
            block = '\n<!-- library-related:start -->\n'+RELATED_STYLE+'<nav class="library-related" aria-labelledby="library-related-title">\n  <h2 id="library-related-title">Что почитать рядом</h2>\n  <ul>\n'+links+'\n  </ul>\n</nav>\n<!-- library-related:end -->\n'
            source = source.replace('<!-- author-connect:start -->',block+'<!-- author-connect:start -->',1)
        # Меняется только название навигации, сами адреса остаются прежними.
        source = source.replace('← Библиотека','← Пересказы книг')
        source = add_tracking(source,slug,entry,manifest.get('tracking'))
        write_changed(path,source)

    home_path = ROOT/'index.html'
    home = add_tracking(home_path.read_text(),'home',None,manifest.get('tracking'))
    write_changed(home_path,home)

    collection_url = base+'/biblioteka/'
    collection = {'@context':'https://schema.org','@type':'CollectionPage','name':'Пересказы книг','description':'Основные идеи, объяснения и практические инструменты простым языком. Библиотека Алексея Шаповалова.','url':collection_url,'inLanguage':'ru','author':author,'mainEntity':{'@type':'ItemList','numberOfItems':len(entries),'itemListElement':[{'@type':'ListItem','position':i,'name':entry['name'],'url':f'{collection_url}{slug}/'} for i,(slug,entry) in enumerate(entries.items(),1)]}}
    shelf = re.sub(r'<title>.*?</title>','<title>Пересказы книг — краткое содержание и основные идеи | Алексей Шаповалов</title>',shelf,count=1,flags=re.S)
    shelf = shelf.replace('<h1>Библиотека.</h1>','<h1>Пересказы книг.</h1>')
    shelf = shelf.replace('Книги в пересказе без воды. Коротко за 45 минут — понять, стоит ли покупать. Полностью за 2–3 часа — можно не покупать.','Основные идеи, объяснения и практические инструменты простым языком.')
    for key,value,prop in [('description',collection['description'],False),('og:title','Пересказы книг — Алексей Шаповалов',True),('og:description',collection['description'],True),('og:url',collection_url,True),('og:locale','ru_RU',True)]:
        shelf = replace_meta(shelf,key,value,prop)
    shelf = add_head(shelf,collection_url,collection)
    # Публичный путеводитель тоже получает обычную ссылку с полки.
    if 'class="library-guide"' not in shelf:
        guide = '<p class="library-guide" style="margin-top:24px"><a href="tri-vetki-psihologii/">С чего начать: что читать по психологии и в каком порядке →</a></p>'
        shelf = shelf.replace('<!-- КАТЕГОРИИ.',guide+'\n\n<!-- КАТЕГОРИИ.',1)
        # Ссылка относится к вступлению и использует ширину основного текста.
        shelf = shelf.replace(guide,'<div class="content">'+guide+'</div>')
    shelf = add_tracking(shelf,'library',None,manifest.get('tracking'))
    write_changed(shelf_path,shelf)

    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    sitemap = ET.Element(namespace+'urlset')
    urls = [base+'/',collection_url] + [f'{collection_url}{slug}/' for slug in entries]
    for url in urls:
        node = ET.SubElement(sitemap,namespace+'url')
        ET.SubElement(node,namespace+'loc').text = url
    ET.indent(sitemap,space='  ')
    write_changed(ROOT/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(sitemap,encoding='unicode')+'\n')
    robots_path = ROOT/'robots.txt'
    robots = robots_path.read_text() if robots_path.exists() else 'User-agent: *\nDisallow:\n'
    robots = re.sub(r'(?im)^Sitemap:\s*'+re.escape(base)+r'/sitemap\.xml\s*\n?', '', robots)
    write_changed(robots_path,robots.rstrip()+'\n\nSitemap: '+base+'/sitemap.xml\n')
    write_changed(MANIFEST,json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(f'Обновлено {len(entries)} материалов, полка, robots.txt и карта из {len(urls)} адресов.')


if __name__ == '__main__':
    main()

"""Structural publication regressions; external URLs are deliberately not fetched."""
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = ('index.html', 'agent-psychotherapy.html', 'couple-psychotherapy.html',
         'psychological-safety-assessment.html')


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.tags = []
        self.feed(path.read_text(encoding='utf-8'))
        self.close()

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for name in ('href', 'src'):
            if name in attrs:
                self.links.append(attrs[name])


class StaticTests(unittest.TestCase):
    def test_landing_pages_and_local_links(self):
        documents = {name: Document(ROOT / name) for name in PAGES}
        for name, document in documents.items():
            with self.subTest(page=name):
                self.assertIn('title', document.tags)
                self.assertIn('h1', document.tags)
                self.assertEqual(len(document.ids), len(set(document.ids)), 'Duplicate HTML ids')
                for link in document.links:
                    url = urlsplit(link)
                    if url.scheme or url.netloc:
                        continue
                    target = (ROOT / unquote(url.path.lstrip('/'))).resolve() if url.path else ROOT / name
                    self.assertTrue(target.is_relative_to(ROOT), f'{name}: escaping link {link}')
                    if target.is_dir():
                        target /= 'index.html'
                    self.assertTrue(target.is_file(), f'{name}: missing local target {link}')
                    if url.fragment and target.suffix == '.html':
                        self.assertIn(unquote(url.fragment), Document(target).ids, f'{name}: broken fragment {link}')
        for name in PAGES[1:]:
            self.assertIn(name, documents['index.html'].links, 'Product missing from homepage')

    def test_help_page_assets_and_routes(self):
        routes = {'/': 'index.html', '/api-docs': 'api.html', '/safety': 'safety.html', '/app.js': 'app.js', '/style.css': 'style.css'}
        web = ROOT / 'help_service' / 'web'
        for filename in ('index.html', 'api.html'):
            document = Document(web / filename)
            for link in document.links:
                url = urlsplit(link)
                if url.scheme or url.netloc:
                    continue
                with self.subTest(page=filename, link=link):
                    self.assertIn(url.path, routes)
                    self.assertTrue((web / routes[url.path]).is_file())

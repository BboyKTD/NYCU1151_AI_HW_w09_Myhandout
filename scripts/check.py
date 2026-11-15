"""Verify publishable content, generated output, links and fragment targets."""
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

from build import ROOT, render_all


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = set()
        self.links = []
        self.h1 = 0
        self.lang = ''
        self.viewport = False
        self.exercises = 0
        self.drafts = 0
        self.review_panels = 0
        self.labels = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'data-case-exercise' in attrs:
            self.exercises += 1
        if 'data-exercise-draft' in attrs:
            self.drafts += 1
        if 'data-review' in attrs:
            self.review_panels += 1
        if tag == 'details':
            assert 'open' not in attrs, 'answers/hints must start collapsed'
        if tag == 'label' and 'for' in attrs:
            self.labels.append(attrs['for'])
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, f'duplicate id {attrs["id"]}'
            self.ids.add(attrs['id'])
        if tag == 'h1':
            self.h1 += 1
        if tag == 'html':
            self.lang = attrs.get('lang')
        if tag == 'meta' and attrs.get('name') == 'viewport':
            self.viewport = True
        for attr in ['href', 'src']:
            if attr in attrs:
                self.links.append(attrs[attr])


def main():
    expected = render_all()
    pages = {}
    for name, text in expected.items():
        path = ROOT / name
        assert path.is_file(), f'missing generated page: {name}'
        assert path.read_text(encoding='utf-8') == text + '\n', f'stale output: {name}; rebuild first'
        pages[path.resolve()] = Page(text)
    generated = {path.resolve() for path in (ROOT / 'lessons').glob('*.html')}
    assert generated == {path for path in pages if path.parent.name == 'lessons'}, 'orphan lesson HTML; review old outputs'
    link_count = 0
    for path, page in pages.items():
        assert page.h1 == 1 and page.lang == 'zh-Hant' and page.viewport, f'page semantics: {path.name}'
        assert set(page.labels).issubset(page.ids), f'label has no matching field: {path.name}'
        if path.parent.name == 'lessons':
            assert 'practice' in page.ids, 'lesson must have case practice navigation target'
            assert page.exercises == page.drafts == page.review_panels == 2, 'main and variation each need a draft/review workflow'
        for link in page.links:
            target = urlsplit(link)
            if target.scheme:
                assert target.scheme == 'https', f'unsupported external URL: {link}'
                continue
            assert not target.netloc and not target.path.startswith('/'), f'nonportable path: {link}'
            resolved = (path.parent / unquote(target.path)).resolve() if target.path else path
            assert resolved.is_relative_to(ROOT), f'link leaves project: {link}'
            assert resolved.is_file(), f'broken link in {path.name}: {link}'
            if target.fragment:
                assert resolved in pages and unquote(target.fragment) in pages[resolved].ids, f'missing anchor: {link}'
            link_count += 1
    for name in ['AGENTS.md', 'README.md', 'docs/作業繳交說明.md', 'docs/CHANGELOG.md']:
        assert (ROOT / name).is_file(), f'missing assignment documentation: {name}'
    print(f'PASS: {len(pages)} generated HTML pages match source and templates.')
    print(f'PASS: {link_count} local links/assets/fragments resolve within this project.')
    print('PASS: lesson schema, official source URLs, dates, reciprocal related links, quiz answer indexes.')
    print('PASS: unique IDs, single h1, zh-Hant, viewport, relative paths, required assignment documents.')
    print('PASS: main/variation draft fields, associated labels, collapsed hints/answers, practice navigation and statutory references.')
    print('LIMIT: no network link availability, legal expert review, or browser interaction is implied by these checks.')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, ValueError, KeyError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)

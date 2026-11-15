"""Generate a portable static notebook with only the Python standard library."""
from datetime import date
from html import escape
import json
from pathlib import Path
import re
from string import Template
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SECTION_IDS = ['concept', 'rules', 'case', 'pitfalls']


def e(value):
    return escape(str(value), quote=True)


def load_lessons():
    lessons = []
    for path in sorted((ROOT / 'content/lessons').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        required = ['slug', 'order', 'title', 'description', 'minutes', 'verified',
                    'tags', 'goals', 'sections', 'sources', 'quiz', 'practice', 'related']
        assert all(key in data for key in required), f'{path.name}: missing fields'
        assert re.fullmatch(r'[a-z]+(?:-[a-z]+)*', data['slug']), 'invalid slug'
        assert data['slug'] == path.stem, 'slug and filename differ'
        assert isinstance(data['order'], int) and data['order'] > 0
        assert isinstance(data['minutes'], int) and data['minutes'] > 0
        assert date.fromisoformat(data['verified']) <= date.today(), 'future verification date'
        assert data['title'] and data['description'] and data['tags'] and data['goals']
        assert [section['id'] for section in data['sections']] == SECTION_IDS
        assert data['sources'], 'every lesson needs official sources'
        for source in data['sources']:
            url = urlparse(source['url'])
            assert url.scheme == 'https' and url.hostname == 'law.moj.gov.tw'
            assert 'pcode=B0000001' in url.query and source['article'] and source['summary']
        assert len(data['quiz']) >= 2
        for question in data['quiz']:
            assert question['question'] and question['explanation']
            assert len(question['options']) >= 2
            assert isinstance(question['answer'], int)
            assert 0 <= question['answer'] < len(question['options'])
        practice = data['practice']
        assert practice['title'] and practice['facts'] and practice['questions']
        assert isinstance(practice['minutes'], int) and practice['minutes'] > 0
        assert len(practice['hints']) == 3, 'practice needs three hint levels'
        assert all(hint['title'] and hint['text'] for hint in practice['hints'])
        assert len(practice['self_check']) >= 4, 'practice needs facts/rules/application/conclusion self-checks'
        assert [item['question'] for item in practice['solutions']] == list(range(1, len(practice['questions']) + 1)), 'one solution per question, in order'
        variation = practice['variation']
        assert variation['title'] and variation['change'] and variation['question']
        source_articles = {item['article'] for item in data['sources']}
        for solution in [*practice['solutions'], variation['solution']]:
            assert all(solution[key] for key in ['issue', 'rule', 'application', 'conclusion', 'articles'])
            assert set(solution['articles']).issubset(source_articles), 'practice references missing lesson sources'
        lessons.append(data)
    assert lessons, 'no lessons found'
    slugs = {lesson['slug'] for lesson in lessons}
    assert len(slugs) == len(lessons), 'duplicate slugs'
    assert len({lesson['order'] for lesson in lessons}) == len(lessons), 'duplicate order'
    by_slug = {lesson['slug']: lesson for lesson in lessons}
    for lesson in lessons:
        assert len(lesson['related']) == len(set(lesson['related'])), 'duplicate related entries'
        for related in lesson['related']:
            assert related in slugs and related != lesson['slug'], 'unknown related lesson'
            assert lesson['slug'] in by_slug[related]['related'], 'related link must be reciprocal'
    return sorted(lessons, key=lambda lesson: lesson['order'])


def paragraphs(items):
    return ''.join(f'<p>{e(item)}</p>' for item in items)


def render_section(section):
    kind = section['kind']
    if kind == 'prose':
        body = paragraphs(section['paragraphs'])
    elif kind == 'table':
        assert all(len(row) == len(section['headers']) for row in section['rows'])
        head = ''.join(f'<th scope="col">{e(item)}</th>' for item in section['headers'])
        rows = ''.join('<tr>' + ''.join(f'<td>{e(cell)}</td>' for cell in row) + '</tr>' for row in section['rows'])
        body = f'<div class="table-wrap" role="region" aria-label="{e(section["title"])}比較表" tabindex="0"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    elif kind == 'steps':
        items = ''.join(f'<li><h3>{e(item["title"])}</h3><p>{e(item["text"])}</p></li>' for item in section['items'])
        body = f'<ol class="steps">{items}</ol>'
    elif kind == 'case':
        body = f'<div class="case-box"><p class="case-label">虛構教學例子</p><p>{e(section["facts"])}</p><h3>一步一步判斷</h3>{paragraphs(section["analysis"])}</div>'
    elif kind == 'list':
        body = '<ul class="pitfall-list">' + ''.join(f'<li>{e(item)}</li>' for item in section['items']) + '</ul>'
    else:
        raise ValueError(f'Unknown section kind: {kind}')
    return f'<section id="{e(section["id"])}" class="lesson-section"><h2>{e(section["title"])}</h2>{body}</section>'


def render_quiz(quiz):
    output = []
    for n, question in enumerate(quiz, 1):
        options = ''.join(f'<label class="quiz-option"><input type="radio" name="q{n}" value="{i}"><span>{e(option)}</span></label>' for i, option in enumerate(question['options']))
        answer = question['options'][question['answer']]
        output.append(f'<fieldset class="quiz-question" data-answer="{question["answer"]}"><legend>{n:02d} · {e(question["question"])}</legend>{options}<p class="question-feedback"></p><details class="answer"><summary>查看答案與解析</summary><p><strong>答案：{e(answer)}</strong></p><p>{e(question["explanation"])}</p></details></fieldset>')
    return ''.join(output)


def render_solution(solution):
    labels = [('issue', '問題'), ('rule', '法律依據與要件'),
              ('application', '套用事實'), ('conclusion', '結論')]
    parts = ''.join(f'<div class="analysis-part"><h5>{label}</h5><p>{e(solution[key])}</p></div>' for key, label in labels)
    references = '、'.join(e(article) for article in solution['articles'])
    return f'{parts}<p class="analysis-source">依據：{references}；官方連結見本頁「法條與來源」。</p>'


def render_draft(slug, suffix, label):
    key = f'{slug}-{suffix}'
    return f'''<div class="draft-block">
<label for="{key}-draft">{e(label)}</label>
<textarea id="{key}-draft" data-exercise-draft rows="9" placeholder="請先完整寫下自己的分析；也可以在紙本作答。" aria-describedby="{key}-note"></textarea>
<p id="{key}-note" class="draft-note">草稿僅留在目前頁面，不會傳送或儲存；重新整理或離開前，請自行複製保留。</p>
<label class="paper-check"><input type="checkbox" data-paper-complete><span>我已在紙本或其他地方完整作答</span></label>
</div>
<div class="review-gate" hidden><button class="button" type="button" data-review-unlock>我已完成作答，開啟檢討 <span aria-hidden="true">↗</span></button><p class="gate-status" role="status" aria-live="polite"></p></div>'''


def render_practice(practice, slug):
    questions = '<ol class="practice-questions">' + ''.join(f'<li>{e(item)}</li>' for item in practice['questions']) + '</ol>'
    hints = ''.join(f'<details class="practice-reveal"><summary>{e(hint["title"])}</summary><p>{e(hint["text"])}</p></details>' for hint in practice['hints'])
    solutions = ''.join(f'<section class="model-answer"><h4>第 {item["question"]} 問</h4>{render_solution(item)}</section>' for item in practice['solutions'])
    checklist = ''.join(f'<li><label><input type="checkbox"><span>{e(item)}</span></label></li>' for item in practice['self_check'])
    variation = practice['variation']
    return f'''<section id="practice" class="lesson-section practice-section">
<p class="eyebrow">THINK FIRST / CASE PRACTICE</p><h2>案例練習｜先寫，再對照</h2>
<p class="practice-intro">先用約 {practice["minutes"]} 分鐘完整作答，再開啟檢討。提示與擬答均由你自行展開，不會自動顯示。</p>
<div class="practice-sheet" data-case-exercise><p class="case-label">虛構教學例子 · AI 協作自編題</p><h3>{e(practice["title"])}</h3>
{paragraphs(practice['facts'])}<h4>請具明理由回答</h4>{questions}
{render_draft(slug, 'main', '我的完整作答')}
<noscript><p class="draft-note">請先完成作答，再自行展開下方檢討區；未啟用 JavaScript 時不會檢查作答狀態。</p></noscript>
<details class="review-panel" data-review><summary>完成作答後，展開檢討區</summary>
<div class="review-content"><h3>先回看你的思考</h3><p>需要引導時，依序展開提示；也可以直接對照參考擬答。寫法不必相同，重點是法律推理是否完整。</p>
<div class="hint-stack">{hints}</div>
<details class="practice-reveal model-reveal"><summary>參考擬答｜展開逐問解析</summary><p class="draft-note">以下為本站 AI 協作教學擬答，非教授原擬答或評分保證。</p>{solutions}</details>
<details class="practice-reveal"><summary>自評清單｜檢查我的論證</summary><ul class="self-check">{checklist}</ul><p class="draft-note">勾選僅協助自評，不代表法律答案已獲審訂。</p></details>
<div class="variation-sheet" data-case-exercise><p class="eyebrow">CHANGE ONE FACT</p><h3>{e(variation['title'])}</h3><p>{e(variation['change'])}</p><p><strong>設問：</strong>{e(variation['question'])}</p>
{render_draft(slug, 'variation', '我的變化題作答')}
<details class="review-panel" data-review><summary>完成變化題後，展開檢討區</summary><div class="review-content"><details class="practice-reveal model-reveal"><summary>變化題參考擬答｜比較判斷差異</summary><div class="model-answer"><h4>變化題分析</h4>{render_solution(variation['solution'])}</div></details></div></details>
</div></div></details></div></section>'''


def render_all():
    lessons = load_lessons()
    home = Template((ROOT / 'templates/home.html').read_text(encoding='utf-8'))
    template = Template((ROOT / 'templates/lesson.html').read_text(encoding='utf-8'))
    cards = []
    pages = {}
    by_slug = {lesson['slug']: lesson for lesson in lessons}
    for lesson in lessons:
        number = f'{lesson["order"]:02d}'
        tags = ''.join(f'<span class="tag">{e(tag)}</span>' for tag in lesson['tags'])
        search = ' '.join([lesson['title'], lesson['description'], *lesson['tags'], *[source['article'] for source in lesson['sources']]])
        cards.append(f'<article class="lesson-card" data-search="{e(search)}"><div class="card-top"><span class="card-number">{number}</span><span class="muted">約 {lesson["minutes"]} 分鐘 · 入門</span></div><h3>{e(lesson["title"])}</h3><p>{e(lesson["description"])}</p><div class="tags">{tags}</div><a class="card-link" href="lessons/{lesson["slug"]}.html">閱讀講義 {number}<span aria-hidden="true">↗</span></a></article>')
        toc_items = [('goals', '學習目標'), *[(section['id'], section['title'].split('｜')[0]) for section in lesson['sections']], ('quiz', '自我檢核'), ('practice', '案例練習'), ('sources', '法條與來源'), ('related', '接著閱讀')]
        toc = ''.join(f'<a href="#{e(anchor)}">{e(label)}</a>' for anchor, label in toc_items)
        sources = ''.join(f'<li><a href="{e(source["url"])}">{e(source["article"])} · 官方條文 ↗</a><p>{e(source["summary"])}</p></li>' for source in lesson['sources'])
        related = ''.join(f'<a href="{e(slug)}.html">{e(by_slug[slug]["title"])} <span aria-hidden="true">↗</span></a>' for slug in lesson['related'])
        if not related:
            related = '<p class="muted">更多主題將陸續加入。</p>'
        values = {key: e(lesson[key]) for key in ['title', 'description', 'minutes', 'verified']}
        values.update(number=number, tags=tags, toc=toc, goals=''.join(f'<li>{e(goal)}</li>' for goal in lesson['goals']), sections='\n'.join(render_section(section) for section in lesson['sections']), quiz=render_quiz(lesson['quiz']), practice=render_practice(lesson['practice'], lesson['slug']), sources=sources, related=related)
        pages[f'lessons/{lesson["slug"]}.html'] = template.substitute(values)
    pages['index.html'] = home.substitute(count=len(lessons), first_href=f'lessons/{lessons[0]["slug"]}.html', cards='\n'.join(cards))
    return pages


def main():
    pages = render_all()
    for name, text in pages.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + '\n', encoding='utf-8')
        print(f'Generated {name}')
    print(f'Built {len(pages) - 1} lessons + homepage; no dependencies required.')


if __name__ == '__main__':
    main()

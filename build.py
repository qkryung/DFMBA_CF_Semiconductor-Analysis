"""Build index.html (presentation) and study.html (study guide) from content/*.json, data.json, theme.css, app.js.

Usage: python build.py [--study-only] [--check]
"""
import argparse, json, html, re, sys
from pathlib import Path

parser = argparse.ArgumentParser(description='Build the presentation and study HTML files.')
parser.add_argument('--study-only', action='store_true', help='Rebuild study.html without writing index.html.')
parser.add_argument('--check', action='store_true', help='Validate content and exit without writing.')
args = parser.parse_args()

P = Path(__file__).parent
E = html.escape
deck = json.loads((P / 'content' / 'deck.json').read_text(encoding='utf-8'))
D = json.loads((P / 'data.json').read_text(encoding='utf-8'))
css = (P / 'theme.css').read_text(encoding='utf-8')
js = (P / 'app.js').read_text(encoding='utf-8')

# ---------- assemble slides ----------
slides = []
for f in sorted((P / 'content').glob('part*.json')):
    part = json.loads(f.read_text(encoding='utf-8'))
    slides.extend(part['slides'])

parts = deck['parts']
ids = [s['id'] for s in slides]
dupes = {x for x in ids if ids.count(x) > 1}
if dupes:
    sys.exit('duplicate slide ids: ' + ', '.join(sorted(dupes)))
for p in parts:
    first = next((s['id'] for s in slides if s['part'] == p['id']), None)
    if not first:
        sys.exit('part without slides: ' + p['id'])
    p['first'] = first
problems = []
for s in slides:
    for k in ('id', 'part', 'title', 'type'):
        if k not in s:
            problems.append(f"{s.get('id','?')}: missing {k}")
    if s['part'] not in {p['id'] for p in parts}:
        problems.append(f"{s['id']}: unknown part {s['part']}")
    for sid in s.get('sources', []):
        if sid not in D['sources']:
            problems.append(f"{s['id']}: unknown source id {sid}")
    for sid in s.get('study', {}).get('sourceIds', []):
        if sid not in D['sources']:
            problems.append(f"{s['id']}: unknown study source id {sid}")
    if s['type'] not in ('cover', 'divider', 'agenda') and len(s.get('study', {}).get('paragraphs', [])) < 2:
        problems.append(f"{s['id']}: study paragraphs < 2")
    if s['type'] == 'era':
        for k in ('macro', 'tech', 'leaders', 'finance'):
            if k not in s.get('quad', {}):
                problems.append(f"{s['id']}: era quad missing {k}")
        if s.get('rankYear') and not any(sn['year'] == s['rankYear'] for sn in D['ranking']['snapshots']):
            problems.append(f"{s['id']}: rankYear {s['rankYear']} has no snapshot")
    if 'data-goto' in json.dumps(s, ensure_ascii=False):
        pass
for e in D.get('eras', []):
    if e['slide'] not in ids:
        problems.append(f"era {e['num']} points to unknown slide {e['slide']}")
if problems:
    print('\n'.join(problems))
    sys.exit('content validation failed')

CONTENT = {
    'title': deck['title'], 'coverTitle': deck['coverTitle'], 'coverDesc': deck['coverDesc'], 'coverMeta': deck['coverMeta'],
    'asOf': deck['asOf'], 'agendaFoot': deck.get('agendaFoot', ''), 'parts': parts, 'slides': slides,
}
core_count = sum(1 for s in slides if s.get('core'))
print(f'{len(slides)} slides, {core_count} core, {len(D["sources"])} sources')
if args.check:
    sys.exit(0)


def data_script():
    dump = lambda o: json.dumps(o, ensure_ascii=False).replace('</', r'<\/')
    return '<script>const CONTENT=' + dump(CONTENT) + ';const DATA=' + dump(D) + ';</script>'


def page(title, body, cls=''):
    return ('<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="color-scheme" content="dark light"><meta name="description" content="' + E(deck['description']) + '"><title>' + E(title) +
            '</title><style>' + css + '</style></head><body class="' + cls + '">' + body + data_script() + '<script>' + js + '</script></body></html>')


chapters = ''.join(f'<span data-part="{p["id"]}">{p["num"]} {E(p["short"])}</span>' for p in parts if p['id'] != 'p0')
deck_html = (
    '<header class="topbar"><div class="brand"><b>12</b> SEMICONDUCTOR / 1980→2026</div><nav class="chapters" aria-label="발표 흐름">' + chapters + '</nav>'
    '<label class="sr-only" for="route" style="position:absolute;left:-9999px">발표 경로</label><select id="route"><option value="all">전체 ' + str(len(slides)) + '장</option><option value="core">15분 핵심 ' + str(core_count) + '장</option></select>'
    '<a href="study.html" target="_blank">공부용 해설 ↗</a></header><main class="deckviewport"><div class="stage" id="stage"></div></main>'
    '<footer class="controlbar"><button id="prev" aria-label="이전 장표">←</button><span class="position" id="position"></span><button id="next" aria-label="다음 장표">→</button>'
    '<div class="progress" aria-hidden="true"><i id="progress"></i></div><button id="toc" title="T">목차 T</button><button id="notes" title="N">메모 N</button><button id="sources" title="S">출처 S</button>'
    '<button id="presenter" class="hide-small" title="P">발표자 P</button><span class="time hide-small" id="clock">00:00</span><button id="timer" class="hide-small">타이머 시작</button>'
    '<button id="resettime" class="hide-small" aria-label="타이머 초기화">↺</button><button id="full" title="F">전체화면 F</button></footer>'
    '<aside class="overlay" id="overlay" hidden role="dialog" aria-modal="true" aria-label="발표 보조 패널"></aside>')
if not args.study_only:
    (P / 'index.html').write_text(page(deck['title'] + ' | 발표', deck_html), encoding='utf-8')

# ---------- study page ----------
TAG = re.compile(r'<[^>]+>')


def plain(x):
    return TAG.sub('', str(x).replace('<br>', ' ').replace('<br/>', ' ')).strip()


def srclinks(ids):
    out = []
    for x in dict.fromkeys(ids):
        v = D['sources'][x]
        if v.get('url'):
            out.append('<a href="' + E(v['url'], quote=True) + '" target="_blank" rel="noopener">' + E(v.get('short', x)) + ' ↗</a>')
        else:
            out.append('<span>' + E(v['title']) + '</span> ')
    return '<div class="source-links">근거: ' + ''.join(out) + '</div>'


def table(headers, rows, note=''):
    t = ('<table><thead><tr>' + ''.join('<th>' + E(plain(h)) + '</th>' for h in headers) + '</tr></thead><tbody>' +
         ''.join('<tr>' + ''.join('<td>' + E(plain(c)) + '</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table>')
    if note:
        t += '<p class="table-note">' + E(plain(note)) + '</p>'
    return t


def preview(s):
    """Plain-text rendering of what the slide shows, so the reader can connect deck and notes."""
    t = s['type']
    if t == 'cards':
        return '<ul>' + ''.join('<li><b>' + E(plain(c['title'])) + '</b>' + (' · ' + E(plain(c['stat'])) if c.get('stat') else '') + ' — ' + E(plain(c.get('text', ''))) + (' <i>(' + E(plain(c['detail'])) + ')</i>' if c.get('detail') else '') + '</li>' for c in s['cards']) + '</ul>'
    if t in ('rows', 'table'):
        return table(s['headers'], s['rows'], s.get('note', ''))
    if t == 'flow':
        return ' → '.join('<b>' + E(plain(n['title'])) + '</b> (' + E(plain(n['text'])) + ')' for n in s['nodes'])
    if t == 'timeline':
        return '<ul>' + ''.join('<li><b>' + E(plain(e['year'])) + ' · ' + E(plain(e['title'])) + '</b> — ' + E(plain(e['text'])) + '</li>' for e in s['events']) + '</ul>'
    if t == 'watch':
        return '<ul>' + ''.join('<li><b>' + E(plain(i['title'])) + '</b> — ' + E(plain(i['text'])) + '</li>' for i in s['items']) + '</ul>'
    if t == 'chart':
        return '<p>' + ' · '.join(E(plain(i['label'])) + ' ' + E(str(i.get('text', i['value']))) + (E(s.get('unit', '')) if 'text' not in i else '') for i in s['items']) + '</p><p>' + E(plain(s.get('note', ''))) + '</p>'
    if t == 'era':
        q = s['quad']
        names = [('macro', '거시 배경'), ('tech', '산업·기술'), ('leaders', '주도 기업'), ('finance', '재무적 특징')]
        return '<div class="quad-list">' + ''.join('<div><h4>' + n + '</h4><ul>' + ''.join('<li>' + E(plain(x)) + '</li>' for x in q[k]) + '</ul></div>' for k, n in names) + '</div>'
    if t == 'analogy':
        return '<ul>' + ''.join('<li><b>' + E(plain(i['term'])) + '</b> = ' + E(plain(i['as'])) + ' — ' + E(plain(i['text'])) + '</li>' for i in s['items']) + '</ul>'
    if t == 'scenarios':
        return '<ul>' + ''.join('<li><b>' + E(plain(p['label'])) + ' · ' + E(plain(p['title'])) + '</b> — 조건: ' + E(plain(p['condition'])) + ' / 영향: ' + E(plain(p['effect'])) + ' / 신호: ' + E(plain(p['signal'])) + '</li>' for p in s['paths']) + '</ul>'
    if t == 'closing':
        return '<p>' + E(plain(s['statement'])) + (' / ' + E(plain(s['formula'])) if s.get('formula') else '') + '</p>'
    if t == 'era_map':
        return '<div class="study-era-map"></div>'
    if t == 'linear_chart':
        return '<div class="study-linear-chart"></div>'
    if t == 'ranking':
        return ''.join('<details><summary>' + str(sn['year']) + (' · 잠정' if 'preliminary' in sn['status'] else ' · 스냅샷') + '</summary>' + table(['순위', '기업명(당시 기준)', '반도체 매출 · $bn'], [[r['rank'], r['name'], f"{r['revenue']:.3f}"] for r in sn['rows']]) + '</details>' for sn in D['ranking']['snapshots'])
    return ''


toc = []
sections = []
n = 0
part_of = {p['id']: p for p in parts}
for s in slides:
    n += 1
    p = part_of[s['part']]
    if s['type'] in ('cover', 'divider', 'agenda'):
        if s['type'] == 'divider':
            toc.append('<div class="toc-part">PART ' + p['num'] + ' · ' + E(p['short']) + '</div>')
            sections.append('<section class="study-part" id="' + s['id'] + '" data-part="' + p['id'] + '"><div class="eyebrow">PART ' + p['num'] + ' · 권장 ' + str(p['minutes']) + '분</div><h2>' + E(p['title']) + '</h2>' +
                            ''.join('<p>' + E(x) + '</p>' for x in p.get('studyIntro', [])) + '</section>')
        continue
    st = s.get('study', {})
    toc.append(f'<a href="#{s["id"]}">{n:02} · {E(s["title"])}<br><small>{"핵심" if s.get("core") else "선택 심화"}</small></a>')
    body = f'<section class="study-section" id="{s["id"]}"><div class="eyebrow">{n:02} / {len(slides)} · PART {p["num"]} {E(p["short"])} · {"15분 핵심" if s.get("core") else "선택 심화"}</div><h2>{E(s["title"])}</h2>'
    if s.get('subtitle'):
        body += '<p class="muted">' + E(plain(s['subtitle'])) + '</p>'
    body += '<div class="key">' + E(plain(s.get('takeaway') or '')) + '</div>'
    pv = preview(s)
    if pv:
        body += '<h3>장표에 보이는 것</h3><div class="slide-preview">' + pv + '</div>'
    body += '<h3>내용을 이해하기</h3>' + ''.join('<p>' + E(x) + '</p>' for x in st.get('paragraphs', []))
    for tb in st.get('tables', []):
        body += '<h4>' + E(tb['title']) + '</h4>' + table(tb['headers'], tb['rows'], tb.get('note', ''))
    if st.get('script'):
        body += '<h3>발표할 때 이렇게 말하기</h3><div class="script"><p>' + E(st['script']) + '</p></div>'
    if st.get('transition'):
        body += '<p class="transition">다음 장표 연결 → ' + E(st['transition']) + '</p>'
    qa = [(st['question'], st['answer'])] if st.get('question') else []
    qa += [(q['q'], q['a']) for q in st.get('extraQA', [])]
    for q, a in qa:
        body += '<details><summary>예상 질문 · ' + E(q) + '</summary><p>' + E(a) + '</p></details>'
    body += srclinks(list(dict.fromkeys(s.get('sources', []) + st.get('sourceIds', []))))
    body += f'<p><a href="index.html#{s["id"]}" target="_blank">이 장표 열기 ↗</a></p></section>'
    sections.append(body)

extras = ''
# timing plan
if deck.get('timing'):
    extras += '<section class="study-section" id="timing"><div class="eyebrow">PLAN</div><h2>15분 발표 시간 배분안</h2>' + ''.join('<p>' + E(x) + '</p>' for x in deck['timing'].get('intro', [])) + table(['구간', '장표', '시간', '핵심 메시지'], deck['timing']['rows'], deck['timing'].get('note', '')) + '</section>'
    toc.append('<div class="toc-part">부록</div><a href="#timing">시간 배분안</a>')
# verification
if deck.get('verification'):
    extras += '<section class="study-section" id="verification"><div class="eyebrow">FACT CHECK</div><h2>숫자 검증표 · 확인 상태</h2><p>' + E(deck['verification']['intro']) + '</p>' + table(['항목', '사용한 값', '상태', '근거·메모'], deck['verification']['rows']) + '</section>'
    toc.append('<a href="#verification">숫자 검증표</a>')
# faq
if deck.get('faq'):
    extras += '<section class="study-section" id="faq"><div class="eyebrow">Q&amp;A</div><h2>예상 질문 모음</h2>' + ''.join('<details><summary>' + E(q['q']) + '</summary><p>' + E(q['a']) + '</p></details>' for q in deck['faq']) + '</section>'
    toc.append('<a href="#faq">예상 질문 모음</a>')
# glossary
extras += '<section class="study-section" id="glossary"><h2>발표 전 익혀둘 용어</h2><div class="glossary">' + ''.join('<div><b>' + E(a) + '</b><p>' + E(b) + '</p></div>' for a, b in deck['glossary']) + '</div></section>'
toc.append('<a href="#glossary">용어 사전</a>')
# sources
registry = ('<section class="study-section" id="source-library"><div class="eyebrow">REFERENCE LIBRARY</div><h2>출처와 검증 범위</h2><p>' + E(deck['sourceNote']) + '</p>' +
            ''.join('<div class="source-item"><a href="' + E(v.get('url', ''), quote=True) + '" target="_blank" rel="noopener">' + E(k) + ' · ' + E(v['title']) + '</a><p>' + E(v.get('publisher', '')) + ' · ' + E(v.get('published', '원문 참조')) + '<br>' + E(v.get('note', '')) + '</p></div>'
                    if v.get('url') else '<div class="source-item"><b>' + E(k) + ' · ' + E(v['title']) + '</b><p>' + E(v.get('note', '')) + '</p></div>' for k, v in D['sources'].items()) + '</section>')
toc.append('<a href="#source-library">전체 출처</a>')

study = ('<header class="studybar"><h1><span class="cyan">12조</span> ' + E(deck['title']) + ' · 발표자 학습노트</h1><label for="study-search" style="position:absolute;left:-9999px">장표와 해설 검색</label><input id="study-search" type="search" placeholder="키워드 검색"><button id="theme">밝게</button><button id="expand" class="hide-small">질문 펼치기</button><button id="print" class="hide-small">인쇄</button><a href="index.html">발표 자료 ↗</a></header>'
         '<div class="study-layout"><nav class="study-toc" aria-label="학습 목차">' + ''.join(toc) + '</nav><main class="study-main"><header class="study-intro"><div class="eyebrow">PRESENTER’S READING EDITION</div><h1>' + deck['studyTitle'] + '</h1>' +
         ''.join('<p>' + E(x) + '</p>' for x in deck['studyIntro']) + '<span id="search-count" class="cyan" aria-live="polite"></span></header><div class="empty" id="empty" hidden>검색어가 포함된 항목이 없습니다.</div>' + ''.join(sections) + extras + registry + '</main></div>')
(P / 'study.html').write_text(page(deck['title'] + ' | 개인 공부용', study, 'study-body'), encoding='utf-8')
print('Built study.html only. Presentation left unchanged.' if args.study_only else 'Built index.html and study.html.')

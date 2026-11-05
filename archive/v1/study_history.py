"""Render the history reading supplement without changing presentation content."""
from html import escape


def render(history):
    sources = history['sources']

    def refs(ids):
        return '<p class="history-sources">근거 · ' + ' / '.join(
            '<a href="' + escape(sources[key]['url'], quote=True) +
            '" target="_blank" rel="noopener">' + escape(sources[key]['label']) + ' ↗</a>'
            for key in ids
        ) + '</p>'

    def paragraphs(items):
        return ''.join('<p>' + escape(item) + '</p>' for item in items)

    def rows(headers, items):
        return '<div class="history-table"><table><thead><tr>' + ''.join(
            '<th scope="col">' + escape(head) + '</th>' for head in headers
        ) + '</tr></thead><tbody>' + ''.join(
            '<tr>' + ''.join('<td>' + escape(str(cell)) + '</td>' for cell in row) + '</tr>'
            for row in items
        ) + '</tbody></table></div>'

    content = [
        '<article class="history-guide" id="history-guide" aria-labelledby="history-title">',
        '<div class="eyebrow">STUDY NOTE · 2026.11.04 추가</div>',
        '<h3 id="history-title">' + escape(history['title']) + '</h3>',
        '<p class="history-lead">' + escape(history['lead']) + '</p>',
        paragraphs(history['intro']),
        '<nav class="history-jumps" aria-label="시대별 심화 해설 바로가기">',
        ''.join('<a href="#' + escape(era['id'], quote=True) + '">' +
                escape(era['period']) + ' · ' + escape(era['short']) + '</a>'
                for era in history['eras']),
        '</nav>',
        '<h4>먼저, 1위 교체의 큰 흐름</h4>',
        rows(['시기', '반도체 매출 1위', '순위를 설명하는 핵심'], history['leaders']),
        '<p class="history-note">' + escape(history['ranking_note']) + '</p>',
        refs(history['leader_sources']),
        '<h4>매출과 주식가치에 이르는 경로를 구분하기</h4>',
        rows(['경로', '작동 방식', '확인할 지표'], history['channels']),
        '<p class="history-note">' + escape(history['interpretation_note']) + '</p>',
    ]

    for number, era in enumerate(history['eras'], 1):
        content += [
            '<article class="history-era" id="' + escape(era['id'], quote=True) + '">',
            '<p class="history-period">' + f'{number:02} · ' + escape(era['period']) + '</p>',
            '<h4>' + escape(era['title']) + '</h4>',
            '<p class="history-leader"><strong>순위 연결</strong> ' + escape(era['leader']) + '</p>',
            paragraphs(era['paragraphs']),
            '<h5>어떤 기업이 어떻게 영향을 받았나</h5>',
            '<dl class="history-companies">',
            ''.join('<div><dt>' + escape(company['name']) + '</dt><dd>' +
                    escape(company['explanation']) + '</dd></div>' for company in era['companies']),
            '</dl>',
            '<p class="history-point"><strong>이 시기를 읽는 관점</strong><br>' + escape(era['lesson']) + '</p>',
            refs(era['sources']),
            '</article>',
        ]

    content += [
        '<h4>처음 떠올린 흐름을 이렇게 다듬으면 정확하다</h4>',
        rows(['초기 생각', '자료를 확인한 뒤의 설명'], history['corrections']),
        '<h4>흐름을 연결해서 말해보기</h4>',
        '<div class="script">' + paragraphs(history['narration']) + '</div>',
        '<h4>스스로 확인할 질문</h4>',
        ''.join('<details><summary>' + escape(item['question']) + '</summary><p>' +
                escape(item['answer']) + '</p></details>' for item in history['questions']),
        '<details class="history-reference"><summary>추가 해설의 출처와 집계 기준</summary>',
        '<p>' + escape(history['source_note']) + '</p>',
        ''.join('<div class="source-item"><a href="' + escape(source['url'], quote=True) +
                '" target="_blank" rel="noopener">' + escape(source['label']) + '</a><p>' +
                escape(source['note']) + '</p></div>' for source in sources.values()),
        '</details>',
        '<p class="history-back"><a href="#history-guide">시대별 해설 처음으로 ↑</a></p>',
        '</article>',
    ]
    return ''.join(content)

import argparse,json,html
from pathlib import Path
from study_history import render as render_history

parser=argparse.ArgumentParser(description='Build the presentation and study HTML files.')
parser.add_argument('--study-only',action='store_true',help='Rebuild study.html without writing index.html.')
args=parser.parse_args()
P=Path(__file__).parent
C=json.loads((P/'content.json').read_text(encoding='utf-8'))
D=json.loads((P/'data.json').read_text(encoding='utf-8'))
css=(P/'theme.css').read_text(encoding='utf-8')
js=(P/'app.js').read_text(encoding='utf-8')
E=html.escape
def data_script():
    return '<script>const CONTENT='+json.dumps(C,ensure_ascii=False).replace('</',r'<\/')+';const DATA='+json.dumps(D,ensure_ascii=False).replace('</',r'<\/')+';</script>'
def page(title,body,cls='',extra_css=''):
    return '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark light"><meta name="description" content="KAIST DFMBA 12조 · 반도체 산업의 역사, 기업 재편과 자본배분, AI·HBM의 재무 이슈"><title>'+title+'</title><style>'+css+extra_css+'</style></head><body class="'+cls+'">'+body+data_script()+'<script>'+js+'</script></body></html>'
deck='''<header class="topbar"><div class="brand"><b>12</b> SEMICONDUCTOR / CAPITAL</div><nav class="chapters" aria-label="발표 흐름"><span data-chapter="01">시장</span><span data-chapter="02">기초</span><span data-chapter="03">기업 재편</span><span data-chapter="04">재무</span><span data-chapter="05">AI</span><span data-chapter="06">결론</span></nav><label class="sr-only" for="route" style="position:absolute;left:-9999px">발표 경로</label><select id="route"><option value="all">전체 32장</option><option value="core">20분 핵심 22장</option></select><a href="study.html" target="_blank">공부용 해설 ↗</a></header><main class="deckviewport"><div class="stage" id="stage"></div></main><footer class="controlbar"><button id="prev" aria-label="이전 장표">←</button><span class="position" id="position"></span><button id="next" aria-label="다음 장표">→</button><div class="progress" aria-hidden="true"><i id="progress"></i></div><button id="toc" title="T">목차 T</button><button id="notes" title="N">메모 N</button><button id="sources" title="S">출처 S</button><button id="presenter" class="hide-small" title="P">발표자 P</button><span class="time hide-small" id="clock">00:00</span><button id="timer" class="hide-small">타이머 시작</button><button id="resettime" class="hide-small" aria-label="타이머 초기화">↺</button><button id="full" title="F">전체화면 F</button></footer><aside class="overlay" id="overlay" hidden role="dialog" aria-modal="true" aria-label="발표 보조 패널"></aside>'''
if not args.study_only:
    (P/'index.html').write_text(page(C['title']+' | 발표',deck),encoding='utf-8')

history=json.loads((P/'study_history.json').read_text(encoding='utf-8'))
history_html=render_history(history)
history_css=(P/'study_history.css').read_text(encoding='utf-8')
def srclinks(ids):
    return '<div class="source-links">근거: '+''.join('<a href="'+E(D['sources'][x]['url'],quote=True)+'" target="_blank" rel="noopener">'+E(D['sources'][x].get('short',x))+' ↗</a>' if D['sources'][x].get('url') else '<span>'+E(D['sources'][x]['title'])+'</span> ' for x in ids)+'</div>'
def table(headers,rows):return '<table><thead><tr>'+''.join('<th>'+E(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table>'
special={
'market':table(['시점 / 모집단','IT 비중','해석'],[['1990 연말 S&P 500','6.30%','Bespoke 과거 지수집계'],['1999 연말 S&P 500','29.18%','2000년 고점과 기준일 다름'],['2010 연말 S&P 500','18.65%','연말 가중치'],['2020 연말 S&P 500','27.61%','2018 업종개편 이후'],['2026.09.30 SPY','39.71%','S&P 500 추종 ETF 대용치'],['2026.09.30 MSCI ACWI','33.21%','글로벌 대형·중형주; 위 시계열과 구분']]),
'itmix':table(['XLK 업종 비중','2020.09.30','2026.09.30'],[['반도체·장비','18.0%','45.95%'],['소프트웨어','32.7%','23.81%'],['하드웨어·스토리지·주변기기','24.6%','19.35%'],['통신장비','2.8%','4.95%'],['전자장비·기기·부품','1.9%','3.64%'],['IT 서비스','19.9%','2.31%']])+'<p class="small">2020 보통주 99.9%, 소액 현금성 0.1%. 2026 표 합계 100.01%는 반올림. 지수 가중치 제한·분류개편이 포함되므로 순수 주가효과로 해석하지 않는다.</p>',
'cycle':table(['연도','세계 매출 · 십억 USD','자료 성격'],[[2000,'204.393623','연간 실제'],[2001,'138.962610','연간 실제'],[2010,'298.315115','연간 실제'],[2020,'440.389358','연간 실제'],[2022,'574.084194','연간 실제'],[2023,'526.885425','연간 실제'],[2024,'630.548606','연간 실제 · 수정치'],[2025,'795.640305','연간 실제 · 수정치']]),
'financials':table(['기업·기간','매출 · $bn','영업이익률','투자/매출','회사 정의 FCF/매출'],[['NVIDIA FY26 (2026.01.25 종료)','215.938','60.4%','2.8%','44.7%'],['TSMC CY2025','122.42','50.8%','33.4%','26.3%'],['TI CY2025','17.682','34.1%','25.7%','16.6%'],['Micron FY25 (2025.08.28 종료)','37.378','26.1%','36.9% 순투자','10.0% adjusted']])+'<p>TI의 FCF는 CFO − CAPEX + CHIPS 유입으로 2,938백만달러다. 단순 CFO − CAPEX는 2,603백만달러, 매출 대비 14.7%다. Micron은 순CAPEX와 조정 FCF, NVIDIA는 유형·무형자산 구매와 관련 원금상환을 공제한 회사 정의다. 수치의 정의와 기간을 동일하다고 가정하면 안 된다.</p>',
'korea':table(['공시 범위·기간','매출','영업이익','발표일'],[['삼성전자 DS · 2026 Q3','147.1조원','106.5조원','2026.10.29'],['SK하이닉스 연결 · 2026 Q3','104.6155조원','83.3338조원','2026.10.28']]),
'valuation':table(['5년 뒤 현금','할인율','현재가치','기준 대비'],[[100,'8%','68.06','기준'],[100,'10%','62.09','−8.77%'],[100,'12%','56.74','−16.63%'],[80,'12%','45.39','−33.30%']])+'<p>계산식: PV = CF₅ / (1 + r)⁵. 반올림 전 값을 기준으로 변화율 계산. 실제 기업가치 모형은 기간별 현금흐름, 영구가치, 순부채, 비영업자산, 희석 등을 추가해야 한다.</p>',
'outlook':table(['WSTS 2026.06.02 전망','2025 실제','2026 전망','2027 전망'],[['세계 반도체 매출 · $bn','795.640','1,511.248','1,913.683'],['메모리 매출 · $bn','230.042','803.941','1,062.085']])+'<p>위 숫자는 WSTS Spring 2026 전망의 발표 시점 조건부 추정이다. 2026 연간 실적은 아직 완결되지 않았다. 미래의 매출·마진·가격이 확정됐다는 뜻이 아니며 11월 후속 전망에서 달라질 수 있다.</p>'}
special['ranking']=''.join('<details><summary>'+str(sn['year'])+(' · 잠정 (2026.01.12 발표)' if sn['year']==2025 else ' · 관측 스냅샷')+'</summary>'+table(['순위','기업명 (당시 기준)','반도체 매출 · $bn'],[[r['rank'],r['name'],f"{r['revenue']:.3f}"] for r in sn['rows']])+'</details>' for sn in D['ranking']['snapshots'])
def mini(values,unit):
    m=max(v for _,v in values)
    return '<div class="study-mini" role="img" aria-label="'+E(unit)+' 비교 막대 차트">'+''.join('<div><label>'+str(y)+'</label><i style="width:'+str(v/m*65)+'%"></i><b>'+f'{v:.1f}'+unit+'</b></div>' for y,v in values)+'</div>'
special['market']=mini([('1990',6.3),('1999',29.18),('2010',18.65),('2020',27.61),('2026.9',39.71)],'%')+special['market']
special['market']+='<h3>주요 업종 비교 · %</h3>'+table(['기준','IT','금융','산업재','에너지','기타'],[['1990 연말',6.30,7.46,13.60,13.38,59.26],['1999 연말',29.18,13.02,9.91,5.55,42.34],['2006 연말',15.14,22.27,10.84,9.82,41.93],['2010 연말',18.65,16.06,10.95,12.03,42.31],['2020 연말',27.61,10.44,8.40,2.28,51.27],['2026.09 SPY',39.71,11.40,8.05,3.40,37.44]])
special['cycle']=mini([('2000',204.4),('2001',139.0),('2010',298.3),('2020',440.4),('2023',526.9),('2025',795.6)],' $bn')+special['cycle']
glossary=[('아날로그','연속적인 신호나 물리량을 처리하는 회로.'),('시스템 반도체','국내에서 비메모리 기능을 넓게 묶어 부르는 용어. 아날로그와 배타적인 분류가 아니다.'),('팹리스 / 파운드리 / IDM','설계 중심 / 위탁 제조 / 설계·제조 통합이라는 사업모델.'),('HBM / TSV','고대역폭 적층 DRAM / 칩을 관통하는 수직 연결 기술.'),('ASP / 비트 출하','평균판매가격 / 메모리가 공급한 정보 저장량의 단위 기준 출하.'),('수율 / 가동률','생산품 중 양품 비율 / 생산능력을 실제 사용하는 정도.'),('CAPEX / 감가상각','공장·장비 등 자산 투자 / 투자비를 사용기간에 걸쳐 비용으로 배분.'),('CFO / FCF','영업현금흐름 / 일반적으로 영업현금에서 설비투자를 뺀 값. 회사 정의 확인.'),('ROIC / WACC','투하자본수익률 / 가중평균자본비용. 투자 수익과 요구수익을 비교.'),('EV / 시가총액','기업가치 / 주식가치. EV는 일반적으로 시가총액에 순부채 등을 조정.'),('LTA / take-or-pay','장기공급계약 / 인수 여부와 관계없이 계약상 지급 의무를 지는 형태. 조건·신용 중요.'),('RPO / 백로그','남은 계약상 수행의무 / 수주잔고. 매출·현금·이익과 동일하지 않음.')]
toc=''.join(f'<a href="#{x["id"]}">{i+1:02} · {E(x["title"])}<br><small>{"핵심" if x["core"] else "선택 심화"}</small></a>'+('<a href="#history-guide">↳ 시대 변화와 1위 교체<br><small>공부용 심화 · 9개 시기</small></a>' if x['id']=='ranking' else '') for i,x in enumerate(C['slides']))
sections=[]
for i,x in enumerate(C['slides']):
    st=x['study']; paras=st.get('paragraphs',[])
    if len(paras)<3:raise ValueError('missing study: '+x['id'])
    body=f'<section class="study-section" id="{x["id"]}"><div class="eyebrow">{i+1:02} / {len(C["slides"])} · {x["chapter"]} · {"20분 핵심" if x["core"] else "선택 심화"}</div><h2>{x["title"]}</h2><div class="key">{x["takeaway"] or "산업의 성장과 기업의 현금창출력, 자본배분을 연결해 읽는다"}</div>'
    body+='<h3>내용을 이해하기</h3>'+''.join('<p>'+E(p)+'</p>' for p in paras)
    if x['id']=='ranking':body+=history_html
    if x['id'] in special:body+='<h3>숫자와 정의 확인</h3>'+special[x['id']]
    body+='<h3>발표할 때 이렇게 설명하기</h3><div class="script"><p>'+E(st.get('script',''))+'</p></div><p class="transition">다음 장표 연결 → '+E(st.get('transition',''))+'</p>'
    body+='<details><summary>예상 질문 · '+E(st.get('question',''))+'</summary><p>'+E(st.get('answer',''))+'</p></details>'+srclinks(list(dict.fromkeys(x['sources']+st.get('sourceIds',[]))))+f'<p><a href="index.html#{x["id"]}" target="_blank">이 장표 열기 ↗</a></p></section>'
    sections.append(body)
registry='<section class="study-section" id="source-library"><div class="eyebrow">REFERENCE LIBRARY</div><h2>출처와 검증 범위</h2><p>조회 기준일은 2026-11-03입니다. 고정 과거 자료와 월별로 갱신되는 팩트시트 URL을 구분했습니다. 제공된 HBS 원문·기존 학습 HTML·참고 이미지는 재배포하지 않습니다. 숫자, 요약, 직접 제작한 도식만 수록합니다.</p>'+''.join('<div class="source-item"><a href="'+E(v.get('url',''),quote=True)+'" target="_blank" rel="noopener">'+E(k)+' · '+E(v['title'])+'</a><p>'+E(v.get('publisher',''))+' · '+E(v.get('published','원문 참조'))+'<br>'+E(v.get('note',''))+'</p></div>' if v.get('url') else '<div class="source-item"><b>'+E(k)+' · '+E(v['title'])+'</b><p>'+E(v.get('note',''))+'</p></div>' for k,v in D['sources'].items())+'</section>'
study='<header class="studybar"><h1><span class="cyan">12조</span> 반도체 · 발표자 학습노트</h1><label for="study-search" style="position:absolute;left:-9999px">장표와 해설 검색</label><input id="study-search" type="search" placeholder="키워드 검색"><button id="theme">밝게</button><button id="expand" class="hide-small">질문 펼치기</button><button id="print" class="hide-small">인쇄</button><a href="index.html">발표 자료 ↗</a></header><div class="study-layout"><nav class="study-toc" aria-label="학습 목차">'+toc+'<a href="#glossary">용어 사전</a><a href="#source-library">전체 출처</a></nav><main class="study-main"><header class="study-intro"><div class="eyebrow">PRESENTER’S READING EDITION</div><h1>반도체의 역사를<br>현금흐름으로 읽기</h1><p>발표 32장과 같은 순서로 기술·산업·재무를 연결한 개인 학습자료입니다. 각 장의 설명, 발언 예시, 다음 연결 문장, 예상 질문을 함께 읽으세요.</p><p><b class="cyan">권장 20분 경로:</b> 발표 화면 상단에서 핵심 22장을 선택합니다. 전체 설명은 약 35~45분 분량이며, 선택 심화 장표는 공부와 질의응답에 활용할 수 있습니다. 핵심 경로의 시간은 발표 속도에 따라 달라집니다.</p><p>조사 기준 2026.11.03 · 시장비중 2026.09.30 · 산업 매출 2025 연간 실제 · 최신 주요 실적 2026 Q3. 실제치·회사 전망·교육용 가정을 구분합니다.</p><span id="search-count" class="cyan" aria-live="polite"></span></header><div class="empty" id="empty" hidden>검색어가 포함된 장표가 없습니다.</div>'+''.join(sections)+'<section class="study-section" id="glossary"><h2>발표 전 익혀둘 용어</h2><div class="glossary">'+''.join('<div><b>'+E(a)+'</b><p>'+E(b)+'</p></div>' for a,b in glossary)+'</div></section>'+registry+'</main></div>'
study=study.replace('<span id="search-count"', '<p><b class="cyan">2026.11.04 학습 해설 추가:</b> <a href="#history-guide">시대 변화와 반도체 매출 1위 교체 →</a><br>PC·인터넷, 닷컴 조정, 금융위기, 모바일·클라우드, 메모리 가격 사이클, AI 인프라를 기업별 수혜와 연결합니다.</p><span id="search-count"',1)
study=study.replace('조회 기준일은 2026-11-03입니다.', '기존 자료 조회 기준일은 2026-11-03입니다. 시대별 심화 해설은 2026-11-04에 추가 조사했으며, 해당 해설 아래에 출처와 집계 기준을 별도로 수록했습니다.',1)
(P/'study.html').write_text(page(C['title']+' | 개인 공부용',study,'study-body',history_css),encoding='utf-8')
print('Built study.html only. Presentation left unchanged.' if args.study_only else 'Built index.html and study.html. Each includes CSS, JS, data and prose.')

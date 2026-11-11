"""기업재무 12조 발표 덱 빌더.

data.json · research_*.json · macro_raw.json · sector_us.json 을 읽어
SLIDES / CHARTS / SOURCES / ERAS / FIN / SECTOR / TL 상수를 만들고,
v3.css · v3.js 와 합쳐 한 파일짜리 HTML(기업재무_발표자료_12조_v5.html)로 내보낸다.
이전 판(_v4.html 28장 · _v3.html 26장 · _v2.html 28장 · 기업재무_발표자료_12조.html = index.html 31장)은 건드리지 않는다.

v5 는 v4 를 다듬은 25장 판이다(발표 흐름: 도입 → PART 1 → PART 2 → PART 3 의 세 이슈 → 마무리).
- PART 2 의 순서: 간지 → 시간축 → 태동기 → 제1기 → 제2기(분업) → 제3기(탈락과 인수) → 그 결과인 밸류체인 × 제품군 지도 ·
  M&A 재편 → 제4기 → 정리. 제2기는 분업이 깊어진 이유를 설명하는 한 장으로, 제3기는 두 장을 한 장으로 합쳤다.
- PART 3: ② 미·중 장표를 다시 짰고, ③ 현금 배분과 장기계약을 한 장으로 합쳤다.
- 표지 문구 · 4쪽의 주력 제품군 · 7쪽의 ‘함께 볼 기업’ 표시 · 정리 장표의 ‘사이클’ 카드를 고쳤다.
발표에서 넘어가는 장표는 add(..., ref=True) 로 표시하며 제목 앞에 (참고)가 붙는다.

장표 본문은 1440×810 무대 기준이다. 본문 영역은 대략 1326×554px
(머리 102 + 본문 + 한 줄 요약 64 + 바닥 26)이므로 높이를 넘기지 않게 맞춘다.
"""
import base64
import csv
import json
import mimetypes
import re
from decimal import Decimal, ROUND_HALF_UP
from html import escape
from pathlib import Path

P = Path(__file__).parent


def read(name):
    return json.loads((P / name).read_text(encoding='utf-8-sig'))


D = read('data.json')                      # Linear 시계열 · WSTS 연간 · 1990 순위 · 출처 목록
F = read('research_financials.json')       # 빅테크 연간 재무 · 아날로그 동종사 · 감사 메모
M = read('macro_raw.json')                 # FEDFUNDS · GS10 월별
Q = read('research_quarterly.json')        # 빅테크 · 삼성 · SK hynix · WSTS 분기
QF = read('research_quarterly_fin.json')   # 빅테크 분기 손익 · 재무상태 (대시보드)
QA = read('research_quarterly_fin_added.json')   # 대시보드에 추가한 6개사 분기 손익 · 재무상태 · 현금흐름
HIS = read('research_history.json')        # 냉전 군사비 · 1980년대 거시 · Linear 인수 협상
RAW_SECTOR = read('sector_us.json')        # Fortune 500 섹터별 매출 Top 10 (build_sector_us.py 가 만든다)
ATTR = read('assets/v3/deck/attribution.json')

SLIDES, CHARTS, ERAS = [], {}, []
PARTS = {0: '도입', 1: '케이스 이후의 Linear Technology', 2: '반도체 산업의 변천', 3: 'AI 시대가 마주한 세 가지 재무적 이슈'}

# 차트 색: v3.js 의 K.s 와 같은 순서. 색은 순위가 아니라 대상(기업·국가)을 따라간다.
C = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']
MUTE, INK, INK2, INK3 = '#566b7e', '#edf7ff', '#a8bbcb', '#7f97aa'
AXIS, GRID, SURF = '#33495d', '#142536', '#07121f'
CYAN, GREEN, AMBER, RED = '#37ccff', '#39e2b0', '#ffb15e', '#ff8298'


# ───────────────────────── 도구 ─────────────────────────
def r1(x, nd=1):
    """표시용 반올림(사사오입). 부동소수 오차로 12.85가 12.8이 되는 일을 막는다."""
    return Decimal(str(x)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)


def fmt(x, nd=1, sign=False):
    v = r1(x, nd)
    body = f'{abs(v):,.{nd}f}'
    if v < 0:
        return '−' + body
    return ('+' if sign and v > 0 else '') + body


def cagr(first, last, years):
    return ((last / first) ** (1 / years) - 1) * 100


def tw(text, fs):
    """v3.js 의 tw 와 같은 글자 폭 추정."""
    w = 0
    for ch in str(text):
        if ord(ch) > 0x2e7f:
            w += 1
        elif ch == ' ':
            w += .3
        elif ch in ".,:;·'|il1()":
            w += .32
        elif ch in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ%$−+':
            w += .7
        else:
            w += .57
    return w * fs


REF_MARK = '(참고)'


def add(id, part, title, sub, body, take='', sources=None, kind='', method='', tables=None, ref=False):
    """ref=True 는 발표에서 넘어가는 참고 장표: 제목 앞에 (참고)를 붙이고 목차에서도 흐리게 보인다."""
    if ref:
        title = f'<span class="ref">{REF_MARK}</span> {title}'
    SLIDES.append(dict(id=id, part=part, title=title, sub=sub, html=body, take=take,
                       sources=sources or [], kind=kind, method=method, tables=tables or [], ref=ref))


def slot(chart_id, h=None):
    """차트 자리. 높이를 주지 않으면 세로 배치 안에서 남는 높이를 모두 쓴다."""
    if h is None:
        return f'<div data-chart="{chart_id}" class="grow"></div>'
    return f'<div data-chart="{chart_id}" data-h="{h}" style="min-height:{h}px"></div>'


def card(title, unit, inner, note='', cls=''):
    small = f'<small>{unit}</small>' if unit else ''
    foot = f'<p class="note">{note}</p>' if note else ''
    return f'<div class="chartcard {cls}"><h3>{title}{small}</h3>{inner}{foot}</div>'


def panel(kicker, title, text='', cls='', pre='', post=''):
    p = f'<p>{text}</p>' if text else ''
    return f'<article class="panel {cls}">{pre}<div class="kicker">{kicker}</div><h3>{title}</h3>{p}{post}</article>'


def steps(items, cls=''):
    return (f'<div class="steps {cls}">'
            + ''.join(f'<div class="step"><b>{head}</b><span>{text}</span></div>' for head, text in items) + '</div>')


def tags(items, sep='→', cls=''):
    """알약 꼬리표. sep 을 비우면 화살표 없이 나열한다."""
    mid = f'<i>{sep}</i>' if sep else ''
    return f'<div class="tags {cls}">' + mid.join(f'<span>{t}</span>' for t in items) + '</div>'


def T(x, y, s, size=12, fill=INK2, anchor='start', weight=None, cls='', extra=''):
    """SVG 글자 한 줄."""
    a = f' text-anchor="{anchor}"' if anchor != 'start' else ''
    w = f' font-weight="{weight}"' if weight else ''
    c = f' class="{cls}"' if cls else ''
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}"{a}{w}{c}{extra}>{s}</text>'


def legend(items, cls=''):
    """items: (모양 클래스, 색, 글자). 모양: ln 선 · sq 사각 · dot 점 · ring 빈 점."""
    return (f'<div class="legend inline {cls}">'
            + ''.join(f'<span><i class="{k}" style="background:{c};border-color:{c}"></i>{t}</span>' for k, c, t in items) + '</div>')


# ───────────────────────── 출처 ─────────────────────────
SOURCES = D['sources'].copy()


def source(key, title, url, note='', publisher='공식 자료', published=''):
    SOURCES[key] = {'title': title, 'url': url, 'note': note, 'publisher': publisher, 'published': published}
    return key


FRED = 'FRED · 세인트루이스 연준'
FEDHIST = 'Federal Reserve History'
STATE = '미 국무부 역사실 (Office of the Historian)'
SEC = 'SEC EDGAR'

source('fred_ff', '미 연준 · 연방기금 실효금리, 월평균', 'https://fred.stlouisfed.org/series/FEDFUNDS',
       '정책 목표범위와 구별. 금리 자체가 기업 WACC는 아님.', FRED)
source('fred_10', '미 연준 · 미국 10년 국채 수익률, 월평균', 'https://fred.stlouisfed.org/series/GS10', '', FRED)
source('fred_cpi', '미국 소비자물가지수 (CPI-U, 비계절조정)', 'https://fred.stlouisfed.org/series/CPIAUCNS',
       '전년동월 대비 상승률 정점 14.76% (1980.03).', FRED)
source('fred_twex', '달러 실효환율 지수 (주요 통화, TWEXMMTH)', 'https://fred.stlouisfed.org/series/TWEXMMTH',
       '1980.09 93.16 → 1985.03 143.91 (+54.5%). 시작 월을 어디로 잡느냐에 따라 상승 폭이 달라짐.', FRED)
source('fred_exjpus', '엔/달러 환율, 월평균 (EXJPUS)', 'https://fred.stlouisfed.org/series/EXJPUS',
       '1985.09 236.53엔 → 1987.12 128.24엔.', FRED)
source('boj', '일본은행 · 1972–95 공정할인율', 'https://www.boj.or.jp/en/statistics/boj/other/discount/',
       '미국 실효 연방기금금리와 지표 정의가 다름. 일본은 당시 공정할인율.', '일본은행')
source('fh_inflation', 'The Great Inflation', 'https://www.federalreservehistory.org/essays/great-inflation', '', FEDHIST)
source('fh_oil73', 'Oil Shock of 1973–74', 'https://www.federalreservehistory.org/essays/oil-shock-of-1973-74', '', FEDHIST)
source('fh_oil79', 'Oil Shock of 1978–79', 'https://www.federalreservehistory.org/essays/oil-shock-of-1978-79', '', FEDHIST)
source('fh_volcker', "Volcker's Announcement of Anti-Inflation Measures",
       'https://www.federalreservehistory.org/essays/anti-inflation-measures',
       '1979.10.06 통화량 목표를 앞세운 긴축 전환 발표.', FEDHIST)
source('fh_recession', 'Recession of 1981–82', 'https://www.federalreservehistory.org/essays/recession-of-1981-82', '', FEDHIST)
source('feds_2016062', 'Kahn & Meade (2016) · 연준 FEDS 2016-062 — 1980년대 달러 강세와 국제 정책 공조',
       'https://www.federalreserve.gov/econresdata/feds/2016/files/2016062pap.pdf',
       '긴축 통화정책과 확장 재정의 조합이 금리와 달러를 함께 끌어올린 경로를 설명.', '미 연준 이사회')
source('omb_hist', 'OMB · Historical Tables 1.2 (재정수지의 GDP 대비 비율)',
       'https://www.govinfo.gov/content/pkg/BUDGET-2025-TAB/xls/BUDGET-2025-TAB-2-2.xlsx',
       '연방 재정적자는 FY1983에 GDP의 5.9%까지 확대.', '미 관리예산처')
source('g5_plaza', 'G5 재무장관·중앙은행 총재 발표문 (플라자 합의, 1985.09.22)',
       'https://www.g7.utoronto.ca/finance/fm850922.htm', '', 'G7 Information Centre · 토론토대')
source('chm', 'Computer History Museum · 항공우주와 초기 IC',
       'https://www.computerhistory.org/siliconengine/aerospace-systems-are-first-the-applications-for-ics-in-computers/',
       '아폴로 유도컴퓨터(AGC)는 1965년까지 IC의 최대 수요처로 약 20만 개를 개당 $20–30에 구매. 이후 미니트맨 II 미사일이 최대 수요처가 됨.',
       'Computer History Museum')
source('cow_nmc', 'Correlates of War · National Material Capabilities v6.0 (군사비)', HIS['milex']['url'],
       '명목 달러(당해연도). 소련 값은 환율·가격 가정에 따라 크게 달라지는 추정치이므로 수준·순위보다 추세를 본다.',
       'Correlates of War Project')
source('hist_korea', 'The Korean War, 1950–1953', 'https://history.state.gov/milestones/1945-1952/korean-war', '', STATE)
source('hist_sputnik', 'Sputnik, 1957', 'https://history.state.gov/milestones/1953-1960/sputnik',
       '1957.10.04 소련의 첫 인공위성 발사.', STATE)
source('hist_vietnam', 'U.S. Involvement in the Vietnam War: the Gulf of Tonkin and Escalation, 1964',
       'https://history.state.gov/milestones/1961-1968/gulf-of-tonkin',
       '1964년 통킹만 사건 이후 1965년 북폭 개시와 지상 전투부대 파병으로 확전.', STATE)
source('apple_iphone', 'Apple · iPhone 발표 (2007.01.09)',
       'https://www.apple.com/newsroom/2007/01/09Apple-Reinvents-the-Phone-with-iPhone/', '', 'Apple Newsroom')
source('ai_index', 'Stanford HAI · AI Index 2026', 'https://hai.stanford.edu/ai-index/2026-ai-index-report',
       '2026.03 Arena 최고 모델 점수 미국 1,503 / 중국 1,464. 모델 벤치마크이며 반도체 제조역량 지표가 아님.', 'Stanford HAI')
source('midterms', 'AP · 2026 미국 중간선거', 'https://apnews.com/article/ef6199e25927a9ac9f4c18eae0e497cd',
       '2026.11.04 민주당 상·하원 다수 확보 보도. 새 의회는 2027년 출범.', 'AP')
source('dc_ballot', 'Data Center Ballot · 지역 주민투표 집계', 'https://ballot.dcmap.us/',
       '2026.11.06 집계. 구속력 있는 35건 중 31건 제한 찬성. 인증 전 결과 포함. 정당별·전국 법률 통계 아님.', 'Data Center Ballot')
# ② 미·중 장표(v3)에서 새로 쓰는 금리 자료 · 2026-11-10 조사
source('cn_adb', 'AsianBondsOnline · 중국 시장 지표 (정책금리 · 국채 수익률)', 'https://asianbondsonline.adb.org/china/',
       '2026.11.10 확인. 정책금리(7일물 역레포) 1.400% — 2025.05.07 적용, 직전(2024.09.27 적용) 대비 −10bp. '
       '10년물 국채 수익률 1.573%(2026.11.09 종가, 연초 대비 −27.0bp), 2년물 1.209%, 5년물 1.311%.',
       '아시아개발은행(ADB) · AsianBondsOnline')
source('cn_lpr', 'Trading Economics · 중국 LPR 17개월 연속 동결 (2026.10.20)',
       'https://tradingeconomics.com/china/interest-rate/news/593249',
       '1년 LPR 3.0% · 5년 LPR 3.5%. 2025.05 이후 사상 최저 수준에서 17개월째 유지. 인민은행 고시를 전한 2차 자료.',
       'Trading Economics (2차)')
source('cn_policy_shift', 'Trading Economics · 중국 10년물 국채 수익률과 정책금리 체계 전환 보도',
       'https://tradingeconomics.com/china/government-bond-yield',
       '2026.11.10 10년물 1.60%. 2026.11.06 보도: 인민은행이 익일물 정책금리를 1.25%로 설정(기존 7일물 역레포 1.4%). '
       '이 덱의 중국 정책금리는 2026.10 기준인 7일물 역레포.', 'Trading Economics (2차)')
source('fred_dgs10d', '미 연준 · 미국 10년 국채 수익률, 일별 (DGS10)', 'https://fred.stlouisfed.org/series/DGS10',
       '2026.11.06 4.86% (2026.11.10 확인 시 최신 관측치). 2026.10 일별 평균 5.13%(21영업일)는 월평균 계열 GS10과 일치.', FRED)
source('analog_rank2025', 'GMI · 2025 아날로그 반도체 시장 추정',
       'https://www.gminsights.com/industry-analysis/analog-semiconductors-market',
       '2026.09 발행. TI 1위, ADI 2위. 시장 범위에 따라 순위와 점유율이 달라질 수 있음.', 'Global Market Insights')
source('linear_defm14a_val', 'Linear DEFM14A · 재무자문사(Qatalyst Partners)의 가치평가 요약', HIS['deal']['url'],
       'DCF $51.51–66.99 · 유사 거래 P/E $45.10–68.84 · 유사 거래 매출 배수 $44.89–57.01 · 동종 상장사 P/E '
       '$41.12–55.63(경영진 계획) / $38.28–51.79(애널리스트 전망). 경영진 계획 매출 2016E $1,424M → 2022E $2,218M(연 +7.7%). '
       '자문사가 경영진 전망을 바탕으로 낸 분석 범위이며 확정 가치가 아님.', SEC)
source('linear_pr_sec', 'ADI · Linear 공동 보도자료 (2016.07.26, SEC 제출본)',
       'https://www.sec.gov/Archives/edgar/data/791907/000119312516658272/d215052dex991.htm',
       '지분가치 약 $14.8bn. 조달 계획: 신주 약 5,800만 주 + 신규 장기부채 약 $7.3bn + 보유 현금.', SEC)
source('adi_presentation_2016', 'ADI · 인수 발표 투자자 설명 자료 (2016.07.26, Rule 425)',
       'https://www.sec.gov/Archives/edgar/data/6281/000119312516658223/d225858d425.htm',
       '산업·통신 인프라·자동차 대응 시장(2015) $8bn → $14bn. 늘어난 $6bn이 전원 관리. Linear FY2015 매출의 59%가 전원 관리.', SEC)
# PART 2 의 밸류체인 · M&A 장표(v4)에서 새로 쓰는 자료 · 2026-11-11 확인
# 거래 연도와 계보는 팀 조사 자료 「반도체 산업 주요 분야별 역사와 기업 계보 2026」(2026.11.10 기준)의 확인 링크를 따랐다
TEAM_DOC = '팀 조사 자료(2026.11.10 기준)의 확인 링크'
source('asml_euv', 'ASML · EUV lithography systems', 'https://www.asml.com/en/products/euv-lithography-systems',
       'EUV 노광 기술을 “unique to ASML”로 소개. EUV 장비의 공급자가 ASML 하나라는 뜻이며 노광장비 전체의 점유율이 아님.', 'ASML')
source('amd_10k_2025', 'AMD · FY2025 Form 10-K (제조 · 사업 구조)',
       'https://www.sec.gov/Archives/edgar/data/2488/000000248826000018/amd-20251227.htm',
       f'첨단 제품의 웨이퍼 제조를 외부 파운드리에 위탁하는 팹리스 구조. {TEAM_DOC}.', SEC)
source('google_tpu', 'Google Cloud · TPU 문서', 'https://docs.cloud.google.com/tpu/docs/tpu7x',
       f'클라우드 기업이 직접 설계한 AI 전용 칩의 예. {TEAM_DOC}.', 'Google Cloud')
source('aws_trainium', 'AWS · Trainium 기반 EC2 Trn1 인스턴스 발표',
       'https://aws.amazon.com/blogs/aws/amazon-ec2-trn1-instances-for-high-performance-model-training-are-now-available/',
       f'클라우드 기업이 직접 설계한 AI 전용 칩의 예. {TEAM_DOC}.', 'AWS')
source('ti_burrbrown', 'TI · Burr-Brown 기술 기사 (2000년 인수)',
       'https://www.ti.com/document-viewer/lit/html/SSZT411/GUID-10A27CC6-C78E-4475-8D45-CD2A9A313D8B',
       '“Since acquiring Burr-Brown in 2000”. Burr-Brown은 1956년 설립된 정밀 아날로그 · 데이터 변환 기업.', 'Texas Instruments')
source('avago_broadcom_10k', 'Broadcom Limited · FY2016 Form 10-K (Avago–Broadcom 결합 완료)',
       'https://www.sec.gov/Archives/edgar/data/1649345/000164934516000016/avgo-10302016x10k.htm',
       f'2016년 Avago와 Broadcom의 결합 완료, 결합 뒤 Broadcom 이름을 사용. {TEAM_DOC}.', SEC)
source('broadcom_lineage', 'Broadcom · 회사 계보 자료 (HP → Agilent → Avago)',
       'https://investors.broadcom.com/static-files/cdcc3313-0657-4416-bce4-d229b67c3e79',
       f'HP 반도체 사업 → 1999 Agilent → 2005 Avago. {TEAM_DOC}.', 'Broadcom')
source('qcom_nxp_term', 'Qualcomm Announces Termination of NXP Acquisition (2018.07)',
       'https://www.qualcomm.com/news/releases/2018/07/qualcomm-announces-termination-nxp-acquisition-and-board-authorization-30',
       '2016.10 발표한 NXP 인수 계약을 종료. 중국 당국의 승인을 기한 안에 받지 못함.', 'Qualcomm')
source('amd_ati', 'AMD · ATI 인수 완료 보도자료 (2006.10.25, Form 8-K 첨부)',
       'https://ir.amd.com/financial-information/sec-filings/content/0001193125-06-217735/dex991.htm',
       '약 $5.4bn 규모의 ATI Technologies 인수 완료. CPU와 GPU의 결합.', 'AMD')
source('amd_xilinx', 'AMD Completes Acquisition of Xilinx (2022.02.14)',
       'https://ir.amd.com/news-events/press-releases/detail/1047/amd-completes-acquisition-of-xilinx',
       'CPU · GPU · FPGA · Adaptive SoC를 한 회사의 제품군으로.', 'AMD')
source('amd_10k_2022', 'AMD · FY2022 Form 10-K (Pensando 인수)',
       'https://ir.amd.com/financial-information/sec-filings/content/0000002488-23-000047/amd-20221231.htm',
       f'2022년 Pensando(DPU) 인수. {TEAM_DOC}.', 'AMD')
source('nvda_mellanox', 'NVIDIA Completes Acquisition of Mellanox (2020.04.27)',
       'https://nvidianews.nvidia.com/news/nvidia-completes-acquisition-of-mellanox-creating-major-force-driving-next-gen-data-centers',
       '거래 규모 $7bn. 연산과 데이터센터 네트워크의 결합.', 'NVIDIA')
source('nvda_arm_term', 'NVIDIA · SoftBank, Arm 인수 계약 종료 발표 (2022.02.07)',
       'https://nvidianews.nvidia.com/news/nvidia-and-softbank-group-announce-termination-of-nvidias-acquisition-of-arm-limited',
       '2020.09.13 계약 → “significant regulatory challenges” 때문에 종료. Arm은 NVIDIA의 자회사가 아님.', 'NVIDIA')
source('gf_history', 'GlobalFoundries · About GF (연혁)', 'https://gf.com/about-gf/',
       '2009 AMD와 Mubadala의 합작으로 출범 → 2010 Chartered Semiconductor → 2015 IBM 마이크로일렉트로닉스 사업(팹 · 지식재산 포함) 인수.',
       'GlobalFoundries')
source('intel_idm2', 'Intel · IDM 2.0 전략 발표 (2021.03.23)',
       'https://www.intc.com/news-events/press-releases/detail/1451/intel-ceo-pat-gelsinger-announces-idm-2-0-strategy',
       'Intel Foundry Services(IFS)를 독립 사업부로 신설해 외부 고객의 칩을 위탁 생산.', 'Intel')
source('intel_foundry_sub', 'Intel · CEO 메시지 (2024.09.16) — Intel Foundry 자회사화 계획',
       'https://www.intc.com/news-events/press-releases/detail/1710/a-message-from-intel-ceo-pat-gelsinger-to-employees',
       '“we plan to establish Intel Foundry as an independent subsidiary inside of Intel”. 계획 발표이며 그 뒤의 진행은 확인하지 않음.', 'Intel')
# v5 에서 새로 쓰는 자료 · 2026-11-11 확인 (제2기 · 제3기 · 정리 · ② 미·중)
source('hoover_triangle', 'Wong & Plummer (2023) · Silicon Triangle 2장 — 반도체 기술 동향의 함의',
       'https://www.hoover.org/sites/default/files/research/docs/SiliconTriangle_Chapter2_230828.pdf',
       '선단 팹 한 곳의 건설비는 최대 약 $20bn. 선단 로직의 주요 제조사는 Intel · Samsung · TSMC 세 곳. '
       '새 팹은 생산능력을 한꺼번에 늘리므로 한동안 공급 과잉이 되기 쉬움(호황 · 불황의 한 원인). 파운드리는 팹리스 스타트업에 '
       '생산능력을 대 주는 벤처캐피털 같은 역할.', 'Hoover Institution', '2023-08')
source('icinsights_fabless2020', 'IC Insights: Fabless Suppliers Held a Record 33% of the 2020 IC Market (2021.04.29)',
       'https://www.design-reuse.com/news/10010-fabless-suppliers-held-a-record-33-of-the-2020-ic-market/',
       '팹리스 · 시스템 IC 기업이 세계 IC 매출에서 차지한 몫: 2002년 13% → 2019년 29.9% → 2020년 32.8%(당시 사상 최고). '
       '메모리가 호황인 해(2017 · 2018)에는 낮아짐.', 'IC Insights (Design & Reuse 전재)', '2021-04-29')
source('trendforce_dram2008', 'TrendForce(DRAMeXchange): Major events in the 2008 DRAM industry',
       'https://www.trendforce.com/presscenter/news/20090105-6986.html',
       '2008년 DRAM 산업은 심한 공급 과잉과 구조 문제를 겪었고 금융위기가 겹침. DRAM 가격은 2008년에 약 75% 하락'
       '(1Gb 667MHz 현물 $2.29 → $0.58)해 현금원가(약 $1) 아래로 내려감. 2008년 1–3분기 업계 손실 $8bn 이상. '
       '감산으로 세계 DRAM 생산능력 약 20% 감소. 트렌치 방식의 점유율은 2006년 23% → 2008년 8%.', 'TrendForce', '2009-01-05')
source('isuppli_dram2008', 'iSuppli: DRAM downturn shows no favouritism (2009.02.10)',
       'https://siliconsemiconductor.net/article/71915/DRAM_downturn_shows_no_favouritism',
       'DRAM 업체들은 2007년 4분기부터 현금원가 아래로 판매. 2008년 4분기에는 1위 삼성도 DRAM에서 적자, 평균 판매가 −38%. '
       'Qimonda는 2009년 1월 파산 신청.', 'iSuppli (Silicon Semiconductor 전재)', '2009-02-10')
source('trendforce_elpida2012', 'TrendForce: Elpida filed for bankruptcy protection (2012.02.27)',
       'https://www.trendforce.com/presscenter/news/20120227-7473.html',
       'Elpida는 제조 기술에서 뒤지지 않았고(30nm 주력 · 25nm 개발 막바지) 파산한 Qimonda보다 경쟁력이 있었으나, '
       '오랜 공급 과잉 속에 만기가 닥친 단기 차입과 높은 부채비율(70%)을 넘지 못함.', 'TrendForce', '2012-02-27')
source('bullwhip', 'Lee · Padmanabhan · Whang (1997) · The Bullwhip Effect in Supply Chains',
       'https://sloanreview.mit.edu/article/the-bullwhip-effect-in-supply-chains/',
       '최종 수요는 고르게 움직여도 주문의 변동은 공급망을 거슬러 올라갈수록 커진다(채찍효과). 반도체에 한정한 연구는 아님.',
       'MIT Sloan Management Review', '1997-04-15')
source('sipri_2025', 'SIPRI Fact Sheet · Trends in World Military Expenditure, 2025 (2026.04)',
       'https://www.sipri.org/publications/2026/sipri-fact-sheets/trends-world-military-expenditure-2025',
       '2025년 군사비: 미국 $954bn(세계의 33%, 전년 대비 −7.5%), 중국 $336bn(추정치 · 세계의 12%, +7.4%, 31년 연속 증가). '
       '당해연도 달러 기준이며 중국 값은 SIPRI의 추정.', 'SIPRI', '2026-04-27')
source('icinsights_mna2020', 'IC Insights: 2020년 반도체 M&A 발표액 사상 최대 (2021.01.13)',
       'https://www.design-reuse.com/news/9463-value-of-semiconductor-industry-m-a-agreements-sets-record-in-2020/',
       '2020 발표액 $118.0bn — 2015년의 종전 기록을 넘어섬. 상위 5건(7 · 9 · 10월 발표)이 $94.0bn으로 약 80%: '
       'NVIDIA–Arm $40bn · AMD–Xilinx $35bn · ADI–Maxim $21bn 등. 발표액 기준이어서 뒤에 무산된 거래(Arm)도 들어 있음.',
       'IC Insights (Design & Reuse 전재)', '2021-01-13')
source('wsts_hbr', 'WSTS · Historical Billings Report (2026.08판 통계표)', Q['sources']['wsts_workbook'],
       '월별 실적을 분기로 합산. 2026 상반기 $722.0bn, 전년동기 $347.0bn 대비 +108%. '
       '8월 6일 보도자료의 $702bn · +102%와는 집계 시점·기준이 달라 수치에 차이가 있음.', 'WSTS')
source('sia_q3_2026', 'SIA · 2026년 3분기 세계 반도체 매출 (2026.11.03)', Q['wsts']['sia_reported_2026Q3']['url'],
       '3분기 $517.7bn, 전분기 대비 +24.1%. WSTS 8월판 통계표보다 나중에 집계된 수치.', 'SIA')
source('skh_q', 'SK hynix · 분기 실적 발표 (2023Q1–2026Q3)', Q['skhynix'][-1]['url'],
       '연결 K-IFRS, 조원. 분기별 발표문 주소는 research_quarterly.json 에 기록.', 'SK hynix Newsroom')
source('sam_q', '삼성전자 · 분기 실적 발표 (2023Q1–2026Q3)', Q['samsung'][-1]['url'],
       '연결 기준, 조원. 발표 수치(반올림). 분기별 발표문 주소는 research_quarterly.json 에 기록.', 'Samsung Newsroom')
for name, c in F['companies'].items():
    source('fin_' + name, name + ' · SEC XBRL 재무 공시', c['source'],
           '연도·공시·태그별 근거는 research_financials.json. FCF=영업CF−총현금 CAPEX; 리스 원금 제외.', 'SEC')
    source('sec_q_' + name, name + ' · SEC XBRL 분기 현금흐름', Q['sources']['sec_companyfacts'][name],
           '분기 영업현금흐름과 CAPEX(총현금 기준). FCF=영업CF−CAPEX, 금융리스 원금은 차감하지 않음.', 'SEC')
    source('sec_qf_' + name, name + ' · SEC XBRL 분기 재무 (손익 · 재무상태 · 현금흐름)', QF['tags'][name]['source'],
           '분기 매출 · 순이익 · 영업이익 · 이자비용 · 자본 · 부채를 역년 분기로 맞춘 값. 태그와 산출 근거는 research_quarterly_fin.json.', 'SEC')
for name in QA['order']:
    t = QA['tags'][name]
    source('sec_qf_' + name, name + ' · ' + t['sourceTitle'], t['source'], t['sourceNote'], t['publisher'])
for name, c in F['peers'].items():
    source('peer_' + name, name + ' · SEC 매출 공시', c['source'], '', 'SEC')
for i, a in enumerate(F['audit']):
    for j, url in enumerate(a.get('sources', [a.get('url')])):
        if url:
            source(f'audit_{i}_{j}', a['claim'], url, a['finding'])
for ly, ry in zip(RAW_SECTOR['listYears'], RAW_SECTOR['years']):
    source(f'fortune500_{ly}', f'Fortune 500 · {ly}년판 ({ry} 회계연도 매출 순위)', f'https://fortune.com/ranking/fortune500/{ly}/',
           'N년판은 직전 회계연도(N−1)의 매출 순위. 화면에는 매출 연도로 표시.', 'Fortune')
GAPS = RAW_SECTOR['gapRows']
source('fortune500_gap', 'Fortune 500 과거 순위 보완 자료 · ' + GAPS['source']['name'], GAPS['source']['url'],
       f'Fortune 아카이브 페이지에서 빠진 순위 {GAPS["added"]}건을 채우고, 값이 어긋난 {GAPS["dropped"]}건을 바로잡는 데 사용. '
       f'확인 {GAPS["source"]["checked"]}.', 'GitHub 공개 데이터셋')
IMG = {a['id']: a for a in ATTR}
for a in ATTR:
    source('img_' + a['id'], a['caption'], a['source'], f'{a["credit"]} · {a["license"]} · {a["licenseUrl"]}', '이미지 출처')


def credit(a):
    lic = 'Public domain' if 'public domain' in a['license'].lower() else a['license']
    return a['credit'].split(' / ')[0] + ' · ' + lic


def frame(img_id, year, title, text='', ph=None, cls=''):
    """사진 한 칸. src 는 상대 경로로 두고, HTML 을 쓸 때 data URI 로 바꾼다."""
    a = IMG[img_id]
    style = f' style="--ph:{ph}px"' if ph else ''
    p = f'<p>{text}</p>' if text else ''
    return (f'<div class="frame {cls}"{style}><img src="{a["path"]}" alt="{a["caption"]}">'
            f'<span class="yr">{year}</span><h3>{title}</h3>{p}<div class="cr">사진 · {credit(a)}</div></div>')


# ───────────────────────── 표지 ─────────────────────────
def chip_svg():
    """표지 그림: 등각 투영으로 그린 칩 패키지."""
    cx, cy, k = 270, 208, .52

    def pt(u, v, z=0):
        return f'{cx + u - v:.1f},{cy + (u + v) * k - z:.1f}'

    def poly(pts, fill, stroke='none', sw=1, extra=''):
        return (f'<polygon points="{" ".join(pt(*p) for p in pts)}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw}" stroke-linejoin="round"{extra}/>')

    def square(half, z):
        return [(-half, -half, z), (half, -half, z), (half, half, z), (-half, half, z)]

    h, bt, d, dz = 107.5, 18, 68, 40          # 기판 반폭 · 기판 두께 · 다이 반폭 · 다이 윗면 높이
    pins = range(-78, 79, 26)
    s = ['<defs><radialGradient id="cvGlow"><stop offset="0" stop-color="#1479b8" stop-opacity=".42"/>'
         '<stop offset="1" stop-color="#1479b8" stop-opacity="0"/></radialGradient>'
         '<linearGradient id="cvDie" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1f7fb3"/>'
         '<stop offset="1" stop-color="#12456a"/></linearGradient></defs>',
         f'<ellipse cx="{cx}" cy="{cy + 14}" rx="262" ry="170" fill="url(#cvGlow)"/>']
    for m in (1.12, 1.24):
        s.append(poly(square(h * m, 0), 'none', '#1a5373', 1, ' stroke-dasharray="3 7"'))
    for t in pins:                             # 뒤쪽 핀: 기판에 가려지도록 먼저 그린다
        s.append(poly([(-h - 15, t - 6, 9), (-h, t - 6, 9), (-h, t + 6, 9), (-h - 15, t + 6, 9)], '#2a88ad'))
        s.append(poly([(t - 6, -h - 15, 9), (t + 6, -h - 15, 9), (t + 6, -h, 9), (t - 6, -h, 9)], '#1f6f90'))
    s.append(poly([(-h, h, bt), (h, h, bt), (h, h, 0), (-h, h, 0)], '#071f33', '#1d5f85'))
    s.append(poly([(h, h, bt), (h, -h, bt), (h, -h, 0), (h, h, 0)], '#05182a', '#1d5f85'))
    s.append(poly(square(h, bt), '#0a2c47', '#37ccff', 2))
    for t in range(-44, 45, 22):               # 다이에서 기판 가장자리로 뻗는 배선
        for a, b in (((t, d), (t, h - 8)), ((d, t), (h - 8, t)), ((t, -d), (t, 8 - h)), ((-d, t), (8 - h, t))):
            s.append(f'<polyline points="{pt(*a, bt)} {pt(*b, bt)}" fill="none" stroke="#37ccff" '
                     'stroke-opacity=".55" stroke-width="1.5"/>')
            ex, ey = pt(*b, bt).split(',')
            s.append(f'<circle cx="{ex}" cy="{ey}" r="2.4" fill="#7bebff"/>')
    for t in pins:                             # 앞쪽 핀: 다리(세로 면) 다음에 윗면
        s.append(poly([(t - 6, h + 15, 9), (t + 6, h + 15, 9), (t + 6, h + 15, -5), (t - 6, h + 15, -5)], '#2a88ad'))
        s.append(poly([(t - 6, h, 9), (t + 6, h, 9), (t + 6, h + 15, 9), (t - 6, h + 15, 9)], '#7bebff'))
        s.append(poly([(h + 15, t - 6, 9), (h + 15, t + 6, 9), (h + 15, t + 6, -5), (h + 15, t - 6, -5)], '#1f6f90'))
        s.append(poly([(h, t - 6, 9), (h, t + 6, 9), (h + 15, t + 6, 9), (h + 15, t - 6, 9)], '#5fd0ee'))
    s.append(poly([(-d, d, dz), (d, d, dz), (d, d, bt), (-d, d, bt)], '#0d3a5b', '#2e9fd0'))
    s.append(poly([(d, d, dz), (d, -d, dz), (d, -d, bt), (d, d, bt)], '#0a2e4a', '#2e9fd0'))
    s.append(poly(square(d, dz), 'url(#cvDie)', '#7bebff', 2))
    s.append(poly(square(52, dz), 'none', '#7bebff', 1, ' stroke-opacity=".45"'))
    s.append(f'<text x="{cx}" y="{cy - dz + 8}" fill="#fff" text-anchor="middle" font-size="24" font-weight="800" '
             'letter-spacing="1">LINEAR → AI</text>')
    s.append(f'<text x="{cx}" y="420" fill="#5e99bd" text-anchor="middle" font-size="15" letter-spacing="5">'
             'DEMAND × CAPITAL × TIME</text>')
    return '<svg viewBox="0 0 540 430" role="img" aria-label="반도체 칩 개념도">' + ''.join(s) + '</svg>'


TEAM = [('김태현', '20269117'), ('박민영', '20269159'), ('박상준', '20269162'),
        ('안상현', '20269234'), ('채재희', '20269423'), ('하진관', '20269450')]
assert [n for n, _ in TEAM] == sorted(n for n, _ in TEAM), '팀원은 가나다순'

add('cover', 0, '리니어는 왜 사라졌나?', '',
    '<div class="cover-main"><div class="eyebrow">KAIST DFMBA · 기업재무 · 12조</div>'
    '<h1>리니어는 왜<br><span class="green">사라졌나?</span></h1>'
    # 도입의 핵심 메시지(v5): 성패를 단정하지 않고, 재무적 선택의 출발점을 말한다
    '<p class="lede">기업의 재무적 선택은<br><b>산업과 거시 환경에 대한 이해</b>를 바탕으로 결정되어야 한다.</p><div class="parts">'
    + ''.join(f'<button data-goto="part{i}"><b>PART {i}</b>{PARTS[i]}</button>' for i in (1, 2, 3))
    + f'</div></div><div class="cover-art">{chip_svg()}</div>'
    '<div class="team"><div class="team-label">TEAM 12<small>가나다순</small></div>'
    + ''.join(f'<div class="member"><b>{n}</b><span>DFMBA · {sid}</span></div>' for n, sid in TEAM) + '</div>',
    kind='cover')


def divider(n, title, desc):
    road = ''.join(f'<div class="{"on" if i == n else ""}"><b>PART {i}</b>{PARTS[i]}</div>' for i in (1, 2, 3))
    add(f'part{n}', n, title, '',
        f'<div class="number">0{n}</div><div><div class="eyebrow">PART {n}</div><h1>{title}</h1>{desc}</div>'
        f'<div class="roadmap">{road}</div>', kind='divider')


# ═════════════════════════ PART 1 · Linear ═════════════════════════
divider(1, '케이스 이후의<br>Linear Technology',
        '<div class="qrow"><span><span class="qy">2003</span>년의 질문은</span><span class="q">“현금을 어떻게 나눌까”</span></div>'
        '<div class="qrow now"><span><span class="qy">오늘</span>의 질문은</span><span class="q">“그 우량 기업은 왜 사라졌나”</span></div>')

# ── 배당은 늘고 성장은 사라졌다 ──
LIN = D['linear']['series']
lin_rev = [x['revenue'] for x in LIN]
lin_dps = [x['dps'] for x in LIN]
lin_lab = ["'" + str(x['fy'])[2:] for x in LIN]
lin_tip = ['FY' + str(x['fy']) for x in LIN]
i11 = next(i for i, x in enumerate(LIN) if x['fy'] == 2011)
i16 = next(i for i, x in enumerate(LIN) if x['fy'] == 2016)
lin_cagr = cagr(lin_rev[i11], lin_rev[i16], 5)
lin_growth = [(lin_rev[i] / lin_rev[i - 1] - 1) * 100 for i in range(1, len(LIN))]
assert fmt(lin_cagr) == '−0.8' and (LIN[0]['fy'], LIN[-1]['fy']) == (2003, 2016)

lin_pad = {'l': 64, 'r': 26}
CHARTS['linear'] = {'panels': [
    dict(share=.56, title='Linear 매출', cap='매출 ($M)', labels=lin_lab, tipLabels=lin_tip, pre='$', suf='M', dec=0,
         x={'hide': True}, y={'step': 500, 'max': 1700, 'pre': '$'}, pad=lin_pad,
         series=[dict(name='매출', values=lin_rev, area=True, w=3, pts=[0, i11, i16],
                      ptText={0: f'${lin_rev[0]:,.0f}M', i11: f'${lin_rev[i11]:,.0f}M · 정점', i16: f'${lin_rev[i16]:,.0f}M'},
                      ptAnchor={0: 'start', i16: 'end'}, ptBelow=[i16])],
         bands=[dict(a=i11, b=i16, label=f'FY11–16 · 매출 연평균 {fmt(lin_cagr)}%')]),
    dict(share=.44, title='Linear 주당배당', cap='주당배당 ($)', type='bar', labels=lin_lab, tipLabels=lin_tip, pre='$', dec=2,
         y={'step': .5, 'max': 1.5, 'pre': '$', 'dec': 2}, pad=lin_pad,
         series=[dict(name='주당배당', values=lin_dps, color=C[2], pts=[0, len(LIN) - 1])]),
]}
CHARTS['linearGrowth'] = dict(
    title='Linear 연간 매출 성장률', cap='연간 매출 성장률 (전년 대비, %)', type='bar', labels=lin_lab[1:], tipLabels=lin_tip[1:],
    suf='%', dec=1, y={'min': -30, 'max': 40, 'step': 10, 'suf': '%'}, pad=lin_pad,
    series=[dict(name='매출 성장률', values=[round(v, 2) for v in lin_growth], div=True, pts=[0, 5, 7, 8, 12])],
    bands=[dict(a=i11, b=i16 - 1, label=f'FY2011 → FY2016 · 연평균 {fmt(lin_cagr)}%')],
    legendItems=[dict(c=C[0], t='증가', bar=True), dict(c=C[7], t='감소', bar=True)])

add('linear-cash', 1, '배당은 계속 늘었지만, 성장은 사라졌다', 'FY2003–2016 · 성숙한 현금창출 기업의 모습',
    '<div class="split"><div class="col">'
    '<div class="pills"><button data-linear="linear">매출 × 주당배당</button><button data-linear="linearGrowth">매출 성장률</button></div>'
    '<div id="linearChart" data-h="470"></div>'
    '<p class="note">회계연도. 배당은 연간 합계, 주가 수익률과 다름. 2011→16 매출 CAGR 직접 계산.</p></div>'
    '<div class="statcol">'
    '<button class="stat" data-linear="linear"><span class="kicker">① 배당은 계속 늘었다</span>'
    f'<span class="hero green">${lin_dps[0]:.2f} → ${lin_dps[-1]:.2f}</span>'
    '<span class="cap">2003–2016 주당배당<br>2016 영업이익률 <b>44.5%</b></span></button>'
    '<div class="then">그러나</div>'
    '<button class="stat" data-linear="linearGrowth"><span class="kicker">② 성장은 사라졌다</span>'
    f'<span class="hero amber">{fmt(lin_cagr)}%</span>'
    '<span class="cap">2011–2016 매출 연평균 성장</span></button>'
    '</div></div>',
    '회사는 잘 벌고 있었다. 성장의 다음 축이 약해졌을 뿐이다.', ['linear_10k_2016', 'linear_10k_2007'])

# ── 아날로그 4사: 둔화는 공통, 대응은 달랐다 ──
ORDER4 = ['Linear', 'Maxim', 'TI', 'ADI']
COL4 = dict(zip(ORDER4, C))
PEER = {n: [r['revenue'] for r in F['peers'][n]['series'][-6:]] for n in ('Maxim', 'TI', 'ADI')}
PEER['Linear'] = lin_rev[i11:i16 + 1]          # 지수로 바꾸므로 $M · $bn 단위 차이는 상관없다
for n in ('Maxim', 'TI', 'ADI'):
    assert [r['year'] for r in F['peers'][n]['series'][-6:]] == list(range(2011, 2017)), n
peer_idx = {n: [v / PEER[n][0] * 100 for v in PEER[n]] for n in ORDER4}
peer_cagr = {n: cagr(PEER[n][0], PEER[n][-1], 5) for n in ORDER4}

CHARTS['peersIdx'] = dict(
    title='아날로그 4사 매출 지수 (FY2011=100)', labels=[f'FY{y}' for y in range(11, 17)], dec=1, fs=13,
    y={'min': 80, 'max': 120, 'step': 10, 'fit': True}, refs=[dict(v=100, label='FY2011 = 100', left=True)],
    series=[dict(name=n, values=[round(v, 2) for v in peer_idx[n]], color=COL4[n], end=True, w=3.5 if n == 'Linear' else 2)
            for n in ORDER4],
    notes=[dict(i=4, v=peer_idx['ADI'][4], text='Hittite 인수(2014) 반영', dx=-12, dy=5, anchor='end')])


def choice_row(name, color, tag, desc, out_head, out_sub='', gone=False, prod=''):
    """prod 를 주면 이름 아래에 주력 제품군을 한 줄로 적는다."""
    line = f'<div class="prod"><em>주력</em>{prod}</div>' if prod else ''
    return (f'<div class="choice-row{" gone" if gone else ""}"><div><div class="nm"><i style="background:{color}"></i>{name}'
            f'<span class="tag">{tag}</span></div>{line}<p>{desc}</p></div><div class="out"><b>{out_head}</b>{out_sub}</div></div>')


add('linear-peers', 1, '성장 둔화는 공통이었다. 대응은 달랐다',
    '아날로그 4사 매출 지수 (FY2011=100) · 기업별 회계연도 · 인수 효과 포함',
    '<div class="split s55"><div class="col">' + slot('peersIdx', 392)
    + '<div class="cagr">' + ''.join(
        f'<div><span><i style="background:{COL4[n]}"></i>{n}</span><b>{fmt(peer_cagr[n], sign=True)}%</b></div>' for n in ORDER4)
    + '</div><p class="note">FY2011→2016 매출 연평균 성장률 · 기업별 회계연도. ADI에는 Hittite 인수(2014) 효과가 포함돼 '
      '유기적 성장률 비교는 아님.</p></div>'
    '<div class="choice p3"><div class="choice-h"><span>주력 제품군 · 성장 둔화에 대한 대응</span><span style="text-align:right">그 이후</span></div>'
    + choice_row('Linear', COL4['Linear'], '집중', '고성능 아날로그 한 우물 · 영업이익률 44.5%', '2017 ADI에 편입', '독립 상장 종료', True,
                 prod='전원 관리 IC <small>매출의 59% · FY2015</small>')
    + choice_row('Maxim', COL4['Maxim'], '집중', '대형 인수 없이 독자 노선 유지', '2021 ADI에 편입', '독립 상장 종료', True,
                 prod='혼합신호 · 전력 관리 IC')
    + choice_row('TI', COL4['TI'], '확장', '제품군·자체 제조 확대 · 2011 National 인수', '독립 유지', '아날로그 1위',
                 prod='아날로그 · 임베디드 프로세서')
    + choice_row('ADI', COL4['ADI'], '확장', 'Hittite(2014) → Linear(2017) → Maxim(2021)', '인수 주체', '2025 아날로그 2위',
                 prod='데이터 컨버터 · 증폭기 · RF')
    + '<div class="insight"><b>집중</b>을 택한 두 회사는 ADI에 편입됐고,<br><b>확장</b>(규모 · 인수)을 택한 두 회사는 독립을 지켰다.'
      '<small>순위: IC Insights(2015) · GMI(2025 추정)</small></div>'
    '</div></div>',
    '성장 둔화는 모두에게 왔다. 갈린 것은 그 다음의 선택 — 집중이냐, 확장이냐였다.',
    ['linear_10k_2016', 'peer_TI', 'peer_ADI', 'peer_Maxim', 'NATIONAL', 'MAXIM', 'linear_close', 'icinsights_analog2015',
     'analog_rank2025', 'adi_presentation_2016', 'analog_technology'],
    method='주력 제품군은 각 회사의 연차보고서와 ADI의 인수 발표 자료(2016.07)에 나온 사업 설명을 줄여 적은 것이며 매출 구성 통계가 아님. '
           'Linear의 전원 관리 비중 59%는 ADI 인수 발표 자료의 FY2015 수치. Maxim의 인수 이력(Volterra 2013 등)은 규모가 작아 '
           '‘대형 인수 없이’로 요약함. 조사 기준 2026-11-08 (제품군 표기는 2026-11-11).')

# ── 인수 협상: 독자 성장의 가치 vs 지금의 프리미엄 ──
DEAL = HIS['deal']
OFFER = {t['date']: t for t in DEAL['timeline']}
PX_CLOSE, PX_FINAL = DEAL['close_2016_07_25'], DEAL['implied_value']
premium = (PX_FINAL / PX_CLOSE - 1) * 100
cash_share = 46 / PX_FINAL * 100                       # 대가: 주당 현금 $46 + ADI 0.2321주
VAL = sorted((dict(v, mid=(v['lo'] + v['hi']) / 2) for v in DEAL['valuation']), key=lambda v: v['mid'])
DCF = next(v for v in VAL if v['method'] == 'DCF')
assert round(premium) == DEAL['premium_pct']['close'] == 24 and round(cash_share) == 77
assert all(v['mid'] < PX_FINAL for v in VAL), '제안가는 다섯 범위의 중간값보다 모두 높다'
assert {v['method'] for v in VAL if v['hi'] >= PX_FINAL} == {'DCF', '유사 거래 P/E'}, '세 범위는 상단도 넘는다'
assert fmt(DEAL['projection']['revenue_cagr_pct']) == '7.7'


def tip(title, *lines):
    return ' data-tip="' + escape('|'.join((title,) + lines), quote=True) + '"'


def negotiation_svg():
    """협상 흐름. 가로축은 사건 순서이며 시간 간격에 비례하지 않는다."""
    W, H, base, k = 709, 438, 408, 21.2

    def y(p):
        return round(base - (p - 44) * k, 1)

    dates = ['2015-08-14', '2015-09-04', '2016-04-05', '2016-05-18', '2016-06-22', '2016-07-26']
    xs = dict(zip(dates, [100, 196, 330, 428, 528, 640]))
    y1, y2, y3 = (y(OFFER[d]['price']) for d in ('2015-08-14', '2016-04-05', '2016-06-22'))
    y3rd, yf, yc = y(OFFER['2016-05-18']['price']), y(PX_FINAL), y(PX_CLOSE)
    adi = C[3]
    s = []
    for p in (45, 50, 55, 60):
        s.append(f'<line x1="52" x2="{W - 8}" y1="{y(p)}" y2="{y(p)}" stroke="{GRID}"/>')
        s.append(T(46, y(p) + 4, f'${p}', 12, INK3, 'end', cls='tn'))
    s.append(f'<path d="M52,{base}H255M271,{base}H{W - 8}" stroke="{AXIS}" fill="none"/>')
    s.append(f'<path d="M256,{base + 6}l6,-12M264,{base + 6}l6,-12" stroke="{INK3}" stroke-width="1.5" fill="none"/>')
    for d, x in xs.items():
        s.append(T(x, base + 22, d[:7].replace('-', '.'), 12, INK3, 'middle', cls='tn'))
    # ADI 제안가: 거절 뒤 7개월은 제안이 없던 구간(점선)
    s.append(f'<path d="M100,{y1}H196" fill="none" stroke="{adi}" stroke-width="3" stroke-linecap="round"/>')
    s.append(f'<path d="M204,{y1}H330" fill="none" stroke="{INK3}" stroke-width="2" stroke-dasharray="3 6"/>')
    s.append(f'<path d="M330,{y1}V{y2}H528V{y3}H640V{yf}" fill="none" stroke="{adi}" stroke-width="3" '
             'stroke-linejoin="round" stroke-linecap="round"/>')
    # 프리미엄: 발표 전 종가 → 합의 가격
    s.append(f'<line x1="640" x2="640" y1="{yc - 10}" y2="{yf + 20}" stroke="{GREEN}" stroke-width="3"/>')
    s.append(f'<polygon points="640,{yf + 9} 633,{yf + 22} 647,{yf + 22}" fill="{GREEN}"/>')
    s.append(f'<circle cx="640" cy="{yc}" r="6" fill="{SURF}" stroke="{INK2}" stroke-width="2"/>')
    for x, yy in ((100, y1), (330, y2), (528, y3)):
        s.append(f'<circle cx="{x}" cy="{yy}" r="6" fill="{adi}" stroke="{SURF}" stroke-width="2"/>')
    s.append(f'<circle cx="428" cy="{y3rd}" r="6" fill="{MUTE}" stroke="{SURF}" stroke-width="2"/>')
    s.append(f'<circle cx="640" cy="{yf}" r="7.5" fill="{GREEN}" stroke="{SURF}" stroke-width="2"/>')
    s.append(f'<circle cx="196" cy="{y1}" r="11" fill="{SURF}"/>'
             f'<path d="M189,{y1 - 7}l14,14M203,{y1 - 7}l-14,14" stroke="{RED}" stroke-width="3" stroke-linecap="round"/>')
    # 라벨
    s.append(T(100, y1 - 28, '$51.50', 16, INK, 'middle', 800, 'halo tn'))
    s.append(T(100, y1 - 12, '주식 75% · 현금 25%', 11.5, INK2, 'middle', cls='halo'))
    s.append(T(196, y1 + 25, '이사회 거절', 13, INK, 'middle', 700, 'halo'))
    s.append(T(196, y1 + 42, '“상당히 저평가”', 11.5, INK2, 'middle', cls='halo'))
    s.append(T(267, y1 - 9, '2016.03까지 접촉 없음', 11, INK3, 'middle', cls='halo'))
    s.append(T(342, y2 + 24, '$58.00', 16, INK, weight=800, cls='halo tn'))
    s.append(T(342, y2 + 40, '현금 75% · 주식 25%', 11.5, INK2, cls='halo'))
    s.append(T(428, y3rd + 23, '$54.00 · 제3자', 13, INK, 'middle', 700, 'halo'))
    s.append(T(428, y3rd + 39, '전액 현금 제안', 11.5, INK2, 'middle', cls='halo'))
    s.append(T(528, y3 - 28, '$60.00', 16, INK, 'middle', 800, 'halo tn'))
    s.append(T(528, y3 - 12, '‘best and final’', 11.5, INK2, 'middle', cls='halo'))
    s.append(T(640, yf - 38, '$60.05', 21, INK, 'middle', 900, 'halo tn'))
    s.append(T(640, yf - 19, '7/26 계약 체결', 11.5, INK2, 'middle', cls='halo'))
    mid = (yc + yf) / 2
    s.append(T(626, mid + 2, f'+{premium:.0f}%', 25, INK, 'end', 900, 'halo tn'))
    s.append(T(626, mid + 20, '프리미엄', 12.5, INK2, 'end', cls='halo'))
    s.append(f'<text x="626" y="{yc + 4.5}" text-anchor="end" font-size="12.5" fill="{INK2}" class="halo">7/25 종가 '
             f'<tspan fill="{INK}" font-weight="700">${PX_CLOSE:.2f}</tspan></text>')
    # 마우스를 올리면 원문 요지
    hits = [(100, y1, '2015.08.14 · ADI 첫 제안 $51.50', OFFER['2015-08-14']['text']),
            (196, y1, '2015.09.04 · Linear 이사회 거절', OFFER['2015-09-04']['text']),
            (330, y2, '2016.04.05 · ADI 재제안 $58.00', OFFER['2016-04-05']['text']),
            (428, y3rd, '2016.05.18 · 제3자(Company A) $54.00', OFFER['2016-05-18']['text']),
            (528, y3, '2016.06.22 · ADI 최종 제안 $60.00', OFFER['2016-06-22']['text']),
            (640, yf, '2016.07.26 · 합병계약 $60.05', OFFER['2016-07-26']['text']),
            (640, yc, '2016.07.25 · 발표 전 종가 $48.47',
             f'합의 가격은 종가 대비 +{DEAL["premium_pct"]["close"]}%',
             f'30일 평균 대비 +{DEAL["premium_pct"]["avg30d"]}% · 60일 평균 대비 +{DEAL["premium_pct"]["avg60d"]}%')]
    for x, yy, *t in hits:
        s.append(f'<circle cx="{x}" cy="{yy}" r="17" fill="transparent"{tip(*t)}/>')
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            'aria-label="2015년 8월 첫 제안부터 2016년 7월 계약까지 주당 제안가의 변화">' + ''.join(s) + '</svg>')


VAL_LABEL = {   # (평가 방법, 범위 하단) → 화면에 쓸 두 줄 이름
    ('동종 상장사 P/E', 38.28): ('동종 상장사 P/E', '애널리스트 전망 · 17–23배'),
    ('동종 상장사 P/E', 41.12): ('동종 상장사 P/E', '경영진 계획 · 17–23배'),
    ('유사 거래 매출 배수', 44.89): ('유사 거래 · 매출 배수', '향후 12개월 매출 · 6.5–8.5배'),
    ('유사 거래 P/E', 45.1): ('유사 거래 · P/E', '향후 12개월 이익 · 19–29배'),
    ('DCF', 51.51): ('DCF · 현금흐름 할인', '경영진 계획 · 할인율 8–10%'),
}


def valuation_svg():
    """가치 범위(풋볼 필드): 다섯 평가 범위 위에 발표 전 종가와 합의 가격을 겹친다."""
    W, top, pitch = 581, 24, 46
    bottom = top + pitch * len(VAL) + 2
    H = bottom + 22

    def x(p):
        return round(196 + (p - 35) * 8.4, 1)

    s = []
    for p in (40, 50, 60, 70):
        s.append(f'<line x1="{x(p)}" x2="{x(p)}" y1="{top}" y2="{bottom}" stroke="{GRID}"/>')
        s.append(T(x(p), bottom + 16, f'${p}', 12, INK3, 'middle', cls='tn'))
    for i, v in enumerate(VAL):
        cy, key = top + 1 + pitch * i + pitch // 2, v is DCF
        head, sub = VAL_LABEL[(v['method'], v['lo'])]
        s.append(T(0, cy - 3, head, 13.5, INK, weight=700))
        s.append(T(0, cy + 13, sub, 11.5, INK3))
        s.append(f'<rect x="{x(v["lo"])}" y="{cy - 9}" width="{round(x(v["hi"]) - x(v["lo"]), 1)}" height="18" rx="4" '
                 f'fill="{C[0] if key else MUTE}"/>')
        s.append(f'<line x1="{x(v["mid"])}" x2="{x(v["mid"])}" y1="{cy - 13}" y2="{cy + 13}" stroke="{INK}" stroke-width="2"/>')
        s.append(T(W, cy + 4, f'${v["lo"]:.2f} – ${v["hi"]:.2f}', 11.5, INK if key else INK2, 'end', 700 if key else None, 'tn'))
    xc, xf = x(PX_CLOSE), x(PX_FINAL)
    s.append(f'<line x1="{xc}" x2="{xc}" y1="{top - 4}" y2="{bottom}" stroke="{INK2}" stroke-width="1.5" stroke-dasharray="4 4"/>')
    s.append(f'<line x1="{xf}" x2="{xf}" y1="{top - 4}" y2="{bottom}" stroke="{GREEN}" stroke-width="2.5"/>')
    s.append(T(xc - 6, 13, f'7/25 종가 ${PX_CLOSE:.2f}', 12, INK2, 'end', cls='tn'))
    s.append(T(xf + 6, 13, f'ADI 제안 ${PX_FINAL:.2f}', 13.5, INK, weight=800, cls='tn'))
    s.append(f'<line x1="1" x2="1" y1="{bottom + 6}" y2="{bottom + 18}" stroke="{INK}" stroke-width="2"/>'
             + T(8, bottom + 16, '범위의 중간값', 11.5, INK3))
    for i, v in enumerate(VAL):                # 마우스를 올리면 전제 설명
        s.append(f'<rect x="0" y="{top + 1 + pitch * i}" width="{W}" height="{pitch}" fill="transparent"'
                 + tip(f'{v["method"]} · ${v["lo"]:.2f}–{v["hi"]:.2f}', v['basis'], f'중간값 ${v["mid"]:.2f}') + '/>')
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            'aria-label="재무자문사의 다섯 가지 주당 가치 범위와 발표 전 종가, ADI 제안가 비교">' + ''.join(s) + '</svg>')


add('linear-deal', 1, '독자 성장의 가치 vs 지금의 프리미엄',
    '2015.08 첫 제안은 거절 → 2016.07 $60.05에 합의 · 처음부터 매각을 택한 것은 아니었다',
    '<div class="split s55"><div class="col">'
    '<div class="khead"><span class="kicker">협상 흐름 · 주당 제안가 ($)</span>'
    + legend([('ln', C[3], 'ADI 제안가'), ('dot', MUTE, '제3자 제안'), ('ring', INK2, '발표 전 종가')])
    + '</div>' + negotiation_svg()
    + '<div class="dealend"><em>결말</em><span><b>2017.03.10 인수 완료</b> → Linear, 독립 상장회사로서의 역사 종료</span></div>'
    '<p class="note">Linear DEFM14A(2016.09) “Background of the Merger”. 가로축은 사건 순서 · 점에 마우스를 올리면 세부 내용.</p></div>'
    '<div class="deal-right"><span class="kicker">가치 범위 · 주당 ($) — Linear 측 재무자문사(Qatalyst)의 분석</span>'
    + valuation_svg()
    + '<div class="vs lt">'
    f'<div><span class="k">독자 성장의 가치 · DCF 중간값</span><div class="v">${DCF["mid"]:.2f}'
    f'<small class="rng">범위 ${DCF["lo"]:.2f}–{DCF["hi"]:.2f}</small></div>'
    f'<p>전제: 경영진 계획 매출 연 +{fmt(DEAL["projection"]["revenue_cagr_pct"])}%<br>직전 5년 실적은 연 <b>{fmt(lin_cagr)}%</b></p></div>'
    '<span class="sign">&lt;</span>'
    f'<div class="win"><span class="k">지금의 프리미엄</span><div class="v">${PX_FINAL:.2f}'
    f'<small class="rng">7/25 종가 ${PX_CLOSE:.2f} 대비 +{premium:.0f}%</small></div>'
    f'<p>대가의 약 {cash_share:.0f}%가 현금 = 확정 가치<br>지난 15년 어느 종가보다 높은 가격</p></div></div>'
    '<p class="note" style="margin-top:0">제안가는 다섯 평가 범위 중 세 개의 상단을 넘고, 나머지 둘(DCF · 유사 거래 P/E)에서도 중간값보다 높다. '
    '이사회가 명시한 위험: 독립을 유지하면 주가가 합병 대가 이상으로 거래되지 못할 수 있다 — “단기에도, 장기간에도, 혹은 영영”.</p>'
    '</div></div>',
    '독자 성장의 기대가치보다 지금 확정되는 프리미엄이 컸다 — 인수는 실패가 아니라 가치 실현 방식의 선택이었다.',
    ['linear_defm14a', 'linear_defm14a_val', 'linear_deal', 'linear_pr_sec', 'linear_close'],
    method='가치 범위는 Linear 이사회의 재무자문사가 경영진 계획·애널리스트 전망을 바탕으로 낸 분석이며 확정 가치가 아님. '
           '“DCF 중간값”은 범위 양 끝의 산술 평균으로, 위임장 서류의 수치가 아니라 이 덱에서 직접 계산한 값. 조사 기준 2026-11-08.',
    tables=[dict(title='협상 일지 (Linear DEFM14A)', head=['날짜', '주체', '주당 가격($)', '내용'],
                 rows=[[t['date'], t['who'], f'{t["price"]:.2f}' if 'price' in t else '—', t['text']] for t in DEAL['timeline']]),
            dict(title='재무자문사 가치평가 범위 (주당 $)', head=['방법', '전제', '하단', '상단', '중간값'],
                 rows=[[v['method'], v['basis'], f'{v["lo"]:.2f}', f'{v["hi"]:.2f}', f'{v["mid"]:.2f}'] for v in VAL])],
    ref=True)

# ── 왜 팔렸나: 세 가지 시대 배경 ──
VIZ_H = 280


def system_svg():
    """01 수요: 신호 체인의 네 블록 + 그 전부에 전력을 대는 전원 관리, 그리고 합쳤을 때의 대응 시장."""
    W, adi, lin = 388, C[3], C[0]
    s = [T(0, 12, '물리 세계의 신호 → 디지털 처리 → 연결', 11.5, INK3)]
    blocks = [('센서', '온도 · 압력 · 전류', False), ('증폭 · 변환', '증폭기 · 컨버터', True),
              ('프로세서', 'MCU · FPGA', False), ('통신 · RF', 'RF · 인터페이스', True)]
    for i, (name, sub, is_adi) in enumerate(blocks):
        x = i * 100
        fill, stroke = ('rgba(201,133,0,.2)', adi) if is_adi else ('#0c1c2c', '#2b4a62')
        s.append(f'<line x1="{x + 44}" x2="{x + 44}" y1="77" y2="114" stroke="{lin}" stroke-width="1.5" stroke-dasharray="3 3"/>')
        s.append(f'<rect x="{x + .5}" y="22.5" width="87" height="54" rx="6" fill="{fill}" stroke="{stroke}"/>')
        s.append(T(x + 44, 46, name, 13.5, INK, 'middle', 700))
        s.append(T(x + 44, 63.5, sub, 10.5, INK2, 'middle'))
        if i:
            s.append(f'<path d="M{x - 10},49.5h7m-3,-3l3,3l-3,3" fill="none" stroke="{INK3}" stroke-width="1.25"/>')
    s.append(f'<rect x=".5" y="114.5" width="{W - 1}" height="38" rx="6" fill="rgba(57,135,229,.22)" stroke="{lin}"/>')
    s.append(T(W / 2, 138.5, '전원 관리 — 모든 블록에 전력을 공급', 14, INK, 'middle', 700))
    s.append(f'<rect x="0" y="166" width="10" height="10" rx="2" fill="{adi}"/>' + T(15, 175, 'ADI의 강점: 컨버터·증폭기·RF', 12, INK2))
    s.append(f'<rect x="204" y="166" width="10" height="10" rx="2" fill="{lin}"/>' + T(219, 175, 'Linear의 강점: 전원 관리', 12, INK2))
    # 대응 가능 시장: $1bn = 18px
    u, x0 = 18, 90
    s.append(T(0, 206, '대응 가능 시장(TAM) · 2015 · 산업 · 통신 인프라 · 자동차', 11.5, INK3))
    s.append(T(0, 233, 'ADI 단독', 12.5, INK2))
    s.append(f'<rect x="{x0}" y="218" width="{8 * u}" height="20" rx="3" fill="{adi}"/>')
    s.append(T(x0 + 8 * u + 6, 233, '$8bn', 12.5, INK, weight=700, cls='tn'))
    s.append(T(0, 265, 'ADI + Linear', 12, INK, weight=700))
    s.append(f'<rect x="{x0}" y="250" width="{8 * u}" height="20" rx="3" fill="{adi}"/>')
    s.append(f'<rect x="{x0 + 8 * u + 2}" y="250" width="{6 * u - 2}" height="20" rx="3" fill="{lin}"/>')
    s.append(T(x0 + 11 * u + 1, 264.5, '+ 전원 관리 $6bn', 11, '#fff', 'middle', 700))
    s.append(T(x0 + 14 * u + 6, 265, '$14bn', 12.5, INK, weight=800, cls='tn'))
    return (f'<svg width="{W}" height="{VIZ_H}" viewBox="0 0 {W} {VIZ_H}" role="img" aria-label="신호 체인 네 블록과 전원 관리, '
            'ADI 단독 8십억 달러에서 Linear를 더하면 14십억 달러로 넓어지는 대응 시장">' + ''.join(s) + '</svg>')


FF = [(d[:7], v) for d, v in M['FEDFUNDS']]
ff00 = [(d, v) for d, v in FF if '2000-01' <= d <= '2017-12']
at00 = {d: i for i, (d, _) in enumerate(ff00)}
CHARTS['ff2000'] = dict(
    title='미국 연방기금 실효금리 2000–2017', cap='미국 연방기금 실효금리 (월평균, %)', fs=11, suf='%', dec=2, legend=False,
    labels=[d.replace('-', '.') for d, _ in ff00], y={'max': 7, 'step': 2},
    x={'ticks': [at00[f'{y}-01'] for y in range(2000, 2017, 4)], 'map': {at00[f'{y}-01']: str(y) for y in range(2000, 2017, 4)}},
    series=[dict(name='연방기금 실효금리', values=[v for _, v in ff00], area=True)],
    bands=[dict(a=at00['2008-12'], b=at00['2015-12'], label='제로금리 7년')],
    marks=[dict(i=at00['2016-07'], label='2016.07 인수 계약', anchor='end', y=14)])
MNA = [('2010–14 평균', 12.6), ('2015', 107.3), ('2016', 99.8), ('2017', 27.7), ('2018', 25.9)]   # IC Insights, 발표액 $bn
mna_multiple = (MNA[1][1] + MNA[2][1]) / 2 / MNA[0][1]
assert round(mna_multiple) == 8
CHARTS['mna'] = dict(
    title='반도체 M&A 발표액', cap='반도체 M&A 발표액 ($bn)', type='bar', fs=11, pre='$', suf='bn', dec=1, legend=False,
    labels=[k for k, _ in MNA], y={'n': 3, 'pre': '$'},
    series=[dict(name='M&A 발표액', values=[v for _, v in MNA], hi=[1, 2], pts=[0, 1, 2])])


def ctx_panel(kicker, title, viz, text, note):
    return (f'<article class="panel"><div class="kicker">{kicker}</div><h3>{title}</h3><div class="viz">{viz}</div>'
            f'<p>{text}</p><div class="note">{note}</div></article>')


add('linear-context', 1, '왜 팔렸나: 세 가지 시대 배경',
    '배당이라는 선택이 틀려서가 아니다 — 시대의 흐름(통합 수요 + 초저금리 M&amp;A)이 독자 생존을 허용하지 않았다',
    '<div class="ctx">'
    + ctx_panel('01 · 수요', '고객은 통합 솔루션을 원했다', system_svg(),
                '자동차 전장·산업 자동화·통신 인프라처럼 <b>시스템이 복잡해질수록</b> 신호 처리·전력·연결이 한 설계 안에서 맞물려야 한다. '
                '고객사는 자체 아날로그 설계 역량을 줄이면서 검증된 조합을 <b>한 파트너</b>에게 맡기려 했다.',
                'ADI CEO Roche: “고객은 더 많은 시스템 수준의 솔루션을 요구한다” · TAM $8bn → $14bn은 인수 발표 자료(2016.07) · '
                'Linear 매출의 59%가 전원 관리(FY2015)')
    + ctx_panel('02 · 자본', '초저금리가 M&amp;A를 뒷받침했다', slot('ff2000', VIZ_H),
                '2008.12–2015.12 <b>제로금리 7년</b>, 계약 직전 미 10년물 국채금리는 <b>당시 사상 최저 1.37%</b>(2016.07). '
                '인수자의 차입 조달 여건이 좋아졌고, 현금창출 자산의 가치도 높아졌다.',
                'ADI 조달 계획: 신규 장기부채 약 $7.3bn + 신주 약 5,800만 주 + 보유 현금 (인수 발표문)')
    + ctx_panel('03 · 규모', '포트폴리오의 폭이 중요해졌다', slot('mna', VIZ_H),
                f'2015–16년 반도체 M&amp;A 발표액은 직전 5년 평균의 <b>약 {mna_multiple:.0f}배</b>. 아날로그 1위 TI의 점유율이 <b>18%</b>일 때 '
                'Linear는 <b>3%</b>(8위) — 제품·고객·판매망의 폭이 경쟁 조건이 됐다.',
                'IC Insights · 발표액 기준 · 점유율은 2015 아날로그 IC 시장($47.0bn) 기준')
    + '</div>',
    '리니어는 마지막까지 좋은 회사였다. 환경이 바뀌면, 좋은 회사도 사라질 수 있다.',
    ['linear_deal', 'linear_finance', 'adi_presentation_2016', 'mckinsey_mna', 'linear_pr_sec', 'fred_ff', 'fred_dgs10',
     'fed_history', 'icinsights_mna', 'icinsights_analog2015', 'adi_10k_2017'],
    tables=[dict(title='대응 가능 시장 (ADI 인수 발표 자료, 2015 기준 $bn)', head=['구분', '컨버터', '증폭기', '인터페이스', '클럭·타이밍', '전원 관리', '합계'],
                 rows=[['ADI 단독', '3', '3', '1', '1', '—', '8'], ['ADI + Linear', '3', '3', '1', '1', '6', '14']])])

# ── 섹터별 매출 상위: 미국 Fortune 500, 1995 → 2025 · 5년 간격 ──
SECTOR_YEARS = RAW_SECTOR['years']
assert SECTOR_YEARS == [1995, 2000, 2005, 2010, 2015, 2020, 2025] and RAW_SECTOR['top'] == 10
assert RAW_SECTOR['listYears'] == [y + 1 for y in SECTOR_YEARS]
SECTOR_NOTE = {     # 원자료의 연결 규칙 · 유의점 가운데 그 섹터를 읽을 때 꼭 필요한 것
    'communication': 'AT&T는 2005년 SBC가 인수해 사명을 승계 — 존속 법인(SBC) 기준으로 연결',
    'utilities': '2000년 매출은 에너지 트레이딩 총액 계상으로 부풀려짐',
    'financials': '2005년은 결산 지연으로 Fannie Mae · Freddie Mac 제외',
}


# 함께 볼 기업(v5): 1위는 아니지만 순위가 오르내린 모습을 따라가 볼 곳. 섹터마다 변화의 크기가 다르다는 것을 보이기 위해
# 1위 기업(주황 · 파랑)과 다른 색으로 칸과 선을 칠한다. 키는 sector_us.json 의 기업 키
SECTOR_FOCUS = {
    'staples': ['kroger', 'target', 'costco'], 'energy': ['chevron'], 'discretionary': ['ford-motor', 'home-depot'],
    'materials': ['international-paper'], 'industrials': ['raytheon-technologies', 'lockheed-martin'],
    'it': ['hp', 'microsoft', 'motorola-solutions'], 'utilities': ['southern'], 'communication': ['verizon', 'att'],
    'financials': ['jpmorgan-chase', 'bank-of-america-corp'], 'healthcare': ['mckesson', 'cardinal-health', 'merck'],
}


def sector_view(sec):
    """화면에 쓰는 항목만 추린다. 1위의 이동은 같은 기업이 이어지는 동안 하나로 묶고 가장 최근 사명으로 적는다."""
    snaps = {str(y): {'rows': [{k: r[k] for k in ('key', 'name', 'revenue', 'rankOverall', 'gap') if k in r}
                               for r in sec['snapshots'][str(y)]['rows']]} for y in SECTOR_YEARS}
    assert all(len(v['rows']) == 10 for v in snaps.values()), sec['id']
    chain = []
    for y in SECTOR_YEARS:
        top = snaps[str(y)]['rows'][0]
        if chain and chain[-1][0] == top['key']:
            chain[-1][1] = top['name']
        else:
            chain.append([top['key'], top['name']])
    first, last = ({r['key'] for r in snaps[str(y)]['rows']} for y in (SECTOR_YEARS[0], SECTOR_YEARS[-1]))
    m = sec['metrics']
    assert len(chain) - 1 == m['leaderChanges'] and len(first & last) == m['stay30'], sec['id']
    focus = SECTOR_FOCUS[sec['id']]
    seen = {r['key'] for v in snaps.values() for r in v['rows']}
    ends = {snaps[str(y)]['rows'][0]['key'] for y in (SECTOR_YEARS[0], SECTOR_YEARS[-1])}     # 이미 주황 · 파랑으로 칠하는 1위 기업
    assert 1 <= len(focus) <= 3 and set(focus) <= seen and not set(focus) & ends, (sec['id'], focus)
    return dict(id=sec['id'], name=sec['name'], note=SECTOR_NOTE.get(sec['id'], ''), changes=m['leaderChanges'], stay=m['stay30'],
                leaders=[name for _, name in chain], focus=focus, snapshots=snaps)


def sector_table(sec):
    cols = [sec['snapshots'][str(y)]['rows'] for y in SECTOR_YEARS]
    filled = any(r.get('gap') for c in cols for r in c)        # 아카이브에 빠져 있어 보완 자료로 채운 칸
    return dict(title=f'{sec["name"]} · 매출 Top 10 ($bn)' + (' · †는 보완 자료의 값' if filled else ''),
                head=['순위'] + [str(y) for y in SECTOR_YEARS],
                rows=[[str(i + 1)] + [f'{c[i]["name"]} {c[i]["revenue"]:,.1f}' + (' †' if c[i].get('gap') else '') for c in cols]
                      for i in range(10)])


SECTOR = dict(
    years=SECTOR_YEARS,
    scope='Fortune 500 매출($bn) · 연도는 매출 연도 · 섹터는 Fortune 업종을 묶은 분석용 분류 · 합병은 존속 법인으로 연결',
    # 매출 1위가 덜 바뀐 섹터부터 (같으면 1995년 Top 10이 2025년에 더 많이 남은 섹터 먼저)
    sectors=sorted((sector_view(s) for s in RAW_SECTOR['sectors']), key=lambda s: (s['changes'], -s['stay'])))
SECTOR_BY_ID = {s['id']: s for s in SECTOR['sectors']}
sector_stable = [s['name'] for s in SECTOR['sectors'] if not s['changes']]
sector_span = SECTOR_YEARS[-1] - SECTOR_YEARS[0]
assert len(SECTOR_BY_ID) == 10 and sector_stable == ['필수소비재', '에너지'] and sector_span == 30, sector_stable
assert SECTOR_BY_ID['it']['leaders'] == ['IBM', 'Hewlett-Packard', 'Apple'], SECTOR_BY_ID['it']['leaders']
assert set(SECTOR_FOCUS) == set(SECTOR_BY_ID)
sector_stable_txt = ' · '.join(sector_stable)
gap_in_top = ' · '.join(GAPS['inTop'])

add('sector-ranking', 1, '1위가 바뀌지 않는 산업, 1위가 바뀌는 산업',
    f'미국 Fortune 500 · 10개 섹터 매출 Top 10 · {SECTOR_YEARS[0]} → {SECTOR_YEARS[-1]} · 5년 간격',
    '<div class="sector"><div class="sector-nav"><div class="sector-h"><span>섹터</span><span>1위 교체</span></div>'
    '<div id="sectorPills"></div><button id="sectorPlay">▶ 산업 순환</button>'
    '<div class="sector-keep" id="sectorKeep"></div></div>'
    '<div class="col"><div id="bump" data-h="454" style="min-height:454px"></div><div id="sectorStat"></div>'
    '<p class="note" id="sectorScope"></p></div></div>',
    f'{sector_stable_txt}의 1위는 {sector_span}년간 그대로다. IT의 1위는 IBM → HP → Apple — 산업의 중심이 이동하면 선두도 바뀐다.',
    [f'fortune500_{y}' for y in RAW_SECTOR['listYears']] + ['fortune500_gap'],
    method=f'Fortune 500 N년판은 직전 회계연도(N−1)의 매출 순위이므로 화면에는 매출 연도({SECTOR_YEARS[0]}–{SECTOR_YEARS[-1]})로 표시. '
           f'5년 간격 {len(SECTOR_YEARS)}개 시점만 비교하므로 그 사이의 순위 변동은 반영되지 않음. '
           + ' '.join(RAW_SECTOR['classification'] + RAW_SECTOR['continuity'] + RAW_SECTOR['caveats'])
           + f' 부동산 섹터는 제외({RAW_SECTOR["excluded"]["realestate"]["reason"]}). '
           f'Fortune 아카이브 페이지에 빠져 있던 순위 {GAPS["added"]}건은 공개 데이터셋 {GAPS["source"]["name"]}으로 채웠고'
           f'(이 가운데 Top 10에 들어간 것은 {len(GAPS["inTop"])}건: {gap_in_top}), '
           f'2001년판에서 순위·매출이 어긋난 {GAPS["dropped"]}건은 같은 자료로 바로잡음. '
           '회사 전체 연결매출 기준이어서 반도체 매출·시가총액 순위와 다르며, 합병 전후로 사업 범위와 회계기준이 달라 '
           '매출 증가를 성장률로 해석하면 안 됨. 색을 칠한 ‘함께 볼 기업’은 1위가 아닌 기업 가운데 순위 변화를 따라가 보려고 고른 곳이며, '
           '옆의 순위는 Top 10에 처음 나온 시점 → 2025년(Top 10 밖이면 권외). 조사 기준 2026-11-09.',
    tables=[sector_table(sec) for sec in SECTOR['sectors']], ref=True)


# ═════════════════════════ PART 2 · 반도체 산업의 변천 ═════════════════════════
# 두 축: (번호, 이름, 간지에 적는 그 축의 내용, 정리 장표에 적는 그 축이 하는 일). 간지와 정리 장표(industry-lessons)가 함께 쓴다
AXES = [('축 1', '수요의 이동과 밸류체인 분업화', 'IDM vs Fabless–Foundry', '주도 기업과 사이클을 만든다'),
        ('축 2', '자본력과 M&amp;A 재편', '아날로그 · 팹리스 대형화 → AI 전용 칩 시대로의 진화', '사이클을 버티고 재편을 이끈다')]
divider(2, '반도체 산업의 변천',
        '<p class="dv-desc">기술 스펙이 아니라 <strong>두 개의 축</strong>으로 읽는다.</p>'
        + ''.join(f'<div class="axrow"><em>{k}</em><b>{name}</b><span>{scope}</span></div>' for k, name, scope, _ in AXES))


# ── 밸류체인 × 제품군: 누가 어디서 무엇을 만드는가 (v4 신규 · v5 에서 제3기 뒤로 옮기고 색으로 두 축을 구분) ──
# 가로는 밸류체인 단계(위쪽의 화살표 띠), 세로는 제품군(줄마다 다른 색). 분업(로직)은 세 조각의 사슬로, IDM(메모리 · 아날로그)은
# 긴 띠 하나로 그려 구조의 차이가 모양으로 보이게 한다. 대체 공급자가 거의 없는 단계에는 ‘병목’ 표시를 단다.
VC_COL = dict(logic=C[0], memory=C[4], analog=C[2], base=MUTE)      # 제품군의 색. 병목(호박색)과 겹치지 않는 색을 쓴다
def choke(text):
    return f'<i class="choke"><em>병목</em>{text}</i>'


def vlk(em, b, span, extra, *t):
    return f'<div class="lk"{tip(*t)}><em>{em}</em><b>{b}</b><span>{span}</span>{extra}</div>'


def vrow(n, color, kind, name, items, cells, why):
    """제품군 한 줄: 이름 · 밸류체인 칸 · 그 구조가 된 까닭(원인 → 구조). 줄 전체가 그 제품군의 색(--rc)을 쓴다."""
    cause, result, foot = why
    small = f'<small>{items}</small>' if items else ''
    row = f'style="grid-row:{n};--rc:{color}"'
    assert cells.count(f'style="grid-row:{n}"') == 1, name
    return (f'<div class="rl" {row}><em>{kind}</em><b>{name}</b>{small}</div>' + cells.replace(f'style="grid-row:{n}"', row)
            + f'<div class="why" {row}>{cause}<b>→ {result}</b>' + (f'<small>{foot}</small>' if foot else '') + '</div>')


LIN_OPM16 = '44.5%'                            # Linear FY2016 영업이익률 · PART 1 장표와 같은 값 (linear_10k_2016)
VC_HEAD = ['IP · EDA', '설계', '웨이퍼 제조', '패키징 · 테스트']
vc_logic = (
    '<div class="lg" style="grid-row:2"><div class="chain">'
    + vlk('설계 · 판매', '팹리스', 'NVIDIA · AMD<br>Qualcomm · Apple', '',
          '팹리스 · 설계와 판매만', '웨이퍼 제조는 파운드리에 위탁 (AMD 첨단 제품: TSMC)',
          '클라우드 기업의 AI 전용 칩(Google TPU · AWS Trainium)도 같은 방식')
    + vlk('위탁 생산', '파운드리', 'TSMC · 삼성 파운드리', choke('선단 공정 생산 집중'),
          '파운드리 · 고객이 설계한 칩을 제조', 'TSMC는 제조와 첨단 패키징(CoWoS)을 함께 제공',
          '삼성전자는 메모리(IDM)와 파운드리를 함께 운영')
    + vlk('패키징 · 검사 외주', 'OSAT', 'ASE · Amkor · JCET', '<small>첨단 패키징은 TSMC도</small>',
          'OSAT · 칩을 연결 · 보호 · 검사', '후공정 전부가 OSAT에 맡겨지는 것은 아님',
          'GPU와 HBM을 잇는 첨단 패키징은 파운드리 · IDM도 수행')
    + '</div><div class="one sm"' + tip('Intel · 로직의 IDM', 'CPU를 직접 설계 · 제조', '자체 팹과 외부 위탁을 함께 사용')
    + '><b>Intel</b><span>IDM — 로직에서도 설계 · 제조를 한 회사에서 (자체 팹 + 일부 위탁)</span></div></div>')
def inhouse(caption):
    """IDM 띠의 오른쪽: 위 사슬의 세 단계를 한 회사가 모두 맡는다는 표시."""
    return f'<div class="inh"><em>{caption}</em>' + tags(['설계', '제조', '패키징 · 테스트']) + '</div>'


vc_memory = ('<div class="one" style="grid-row:3"'
             + tip('메모리 · IDM', '메모리 기업이 직접 설계 · 제조', 'HBM은 DRAM을 쌓아 AI 가속기에 데이터를 빠르게 전달',
                   '하단 로직 다이 · 첨단 패키징은 외부(TSMC 등)와 협업')
             + '><div class="who"><b>삼성전자 · SK hynix · Micron</b><span>DRAM · NAND를 직접 설계 · 제조</span>'
             + choke('HBM · AI 가속기에 붙는 적층 DRAM') + '</div>' + inhouse('세 단계를 한 회사 안에서') + '</div>')
vc_analog = ('<div class="one" style="grid-row:4"'
             + tip('아날로그 · 전력 · IDM', '신호 변환 · 증폭, 전압 · 전류 관리', '자체 제조와 외부 위탁을 조합',
                   'ADI는 Linear(2017) · Maxim(2021)을 인수')
             + '><div class="who"><b>TI · ADI · Infineon</b><span>신호 변환 · 증폭 · 전력 관리 칩을 설계 · 제조</span></div>'
             + inhouse('자체 제조 + 외부 위탁을 조합') + '</div>')
vc_base = ('<div class="eq" style="grid-row:5">'
           '<div class="base"' + tip('ASML · 노광 장비', 'EUV 노광장비는 ASML만 공급', '선단 공정의 가장 미세한 층을 찍는 장비')
           + '><b>노광 장비</b>ASML ' + choke('EUV 노광장비 유일 공급') + '</div>'
           '<div class="base"><b>공정 · 검사 장비</b>Applied · Lam · Tokyo Electron · KLA</div>'
           '<div class="base"><b>웨이퍼 · 소재</b>신에츠 · SUMCO</div></div>')
# 한 줄(1289px)에 들어가는 문안: 브라우저에서 잰 폭 1258px. ‘분업화’ · ‘고유의’를 넣으면 두 줄로 넘어간다
VC_TAKE = '제품 특성에 따라 밸류체인 구조가 다르다. 로직은 분업(Fabless–Foundry), 메모리 · 아날로그는 생산 · 설계 노하우가 핵심이다.'
def slide_valuechain():
    """제3기 뒤에서 부른다(v5): 분업과 재편의 결과로 생긴 오늘의 지도."""
    add('semicon-valuechain', 2, '반도체 밸류체인과 제품군: 누가 어디서 무엇을 만드는가?',
        '분업(제2기)과 재편(제3기)이 만든 오늘의 지도 — <b class="vk">가로 · 밸류체인 단계</b> × <b class="pk">세로 · 제품군</b>',
        '<div class="rows" style="gap:8px"><div class="vsplit vmap">'
        '<span class="axk"><b>밸류체인 →</b><b>제품군 ↓</b></span><div class="hband">'
        + ''.join(f'<span class="h">{h}</span>' for h in VC_HEAD)
        + '</div><span class="hw">제품 특성 → 구조</span>'
        '<div class="ip"><div><em>설계 자산 · IP</em><b>Arm</b></div><div><em>설계 도구 · EDA</em><b>Synopsys</b><b>Cadence</b></div>'
        '<p>모든 칩 설계의<br>공통 기반</p></div>'
        + vrow(2, VC_COL['logic'], '수직 분업', '로직 · AI', 'CPU · GPU · AP<br>AI 가속기', vc_logic,
               ('미세공정일수록 팹 투자 급증', '설계와 제조를 나눈다', ''))
        + vrow(3, VC_COL['memory'], '통합 · IDM', '메모리', 'DRAM · HBM · NAND', vc_memory,
               ('표준 제품 · 대량 생산', '공정 · 수율이 경쟁력', ''))
        + vrow(4, VC_COL['analog'], '통합 · IDM', '아날로그 · 전력', '신호 변환 · 전력 관리', vc_analog,
               ('다품종 · 긴 제품 수명', '설계 노하우 = 고마진', f'Linear 영업이익률 {LIN_OPM16} (FY2016)'))
        + vrow(5, VC_COL['base'], '공통 기반', '장비 · 소재', '', vc_base, ('대체하기 어려운 공정 기술', '소수가 병목을 쥔다', ''))
        + '</div><p class="note" style="margin-top:0">대표 기업 예시이며 전체 목록이 아님 · 한 회사가 여러 역할을 맡기도 한다 — '
          '삼성전자: 메모리 + 파운드리, TSMC: 제조 + 첨단 패키징 · ‘병목’ = 대체 공급자가 거의 없는 단계 · 줄의 색 = 제품군 · 칸에 마우스를 올리면 설명</p></div>',
        VC_TAKE,
        ['sia_ecosystem', 'sia_chain', 'tsmc_foundry', 'cowos', 'micron_hbm', 'analog_technology', 'asml_euv', 'amd_10k_2025',
         'google_tpu', 'aws_trainium', 'linear_10k_2016', 'linear_close', 'MAXIM'],
        method='대표 기업을 예로 든 구조도이며 전체 목록이나 점유율 통계가 아님. 제품 공급사(설계 · 판매)와 실제 제조사를 구분함. '
               '한 회사가 여러 역할을 맡을 수 있음(삼성전자: 메모리 + 파운드리, TSMC: 제조 + 첨단 패키징, Intel: 자체 제조 + 위탁). '
               '‘병목’은 대체 공급자가 거의 없는 단계를 가리키는 설명용 표시: EUV 노광장비는 ASML만 공급하고, '
               '선단 공정 위탁 생산은 TSMC에 집중돼 있으며, HBM은 메모리 3사가 공급함. ‘제품 특성 → 구조’ 칸은 구조를 설명하는 정성적 요약. '
               f'Linear 영업이익률 {LIN_OPM16}는 FY2016 Form 10-K. '
               '기업과 역할 구분은 팀 조사 자료 「반도체 산업 주요 분야별 역사와 기업 계보 2026」(2026.11.10 기준)을 따름. 조사 기준 2026-11-11.',
        tables=[dict(title='제품별 공급 기업과 제조 방식', head=['종류', '역할', '설계 · 공급 기업', '제조 방식'],
                     rows=[['CPU', '명령 실행 · 범용 연산', 'Intel · AMD', 'Intel: 자체 + 위탁 / AMD 첨단 제품: TSMC'],
                           ['GPU', '병렬 계산 · AI 학습 · 추론', 'NVIDIA · AMD', '대표 첨단 제품은 TSMC 제조'],
                           ['AI 전용 칩', '특정 AI 작업의 효율적인 처리', 'Google TPU · AWS Trainium', '자체 설계와 외부 제조 · 패키징 협업'],
                           ['일반 DRAM', '작업 중 데이터 저장 · 접근', '삼성전자 · SK hynix · Micron 등', '메모리 기업이 직접 설계 · 제조'],
                           ['HBM', 'AI 가속기에 대량의 데이터를 빠르게 전달', 'SK hynix · 삼성전자 · Micron', 'DRAM 적층, 베이스 다이 등 외부 협업'],
                           ['NAND', '전원이 꺼져도 데이터 보관', '삼성전자 · SK hynix · Micron · Kioxia · Sandisk 등', '자체 또는 공동 생산시설 활용'],
                           ['아날로그 · 전력관리', '신호 변환 · 증폭, 전압 · 전류 관리', 'TI · ADI(Linear · Maxim 인수) 등', '자체 제조와 외부 위탁을 조합']]),
                dict(title='공급망에서 맡는 역할', head=['구분', '담당 업무', '대표 기업'],
                     rows=[['IP · EDA', '회로 자산 · 설계 도구', 'Arm · Synopsys · Cadence'],
                           ['팹리스', '칩 설계 · 판매, 제조 위탁', 'NVIDIA · AMD · Qualcomm'],
                           ['파운드리', '고객 설계에 따른 제조', 'TSMC · 삼성전자 파운드리'],
                           ['IDM', '자사 제품 설계 · 제조', '삼성전자 · SK hynix · Micron · Intel · TI'],
                           ['패키징 · 검사', '칩 연결 · 보호 · 검사', 'ASE · Amkor · JCET / 첨단 패키징: TSMC 등'],
                           ['장비', '노광 · 식각 · 증착 · 검사', 'ASML · Applied · Lam · Tokyo Electron · KLA · Advantest'],
                           ['소재 · 기판', '웨이퍼 · 공정 소재 · 기판', 'SUMCO · Shin-Etsu · Entegris · IBIDEN · Unimicron 등']])])


# ── M&A 재편: 네 갈래의 계보를 같은 시간축에 (v4 신규) ──
# 한 줄 = 재편의 한 갈래, 그 안의 선 = 인수 주체. 완료된 인수는 알약 + 점, 분리 · 재편은 빈 마름모, 무산된 거래는 ✕ 로 구분한다
MNA_Y0, MNA_Y1, MNA_TICKS = 1999, 2027, list(range(2000, 2026, 5))
MNA_W, MNA_X0, MNA_X1 = 834, 124, 824          # 그림 폭 · 시간축의 왼쪽 끝과 오른쪽 끝. 네 줄과 눈금 줄이 같은 축을 쓴다
MNA_H, MNA_LANE, MNA_PITCH = 108, 38, 52       # 한 줄의 높이 · 첫 선의 높이 · 두 선 사이 간격
# 반도체 M&A 발표가 몰린 두 구간(IC Insights · 발표액 기준): 2015–16 은 PART 1 의 MNA, 2020 은 당시 사상 최대
MNA_WAVES = [(2015, 2016), (2020, 2020)]
MNA_2020 = 118.0                               # 2020 발표액 $bn · 출처 icinsights_mna2020
assert [k for k, _ in MNA[1:3]] == [str(y) for y in MNA_WAVES[0]] and all(v > 3 * MNA[0][1] for _, v in MNA[1:3])
assert f'${MNA_2020}bn' in SOURCES['icinsights_mna2020']['note'] and MNA_2020 > max(v for _, v in MNA)


def mna_bands(y0, h):
    """M&A 발표가 몰린 구간을 옅은 띠로."""
    return [f'<rect x="{mx(a)}" y="{y0}" width="{round(mx(b + 1) - mx(a), 1)}" height="{h}" fill="#fff" opacity=".05"/>'
            for a, b in MNA_WAVES]


def mx(year):
    return round(MNA_X0 + (year - MNA_Y0) / (MNA_Y1 - MNA_Y0) * (MNA_X1 - MNA_X0), 1)


def deal(year, name, *tips, kind='acq', dx=0, hi=False, since=None, left=False):
    """kind: acq 인수 완료 · new 분리 · 출범 · 재편 추진 · fail 무산(year = 종료, since = 발표). tips = 툴팁(제목, 줄 …)."""
    return dict(y=year, name=name, tips=tips, kind=kind, dx=dx, hi=hi, since=since, left=left)


def lane(co, color, deals, a=None, pre=''):
    """a = 선이 시작하는 해(없으면 축의 왼쪽 끝부터), pre = 그 앞의 전신을 점선으로 그릴 때의 이름."""
    return dict(co=co, color=color, deals=deals, a=a, pre=pre)


def mna_svg(lanes, label):
    s = mna_bands(0, MNA_H) + [f'<line x1="{mx(y)}" x2="{mx(y)}" y1="0" y2="{MNA_H}" stroke="{GRID}"/>' for y in MNA_TICKS]
    hits = []
    for k, ln in enumerate(lanes):
        base, col = MNA_LANE + k * MNA_PITCH, ln['color']
        x0 = mx(ln['a'] + .5) if ln['a'] else MNA_X0
        s.append(f'<rect x="0" y="{base - 5}" width="10" height="10" rx="2" fill="{col}"/>' + T(17, base + 5, ln['co'], 15, INK, weight=800))
        if ln['pre']:
            s.append(f'<line x1="{MNA_X0}" x2="{x0}" y1="{base}" y2="{base}" stroke="{col}" stroke-width="2" '
                     'stroke-dasharray="3 5" opacity=".75"/>')
            s.append(T(round((MNA_X0 + x0) / 2 - 12, 1), base - 8, ln['pre'], 11.5, INK3, 'middle'))
        s.append(f'<path d="M{x0},{base}H{MNA_X1 - 8}" fill="none" stroke="{col}" stroke-width="3.5" stroke-linecap="round"/>')
        s.append(f'<polygon points="{MNA_X1},{base} {MNA_X1 - 10},{base - 6} {MNA_X1 - 10},{base + 6}" fill="{col}"/>')
        for d in ln['deals']:
            x, kind = mx(d['y'] + .5), d['kind']
            diamond = f'<path d="M{x},{base - 7}l7,7l-7,7l-7,-7Z" fill="{SURF}" stroke="{col}" stroke-width="2.5"/>'
            if kind == 'fail':                 # 무산: 선 위의 ✕ 와 이름, 아래에 발표–종료 연도
                s.append(f'<circle cx="{x}" cy="{base}" r="9" fill="{SURF}"/>'
                         f'<path d="M{x - 5.5},{base - 5.5}l11,11M{x + 5.5},{base - 5.5}l-11,11" stroke="{RED}" stroke-width="3" '
                         'stroke-linecap="round"/>')
                s.append(T(x + 11, base - 9, d['name'], 12.5, RED, weight=700, cls='halo'))
                s.append(T(x, base + 16, f'{d["since"]}–{str(d["y"])[2:]}', 11, INK3, 'middle', cls='tn'))
                hits.append((x - 14, base - 24, round(tw(d['name'], 12.5)) + 30, 44, d['tips']))
                continue
            if d['left']:                      # 선이 시작하는 자리: 이름을 선 왼쪽에 적는다
                s.append(diamond)
                s.append(f'<text x="{x - 13}" y="{base + 4.5}" text-anchor="end" font-size="12.5" fill="{INK2}">'
                         f'<tspan fill="{INK3}" class="tn">{d["y"]}</tspan> {d["name"]}</text>')
                hits.append((x - 150, base - 12, 164, 24, d['tips']))
                continue
            w = round(tw(d['name'], 13) * 1.06) + 22
            px = round(x + d['dx'] - w / 2, 1)
            fill, stroke = ('rgba(57,226,176,.18)', GREEN) if d['hi'] else ('#0c2033', '#2b4a62')
            dash = ' stroke-dasharray="4 3"' if kind == 'new' else ''
            s.append(f'<line x1="{x}" x2="{x}" y1="{base - 10}" y2="{base - 5}" stroke="{col}" stroke-width="1.5"/>')
            s.append(f'<rect x="{px}" y="{base - 30}" width="{w}" height="20" rx="10" fill="{fill}" stroke="{stroke}"{dash}/>')
            s.append(T(round(px + w / 2, 1), base - 15.5, d['name'], 13, INK, 'middle', 700))
            s.append(diamond if kind == 'new' else f'<circle cx="{x}" cy="{base}" r="5.5" fill="{col}" stroke="{SURF}" stroke-width="2"/>')
            s.append(T(x, base + 16, str(d['y']), 11, INK3, 'middle', cls='tn'))
            hits.append((px, base - 31, w, 50, d['tips']))
    for hx, hy, hw, hh, t in hits:             # 마우스를 올리면 거래 내용
        s.append(f'<rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" fill="transparent"{tip(*t)}/>')
    return (f'<svg width="{MNA_W}" height="{MNA_H}" viewBox="0 0 {MNA_W} {MNA_H}" role="img" aria-label="{label}">'
            + ''.join(s) + '</svg>')


def mna_axis_svg():
    """네 줄 위의 눈금 줄: 연도와 M&A 발표가 몰린 두 구간."""
    (a1, b1), (a2, _) = MNA_WAVES              # 이름표는 첫 띠의 오른쪽 끝 · 둘째 띠의 왼쪽 끝에 맞춰 서로 겹치지 않게 둔다
    s = mna_bands(17, 13) + [
        T(mx(b1 + 1), 13, f'M&amp;A 발표액 급증 · {a1}–{str(b1)[2:]} 직전 5년 평균의 약 {mna_multiple:.0f}배', 11.5, AMBER, 'end', 700),
        T(mx(a2), 13, f'{a2} ${MNA_2020:.0f}bn · 당시 최대', 11.5, AMBER, weight=700)]
    for y in MNA_TICKS:
        s.append(f'<line x1="{mx(y)}" x2="{mx(y)}" y1="19" y2="30" stroke="{AXIS}"/>')
        s.append(T(mx(y) + 5, 28, str(y), 12, INK2, cls='tn'))
    return (f'<svg width="{MNA_W}" height="30" viewBox="0 0 {MNA_W} 30" role="img" aria-label="{MNA_Y0}년부터 {MNA_Y1 - 1}년까지의 시간축">'
            + ''.join(s) + '</svg>')


MNA_ROWS = [
    dict(no='01', scope='제품군 · 아날로그', name='아날로그 대형화', how='전문기업을 편입해 제품군의 폭을 넓힌다',
         out=('신호 체인 + 전원 관리<br>풀스택', '2025 아날로그 1위 TI · 2위 ADI'),
         lanes=[lane('ADI', C[3], [
                    deal(2014, 'Hittite', '2014 · ADI ← Hittite Microwave', 'RF · 마이크로파 제품군'),
                    deal(2017, 'Linear', '2017.03 · ADI ← Linear Technology', '전원 관리 제품군 · 지분가치 약 $14.8bn',
                         'PART 1의 Linear — 독립 상장 종료', hi=True),
                    deal(2021, 'Maxim', '2021 · ADI ← Maxim Integrated', '전력 관리 · 혼합신호 제품군', '2020.07 발표 · 약 $21bn')]),
                lane('TI', C[2], [
                    deal(2000, 'Burr-Brown', '2000 · TI ← Burr-Brown', '정밀 아날로그 · 데이터 변환', dx=8),
                    deal(2011, 'National', '2011.09 · TI ← National Semiconductor', '아날로그 제품군 · 제조 기반')])]),
    dict(no='02', scope='제품군 · 통신', name='팹리스 통합', how='설계 자산(IP)과 고객을 한데 합친다',
         out=('통신 · 네트워킹 IP의<br>거대화', '대형 거래는 규제 승인이 변수'),
         lanes=[lane('Broadcom', C[7], [
                    deal(2005, 'Avago 출범', '2005 · Avago 출범', 'HP 반도체 사업 → 1999 Agilent → 2005 Avago로 분리', kind='new', dx=12),
                    deal(2016, 'Broadcom', '2016 · Avago + Broadcom', '결합 뒤 Broadcom 이름을 사용',
                         '네트워크 · 연결 · 맞춤형 반도체')], a=2005, pre='HP → Agilent'),
                lane('Qualcomm', C[6], [
                    deal(2018, 'NXP 인수 무산', '2018.07 · Qualcomm의 NXP 인수 무산', '2016.10 인수 발표',
                         '중국 당국의 승인을 받지 못한 채 계약 종료', kind='fail', since=2016)])]),
    dict(no='03', scope='제품군 · 로직 · AI', name='풀스택 로직 결합', how='서로 다른 연산 방식을 한 회사에 묶는다',
         out=('CPU + GPU + FPGA<br>→ 데이터센터 · AI', '연산에 네트워크까지 한 회사 안으로'),
         lanes=[lane('AMD', C[1], [
                    deal(2006, 'ATI', '2006.10 · AMD ← ATI', '그래픽(GPU) · 약 $5.4bn'),
                    deal(2022, 'Xilinx', '2022.02 · AMD ← Xilinx', 'FPGA · Adaptive SoC · 2020.10 발표 · 약 $35bn', '같은 해 Pensando(DPU)도 인수')]),
                lane('NVIDIA', C[5], [
                    deal(2020, 'Mellanox', '2020.04 · NVIDIA ← Mellanox', '데이터센터 네트워크 · $7bn'),
                    deal(2022, 'Arm 인수 무산', '2022.02 · NVIDIA의 Arm 인수 무산', '2020.09 계약 · 약 $40bn',
                         '규제 장벽으로 종료 — Arm은 NVIDIA의 자회사가 아님', kind='fail', since=2020)])]),
    dict(no='04', scope='밸류체인 · 제조', name='파운드리 전문화', how='IDM이 제조를 떼어 내거나 외부에 연다',
         out=('선단 공정 위탁은<br>TSMC 생태계로 집중', 'IDM의 제조 분리 · 외주화'),
         lanes=[lane('GlobalFoundries', C[4], [
                    deal(2009, 'AMD 제조 분리', '2009 · GlobalFoundries 출범', 'AMD의 제조 부문을 분리 · Mubadala와 합작',
                         kind='new', left=True),
                    deal(2010, 'Chartered', '2010 · GlobalFoundries ← Chartered', '싱가포르의 파운드리', dx=20),
                    deal(2015, 'IBM 제조사업', '2015 · GlobalFoundries ← IBM 반도체 제조사업', '팹과 지식재산 포함',
                         'IBM은 반도체 제조에서 손을 뗌')], a=2009),
                lane('Intel', C[0], [
                    deal(2021, 'IFS 출범', '2021.03 · Intel Foundry Services 출범', 'IDM 2.0 — 외부 고객의 칩을 위탁 생산',
                         kind='new', dx=-12),
                    deal(2024, '자회사화 추진', '2024.09 · Intel Foundry 자회사화 계획 발표', '제품과 제조의 손익 분리에 이은 계획',
                         '계획 발표 기준 — 그 뒤의 진행은 확인하지 않음', kind='new', dx=7)])]),
]
MNA_KIND = {'acq': '인수 완료', 'new': '분리 · 재편', 'fail': '무산'}
assert len(MNA_ROWS) == 4 and all(len(r['lanes']) == 2 for r in MNA_ROWS)


def mrow(r):
    who = ' · '.join(ln['co'] for ln in r['lanes'])
    return (f'<div class="mrow"><div class="mrow-h"><em>{r["no"]} · {r["scope"]}</em><b>{r["name"]}</b><span>{r["how"]}</span></div>'
            + mna_svg(r['lanes'], f'{r["name"]}: {who}의 주요 거래를 연도순으로 놓은 계보')
            + f'<div class="mrow-out"><b>{r["out"][0]}</b><span>{r["out"][1]}</span></div></div>')


def slide_mna():
    """제3기 뒤, 밸류체인 지도 다음에 부른다(v5): 메모리 밖에서도 같은 재편이 있었다."""
    # 제목의 & 는 그대로 둔다: 목차 · 출처 창은 제목을 글자로 다시 이스케이프한다 (v3.js 의 plain → esc)
    add('semicon-mna-history', 2, '거대 M&A가 만든 반도체 제국: 밸류체인과 제품군의 재편',
        '재편은 메모리만이 아니었다 — 독자 생존 대신 인수합병으로 규모의 경제를 완성한 4대 축',
        '<div class="mna"><div class="mna-ax"><span class="kicker">재편의 네 갈래</span>' + mna_axis_svg()
        + legend([('dot', INK2, '인수 완료'), ('dia', INK2, '분리 · 재편'), ('x', RED, '무산')])
        + '</div>' + ''.join(mrow(r) for r in MNA_ROWS) + '</div>',
        '오늘날의 반도체 공룡들은 M&amp;A로 밸류체인의 병목을 쥐거나 제품 포트폴리오의 폭을 넓히며 탄생했다.',
        ['linear_close', 'linear_pr_sec', 'MAXIM', 'peer_ADI', 'NATIONAL', 'ti_burrbrown', 'analog_rank2025', 'broadcom', 'avago_broadcom_10k',
         'broadcom_lineage', 'qcom_nxp_term', 'amd_ati', 'amd_xilinx', 'amd_10k_2022', 'nvda_mellanox', 'nvda_arm_term', 'gf_history',
         'intel_idm2', 'intel_foundry_sub', 'tsmc_foundry', 'icinsights_mna', 'icinsights_mna2020'],
        method='가로축은 거래가 완료된 해(무산된 거래는 종료된 해, 분리 · 재편은 출범 · 발표한 해)이며 네 줄이 같은 축을 씀. '
               '산업 구조를 설명하는 주요 거래만 추렸고 전수 목록이 아님. 완료된 인수 · 분리와 재편(추진 포함) · 무산을 구분해 표시하며, '
               '인수 사실이 실적 개선 효과를 뜻하지는 않음. ‘결과’ 칸은 재편의 방향을 요약한 정성적 설명. '
               f'옅은 띠는 IC Insights가 집계한 반도체 M&amp;A 발표액이 몰린 해: {MNA[1][0]} ${MNA[1][1]}bn · {MNA[2][0]} ${MNA[2][1]}bn'
               f'({MNA[0][0]} ${MNA[0][1]}bn), 2020 ${MNA_2020:.1f}bn(당시 사상 최대 · 상위 5건이 약 80%). '
               '띠는 발표한 해, 그림의 점은 완료한 해여서 2020년에 발표된 Maxim · Xilinx 인수는 2021 · 2022년에 찍혀 있음. '
               '아날로그 순위는 GMI의 2025년 추정. '
               'Intel Foundry의 자회사화는 2024.09 계획 발표 기준이며 그 뒤의 진행은 확인하지 않음. 파운드리의 집중은 M&amp;A만의 결과가 아니라 '
               '공정 · 수율 · 설비투자 · 고객 신뢰의 축적이 함께 작용한 것임. '
               '거래 연도와 계보는 팀 조사 자료 「반도체 산업 주요 분야별 역사와 기업 계보 2026」(2026.11.10 기준)의 확인 링크를 따름. 조사 기준 2026-11-11.',
        tables=[dict(title='주요 거래 일지', head=['갈래', '주체', '연도', '거래', '구분', '내용'],
                     rows=[[r['name'], ln['co'], f'{d["since"]} → {d["y"]}' if d['since'] else str(d['y']), d['name'], MNA_KIND[d['kind']],
                            ' · '.join(d['tips'][1:])] for r in MNA_ROWS for ln in r['lanes'] for d in ln['deals']])])


# ── 시대 설명(시간축에서 시대를 누르면 뜨는 창) ──
def era(years, name, demand, macro, events, leaders):
    keys = ('short', 'detail', 'source')
    ERAS.append(dict(years=years, name=name, demand=dict(zip(keys, demand)), macro=dict(zip(keys, macro)),
                     events=dict(zip(keys, events)), leaders=dict(zip(keys, leaders))))


chm, fed, tsmc, rank, wsts = (SOURCES[k]['url'] for k in ('chm', 'fred_ff', 'tsmc_foundry', 'ranking_history', 'wsts_q2_2026'))
era('1947–1970s', '태동기',
    ('국방 · 우주 → 계산기', '1947 트랜지스터, 1958–59 IC가 출발. 미사일·우주용 전자장치가 작은 크기·낮은 전력의 가치를 먼저 인정. 이후 계산기와 민간 전자기기로 확대.', chm),
    ('냉전 · 정부 조달', '정부 연구비와 군수·우주 조달이 기술 초기의 수요 위험을 줄임. 일부 원가보상 계약이 R&D 위험을 분담했지만 모든 IC 계약이 같은 방식이었던 것은 아님.', chm),
    ('트랜지스터 / IC / MPU', '1947 발명 → 1957 Fairchild → 1958 Kilby·1959 Noyce IC → 1968 Intel → 1971 마이크로프로세서. Fairchild는 Shockley를 거친 연구자들이 설립.', chm),
    ('TI · Fairchild · Motorola', '기술·제조 역량을 쌓은 초기 주역. 초기 기업 나열은 매출 순위가 아닌 대표 기업.', chm))
era('1980–1990s 초', '제1기',
    ('PC · DRAM', '1981 IBM PC 이후 대중 컴퓨팅 수요 확대. CPU와 메모리의 역할 분화, DRAM의 수율·공정·규모 경쟁 심화.', rank),
    ('볼커 고금리 / 일본 완화', '미국 고금리와 강달러, 일본 은행 중심 장기금융 및 1986–87 완화가 투자 환경에 영향을 줌. 품질·공정·산업정책도 중요했음.', fed),
    ('1983 삼성 / 1986 협정', '삼성 도쿄 선언과 DRAM 진입. 1986·1991 미일 반도체 협정, 1985 전후 Intel의 DRAM 철수. 자금조달 조건과 사업 선택이 함께 바뀜.', rank),
    ('NEC · Toshiba · Hitachi', '1990 공급업체 순위 NEC 1위·Toshiba 2위·Hitachi 4위. 미국은 CPU 등 비메모리 경쟁력을 유지.', rank))
era('1990s 중반–2000s', '제2기',
    ('PC 확산 · 인터넷', '1990년대 PC·인터넷과 통신망 확대 → 2000–01 닷컴 붕괴 → 디지털 가전 확산. 성장 추세와 재고 사이클이 공존.', rank),
    ('세계화 · 팹 투자 확대', '미세공정이 발전할수록 공장·장비와 설계의 복잡성이 증가. 고정비를 여러 고객에 나누는 제조 전문화가 확대.', tsmc),
    ('1987 TSMC → 분업 정착', 'TSMC 설립은 제2기보다 이른 1987년. 1990년대 이후 팹리스·파운드리 생태계 확대. 2001 산업 매출은 약32% 감소. '
                           'M&A: 2000 TI의 Burr-Brown 인수, 2006 AMD의 ATI 인수, 2009 AMD의 제조 분리(GlobalFoundries 출범).', tsmc),
    ('Intel · 삼성 / TSMC', 'Intel PC CPU, 삼성 메모리. TSMC는 제조 수탁으로 성장해 공급업체 순위와 별도 집계. NVIDIA는 팹리스로 출발.', rank))
era('2010s', '제3기',
    ('스마트폰 · 클라우드', '모바일 연산·통신·전력관리와 서버 메모리 확대. 2017–18 메모리 호황, 2019 조정으로 가격 효과 확인.', rank),
    ('QE · 제로금리', '금융위기 이후 낮은 자본비용. 그러나 저금리도 현금 유출·만기 집중·고객 이탈을 막아주지는 못함.', fed),
    ('2012 Elpida / 대형 M&A', '엘피다 회생절차 2012, Micron 인수완료 2013. SK의 하이닉스 인수 2012. 메모리 Big3 형성. '
                           '대형 M&A: 2011 TI–National, 2015 IBM 반도체 제조사업의 GlobalFoundries 이관, 2016 Avago–Broadcom 결합, '
                           '2017 Linear의 ADI 편입.', SOURCES['elpida_failure']['url']),
    ('삼성 · SK hynix · Micron', 'DRAM 과점. 반도체 전체 공급업체 1위는 2017–18 삼성, 2019–20 Intel로 바뀜. 메모리 가격이 매출 순위를 흔듦.', rank))
era('2020s–현재', '제4기',
    ('AI · GPU + HBM', '팬데믹 공급난 → 2022–23 재고 조정 → 2024–26 AI 인프라. HBM·선단공정·패키징과 범용 메모리로 수요 확산.', wsts),
    ('금리 · 보조금 · 전력', '고금리·공급망 블록화와 국가 보조금 공존. 전력·계통접속·부지 인허가가 투자 시점을 좌우.', SOURCES['audit_3_0']['url']),
    ('생성형 AI / 수출통제', '2022 생성형 AI 확산, 2024 이후 GPU·HBM 투자 확대. 2026 구매자 현금흐름·장기계약·전력 제약이 재무 이슈로 부상. '
                        'M&A: 2020 NVIDIA–Mellanox, 2021 ADI–Maxim, 2022 AMD–Xilinx — 연산 · 네트워크 · 전력을 한 회사로 묶는 결합.', wsts),
    ('NVIDIA / TSMC / HBM', 'NVIDIA 설계 플랫폼, TSMC 제조·패키징, SK hynix·삼성·Micron 메모리. 서로 다른 단계이므로 매출을 단순 합치면 중복.', wsts))

# ── 80년을 한 시간축에 ──
WSTS_Y = D['wsts']
wsts_full = [(w['year'], w['usd_billion']) for w in WSTS_Y if w.get('full_year', True)]
wsts_part = next(w for w in WSTS_Y if not w.get('full_year', True))
WY = dict(wsts_full)
dotcom_drop = (WY[2001] / WY[2000] - 1) * 100
assert wsts_part['year'] == 2026 and fmt(dotcom_drop, 0) == '−32'

TL = dict(
    start=1947, end=2027,
    eras=[dict(a=1947, b=1980, name='태동기', years='1947–1970s', yearsShort="'47–'70s", lead='TI · Fairchild · Motorola'),
          dict(a=1980, b=1994, name='제1기', years='1980–1990s 초', yearsShort="'80–'90s 초", lead='NEC · Toshiba · Hitachi'),
          dict(a=1994, b=2010, name='제2기', years='1990s 중반–2000s', yearsShort="'90s–'00s", lead='Intel · 삼성 · TSMC'),
          dict(a=2010, b=2020, name='제3기', years='2010s', yearsShort='2010s', lead='삼성 · SK hynix · Micron'),
          dict(a=2020, b=2027, name='제4기', years='2020s–현재', yearsShort='2020s–', lead='NVIDIA · TSMC')],
    waves=[dict(a=1950, b=1972, name='국방·우주', tip='미사일 유도·우주 탐사용 전자장치|작고 가볍고 믿을 수 있는 부품에 높은 가격을 지불한 첫 고객'),
           dict(a=1964, b=1988, name='계산기·가전', tip='전자계산기·시계·가전|민간 대량 시장이 열리며 가격이 빠르게 하락'),
           dict(a=1978, b=2012, name='PC', tip='개인용 컴퓨터|CPU와 DRAM 수요를 수십 년간 이끈 중심 시장'),
           dict(a=1993, b=2006, name='인터넷·통신', tip='인터넷·통신망 투자|닷컴 호황과 2001년의 급락을 함께 만든 수요'),
           dict(a=2006, b=2024, name='스마트폰', tip='스마트폰|모바일 AP·통신칩·낸드·전력관리 수요 확대'),
           dict(a=2009, b=2027, name='클라우드', tip='클라우드 데이터센터|서버 CPU·메모리 수요의 장기 확대'),
           dict(a=2021, b=2027, name='AI', tip='AI 가속기|GPU·HBM·첨단 패키징으로 수요 집중')],
    wsts=[[y, round(v, 1)] for y, v in wsts_full]
         + [[wsts_part['year'], round(wsts_part['usd_billion'], 1), f'1–{wsts_part["months"]}월']],
    wstsNotes=[dict(y=1986, t=f'1986 ${WY[1986]:.0f}bn'),
               dict(y=2000, t=f'2000 ${WY[2000]:.0f}bn → 2001 {fmt(dotcom_drop, 0)}%'),
               dict(y=2026, t=f'2026 1–{wsts_part["months"]}월 ${wsts_part["usd_billion"]:,.0f}bn', anchor='end', dx=-9, dy=4)],
    events=[dict(y=1947, t='트랜지스터', key=1, tip='벨 연구소의 점접촉 트랜지스터 시연'),
            dict(y=1958, t='집적회로', key=1, tip='TI 잭 킬비의 첫 집적회로 · 1959년 페어차일드 노이스의 평면형 IC'),
            dict(y=1968, t='Intel 설립', tip='노이스와 무어가 페어차일드를 떠나 설립'),
            dict(y=1971, t='마이크로프로세서', tip='Intel 4004 출시'),
            dict(y=1981, t='IBM PC', key=1, tip='IBM PC 5150 출시 · 개인용 컴퓨터 수요의 본격화'),
            dict(y=1983, t='삼성 도쿄 선언', tip='삼성의 메모리 사업 진출 선언 · 같은 해 64K DRAM 개발'),
            dict(y=1985, t='플라자 합의', tip='G5의 달러 약세 유도 합의 · 엔화 강세로 전환'),
            dict(y=1986, t='미·일 반도체 협정', tip='미·일 반도체 협정 체결 · 1991년 갱신'),
            dict(y=1987, t='TSMC 설립', key=1, tip='첫 순수 파운드리 · 설계와 제조의 분리'),
            dict(y=2001, t='닷컴 붕괴', key=1, tip=f'세계 반도체 매출 약 {abs(dotcom_drop):.0f}% 감소'),
            dict(y=2007, t='iPhone', tip='스마트폰 시대의 시작 (2007.01 발표)'),
            dict(y=2008, t='금융위기 · 제로금리', tip='글로벌 금융위기 · 2008.12 연준 제로금리 진입'),
            dict(y=2012, t='Elpida 파산', key=1, tip='일본 DRAM 업체 Elpida 회생절차 신청 · 2013년 Micron이 인수'),
            dict(y=2017, t='ADI–Linear', key=1, tip='2017.03 ADI의 Linear 인수 완료 · 2021년 Maxim 인수로 이어진 아날로그 대형화'),
            dict(y=2022, t='대중 수출통제', tip='미국 상무부의 대중국 첨단 반도체·장비 수출통제 (2022.10)'),
            dict(y=2026, t='매출 2배', key=1, tip='2026 상반기 세계 반도체 매출이 전년동기 대비 약 2배')],
    # 대형 M&A(v4): 시대 축 위쪽 모서리의 마름모. 이름표 없이 툴팁으로만 보인다 — M&A 재편 장표(semicon-mna-history)의 네 갈래에서 고른 이정표
    mna=[dict(y=2011, t='TI–National', tip='TI의 National Semiconductor 인수 완료 (2011.09)|아날로그 대형화 — 제품군과 제조 기반 통합'),
         dict(y=2015, t='IBM 제조사업 → GlobalFoundries', tip='IBM이 반도체 제조사업을 GlobalFoundries에 넘김|파운드리 전문화 — IDM의 제조 분리'),
         dict(y=2016, t='Avago–Broadcom', tip='Avago와 Broadcom의 결합 완료 · Broadcom 이름 사용|팹리스 통합 — 통신 · 네트워킹 IP의 대형화'),
         dict(y=2017, t='ADI–Linear', tip='ADI의 Linear Technology 인수 완료 (2017.03)|아날로그 대형화 — 신호 체인 + 전원 관리'),
         dict(y=2021, t='ADI–Maxim', tip='ADI의 Maxim Integrated 인수 완료|아날로그 대형화의 연장'),
         dict(y=2022, t='AMD–Xilinx', tip='AMD의 Xilinx 인수 완료 (2022.02)|풀스택 로직 결합 — CPU + GPU + FPGA')],
    ff=[[round(int(d[:4]) + (int(d[5:7]) - .5) / 12, 3), round(v, 2)] for d, v in FF],
    ffNotes=[dict(y=1981.46, v=19.1, t='1981.06 19.1%', dx=8, dy=4, anchor='start'),
             dict(y=2012, v=.14, t='제로금리', dy=-8),
             dict(y=2026.8, v=FF[-1][1], t=f'{FF[-1][1]:.1f}%', anchor='end', dx=-4, dy=-8)],
    macro=[dict(a=1947, b=1991, name='냉전 · 정부 조달', tip='미·소 군비 경쟁과 우주 개발|정부 조달이 초기 반도체 수요의 위험을 줄임'),
           dict(a=1979.6, b=1985.7, row=1, name='볼커 고금리 · 강달러', short='볼커 고금리',
                tip='1979.10 긴축 전환 → 1981.06 FF 월평균 19.1%|달러 강세로 미국 제조업의 수출·투자 부담 확대'),
           dict(a=1991, b=2008, name='세계화 · 팹 투자 확대', tip='냉전 종식 이후 교역·분업 확대|미세공정이 발전할수록 팹 투자비 급증'),
           dict(a=2008.9, b=2015.95, name='QE · 제로금리',
                tip='2008.12–2015.12 사실상 제로금리|낮은 자본비용이 M&A와 설비투자를 뒷받침|2015–16 반도체 M&A 발표액은 직전 5년 평균의 약 8배'),
           dict(a=2022, b=2027, name='금리 · 보조금 · 전력', short='금리·전력',
                tip='금리 재상승 · 각국 보조금 · 수출통제|전력·계통 접속·인허가가 투자 시점을 좌우')],
    structure=[dict(a=1947, b=1987, soft=1, name='IDM 수직통합', tip='설계와 제조를 한 회사 안에서 수행'),
               dict(a=1987, b=2027, name='팹리스 · 파운드리 분업',
                    tip='1987 TSMC 설립 이후 설계와 제조의 분리|1990년대 이후 본격 확산|IDM의 제조 분리: 2009 AMD(GlobalFoundries 출범) · 2015 IBM'),
               dict(a=1981, b=1992, row=1, soft=1, name='일본 메모리 강세', tip='1980년대 일본 업체가 DRAM 시장을 주도|1990 공급업체 Top 10 중 6곳이 일본'),
               dict(a=2013, b=2027, row=1, name='메모리 Big 3', tip='삼성 · SK hynix · Micron의 DRAM 과점|2013 Micron의 Elpida 인수 이후')])
assert len(TL['eras']) == len(ERAS)
assert f'{mna_multiple:.0f}배' in TL['macro'][3]['tip'], 'QE 툴팁의 M&A 배수는 PART 1 의 값과 같아야 한다'
# 시간축의 M&A 표시는 M&A 재편 장표의 완료된 인수 · 재편과 연도가 맞아야 한다
mna_done = {d['y'] for r in MNA_ROWS for ln in r['lanes'] for d in ln['deals'] if d['kind'] != 'fail'}
assert {m['y'] for m in TL['mna']} <= mna_done, sorted({m['y'] for m in TL['mna']} - mna_done)

LAYERS = [('leaders', '기업 · 산업 구조 · M&amp;A'), ('demand', '수요 · 매출'), ('events', '주요 사건'), ('macro', '금리 · 거시 환경')]
add('industry-map', 2, '반도체 80년을 한 시간축에: 수요 · 거시환경 · 사건 · 기업',
    '가운데 시대 축 위는 산업 안쪽(기업·수요·매출 · <span class="amber">◆</span> 대형 M&amp;A), 아래는 바깥 환경(사건·금리·구조) · 시대를 누르면 세부 설명',
    '<div class="pills">'
    + ''.join(f'<label><input type="checkbox" data-layer="{k}" checked> {v}</label>' for k, v in LAYERS)
    + '</div><div id="timeline" data-h="506" style="min-height:506px"></div>',
    '시대 구분은 수요 중심의 분석 틀이다. 실제 전환은 서로 겹친다.',
    ['chm', 'transistor', 'kilby', 'intel_4004', 'ranking_history', 'samsung_history', 'plaza', 'japan', 'tsmc_foundry', 'wsts',
     'wsts_q2_2026', 'apple_iphone', 'fed_history', 'fred_ff', 'elpida_failure', 'linear_close', 'bis_2022',
     'NATIONAL', 'gf_history', 'avago_broadcom_10k', 'MAXIM', 'amd_xilinx', 'icinsights_mna'],
    method='세계 반도체 매출은 WSTS 연간 청구액($bn), 2026년은 1–8월 누계. 금리는 연방기금 실효금리 월평균. '
           '수요의 물결과 시대 구분의 시작·끝은 설명을 위한 대략의 범위이며 통계적 경계가 아님. '
           '시대 축 위의 마름모(◆)는 뒤의 ‘M&amp;A 재편’ 장표에서 다루는 대형 M&amp;A 가운데 완료된 거래 여섯 건의 완료 연도이며 전수 목록이 아님. '
           '조사 기준 2026-11-08 (M&amp;A 표시는 2026-11-11).',
    tables=[dict(title='시대 축 위의 대형 M&A (◆)', head=['연도', '거래', '내용'],
                 rows=[[str(m['y']), m['t'], m['tip'].replace('|', ' · ')] for m in TL['mna']])])

# ── 태동기: 발명에서 오늘의 칩까지 · 첫 고객은 국가였다 (미·소 군비 경쟁) ──
STRIP = [('transistor', '1947', '트랜지스터', '전류를 증폭·전환하는 최초의 반도체 소자', ''),
         ('ic-replica', '1958', '집적회로', '여러 소자를 한 칩에 (사진은 복제품)', ''),
         ('intel-4004', '1971', '마이크로프로세서', 'Intel 4004 · 연산 장치를 칩 하나에', ''),
         ('dram-256k-nec', '1980s', 'D램', 'NEC 256K D램 · 일본 메모리의 전성기', 'later'),
         ('wafer-300mm', '2000s', '300mm 웨이퍼', '12인치 웨이퍼 · 대형 팹의 시대', 'later'),
         ('soc-apple-a4', '2010', '모바일 SoC', 'Apple A4 · 스마트폰의 두뇌', 'later'),
         ('ai-nvidia-b200', '2025', 'AI 가속기', 'NVIDIA HGX B200 · GPU 8개 AI 서버 보드', 'later')]
n_now = sum(1 for s in STRIP if not s[4])
MIL = HIS['milex']['rows']
mil_y = [r[0] for r in MIL]
assert (mil_y[0], mil_y[-1]) == (1947, 1980)
CHARTS['milex'] = dict(
    title='미국 · 소련 군사비 1947–1980', cap='군사비 지출 (명목 $bn)', labels=[str(y) for y in mil_y], pre='$', suf='bn', dec=0, fs=13,
    x={'ticks': [mil_y.index(y) for y in (1950, 1960, 1970, 1980)]}, y={'step': 50, 'max': 220, 'pre': '$'},
    series=[dict(name='미국', values=[r[1] for r in MIL], color=C[0], w=3, end=True),
            dict(name='소련 (추정)', values=[r[2] for r in MIL], color=C[1], end=True)],
    marks=[dict(i=mil_y.index(1950), label='1950 한국전쟁', y=14), dict(i=mil_y.index(1957), label='1957 스푸트니크', y=14),
           dict(i=mil_y.index(1965), label='1965 베트남전 확전', y=14), dict(i=mil_y.index(1969), label='1969 아폴로 11호', y=34)])
add('era0-invention', 2, '태동기: 먼저 위험을 떠안은 고객은 국가였다', '1947–1970s · 발명에서 양산으로 · 미·소 군비 경쟁이 만든 조달 수요',
    '<div class="rows gap14"><div>'
    f'<div class="strip-h"><span class="on" style="flex:{n_now}">태동기 · 이 장의 주제</span>'
    f'<span style="flex:{len(STRIP) - n_now}">그 이후의 발전 → 현재</span></div>'
    '<div class="strip sm" style="--ph:106px">' + ''.join(frame(i, y, t, p, cls=c) for i, y, t, p, c in STRIP) + '</div></div>'
    '<div class="split grow auto"><div class="col">' + slot('milex')
    + '<p class="note">Correlates of War NMC v6.0 · 명목 달러 · 소련은 환산 추정치 — 수준보다 함께 늘어난 추세를 볼 것 · '
      '반도체 구매액이 아닌 거시 배경</p></div>'
    '<div class="col center text"><span class="kicker">첫 번째 대량 고객 · 아폴로 유도컴퓨터</span>'
    '<div class="big amber">20만 개</div>'
    '<p>IC를 개당 <b>$20–30</b>에 구매<br>1965년까지 IC의 <b>최대 수요처</b></p>'
    + tags(['정부 연구 · 조달', '반복 생산 · 단가 하락', '민간 시장'])
    + '<p class="sm">“정부가 모든 손실을 보장했다”는 뜻은 아님 — 기술·생산 위험은 여전히 기업에 남았다.</p></div></div></div>',
    '수익이 아직 불확실한 단계에서, 정부는 첫 고객이자 위험 분담자였다.',
    ['transistor', 'kilby', 'intel_4004', 'chm', 'cow_nmc', 'hist_korea', 'hist_sputnik', 'hist_vietnam', 'img_apollo11']
    + ['img_' + s[0] for s in STRIP],
    method='군사비는 Correlates of War NMC v6.0의 명목 달러(당해연도) 값. 소련 값은 루블 지출을 달러로 환산한 추정치여서 '
           '출처마다 크게 다름. 두 선의 교차 시점을 근거로 삼지 않음. 조사 기준 2026-11-08.')

# ── 제1기: 미국의 고금리 · 강달러 ──
BOJ = []
for row in csv.reader((P / 'boj_discount.csv').read_text(encoding='utf-8').splitlines()):
    if row and re.match(r'^\d{4}\.\d{2}\.\d{2}$', row[0]):
        BOJ.append((row[0].replace('.', '-'), float(row[1])))


def boj_at(month):
    """그 달 말에 적용되던 일본 공정할인율."""
    return next(v for d, v in reversed(BOJ) if d <= month + '-31')


FFD = dict(FF)
GS10 = {d[:7]: v for d, v in M['GS10']}
r80 = [d for d, _ in FF if '1977-01' <= d <= '1992-12']       # 1979.10 표시선 왼쪽에 라벨이 들어갈 자리를 둔다
at80 = {d: i for i, d in enumerate(r80)}
M80 = HIS['macro80']
ff_peak_m, ff_peak = max(((d, FFD[d]) for d in r80), key=lambda t: t[1])
rate_gap = r1(Decimal(str(ff_peak)) - Decimal(str(boj_at(ff_peak_m))))
usd_a, usd_b = M80['dollar_index']['1980-09'], M80['dollar_index']['peak']['value']
usd_rise = (usd_b / usd_a - 1) * 100
deficit83 = abs(M80['deficit_omb_pct_gdp']['1983'])           # OMB Historical Table 1.2, 회계연도
assert (M80['dollar_index']['rise_from'], M80['dollar_index']['peak']['month']) == ('1980-09', '1985-03')
assert f'{usd_rise:.0f}' == '54' and f'{deficit83:.1f}' == '5.9' and f'{abs(M80["deficit_pct_gdp"]["1983"]):.1f}' == '5.7'
assert ff_peak_m == '1981-06' == M80['fedfunds_peak']['month'] and str(rate_gap) == '12.9'
assert M80['gs10_peak']['month'] == '1981-09' and GS10['1981-09'] == M80['gs10_peak']['pct']
yr_ticks80 = {at80[f'{y}-01']: str(y) for y in range(1978, 1993, 2)}
CHARTS['rates80'] = dict(
    title='미국과 일본의 정책금리 1977–1992', cap='정책금리 (%)', labels=[d.replace('-', '.') for d in r80], suf='%', dec=2, fs=13,
    y={'min': 0, 'max': 22, 'step': 5}, x={'ticks': list(yr_ticks80), 'map': yr_ticks80},
    series=[dict(name='미국 연방기금 실효금리 (월평균)', values=[FFD[d] for d in r80], color=C[0], w=2.5,
                 pts=[at80[ff_peak_m]], ptText={at80[ff_peak_m]: f'1981.06 · {ff_peak:.1f}%'}, end=f'미국 {FFD[r80[-1]]:.2f}%'),
            dict(name='일본 공정할인율', values=[boj_at(d) for d in r80], type='step', color=C[1], end=f'일본 {boj_at(r80[-1]):.2f}%')],
    marks=[dict(i=at80['1979-10'], label='1979.10 볼커 긴축', anchor='end', y=14),
           dict(i=at80['1985-09'], label='1985.09 플라자 합의', y=14)])
add('era1-rates', 2, '제1기: 같은 투자에도 자금의 가격은 달랐다', '1980–1990s 초 · PC 확산과 미·일 경쟁',
    '<div class="rows"><div><span class="kicker">왜 미국은 고금리 · 강달러였나</span>'
    + steps([('1973 · 1979 오일쇼크', f'두 차례 유가 급등<br>물가상승률 <b>{M80["cpi_yoy_peak"]["pct"]:.1f}%</b> (1980.03)'),
             ('1979.10 볼커의 긴축', f'통화량 억제로 전환<br>FF 월평균 <b>{ff_peak:.1f}%</b> (1981.06)'),
             ('1981–83 긴축 + 재정 확대', f'재정적자 GDP의 {deficit83:.1f}% (FY1983)<br>10년물 <b>{M80["gs10_peak"]["pct"]:.1f}%</b> (1981.09)'),
             ('1980–85 강달러', f'고금리 → 달러 자산으로 자본 유입<br>달러지수 <b>+{usd_rise:.0f}%</b> (1980.09–85.03)'),
             ('1985.09 플라자 합의', f'G5, 달러 약세 유도에 합의<br>엔/달러 <b>{M80["usdjpy"]["1985-09"]:.0f} → '
                               f'{M80["usdjpy"]["1987-12"]:.0f}엔</b> (1987.12)')], 'sm mt8')
    + '</div><div class="split grow auto"><div class="col">' + slot('rates80')
    + '<p class="note">미국: 연방기금 실효금리 월평균 · 일본: 공정할인율(월말 적용 기준). 정의가 다른 두 지표이며 기업의 실제 조달금리가 아님.</p></div>'
    '<div class="col center text"><span class="kicker">1981.06 · 미·일 정책금리 격차</span>'
    f'<div class="big amber tn">{rate_gap}%p</div><p>미국 FF {ff_peak:.2f}% − 일본 공정할인율 {boj_at(ff_peak_m):.2f}%</p>'
    '<p><b>미국</b> 고금리·강달러 → 투자·수출 부담<br><b>일본</b> 은행 금융·낮은 금리 → 설비 경쟁</p>'
    '<p class="sm">일본의 부상은 금리만의 결과가 아님 — 수율·품질·고객 기반·산업정책이 함께 작용.</p></div></div></div>',
    '낮은 자금조달 비용은 오래 걸리는 설비투자에서 경쟁력이 된다.',
    ['fred_ff', 'boj', 'japan', 'fh_oil73', 'fh_oil79', 'fh_inflation', 'fred_cpi', 'fh_volcker', 'fh_recession', 'feds_2016062',
     'omb_hist', 'fred_10', 'fred_twex', 'g5_plaza', 'plaza', 'fred_exjpus'],
    method='물가상승률은 CPI-U 전년동월비, 금리와 엔/달러는 월평균. 달러지수는 연준 무역가중 지수(주요 통화)의 1980.09 → 1985.03(정점) '
           f'상승률({usd_a:.1f} → {usd_b:.1f})이며, 달러는 플라자 합의(1985.09) 이전에 이미 정점을 지났다. '
           '재정적자는 OMB Historical Table 1.2(FRED 계열은 5.7%). 조사 기준 2026-11-08.')

# ── 제1기: 거시환경의 차이가 바꾼 주도권 (미국 → 일본) · 한국의 진입은 덧붙임 ──
RANK90 = D['ranking']['snapshots'][0]
COUNTRY = {'NEC': '일본', 'Toshiba': '일본', 'Hitachi': '일본', 'Fujitsu': '일본', 'Mitsubishi': '일본', 'Matsushita': '일본',
           'Motorola': '미국', 'Intel': '미국', 'Texas Instruments': '미국', 'Philips': '유럽'}
CCOL = {'미국': C[0], '일본': C[1], '유럽': C[2]}
top10 = RANK90['rows'][:10]
n_jp = sum(COUNTRY[r['name']] == '일본' for r in top10)
assert RANK90['year'] == 1990 and len(top10) == 10 and n_jp == 6
rank_max = max(r['revenue'] for r in top10)
top10_sum = sum(r['revenue'] for r in top10)
# Top 10 매출 합계를 국가별로 나눈 비중: (국가, 기업 수, %)
SHARE90 = [(k, sum(COUNTRY[r['name']] == k for r in top10),
            sum(r['revenue'] for r in top10 if COUNTRY[r['name']] == k) / top10_sum * 100) for k in ('일본', '미국', '유럽')]
assert [(n, f'{p:.0f}') for _, n, p in SHARE90] == [(6, '62'), (3, '31'), (1, '7')], SHARE90
SEG_W = 633                                     # 띠 폭(px, 칸 사이 틈 제외). 글자가 들어갈 자리가 있는 칸에만 이름을 적는다


def seg90(k, n, p):
    full, short = f'{k} {n}곳', f'{p:.0f}%'
    room = SEG_W * p / 100 - 20
    label = (f'<b>{full}</b>{short}' if tw(full + ' ' + short, 14) + 8 <= room else short if tw(short, 14) <= room else '')
    return f'<i style="flex:{p:.2f};background:{CCOL[k]}" data-tip="{k} {n}곳|Top 10 매출 합계의 {p:.1f}%">{label}</i>'


def macro_side(color, who, head, nums, text):
    """한 나라의 거시환경: 큰 숫자와 그 결과 한 줄."""
    cells = ''.join(f'<div><b>{v}</b><span>{k}</span></div>' for v, k in nums)
    return (f'<div class="mside" style="border-left-color:{color}"><div class="mside-h"><em>{who}</em><b>{head}</b></div>'
            f'<div class="mside-n">{cells}</div><p>{text}</p></div>')


share_label = ', '.join(f'{k} {n}곳 {p:.1f}%' for k, n, p in SHARE90)
add('era1-leaders', 2, '거시환경의 차이가 바꾼 주도권: 미국에서 일본으로',
    '1980년대 미·일의 금리 · 환율 격차 → 1990 반도체 공급업체 매출 순위 (파운드리 제외)',
    '<div class="rows gap14"><div class="split s50 linked to grow auto">'
    '<div class="col macro"><span class="kicker">원인 · 1980년대 거시환경의 차이</span>'
    + macro_side(C[0], '미국', '고금리 · 강달러',
                 [(f'{ff_peak:.1f}%', 'FF 금리 · 1981.06 월평균'), (f'+{usd_rise:.0f}%', '달러지수 · 1980.09–85.03')],
                 '<b>투자 · 수출 부담</b> → CPU 등 비메모리로 재편 <small>Intel, 1985년 DRAM 철수 발표</small>')
    + f'<div class="mgap"><span>1981.06 정책금리 격차</span><b>{rate_gap}%p</b></div>'
    + macro_side(C[1], '일본', '저금리 · 은행 금융',
                 [(f'{boj_at(ff_peak_m):.2f}%', '공정할인율 · 1981.06')],
                 '<b>오래 걸리는 설비 경쟁을 지속</b> → 메모리(DRAM) 주도')
    + '<p class="note">금리만의 결과는 아님 — 수율 · 품질 · 고객 기반 · 산업정책이 함께 작용.</p></div>'
    '<div class="col"><span class="kicker">결과 · 1990 반도체 공급업체 매출 Top 10 · $bn</span>'
    f'<div class="medium" style="margin:4px 0 10px">Top 10 중 <span class="amber">{n_jp}곳</span>이 일본</div>'
    f'<div class="segbar" role="img" aria-label="Top 10 매출 합계의 국가별 비중: {share_label}">'
    + ''.join(seg90(*s) for s in SHARE90) + '</div>'
    '<div class="segcap"><span>Top 10 매출 합계의 국가별 비중</span>'
    + legend([('sq', CCOL[k], k) for k, _, _ in SHARE90]) + '</div>'
    '<div class="hb c10" style="--hbn:190px">'
    + ''.join(f'<div class="hb-row"><span><span class="rk">{r["rank"]}</span>{r["name"]}</span><div class="hb-track">'
              f'<i style="width:{r["revenue"] / rank_max * 100:.1f}%;background:{CCOL[COUNTRY[r["name"]]]}"></i></div>'
              f'<b>{r["revenue"]:.2f}</b></div>' for r in top10)
    + '</div><p class="note">미국 3곳(Motorola · Intel · TI)은 CPU 등 비메모리에서 자리를 지켰다. Gartner 집계 기준 대표 연도 순위.</p></div>'
    '</div><div class="band top aside"><em>덧붙임 · 한국의 진입</em>'
    '<span>삼성 — <b>1983</b> 도쿄 선언 → <b>1992</b> DRAM 출하 1위 → <b>1993</b> 메모리 반도체 1위 · '
    '후발주자에게 필요했던 것은 <b>“손실을 견딜 시간”</b></span></div></div>',
    '미국의 퇴장이 아니라 경쟁 분야의 재편이었다. CPU와 메모리의 길이 갈렸다.',
    ['ranking_history', 'japan', 'fred_ff', 'boj', 'fred_twex', 'hist_intel_dram', 'samsung_history'],
    method='금리는 미국 연방기금 실효금리 월평균과 일본 공정할인율(월말 적용 기준)로, 정의가 다른 두 지표이며 기업의 실제 조달금리가 아님. '
           '달러지수는 연준 무역가중 지수(주요 통화)의 1980.09 → 1985.03 상승률. '
           '국가별 비중은 1990년 Top 10 기업의 매출 합계를 본사 소재지로 나눈 값이며 세계 시장 점유율이 아님. 조사 기준 2026-11-09.',
    tables=[dict(title='1990 반도체 공급업체 매출 Top 10', head=['순위', '기업', '국가·지역', '매출 ($bn)'],
                 rows=[[str(r['rank']), r['name'], COUNTRY[r['name']], f'{r["revenue"]:.3f}'] for r in top10]),
            dict(title='1990 Top 10 매출 합계의 국가별 비중', head=['국가·지역', '기업 수', '비중 (%)'],
                 rows=[[k, str(n), f'{p:.1f}'] for k, n, p in SHARE90])])

# ── 제2기: 분업이 깊어진 세 가지 이유 → 그 결과 (v5 에서 다시 짬. 위험의 이동을 다룬 era2-finance 는 뺌) ──
FAB_COST = 20                                   # 오늘날 선단 팹 한 곳의 건설비, 최대 $bn · hoover_triangle
FABLESS = {2002: 13, 2020: 32.8}                # 세계 IC 매출에서 팹리스 · 시스템 IC 기업이 차지한 몫(%) · icinsights_fabless2020
fabless_x = FABLESS[2020] / FABLESS[2002]
assert f'${FAB_COST}bn' in SOURCES['hoover_triangle']['note'] and '13%' in SOURCES['icinsights_fabless2020']['note']
assert f'{FABLESS[2020]}%' in SOURCES['icinsights_fabless2020']['note'] and f'{fabless_x:.1f}' == '2.5'


def lk(em, b, span):
    return f'<div class="lk"><em>{em}</em><b>{b}</b><span>{span}</span></div>'


def reason(no, kicker, title, hero, cap, text):
    """분업이 깊어진 이유 한 장: 큰 숫자 하나와 한 줄 설명."""
    return (f'<article class="panel why"><div class="kicker">이유 {no} · {kicker}</div><h3>{title}</h3>'
            f'<div class="whyn"><b class="tn">{hero}</b><span>{cap}</span></div><p>{text}</p></article>')


FBAR_H = 118                                    # 막대의 최대 높이(px)
add('era2-split', 2, '제2기: 한 회사가 모든 투자를 감당하기 어려워졌다', '1990s 중반–2000s · 인터넷·PC 확산 — 설계와 제조가 갈라진 세 가지 이유',
    '<div class="rows gap12"><div class="grid g3 auto">'
    + reason('①', '투자비', '공장 하나의 값이 치솟았다', f'~${FAB_COST}bn', '오늘날 선단 팹 한 곳의<br>건설비 (최대)',
             '미세공정이 발전할수록 공장 · 장비 · 공정 개발비가 급증 — 선단 로직을 만드는 회사는 이제 <b>세 곳</b>뿐')
    + reason('②', '새 사업 모델', '제조만 하는 회사가 나왔다', '1987', 'TSMC 설립<br>첫 전용 파운드리',
             '자체 칩을 팔지 않아 <b>고객과 경쟁하지 않는다</b> → 공장 없이도 칩 회사를 세울 수 있게 됐다 (NVIDIA 1993)')
    + reason('③', '수요 변동', '불황에는 공장이 짐이 됐다', f'{fmt(dotcom_drop, 0)}%',
             f'2001 세계 반도체 매출<br>${WY[2000]:.0f}bn → ${WY[2001]:.0f}bn',
             '수요가 꺼져도 설비의 고정비는 남는다 → 여러 고객의 물량을 한 공장에 모아 <b>가동률 위험을 나눈다</b>')
    + '</div><div class="splitmark arrows"><i>↓</i><span><b>그래서</b> · 설계와 제조가 갈라졌다</span><i>↓</i></div>'
    '<div class="split s70 grow auto"><div class="vsplit duo">'
    '<div class="rl">이전 · 통합<b>IDM</b></div>'
    '<div class="one"><b>Intel · Samsung · TI</b><span>설계 · 제조 · 패키징을 한 회사가 — 모든 투자를 혼자 감당</span></div>'
    '<div class="rl now">이후 · 분업<b>전문 기업</b></div><div class="chain">'
    + lk('제품 설계 · 판매', '팹리스', '공장 없이 설계에<br>자본을 집중')
    + lk('위탁 생산', '파운드리', '여러 고객의 물량으로<br>가동률을 확보')
    + lk('조립 · 검사 외주', 'OSAT', '후공정을<br>전문 기업에')
    + '</div></div>'
    '<div class="fshare"><span class="kicker">그 결과 · 팹리스의 몫</span>'
    f'<div class="fx tn">약 {fabless_x:.1f}배</div><div class="fbars">'
    + ''.join(f'<div class="{"now" if y == 2020 else ""}"><b class="tn">{v:g}%</b>'
              f'<i style="height:{round(FBAR_H * v / FABLESS[2020])}px"></i><span>{y}</span></div>' for y, v in FABLESS.items())
    + '</div><p class="note">세계 IC 매출에서 팹리스 · 시스템 IC 기업이 차지한 몫 · IC Insights</p></div></div></div>',
    '팹리스는 공장 부담을 덜고, 파운드리는 여러 고객의 수요를 묶었다.',
    ['tsmc_foundry', 'hoover_triangle', 'NVIDIA_HISTORY', 'wsts', 'icinsights_fabless2020', 'sia_ecosystem'],
    method=f'선단 팹 건설비 최대 약 ${FAB_COST}bn과 선단 로직 제조사 세 곳(Intel · Samsung · TSMC)은 Wong & Plummer(2023)의 서술로, 제2기 당시가 아닌 '
           '오늘날의 값이며 투자비가 계속 늘어 온 방향을 보이기 위해 인용함. TSMC는 1987년 설립된 첫 전용 파운드리로, 회사 설명에 따르면 '
           '이 사업 모델이 IC 설계 회사를 세우는 문턱을 크게 낮춤. 2001년 감소율은 WSTS 연간 청구액으로 직접 계산. '
           '팹리스의 몫은 IC Insights가 집계한 세계 IC 매출 대비 팹리스 · 시스템 IC 기업의 비중(2002년 13% → 2020년 32.8%)이며, '
           '메모리가 호황인 해에는 낮아짐. 세 가지 이유는 분업의 배경을 설명하는 정리이며 각 요인의 기여도를 잰 것이 아님. 조사 기준 2026-11-11.',
    tables=[dict(title='분업이 깊어진 이유 · 근거 수치', head=['구분', '수치', '출처'],
                 rows=[['이유 ① 투자비', f'선단 팹 건설비 최대 약 ${FAB_COST}bn · 선단 로직의 주요 제조사 3곳', 'Wong & Plummer (2023)'],
                       ['이유 ② 새 사업 모델', '1987 TSMC 설립(첫 전용 파운드리) · 1993 NVIDIA 설립', 'TSMC · NVIDIA'],
                       ['이유 ③ 수요 변동', f'2000년 ${WY[2000]:.1f}bn → 2001년 ${WY[2001]:.1f}bn ({fmt(dotcom_drop, 1)}%)', 'WSTS'],
                       ['결과 · 팹리스의 몫', '2002년 13% → 2019년 29.9% → 2020년 32.8% (세계 IC 매출 기준)', 'IC Insights']])])

# ── 제3기: 가격 급락은 공통이었다. 버틴 기업이 탈락한 기업을 인수했다 (v5 에서 두 장을 한 장으로 합침) ──
# 위: 원인에서 결과까지의 흐름 · 왼쪽: 왜 탈락했나(자산의 시간과 부채의 시간) · 오른쪽: 누가 떨어지고 누가 남았나
DRAM_DROP08, DRAM_LOSS08 = 75, 8                # 2008년 DRAM 가격 하락률(%) · 1–3분기 업계 손실($bn 이상) · trendforce_dram2008
assert f'약 {DRAM_DROP08}% 하락' in SOURCES['trendforce_dram2008']['note'] and f'${DRAM_LOSS08}bn 이상' in SOURCES['trendforce_dram2008']['note']


def maturity_svg():
    """개념도. 위는 투자 회수(자산)의 시간, 아래는 지급 일정(부채)의 시간. 곡선 좌표는 직접 정한 값."""
    Z, XM, Y_PLAN = 180, 400, 262      # 0 선 · 만기 시점 · 그때 계획 곡선의 높이
    plan = 'M70,180 C120,180 160,290 230,310 C300,330 430,250 520,180 C580,134 680,94 770,82'
    late = 'M230,310 C320,342 460,320 580,260 C640,230 670,195 700,180 C725,168 750,156 770,150'
    s = [T(0, 14, f'자산의 시간 · 누적 현금흐름 <tspan fill="{INK3}" font-weight="400">(개념도 · 실제 수치 아님)</tspan>', 13, INK2, weight=700),
         f'<line x1="492" x2="512" y1="10" y2="10" stroke="{C[0]}" stroke-width="3"/>', T(518, 14, '계획한 회수 경로', 12.5, INK2),
         f'<line x1="630" x2="650" y1="10" y2="10" stroke="{C[1]}" stroke-width="2.5" stroke-dasharray="6 4"/>',
         T(656, 14, '가격 하락 시 회수 지연', 12.5, INK2),
         f'<line x1="50" x2="780" y1="{Z}" y2="{Z}" stroke="#9db4c6" stroke-width="1.5"/>',
         T(40, Z + 5, '0', 13, INK2, 'end', 700), T(40, 112, '+', 17, INK3, 'end'), T(40, 292, '−', 17, INK3, 'end')]
    for x, y0, lab in ((70, Z, '투자 결정'), (230, 310, '양산 시작'), (520, Z, '계획한 회수'), (700, Z, '지연된 회수')):
        s.append(f'<line x1="{x}" x2="{x}" y1="{y0}" y2="352" stroke="{AXIS}" stroke-dasharray="2 4"/>')
        s.append(T(x, 370, lab, 13, INK2, 'middle'))
    s.append(f'<path d="{late}" fill="none" stroke="{C[1]}" stroke-width="2.5" stroke-dasharray="7 6" stroke-linecap="round"/>')
    s.append(f'<path d="{plan}" fill="none" stroke="{C[0]}" stroke-width="3" stroke-linecap="round"/>')
    for x, y, c in ((70, Z, C[0]), (230, 310, C[0]), (520, Z, C[0]), (700, Z, C[1])):
        s.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{c}" stroke="{SURF}" stroke-width="2"/>')
    # 만기: 아래 지급 일정에서 올라와 계획 곡선과 만난다
    s.append(f'<line x1="{XM}" x2="{XM}" y1="40" y2="428" stroke="{RED}" stroke-width="1.5" stroke-dasharray="5 5"/>')
    s.append(T(XM, 32, '부채 만기', 14, INK, 'middle', 700))
    s.append(f'<line x1="{XM}" x2="{XM}" y1="{Z}" y2="{Y_PLAN}" stroke="{RED}" stroke-width="5" stroke-linecap="round"/>')
    for y in (Z, Y_PLAN):
        s.append(f'<circle cx="{XM}" cy="{y}" r="5.5" fill="{RED}" stroke="{SURF}" stroke-width="2"/>')
    s.append(T(XM - 14, 216, '만기 시점의 미회수 투자', 14.5, INK, 'end', 700, 'halo'))
    s.append(T(XM - 14, 236, '→ 차환이 필요하다', 13.5, INK2, 'end', cls='halo'))
    # 부채의 시간
    s.append(T(0, 416, '부채의 시간 · 정해진 지급 일정', 13, INK2, weight=700))
    s.append(f'<line x1="70" x2="{XM}" y1="440" y2="440" stroke="{AXIS}" stroke-width="2"/>')
    s.append(f'<line x1="{XM}" x2="780" y1="440" y2="440" stroke="{AXIS}" stroke-width="2" stroke-dasharray="3 6"/>')
    s.append(f'<circle cx="70" cy="440" r="5" fill="{INK3}" stroke="{SURF}" stroke-width="2"/>')
    s.append(T(70, 464, '차입', 12.5, INK3, 'middle'))
    for x in range(120, 361, 48):
        s.append(f'<circle cx="{x}" cy="440" r="4.5" fill="{SURF}" stroke="{INK3}" stroke-width="2"/>')
    s.append(T(240, 464, '이자 지급', 12.5, INK3, 'middle'))
    s.append(f'<path d="M{XM},428 L{XM + 12},440 L{XM},452 L{XM - 12},440 Z" fill="{RED}" stroke="{SURF}" stroke-width="2"/>')
    s.append(T(XM, 470, '원금 만기', 13.5, INK, 'middle', 700))
    s.append(T(600, 464, '차환하지 못하면 유동성 위기', 12.5, INK3, 'middle'))
    return ('<svg viewBox="0 0 798 476" role="img" '
            'aria-label="자산의 회수 기간과 부채 만기의 불일치 개념도">' + ''.join(s) + '</svg>')


add('era3-consolidation', 2, '제3기: 가격 급락은 공통이었다. 버틴 기업이 더 강해졌다',
    '2007–2013 · 메모리 증설 경쟁과 금융위기 → 탈락과 인수 → DRAM Big 3',
    '<div class="rows">'
    + steps([('2006–07 · 증설 경쟁', '공급 과잉 — 2007년 4분기부터<br><b>현금원가 아래</b>로 판매'),
             ('2008 · 금융위기', f'수요 급감 — DRAM 가격 <b>약 −{DRAM_DROP08}%</b><br>업계 손실 ${DRAM_LOSS08}bn 이상 (1–3분기)'),
             ('2009 · 2012 · 탈락', 'Qimonda 파산 (2009.01)<br>Elpida 회생절차 (2012.02)'),
             ('2012–13 · 인수', 'SK의 하이닉스 인수 · Micron의<br>Elpida 인수 → <b>DRAM Big 3</b>'),
             ('2017–18 · 보상', f'메모리 슈퍼사이클<br>세계 매출 <b>${WY[2018]:.0f}bn</b> (2018)')], 'sm')
    + '<div class="split s55 grow auto"><div class="col"><span class="kicker">왜 탈락했나 · 공장은 장기 자산, 만기는 먼저 돌아온다</span>'
    '<div class="fitsvg">' + maturity_svg() + '</div></div>'
    '<div class="choice tight"><div class="choice-h"><span>누가 떨어지고, 누가 남았나</span><span style="text-align:right">결과</span></div>'
    + choice_row('Qimonda', MUTE, '독일', '공정 전환이 늦은 채 가격 급락을 맞았다', '2009 파산', '', True)
    + choice_row('Elpida', MUTE, '일본', '기술은 대등 — 엔고 · 만기가 닥친 단기 차입', '2012 회생절차', '2013 Micron이 인수', True)
    + choice_row('Samsung', C[0], '한국', '다각화된 사업과 투자 여력 — 불황에도 투자 지속', '생존', 'DRAM Big 3')
    + choice_row('SK hynix', C[1], '한국', '2012 SK그룹 편입(약 3.4조원) — 자본 기반 확보', '생존', 'DRAM Big 3')
    + choice_row('Micron', C[2], '미국', 'Elpida를 인수해 규모 확보', '생존 · 인수자', 'DRAM Big 3')
    + '</div></div></div>',
    '탈락을 가른 것은 기술만이 아니었다. 만기를 버틴 기업이 탈락한 기업을 인수하며 더 강해졌다.',
    ['trendforce_dram2008', 'isuppli_dram2008', 'trendforce_elpida2012', 'elpida_failure', 'elpida_causes', 'elpida_bonds', 'elpida_acquisition',
     'qimonda', 'hynix_lineage', 'fed_crisis', 'ranking_2017', 'wsts'],
    method='왼쪽 그림은 설명을 위한 개념도이며 특정 기업의 실제 현금흐름이 아님. '
           f'DRAM 가격 약 −{DRAM_DROP08}%는 DRAMeXchange가 집계한 2008년 1Gb(667MHz) 현물가 $2.29 → $0.58, 업계 손실 ${DRAM_LOSS08}bn 이상은 '
           '2008년 1–3분기 합계(TrendForce). “현금원가 아래 판매”는 iSuppli(2009.02)의 분석으로, 가격 하락은 금융위기 전인 2007년의 '
           '공급 과잉에서 시작됐고 금융위기가 수요를 줄여 깊어짐. Elpida는 이 첫 불황을 넘겼으나 2011–12년의 가격 재하락과 엔고 속에 '
           '만기가 닥친 차입을 넘지 못함(TrendForce 2012.02 · Elpida 공시). “차입이 많은 회사부터 탈락”은 법칙이 아니며 현금 · 만기 · 원가 · '
           '지원 여력이 함께 작용함. 세계 매출은 WSTS 연간 청구액. 조사 기준 2026-11-08 (DRAM 가격 · 탈락 경위는 2026-11-11).',
    tables=[dict(title='메모리 재편 일지', head=['시기', '사건', '근거'],
                 rows=[['2007년 4분기~', 'DRAM 업체들이 현금원가 아래로 판매 (공급 과잉)', 'iSuppli (2009.02)'],
                       ['2008', f'DRAM 가격 약 −{DRAM_DROP08}% ($2.29 → $0.58) · 1–3분기 업계 손실 ${DRAM_LOSS08}bn 이상 · 감산으로 생산능력 약 20% 감소',
                        'TrendForce (2009.01)'],
                       ['2009.01', 'Qimonda 파산 신청', 'iSuppli (2009.02) · Infineon 연차보고서'],
                       ['2012.02', 'Elpida 회생절차 신청 — 기술은 뒤지지 않았으나 만기가 닥친 단기 차입 · 부채비율 70%', 'Elpida 공시 · TrendForce (2012.02)'],
                       ['2012', 'SK그룹의 하이닉스 인수', 'SK hynix'],
                       ['2013.07', 'Micron의 Elpida 인수 완료 → DRAM Big 3', 'Micron Form 8-K'],
                       ['2017–18', f'메모리 슈퍼사이클 · 세계 반도체 매출 2018년 ${WY[2018]:.1f}bn', 'WSTS']])])

# 분업과 재편의 결과: 오늘의 밸류체인 지도 → M&A 가 만든 네 갈래 (v5 에서 간지 뒤에서 이 자리로 옮김)
slide_valuechain()
slide_mna()

# ── 제4기: AI — 투자하는 쪽과 매출을 얻는 쪽 ──
BT = Q['bigtech']
QS = [r['q'] for r in BT['Microsoft']]
SKH, SAM = Q['skhynix'], Q['samsung']
assert len(QS) == 15 and (QS[0], QS[-1]) == ('2023Q1', '2026Q3'), QS
assert all([r['q'] for r in rows] == QS for rows in list(BT.values()) + [SKH, SAM])
qlab = [q[2:4] + q[4:] for q in QS]                    # 23Q1 … 26Q3
QT = [i for i, q in enumerate(QS) if q.endswith('Q1')] + [len(QS) - 1]


def q4(key):
    return [round(sum(BT[n][i][key] for n in BT), 1) for i in range(len(QS))]


ocf4, capex4 = q4('ocf'), q4('capex')
fcf4_last = sum(BT[n][-1]['fcf'] for n in BT)
over = [i for i in range(len(QS)) if capex4[i] > ocf4[i]]
assert over == [len(QS) - 1], 'CAPEX가 영업현금흐름을 넘은 분기는 2026Q3 하나'
skh_rev = [r['revenue'] for r in SKH]
CHARTS['aiBuyers'] = dict(
    title='빅테크 4사 합계 · 영업현금흐름과 CAPEX', labels=qlab, pre='$', suf='bn', dec=1, fs=13,
    x={'ticks': QT}, y={'step': 50, 'max': 225, 'pre': '$', 'dec': 0},
    series=[dict(name='영업현금흐름', values=ocf4, color=C[0], w=2.5, end=f'영업CF ${ocf4[-1]:.1f}bn'),
            dict(name='CAPEX (설비투자)', values=capex4, color=C[1], w=3, end=f'CAPEX ${capex4[-1]:.1f}bn')],
    notes=[dict(i=len(QS) - 1, v=capex4[-1], text='CAPEX > 영업CF', dx=-10, dy=-10, anchor='end', strong=True)])
CHARTS['aiSupplier'] = dict(
    title='SK hynix 분기 매출', type='bar', labels=qlab, suf='조', dec=1, fs=13, x={'ticks': QT},
    y={'step': 25, 'max': 120, 'dec': 0},
    series=[dict(name='SK hynix 매출', values=[round(v, 1) for v in skh_rev], color=C[1], pts=[0, len(QS) - 1])])


def kpi(value, cls, text):
    return f'<div class="kpi"><b class="tn {cls}">{value}</b><span>{text}</span></div>'


add('era4-ai', 2, '제4기: 투자는 구매자가, 매출은 공급자가', '2023Q1–2026Q3 분기 추이 · AI 수요가 GPU에서 HBM·DRAM·NAND로 확산',
    '<div class="grid g2">'
    + card('구매자 · 빅테크 4사 합계', '분기 · $bn',
           kpi(f'CAPEX {capex4[-1] / capex4[0]:.1f}배', 'amber', f'2023Q1 ${capex4[0]:.1f}bn → 2026Q3 ${capex4[-1]:.1f}bn')
           + slot('aiBuyers'),
           f'Microsoft · Alphabet · Amazon · Meta 분기 현금흐름표 합계. 조사 기간 중 CAPEX가 영업현금흐름을 처음 넘어섰다 — '
           f'2026Q3 4사 합계 FCF −${abs(fcf4_last):.1f}bn.')
    + card('공급자 · SK hynix 분기 매출', '조원',
           kpi(f'매출 {skh_rev[-1] / skh_rev[0]:.1f}배', 'green', f'2023Q1 {skh_rev[0]:.1f}조 → 2026Q3 {skh_rev[-1]:.1f}조원')
           + slot('aiSupplier'),
           '연결 매출, 원화(조원). 달러 금액인 왼쪽 차트와 축·단위가 다르다 — 크기가 아니라 방향을 비교.')
    + '</div>',
    '산업의 호황을 이해하려면, 투자하는 쪽의 장부도 봐야 한다.',
    [f'sec_q_{n}' for n in BT] + ['skh_q', 'audit_6_0'],
    method='빅테크 수치는 SEC 분기 보고서의 현금흐름표(영업활동 현금흐름 · 유형자산 취득)를 역년 분기로 맞춘 값. '
           'Microsoft는 6월 결산이어서 회계 분기를 역년 분기에 대응시킴. FCF = 영업현금흐름 − CAPEX. 조사 기준 2026-11-08.')


# ── PART 2 정리: 간지의 두 축 아래에 질문 카드 두 장씩 (v5: 02 카드를 ‘가격’에서 ‘사이클’로 바꿈) ──
def lesson(num, kicker, question, viz, text, foot):
    """질문 카드. 가운데 그림 칸이 남는 높이를 차지한다."""
    return (f'<article class="panel"><div class="lhead"><span class="num">{num}</span><span class="kicker">{kicker}</span></div>'
            f'<h3>{question}</h3><div class="lviz">{viz}</div><p>{text}</p><div class="pfoot">{foot}</div></article>')


# 세계 반도체 매출의 전년 대비 증감률(WSTS 연간, 온전한 해만): 오르내림의 폭이 곧 사이클
GROW = [(y, (WY[y] / WY[y - 1] - 1) * 100) for y in sorted(WY)[1:]]
g_hi, g_lo = max(GROW, key=lambda t: t[1]), min(GROW, key=lambda t: t[1])
n_down = sum(v < 0 for _, v in GROW)
assert (GROW[0][0], GROW[-1][0], len(GROW)) == (1987, 2025, 39) and (g_hi[0], g_lo[0], n_down) == (1995, 2001, 9), (g_hi, g_lo, n_down)
assert fmt(g_lo[1], 0) == fmt(dotcom_drop, 0)


def cycle_svg():
    """02 사이클 카드의 그림: 해마다의 증감률을 0% 선 위아래의 막대로. 가장 큰 호황과 불황에만 이름표를 단다."""
    W, H, z, top, bot = 262, 104, 62, 15, 14            # 그림 크기 · 0% 선의 높이 · 위아래 글자 자리
    k = min((z - top) / g_hi[1], (H - z - bot) / -g_lo[1])
    bw = W / len(GROW)
    s = []
    for i, (y, v) in enumerate(GROW):
        h, x = max(1, abs(v) * k), round(i * bw + .8, 1)
        s.append(f'<rect x="{x}" y="{round(z - h if v >= 0 else z, 1)}" width="{round(bw - 1.6, 1)}" height="{round(h, 1)}" rx="1" '
                 f'fill="{C[0] if v >= 0 else C[7]}"' + tip(f'{y}년', f'세계 반도체 매출 전년 대비 {fmt(v, 1, sign=True)}%') + '/>')
    s.append(f'<line x1="0" x2="{W}" y1="{z}" y2="{z}" stroke="#9db4c6" stroke-width="1"/>')
    for (y, v), up in ((g_hi, True), (g_lo, False)):
        cx = (y - GROW[0][0] + .5) * bw
        s.append(T(round(cx, 1), round(z - v * k - 4, 1) if up else round(z - v * k + 12, 1),
                   f'{y} {fmt(v, 0, sign=True)}%', 12, INK, 'middle', 700, 'tn'))
    s.append(T(0, H - 1, str(GROW[0][0]), 10.5, INK3, cls='tn') + T(W, H - 1, str(GROW[-1][0]), 10.5, INK3, 'end', cls='tn'))
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="세계 반도체 매출의 전년 대비 증감률 '
            f'{GROW[0][0]}–{GROW[-1][0]}년">' + ''.join(s) + '</svg><span class="lcap">세계 반도체 매출 · 전년 대비</span>')


# PART 3 의 세 이슈: PART 2 정리의 예고 띠 · PART 3 간지 · 마무리 표가 같은 목록을 쓴다
ISSUES = ['빅테크 CAPEX 치킨게임', '미·중 패권 경쟁과 거시 환경', '반도체 기업의 현금 배분']
ISSUE_NO = '①②③'
assert len(ISSUES) == len(ISSUE_NO)

add('industry-lessons', 2, '반도체의 역사는 두 개의 축으로 읽힌다',
    '수요의 이동 · 밸류체인 분업화 × 자본력 · M&amp;A 재편 — 네 가지 질문으로 점검한다',
    '<div class="rows"><div class="axes">'
    + ''.join(f'<div class="axis"><em>{k}</em><b>{name}</b><span>{role}</span></div>' for k, name, _, role in AXES)
    + '</div><div class="grid g4 lessons grow auto">'
    + lesson('01', '수요', '성장의 중심은<br>어디인가',
             '<div class="stair"><span>PC · Intel</span><span>메모리 · 삼성</span><span>AI · NVIDIA</span></div>',
             '수요의 중심이 옮겨갈 때마다<br>선두 기업이 바뀌었다.', '아날로그는 필수지만,<br>리니어의 성장률은 제한됐다')
    + lesson('02', '사이클', '왜 등락이<br>이렇게 큰가', cycle_svg(),
             '최종 수요까지 사슬이 길어<br>수요의 변화가 위로 갈수록 커진다.',
             f'채찍효과 — {len(GROW)}년 가운데<br>{n_down}번의 역성장')
    + lesson('03', '자본', '회복까지<br>버틸 수 있는가',
             '<div class="runway"><div>버틸 수 있는 시간<i style="width:56%"></i></div>'
             '<div>회복까지 걸리는 시간<i class="need" style="width:100%"></i></div></div>',
             '현금·만기·투자 유연성이<br>생존을 가른다.', '버틴 기업이 탈락한 기업을<br>인수하며 재편을 이끈다')
    + lesson('04', '정책', '자본비용을<br>누가 바꾸는가', tags(['금리', '보조금', '수출통제', '전력 · 인허가'], '', 'g2x'),
             '금리·보조금·수출통제·인허가가<br>투자의 속도를 정한다.', '기술 밖의 조건이<br>투자 회수를 좌우한다')
    + '</div><div class="band"><em>PART 3</em><b>같은 틀을 2026년에</b><span>AI 시대의 세 가지 이슈 — '
    + ' · '.join(f'{ISSUE_NO[i]} {t}' for i, t in enumerate(ISSUES)) + '</span></div></div>',
    '수요의 이동이 주도 기업을 바꾸고, 사이클을 버틴 자본력이 M&amp;A로 산업을 재편했다.',
    ['ranking_history', 'linear_10k_2016', 'wsts', 'bullwhip', 'hoover_triangle', 'elpida_failure', 'fed_history'],
    method=f'02 카드의 막대는 WSTS 연간 청구액으로 직접 계산한 세계 반도체 매출의 전년 대비 증감률({GROW[0][0]}–{GROW[-1][0]}, {len(GROW)}개 연도): '
           f'가장 큰 증가는 {g_hi[0]}년 {fmt(g_hi[1], 1, sign=True)}%, 가장 큰 감소는 {g_lo[0]}년 {fmt(g_lo[1], 1, sign=True)}%이고 '
           f'감소한 해는 {n_down}번. 채찍효과는 공급망 일반에 대한 설명(Lee 외 1997)으로, 최종 수요보다 위쪽 단계의 주문 변동이 더 커지는 현상을 말함. '
           '반도체에서는 새 팹이 생산능력을 한꺼번에 늘려 한동안 공급 과잉이 되기 쉽다는 점(Wong & Plummer 2023)이 더해짐. '
           '사슬의 길이와 변동 폭의 관계를 이 덱에서 따로 계량한 것은 아님. 조사 기준 2026-11-08 (02 카드는 2026-11-11).',
    tables=[dict(title='세계 반도체 매출과 전년 대비 증감률 (WSTS 연간)', head=['연도', '매출 ($bn)', '전년 대비 (%)'],
                 rows=[[str(y), f'{WY[y]:,.1f}', fmt(v, 1, sign=True)] for y, v in GROW])])

# ═════════════════════════ PART 3 · AI 시대가 마주한 세 가지 재무적 이슈 ═════════════════════════
divider(3, 'AI 시대가 마주한<br>세 가지 재무적 이슈',
        '<p class="dv-desc">수요가 폭발할수록 더 중요한 질문.<br>누가 끝까지 버티고, 누가 추격하며, 현금을 어디에 쓸 것인가.</p>'
        '<div class="issues">' + ''.join(f'<span><b>{ISSUE_NO[i]}</b>{t}</span>' for i, t in enumerate(ISSUES)) + '</div>')

# ── 2026: 분기 매출 ──
WQ = Q['wsts']['quarters']
SIA3 = Q['wsts']['sia_reported_2026Q3']
HY = Q['wsts']['half_years']
wq = {w['q']: w['usd_bn'] for w in WQ}
h1_26, h1_25 = wq['2026Q1'] + wq['2026Q2'], wq['2025Q1'] + wq['2025Q2']
h1_yoy = (h1_26 / h1_25 - 1) * 100
assert abs(h1_26 - HY['h1_2026_usd_bn']) < .01 and abs(h1_25 - HY['h1_2025_usd_bn']) < .01 and fmt(h1_yoy, 0) == '108'
wq_q = [w['q'] for w in WQ] + ['2026Q3']
wq_v = [round(w['usd_bn'], 1) for w in WQ] + [SIA3['usd_bn']]
assert (wq_q[0], wq_q[-2], len(wq_q)) == ('2022Q1', '2026Q2', 19)
LIGHT = '#8fbdf3'
wi = wq_q.index
CHARTS['wstsQ'] = dict(
    title='세계 반도체 분기 매출 2022Q1–2026Q3', type='bar', labels=[q[2:4] + q[4:] for q in wq_q], tipLabels=wq_q,
    pre='$', suf='bn', dec=0, fs=13, y={'step': 100, 'max': 570, 'pre': '$'},
    x={'ticks': [wi(f'{y}Q1') for y in range(2022, 2027)] + [len(wq_q) - 1]},
    series=[dict(name='세계 반도체 매출', values=wq_v, colors=[MUTE if q < '2026' else C[0] for q in wq_q[:-1]] + [LIGHT],
                 pts=[wi('2023Q1'), wi('2025Q2'), wi('2026Q2'), len(wq_q) - 1])],
    bands=[dict(a=wi('2026Q1'), b=len(wq_q) - 1, label='2026')],
    legendItems=[dict(c=MUTE, t='2022–2025', bar=True), dict(c=C[0], t='2026 상반기 · WSTS 통계표(8월판)', bar=True),
                 dict(c=LIGHT, t='2026 3분기 · SIA 발표 (집계 시점 다름)', bar=True)])
add('market-2026', 3, '2026년, 산업 매출이 1년 만에 두 배가 됐다', '세계 반도체 분기 매출 2022Q1–2026Q3 · 상반기는 실제, 연간은 아직 전망',
    '<div class="split"><div class="col">' + slot('wstsQ')
    + '<p class="note">WSTS Historical Billings Report(2026.08판)의 월별 실적을 분기로 합산. 2026년 3분기는 SIA가 11월에 발표한 수치로, '
      '집계 시점이 달라 앞 분기와 이어서 계산하지 않는다.</p></div>'
    '<div class="col center text"><span class="kicker">2026 상반기 · 전년동기 대비</span>'
    f'<div class="big green tn">+{h1_yoy:.0f}%</div>'
    f'<p>${h1_25:.0f}bn → <b>${h1_26:.0f}bn</b> <span class="badge">WSTS 통계표 8월판</span></p>'
    '<p class="sm">8월 6일 보도자료의 첫 집계는 $702bn · +102%</p>'
    '<div class="medium tn mt20">$1.655tn</div>'
    '<p>2026 연간 전망 · 전년 대비 +108% <span class="badge">연간 확정 실적 아님</span></p>'
    f'<p class="sm">3분기 ${SIA3["usd_bn"]}bn은 SIA 발표치 · 전분기 대비 +{SIA3["qoq_pct_vs_2026Q2"]}%</p></div></div>',
    'AI 물량 확대와 메모리 가격 상승이 함께 만든 호황이다.', ['wsts_hbr', 'wsts_q2_2026', 'sia_q3_2026', 'audit_0_0'],
    method='분기 매출은 WSTS 통계표(2026.08판)의 월별 청구액 합계. 상반기 증가율은 2026 1–2분기 합계 ÷ 2025 1–2분기 합계로 직접 계산. '
           '연간 전망은 WSTS 2026.08 전망. 조사 기준 2026-11-08.')

# ── ① 투자 경쟁과 현금흐름 ──
GUIDE = F['capexGuidance2026']
ENT = dict(zip(F['companies'], C))           # Microsoft 파랑 · Alphabet 주황 · Amazon 청록 · Meta 노랑
assert list(F['companies']) == ['Microsoft', 'Alphabet', 'Amazon', 'Meta']
assert [sum(GUIDE[n][i] for n in F['companies']) for i in (0, 1)] == GUIDE['total'] == [720, 740]
g_max = max(GUIDE[n][1] for n in F['companies'])


def guide_row(n):
    """회사 이름·금액 한 줄, 그 아래에 막대. 가이던스가 범위면 넘는 부분을 옅게 잇는다."""
    lo, hi = GUIDE[n]
    val = f'${hi}' if lo == hi else f'${lo}–{hi}'
    bars = f'<i style="width:{lo / g_max * 100:.1f}%;background:{ENT[n]}"></i>'
    if lo != hi:
        bars += f'<i style="width:{(hi - lo) / g_max * 100:.1f}%;background:{ENT[n]}"></i>'
    return (f'<div class="gr"><div class="gr-h"><span>{n}</span><b>{val}<small>bn</small></b></div>'
            f'<div class="hb-track{" rng" if lo != hi else ""}">{bars}</div></div>')


add('buyer-cash', 3, '① CAPEX 치킨게임: 투자 경쟁이 현금흐름을 압박한다', '2026 CAPEX 가이던스 합계 $720–740bn · 집행 실적과 구별',
    '<div class="g3b">'
    + card('빅테크 4사 · FCF', '$bn', '<div id="financialOverview" class="grow"></div>',
           'FY21–25 + 2026.09 TTM(최근 12개월). Microsoft는 6월 결산, 나머지는 12월 결산.')
    + card('2026 CAPEX 가이던스', '$bn',
           '<div class="col center grow">'
           f'<div class="capex-hero">${GUIDE["total"][0]}–{GUIDE["total"][1]}bn</div><div class="capex-cap">4사 합계 · 회사 가이던스</div>'
           '<div class="guide">'
           + ''.join(guide_row(n) for n in sorted(F['companies'], key=lambda n: -GUIDE[n][1]))
           + '</div></div><p class="note">옅은 부분은 가이던스 범위. 회계연도와 CAPEX 정의가 회사마다 달라 '
             '같은 기준의 실적 합산이 아니다.</p>')
    + card('Meta · 장기차입 조달액', '$bn', '<div id="debtChart" class="grow"></div>',
           '현금흐름표의 조달액. 차입 잔액·순증액과 다르다. 회사마다 포함 범위가 달라 Meta 사례로 한정.')
    + '</div>',
    '모두 적자는 아니다. Amazon은 TTM 적자, 다른 3사는 양수지만 투자 부담은 확대됐다.',
    ['fin_Microsoft', 'fin_Alphabet', 'fin_Amazon', 'fin_Meta', 'audit_1_0', 'audit_1_1', 'audit_1_2', 'audit_1_3', 'audit_2_0'],
    tables=[dict(title='2026 CAPEX 가이던스 ($bn)', head=['기업', '하단', '상단'],
                 rows=[[n, str(GUIDE[n][0]), str(GUIDE[n][1])] for n in F['companies']] + [['합계'] + [str(v) for v in GUIDE['total']]])])

# 대시보드: 빅테크 4사 + 추가 6사(요청 순서). 타일은 세 묶음으로 읽는다 — 버는 힘(위 4개) · 투자와 FCF · 부채 부담
# 회사별 유의점. FISCAL_NOTE · QNOTE 는 장표 아래 한 줄 주석에, DASH_METHOD 는 출처 창의 산식 설명에 쓴다
FISCAL_NOTE = {
    'Microsoft': '6월 결산 — 회계 분기를 역년 분기에 대응',
    'Oracle': '5월 결산 — 2 · 5 · 8 · 11월에 끝나는 회계 분기를 역년 1–4분기에 대응',
    'Apple': '9월 결산 — 회계 분기를 역년 분기에 대응',
}
QNOTE = {
    'Meta': 'Meta의 분기 이자비용은 차입금 이자 기준이어서 이자보상배율이 다소 높게 나오며, 2024Q1–Q2는 분기별 수치가 태그되지 않아 비움.',
    'Oracle': '2023Q1은 자본이 음수여서 부채비율을 비움.',
    'Apple': '이자비용은 2023Q3까지만 공시되어 그 뒤의 이자보상배율은 비움.',
    'CoreWeave': '2025.03 상장 — 2023년은 분기 값이 공시되지 않았고 재무상태는 2024Q4부터. 이자비용은 순이자비용 기준. '
                 '2026Q3는 조사일(11.10)까지 미발표.',
    'Nebius': '분기 XBRL이 없어 회사의 분기 실적 발표문 기준(계속사업, 2024Q1부터). 2025Q2 · 2026Q1의 순이익 흑자는 투자지분 평가이익 때문. '
              '2026Q3는 11.12 발표 예정.',
    'SpaceX': '2026.06 상장 — 10-Q와 투자설명서로 2025Q1부터 구성(xAI · X 합산 기준). 2024년 분기 값은 공시되지 않았고, '
              '재무상태는 2024Q4 · 2025Q4 이후만.',
}
DASH_METHOD = {
    'Microsoft': 'Microsoft는 6월 결산이어서 회계 분기를 역년 분기에 대응시킴.',
    'Amazon': 'Amazon · Oracle은 총부채가 태그되지 않아 자산 − 자본으로 구함.',
    'Meta': 'Meta의 분기 이자비용은 차입금 이자(InterestExpenseDebt, 금융리스 이자 제외) 기준이며, 2024Q1 · Q2는 두 분기 합산치만 '
            '태그되어 있어 이자보상배율을 비움.',
    'Oracle': 'Oracle은 5월 결산으로 2 · 5 · 8 · 11월 말에 끝나는 회계 분기를 역년 1–4분기에 대응시켰고(예: 2026Q3 = 2026.06–08), '
              '2023Q1은 자본이 음수여서 부채비율을 비움.',
    'Apple': 'Apple은 9월 결산(분기 말은 3 · 6 · 9 · 12월 마지막 토요일 무렵)이며, FY2024부터 이자비용을 따로 공시하지 않아 '
             '이자보상배율은 2023Q3까지.',
    'Tesla': 'Tesla의 순이익은 보통주주 귀속분.',
    'CoreWeave': 'CoreWeave는 2025.03 상장으로 2023년은 연간 값만 공시되어 분기를 비웠고, 총자산 · 총부채는 2024Q4부터 태그됨. '
                 '이자비용은 손익계산서의 순이자비용(Interest expense, net)이며, 2026Q3 실적은 조사일까지 발표되지 않음.',
    'Nebius': 'Nebius는 분기 XBRL이 없어(연차보고서만 태그) 회사 분기 실적 발표문의 요약 재무제표에서 읽음: 계속사업 기준이며 '
              '2024Q1–2025Q1은 이후 발표문이 Toloka를 제외해 다시 제시한 값, 영업현금흐름은 계속사업분, CAPEX는 유형 · 무형자산 취득액. '
              '2023년 분기와 2024.03 재무상태는 옛 Yandex N.V. 기준이어서 비웠고, 이자비용은 2025Q2부터 계상됨. 2025Q2 · 2026Q1의 순이익에는 '
              '투자지분 평가이익(각 $597.4M · $780.6M)이 들어 있음. 2025Q3 이후는 감사 전 발표치(감사를 거친 2025년 연간 영업손실은 분기 합계보다 '
              '$15.5M 큼)이며, 2026Q3는 2026.11.12 발표 예정.',
    'SpaceX': 'SpaceX는 2026.06 상장으로, 10-Q(2026Q2 · Q3)에 태그된 값에 회사 IR 사이트의 투자설명서(Form 424B4)를 더해 2025Q1부터 구성함: '
              '1분기와 2025년 연간은 투자설명서, 2025Q4 = 연간 − 9개월 누계, 2분기 현금흐름 = 상반기 − 1분기. 모든 기간은 xAI · X를 소급 합산한 '
              '기준. 2024년 분기 값과 2025년 1–3분기 말 재무상태표는 공시되지 않아 비움.',
}
# 추가 6사의 지표별 공시 범위 (처음, 마지막, 분기 수). 자료가 바뀌면 아래 묶기 단계의 assert 에서 걸린다
ALL_Q = ('2023Q1', '2026Q3', 15)
DASH_KEYS = ('revenue', 'revenueGrowth', 'netIncome', 'operatingMargin', 'capex', 'fcf', 'interestCoverage', 'debtRatio')


def spans_of(**gaps):
    """여덟 지표의 공시 범위. 적지 않은 지표는 15개 분기가 모두 있다."""
    return {k: gaps.get(k, ALL_Q) for k in DASH_KEYS}


DASH_SPANS = {
    'Oracle': spans_of(debtRatio=('2023Q2', '2026Q3', 14)),
    'Apple': spans_of(interestCoverage=('2023Q1', '2023Q3', 3)),
    'Tesla': spans_of(),
    'CoreWeave': spans_of(revenue=('2024Q1', '2026Q2', 10), revenueGrowth=('2025Q1', '2026Q2', 6), netIncome=('2024Q1', '2026Q2', 10),
                          operatingMargin=('2024Q1', '2026Q2', 10), capex=('2024Q1', '2026Q2', 10), fcf=('2024Q1', '2026Q2', 10),
                          interestCoverage=('2024Q1', '2026Q2', 10), debtRatio=('2024Q4', '2026Q2', 7)),
    'Nebius': spans_of(revenue=('2024Q1', '2026Q2', 10), revenueGrowth=('2025Q1', '2026Q2', 6), netIncome=('2024Q1', '2026Q2', 10),
                       operatingMargin=('2024Q1', '2026Q2', 10), capex=('2024Q1', '2026Q2', 10), fcf=('2024Q1', '2026Q2', 10),
                       interestCoverage=('2025Q2', '2026Q2', 5), debtRatio=('2024Q2', '2026Q2', 9)),
    'SpaceX': spans_of(revenue=('2025Q1', '2026Q3', 7), revenueGrowth=('2026Q1', '2026Q3', 3), netIncome=('2025Q1', '2026Q3', 7),
                       operatingMargin=('2025Q1', '2026Q3', 7), capex=('2025Q1', '2026Q3', 7), fcf=('2025Q1', '2026Q3', 7),
                       interestCoverage=('2025Q1', '2026Q3', 7), debtRatio=('2024Q4', '2026Q3', 5)),
}
ADDED = QA['order']
DASH = list(F['companies']) + ADDED
assert ADDED == ['Oracle', 'Apple', 'Tesla', 'CoreWeave', 'Nebius', 'SpaceX'] and len(set(DASH)) == 10, DASH
add('buyer-dashboard', 3, '매출의 성장보다, 현금의 내구성을 확인한다',
    f'하이퍼스케일러 · 네오클라우드 등 {len(DASH)}개사 → 여덟 가지 지표의 분기 추이 · {QS[0]}–{QS[-1]}',
    '<div class="dash-top"><label for="companySelect">기업</label><select id="companySelect">'
    + ''.join(f'<option>{n}</option>' for n in DASH)
    + '</select><div class="dash-legend"><span><i></i>① 버는 힘 · 차입 여력</span>'
      '<span class="k2"><i></i>② 투자 부담 · FCF</span><span class="k3"><i></i>③ 부채 부담 · 기업별 차이</span></div></div>'
      '<div class="dashboard" id="dashboard"></div><p class="note" id="dashNote"></p>',
    '치킨게임에서 끝까지 버티는 힘은 기존 사업의 현금창출력과 재무구조에서 갈린다.',
    [f'sec_qf_{n}' for n in DASH],
    method='SEC XBRL(companyfacts)에 태그된 값을 역년 분기로 맞춤(Nebius는 회사 분기 실적 발표문, SpaceX의 상장 전 기간은 투자설명서 — '
           '뒤의 회사별 설명 참조). 손익 · 현금흐름 항목은 3개월 공시값을 우선 쓰고, 없으면 회계연도 누계의 '
           '차감으로 구함(회계 4분기 = 연간 − 9개월 누계). 재무상태 항목은 분기 말 잔액. 정정 공시가 있으면 가장 최근 제출분을 사용하며, '
           '공시된 값으로 구할 수 없는 분기는 비워 두고 추정 · 보간하지 않음. '
           '매출 성장률 = 전년 동기 대비 · 영업이익률 = 영업이익 ÷ 매출 · FCF = 영업CF − 현금 CAPEX(금융리스 원금 미차감) · '
           '이자보상배율 = 분기 영업이익 ÷ 영업외 이자비용 · 부채비율 = 총부채 ÷ 자본(분기 말). 자본은 자산 − 총부채로, 비지배지분과 '
           '상장 전 상환전환우선주 등 임시자본(temporary equity)을 포함하며 0 이하이면 부채비율을 비움. '
           + ' '.join(DASH_METHOD[n] for n in DASH if n in DASH_METHOD)
           + ' 조사 기준: 기존 4사 2026-11-09, 추가 6사 2026-11-10.')

# ── ② 미·중 패권 경쟁과 거시 환경 · 1980년대 미·일 구도의 재현 ──
# v5 에서 다시 짰다. 말하려는 것: AI 경쟁은 미국 기업끼리의 싸움에서 끝나지 않는다 → 두 나라의 거시 환경(금리 · 정치 · 자금)이 다르다
# → 1980년대 미·일과 닮았지만 금리 격차와 군사 · 안보 구도가 달라 당장 넘어가기는 어렵다 → 길어지면 격차는 좁혀질 수 있다.
# 화면에는 주장마다 근거 하나씩만 두고, 10년물 금리 · LPR 같은 보조 수치는 뺐다.
M_NOW = FF[-1][0]
assert M_NOW == '2026-10', M_NOW
US_FF = FFD[M_NOW]                             # 연방기금 실효금리 2026.10 월평균 (1981.06 수치와 같은 기준)
FED_RANGE = '3.75–4.00%'                       # 연준 목표범위 · 2026.09.16 +25bp → 10.28 동결 (audit 3)
CN_RRP7 = 1.40                                 # 인민은행 7일물 역레포(정책금리) · 2025.05.07 적용 이후 유지 · ADB AsianBondsOnline
BIGFUND3 = '3,440억 위안'                       # 국가집적회로산업투자기금 3기 등록자본 · 2024.05 · Reuters(2차)
BALLOT_YES, BALLOT_ALL = 31, 35                # Data Center Ballot · 2026.11.06 집계
AI_US, AI_CN = 1503, 1464                      # Stanford AI Index 2026 · 2026.03 Arena 최고 모델 점수
MIL_US, MIL_CN = 954, 336                      # 2025년 군사비 $bn · SIPRI (중국은 추정치) · sipri_2025
gap_now = r1(Decimal(str(US_FF)) - Decimal(str(CN_RRP7)))
mil_x = MIL_US / MIL_CN
assert (f'{US_FF:.2f}', str(gap_now), f'{mil_x:.1f}') == ('3.88', '2.5', '2.8'), (US_FF, gap_now, mil_x)
assert f'미국 ${MIL_US}bn' in SOURCES['sipri_2025']['note'] and f'중국 ${MIL_CN}bn' in SOURCES['sipri_2025']['note']
assert '1기 2014년' in SOURCES['bigfund3']['note'] and '2기 2019년' in SOURCES['bigfund3']['note']


def uc_cell(side, head, body, hero=''):
    """한 나라의 한 항목: 낱말 하나(큰 글씨) · (있으면) 숫자 · 근거 한두 줄."""
    big = f'<strong class="tn">{hero}</strong>' if hero else ''
    return f'<div class="uc-v {side}"><div><b>{head}</b>{big}</div><span>{body}</span></div>'


add('us-china', 3, '② 미·중 패권 경쟁과 거시 환경: 1980년대 미·일 구도의 재현',
    'AI 경쟁은 미국 기업끼리의 싸움에서 끝나지 않는다 — 금리도 정치도 다른 두 나라의 패권 다툼',
    '<div class="uc"><div class="uc-now"><span class="kicker">지금 · 두 나라의 거시 환경은 다르다</span><div class="uc-grid">'
    '<span></span><div class="uc-c us">미국</div><div class="uc-c cn">중국</div>'
    '<div class="uc-k">금리</div>'
    + uc_cell('us', '고금리', 'FF 금리 · 2026.10', f'{US_FF:.2f}%')
    + uc_cell('cn', '저금리', '7일물 역레포 · 2026.10', f'{CN_RRP7:.2f}%')
    + '<div class="uc-k">정치</div>'
    + uc_cell('us', '정치 노이즈 심화', '2026.11 중간선거 — 민주당이 상·하원 장악<br>'
              f'데이터센터 제한 주민투표 {BALLOT_YES}/{BALLOT_ALL}건 찬성')
    + uc_cell('cn', '정치 일원화', '정책의 방향이 한곳에서 정해진다<br>반도체 기금 1 → 2 → 3기 (2014 · 2019 · 2024)')
    + '<div class="uc-k">자금</div>'
    + uc_cell('us', '민간 주도', f'빅테크 4사 CAPEX 가이던스 ${GUIDE["total"][0]}–{GUIDE["total"][1]}bn')
    + uc_cell('cn', '정부 주도', f'국가 반도체 기금 3기 {BIGFUND3}')
    + '</div></div>'
    '<div class="uc-then"><span class="kicker">1980년대 미·일과 견주면</span>'
    '<article class="panel sm"><div class="uc-tag">닮은 점</div><h3>고금리의 미국 ↔ 저금리 · 국가가 미는 추격자</h3>'
    f'<p>그때 일본은 메모리 주도권을 가져갔다 — 1981 금리 격차 {rate_gap}%p → 1990 Top 10 중 <b>{n_jp}곳이 일본</b></p></article>'
    '<article class="panel sm grow"><div class="uc-tag diff">다른 점</div><h3>이번에는 그때처럼 넘어가기 어렵다</h3>'
    f'<div class="uc-diff"><div><b class="tn">{rate_gap}%p → {gap_now}%p</b><span>정책금리 격차가 훨씬 작다</span></div>'
    f'<div><b class="tn">${MIL_US}bn vs ${MIL_CN}bn</b><span>군사비(2025) — 일본은 동맹이었고 중국은 경쟁국.<br>'
    '미국은 수출통제로 첨단 장비 · HBM 접근을 막는다</span></div></div></article></div>'
    '<div class="uc-end"><div><em>당장은</em><b>AI 패권이 넘어가기 어렵다</b></div><i>→</i>'
    '<div class="warn"><em>이 환경이 길어지면</em><b>격차는 좁혀질 수 있다</b>'
    f'<span>최고 AI 모델의 격차는 이미 {AI_US - AI_CN}점 · Arena {AI_US:,} vs {AI_CN:,}</span></div></div></div>',
    '당장 패권이 뒤집히기는 어렵다. 그러나 저금리 · 정부 지원이 길어지면 격차는 좁혀질 수 있다.',
    ['fred_ff', 'fed_2026', 'audit_3_0', 'audit_3_1', 'audit_3_2', 'cn_adb', 'cn_policy_shift', 'midterms', 'dc_ballot', 'audit_4_0', 'bigfund3',
     'audit_1_0', 'audit_1_1', 'audit_1_2', 'audit_1_3', 'boj', 'japan', 'ranking_history', 'sipri_2025', 'bis_2022', 'ai_index'],
    method='정책금리 격차는 같은 달의 미국 연방기금 실효금리 월평균에서 상대국 정책금리를 뺀 값: '
           f'1981.06 {ff_peak:.2f}% − 일본 공정할인율 {boj_at(ff_peak_m):.2f}% = {rate_gap}%p, '
           f'2026.10 {US_FF:.2f}% − 인민은행 7일물 역레포 {CN_RRP7:.2f}% = {gap_now}%p. '
           '일본 공정할인율과 중국 7일물 역레포는 정의가 다른 정책금리이며 기업의 실제 조달금리가 아님. '
           f'연준 목표범위는 2026.09.16에 25bp 올린 {FED_RANGE}(10.28 동결). '
           '인민은행이 2026.11 초 익일물 금리(1.25%)를 정책금리로 삼는 체계로 바꿨다는 보도가 있어, 중국 정책금리는 2026.10 기준으로 적음. '
           '모두 명목금리이므로 환율 · 물가 · 신용 위험 · 자본 이동 제약을 반영한 실제 자본비용의 격차와 같지 않음. '
           '‘정치 노이즈 심화’ · ‘정치 일원화’는 발표자의 해석을 줄인 말이며, 근거는 2026.11.04 중간선거에서 민주당이 상·하원 다수를 확보했다는 보도'
           f'(새 의회는 2027년 출범)와 구속력 있는 데이터센터 제한 주민투표 {BALLOT_ALL}건 중 {BALLOT_YES}건 찬성(2026.11.06 집계 · 인증 전 결과 포함), '
           '국가집적회로산업투자기금(반도체 기금)이 2014 · 2019 · 2024년에 세 차례 조성된 사실임. '
           f'빅테크 CAPEX는 Microsoft · Alphabet · Amazon · Meta의 2026년 회사 가이던스 합계(전망), 반도체 기금 3기 {BIGFUND3}은 2024.05 설립 당시 '
           '등록자본으로, 규모와 성격이 다른 자금이어서 두 금액을 직접 비교하지 않음. '
           f'군사비는 SIPRI의 2025년 값(당해연도 달러, 중국은 추정치)으로 미국이 약 {mil_x:.1f}배이며, 군사비가 곧 반도체 경쟁력을 뜻하지는 않음 — '
           '1980년대의 일본은 미국의 동맹이었고 지금의 중국은 수출통제(2022.10~)의 대상이라는 구도의 차이를 보이기 위한 값임. '
           'Arena 점수는 단일 벤치마크 · 단일 시점(2026.03)의 값으로, 점수 차를 성능의 비율로 해석하지 않으며 칩 제조능력이나 국가 경쟁력 순위가 아님. '
           '결론은 전망이 아니라 조건부 판단임. 조사 기준: 금리 2026-11-10, 군사비 2026-11-11, 그 밖은 2026-11-08.',
    tables=[dict(title='미국과 상대국의 정책금리 (%)', head=['시점', '지표', '미국', '상대국', '격차 (%p)'],
                 rows=[['1981.06', '미국 FF 월평균 · 일본 공정할인율', f'{ff_peak:.2f}', f'{boj_at(ff_peak_m):.2f}', str(rate_gap)],
                       ['2026.10', '미국 FF 월평균 · 중국 7일물 역레포', f'{US_FF:.2f}', f'{CN_RRP7:.2f}', str(gap_now)]]),
            dict(title='군사비 (2025 · SIPRI · $bn)', head=['구분', '군사비', '세계 비중'],
                 rows=[['미국', str(MIL_US), '33%'], ['중국 (추정)', str(MIL_CN), '12%']]),
            dict(title='데이터센터 제한 주민투표 (구속력 있는 안건 · 2026.11.06 집계)', head=['구분', '건수'],
                 rows=[['제한 찬성', str(BALLOT_YES)], ['그 외', str(BALLOT_ALL - BALLOT_YES)], ['합계', str(BALLOT_ALL)]]),
            dict(title='최고 AI 모델의 Arena 점수 (2026.03 · Stanford AI Index 2026)', head=['구분', '점수'],
                 rows=[['미국 최고 모델', f'{AI_US:,}'], ['중국 최고 모델', f'{AI_CN:,}'], ['차이', str(AI_US - AI_CN)]])])

# ── ③ 현금 배분 · 리니어의 질문이 돌아왔다 (v5 에서 장기계약 장표를 합침) ──
# 세 칸을 왼쪽에서 오른쪽으로 읽는다: ① 쌓이는 현금 → ② 배분의 선택(투자인가 환원인가) → ③ 그 전에 확인할 것(장기계약의 질)
sam_op, skh_op = [r['op'] for r in SAM], [r['op'] for r in SKH]
CHARTS['supplierOP'] = dict(
    title='삼성전자 · SK hynix 분기 영업이익', cap='분기 영업이익 (조원)', labels=qlab, suf='조', dec=1, fs=13,
    x={'ticks': QT}, y={'step': 25, 'max': 120, 'dec': 0},
    series=[dict(name='삼성전자', values=sam_op, color=C[0], w=2.5, end=True),
            dict(name='SK hynix', values=skh_op, color=C[1], w=2.5, end=True)])
LTA_CUSTOMERS, LTA_SHARE = 14, 50            # 출처 audit_7_0 · SK hynix LTA 14개 고객 · 2027–28 생산능력의 50% 이상


def alloc(name, color, rows, foot):
    body = ''.join(f'<span>{k}<span class="tag{" act" if tag == "실제" else ""}">{tag}</span></span><b>{v}<small>조원</small></b>'
                   for k, tag, v in rows)
    return (f'<article class="panel"><h3><i style="background:{color}"></i>{name}</h3><div class="kv">{body}'
            f'<span class="full">{foot}</span></div></article>')


add('cash-allocation', 3, '③ 막대한 현금, 어디에 배분할 것인가?', '리니어의 질문이 2026년의 삼성·SK hynix로 돌아왔다 — 결정에 앞서 장기계약의 질을 본다',
    '<div class="cash3">'
    '<div class="col"><div class="colh">① 쌓이는 현금 <b>분기 영업이익</b></div>' + slot('supplierOP')
    + '<p class="note">연결 분기 영업이익, 조원. 회사 규모와 사업 구성이 다르며, 영업이익은 현금흐름과 다르다.</p></div>'
    '<div class="col"><div class="colh">② 배분의 선택 <b>투자인가, 환원인가</b></div><div class="alloc">'
    # PART 1 의 리니어를 다시 불러온다: 배당은 늘었고 성장은 멈췄다 (수치는 PART 1 장표와 같은 변수)
    '<div class="recall"><em>PART 1 · 반면교사 Linear</em>'
    f'<span>주당배당 <b>${lin_dps[0]:.2f} → ${lin_dps[-1]:.2f}</b> · 매출 연 <b>{fmt(lin_cagr)}%</b><br>→ 2017년 ADI에 편입</span></div>'
    + alloc('삼성전자', C[0], [('2026 CAPEX', '전망', '84.4'), ('2026 주주환원', '예상', '90–110')],
            '환원 중 확정 · 집행 35조 · 최종 금액은 2027.01 이사회 결정')
    + alloc('SK hynix', C[1], [('3분기 말 순현금', '실제', '98.7'), ('2026 주주환원', '계획', '약 100')],
            '용인 1기 가동으로 2027년 투자 크게 증가 예상')
    + '</div></div>'
    '<div class="col"><div class="colh rest">③ 먼저 확인할 것 <b>계약의 질</b></div>'
    '<article class="panel grow lta"><div class="kicker">SK hynix의 장기공급계약(LTA)</div><h3>물량은 보인다</h3>'
    f'<div class="lta-body"><div class="lrow"><div class="hero tn">{LTA_CUSTOMERS}<small>개 고객</small></div>'
    '<div><div class="custs">' + '<i></i>' * LTA_CUSTOMERS + '</div><p>LTA를 체결한 고객 수</p></div></div>'
    f'<div class="lrow"><div class="hero tn">{LTA_SHARE}<small>% 이상</small></div>'
    f'<div><div class="meter lgm"><i style="width:{LTA_SHARE}%"></i><u style="width:{100 - LTA_SHARE}%"></u></div>'
    '<p>2027–28 생산능력 중 LTA 비중</p></div></div></div>'
    '<div class="lrest"><em>그러나 남는 위험</em>'
    '<div><b>가격</b>시장 상황에 따라 다시 정해질 수 있다</div>'
    '<div><b>신용</b>고객이 끝까지 지불할 수 있는가</div></div>'
    '<div class="pfoot">장기계약은 보이는 물량을 늘릴 뿐,<br>위험을 없애지는 않는다</div></article></div></div>',
    '환원에 묶여 성장을 놓칠 것인가, R&amp;D · M&amp;A로 다음 판을 준비할 것인가 — 리니어가 남긴 질문이다.',
    ['sam_q', 'skh_q', 'C01', 'C02', 'audit_5_0', 'audit_5_1', 'audit_6_0', 'audit_7_0', 'linear_10k_2016', 'linear_10k_2007', 'linear_close'],
    method='영업이익은 삼성전자 · SK hynix의 분기 실적 발표(연결, 조원). 삼성전자의 2026년 CAPEX 84.4조원(DS 부문 76.8조원)은 회사 전망, '
           '주주환원 90–110조원은 예상치로 이 가운데 확정 · 집행분이 35조원이며 최종 금액은 2027.01 이사회에서 정해짐. '
           'SK hynix의 순현금 98.7조원은 3분기 말 현금 114.5조원 − 차입 15.8조원, 주주환원 약 100조원은 회사 계획. '
           f'장기공급계약(LTA)은 SK hynix가 밝힌 {LTA_CUSTOMERS}개 고객 · 2027–28년 생산능력의 {LTA_SHARE}% 이상이며, 가격은 합의한 범위 안에서 '
           '시장 상황을 반영하는 방식이어서 재협상 가능성이 남음. 장기계약은 과거에도 있었고, 지금은 규모 · 기간 · 고객 집중과 위험 배분이 달라진 점임. '
           '조사 기준 2026-11-08.')

# ── 마무리: PART 3 의 세 이슈를 과거 → 현재 → 확인할 것으로 다시 읽는다 ──
CLOSE = [('CAPEX 치킨게임', '메모리 치킨게임 · Elpida', '빅테크 CAPEX · FCF', '끝까지 버틸 자금력 · 재무 건전성'),
         ('미·중 경쟁과 거시 환경', '1980s 미·일의 금리 격차', '미국 고금리 · 중국 정부 지원', '저금리 · 정부 지원의 지속 기간'),
         ('현금 배분', 'Linear · 환원과 매각', '삼성 · SK hynix의 현금', '재투자(R&amp;D · M&amp;A) · 환원 · 완충력')]
assert len(CLOSE) == len(ISSUES)
add('closing', 3, '과거의 질문은 다른 모습으로 돌아온다', '수요의 이동 × 거시 환경 · 자본력 — 반도체의 역사는 같은 틀 안에서 반복된다',
    f'<div class="rows" style="gap:26px;justify-content:center"><div class="closing" style="--n:{len(CLOSE)}"><span></span>'
    + ''.join(f'<div class="hd"><small>이슈 {ISSUE_NO[i]}</small>{c[0]}</div>' for i, c in enumerate(CLOSE))
    + '<div class="rl">과거</div>' + ''.join(f'<div class="c">{c[1]}</div>' for c in CLOSE)
    + '<div class="rl">현재</div>' + ''.join(f'<div class="c">{c[2]}</div>' for c in CLOSE)
    + '<div class="rl r3">확인할 것</div>' + ''.join(f'<div class="c rule">{c[3]}</div>' for c in CLOSE)
    + '</div><div class="quote">과거의 맥락을 AI 시대에 대입하면<br>'
      '<span class="green">다음 의사결정의 이정표</span>가 보인다.</div></div>',
    '리니어는 사라졌지만, 리니어가 마주했던 재무적 선택은 끝나지 않았다.')

# ═════════════════════════ 묶기 · 점검 · 쓰기 ═════════════════════════
# 대시보드가 읽는 항목만 남긴다 (v3.js 의 dashboard · financialOverview)
FIN_KEYS = ('year', 'label', 'revenue', 'revenueGrowth', 'netIncome', 'operatingMargin', 'capex', 'fcf', 'interestCoverage', 'debtRatio')
QKEYS = ('q',) + DASH_KEYS


def dash_quarters(name):
    """대시보드의 분기 지표. 기존 4사의 매출 · CAPEX · FCF 는 다른 장표가 쓰는 분기 자료(Q['bigtech'])와 같아야 한다."""
    rows = [{k: r.get(k) for k in QKEYS} for r in (QF if name in BT else QA)['companies'][name]]
    assert [r['q'] for r in rows] == QS, name
    if name in BT:
        assert all(abs(r[k] - b[k]) < 0.0015 for r, b in zip(rows, BT[name]) for k in ('revenue', 'capex', 'fcf')), name
    return rows


def available(rows, k):
    """그 지표가 공시된 분기: (처음, 마지막, 개수). 하나도 없으면 None."""
    have = [r['q'] for r in rows if r[k] is not None]
    return (have[0], have[-1], len(have)) if have else None


FIN = {'companies': {n: {            # ① 투자 경쟁 장표의 연간 FCF · Meta 차입 차트
    'annual': [{k: r.get(k) for k in FIN_KEYS} for r in c['annual']],
    'ttm2026': {k: c['latestTTM'].get(k) for k in FIN_KEYS},
    'chartSeries': [{k: r.get(k) for k in ('year', 'label', 'debtIssuance')} for r in c['chartSeries']],
} for n, c in F['companies'].items()},
    'dash': {n: {'quarters': dash_quarters(n), 'fiscalNote': FISCAL_NOTE.get(n, ''), 'quarterNote': QNOTE.get(n, '')} for n in DASH}}
q_null = sorted((n, r['q'], k) for n in BT for r in FIN['dash'][n]['quarters'] for k in QKEYS if r[k] is None)
assert q_null == [('Meta', '2024Q1', 'interestCoverage'), ('Meta', '2024Q2', 'interestCoverage')], q_null
# 추가 6사: 공시되지 않은 분기는 비어 있다. 자료가 바뀌면 여기서 걸리게 지표별 공시 범위를 적어 둔다
spans = {n: {k: available(FIN['dash'][n]['quarters'], k) for k in QKEYS[1:]} for n in ADDED}
assert spans == DASH_SPANS, ' 공시 범위가 달라졌다:' + ''.join(f' [{n}] {v!r}' for n, v in spans.items())

# 점검: 하나라도 걸리면 파일을 쓰지 않는다
ids = [s['id'] for s in SLIDES]
assert len(ids) == len(set(ids)), '장표 id 가 겹친다'
# 발표 흐름: 참고 장표는 5 · 7쪽(인수 협상 · 섹터 순위), PART 3 은 번호가 붙은 이슈 세 개가 차례로 나온다
ref_pages = {i + 1: s['id'] for i, s in enumerate(SLIDES) if s['ref']}
assert ref_pages == {5: 'linear-deal', 7: 'sector-ranking'}, ref_pages
numbered = ''.join(s['title'][0] for s in SLIDES if s['title'][0] in '①②③④⑤⑥')
assert numbered == ISSUE_NO, numbered
problems = []
for s in SLIDES:
    problems += [f'{s["id"]}: 출처 목록에 없는 키 {k}' for k in s['sources'] if k not in SOURCES]
    problems += [f'{s["id"]}: 정의되지 않은 차트 {c}' for c in re.findall(r'data-(?:chart|linear)="([^"]+)"', s['html']) if c not in CHARTS]
    problems += [f'{s["id"]}: 없는 이미지 {f}' for f in re.findall(r'src="(assets/[^"]+)"', s['html']) if not (P / f).is_file()]
    if '????' in s['html'] + s['title'] + s['sub'] + s['take']:
        problems.append(f'{s["id"]}: 깨진 글자')
assert not problems, '\n'.join(problems)
used = set(re.findall(r'data-(?:chart|linear)="([^"]+)"', ''.join(s['html'] for s in SLIDES)))
assert used == set(CHARTS), f'쓰이지 않는 차트: {sorted(set(CHARTS) - used)}'
for s in SLIDES:
    if tw(re.sub(r'<[^>]+>', '', s['take']), 22) > 1289:
        print(f'  ! 결론 문장이 두 줄로 넘어갈 수 있음: {s["id"]}')


def embed_images(html):
    """사진을 data URI 로 바꿔 HTML 한 파일만으로 열리게 한다."""
    def uri(m):
        f = P / m.group(1)
        return f'src="data:{mimetypes.guess_type(f.name)[0]};base64,{base64.b64encode(f.read_bytes()).decode()}"'
    return re.sub(r'src="(assets/v3/deck/[^"]+)"', uri, html)


# v4 만 쓴다. v3(26장) · v2(28장) · 기업재무_발표자료_12조.html · index.html(31장)은 이전 커밋의 소스로 만든 결과물을 그대로 둔다
OUT = '기업재무_발표자료_12조_v5.html'
CSS = (P / 'v3.css').read_text(encoding='utf-8-sig')
JS = (P / 'v3.js').read_text(encoding='utf-8-sig')
consts = dict(SLIDES=[dict(s, html=embed_images(s['html'])) for s in SLIDES], CHARTS=CHARTS, SOURCES=SOURCES, PARTS=PARTS,
              ERAS=ERAS, FIN=FIN, SECTOR=SECTOR, TL=TL)
script = '\n'.join(f'const {k}=' + json.dumps(v, ensure_ascii=False).replace('</', '<\\/') + ';' for k, v in consts.items())
PEN_COLORS = [('#ffd84d', '노랑'), ('#ff5d6c', '빨강'), ('#37ccff', '하늘'), ('#ffffff', '흰색')]
page = (
    '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    f'<title>{Path(OUT).stem} | 리니어는 왜 사라졌나?</title><style>' + CSS + '</style></head><body>'
    '<header class="top"><div class="brand"><b>12</b> SEMICONDUCTOR</div><nav aria-label="파트 이동">'
    + ''.join(f'<button data-part="{i}">PART {i} · {PARTS[i]}</button>' for i in (1, 2, 3))
    + '</nav><a href="기업재무_반도체산업.html" target="_blank">반도체 산업 아카이브 ↗</a></header>'
    '<main class="viewport"><div class="stage" id="stage"><div id="slideHost"></div>'
    '<svg id="ink" viewBox="0 0 1440 810" aria-hidden="true"></svg><div id="tip" class="tip" hidden></div></div></main>'
    '<footer class="control"><button id="toc">목차<kbd>T</kbd></button><button id="sources">출처<kbd>S</kbd></button>'
    '<button id="pen" aria-pressed="false" title="화면에 선을 그어 강조합니다. 장표를 넘기면 지워지고 저장되지 않습니다.">✎ 펜<kbd>D</kbd></button>'
    '<span class="pentools" id="penTools" hidden>'
    + ''.join(f'<button class="sw" data-ink-color="{c}" style="background:{c}" aria-label="{n}" title="{n}"></button>' for c, n in PEN_COLORS)
    + '<button data-ink-tool="pen">선</button><button data-ink-tool="hl">형광펜</button>'
    '<button id="inkUndo">되돌리기<kbd>Z</kbd></button><button id="inkClear">모두 지우기<kbd>X</kbd></button></span>'
    '<div class="progress"><i id="progress"></i></div><span id="clock" class="optional">00:00</span>'
    '<button id="timer" class="optional">타이머 시작</button><button id="full">전체화면<kbd>F</kbd></button>'
    '<div class="navgroup"><button id="prev" aria-label="이전 장표">←</button><span id="position" aria-live="polite"></span>'
    '<button id="next" aria-label="다음 장표">→</button></div></footer>'
    '<dialog id="modal" aria-labelledby="modalTitle"><button id="close" class="close" aria-label="닫기">닫기 ×</button>'
    '<h2 id="modalTitle"></h2><div id="modalBody"></div></dialog>'
    '<script>' + script + '</script><script>' + JS + '</script></body></html>')
assert '????' not in re.sub(r'data:image/[^"]+', '', page)

(P / OUT).write_text(page, encoding='utf-8')
(P / 'v3_deck_content.json').write_text(
    json.dumps(dict(slides=SLIDES, charts=CHARTS, eras=ERAS), ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Built {OUT}: {len(SLIDES)} slides; {len(CHARTS)} charts; {len(page):,} characters')

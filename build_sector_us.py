"""미국 Fortune 500 · 섹터별 매출 Top 10 (1996–2026년판, 5년 간격) → sector_us.json

usage:
    python -I -X utf8 build_sector_us.py            sector_us.json 생성
    python -I -X utf8 build_sector_us.py --dump     검토용 표(섹터·연도별 상위 14곳)
    python -I -X utf8 build_sector_us.py --flow     검토용 표(기업별 연도 흐름)

입력
    research/fortune{1996,2001,2006,2011,2016,2021,2026}_next.json   fortune.com 순위 페이지의 __NEXT_DATA__
    research/fortune500_gap_rows.json                               아카이브에서 빠진 행(rows)·잘못 붙은 행(drop)

Fortune 500 N년판은 직전 회계연도(N−1) 매출 순위다. 화면에는 매출 연도(1995 … 2025)로 표시한다.
섹터는 Fortune 업종을 경제 섹터로 다시 묶은 분석용 분류이며, 공식 GICS 과거 시계열이 아니다.

분류 규칙
    1) 당시 Fortune 업종 → 섹터(INDUSTRY 표).
    2) 지금도 존속하는 기업은 현재의 섹터를 전 기간에 적용(COMPANY). 예: Walmart·Target = 필수소비재.
    3) 사라진 기업은 당시 Fortune 업종을 따른다.
    4) 주력 사업이 달랐던 시기는 따로 지정(COMPANY_AT).
연속성 규칙
    합병은 존속 법인(인수 주체), 분할은 본업과 사명을 이어 간 쪽을 같은 기업으로 본다(KEY_ALIAS · KEY_AT).
    표시 이름은 당시 사명(NAME · NAME_AT).
"""
import json
import pathlib
import re
import sys

P = pathlib.Path(__file__).resolve().parent
LIST_YEARS = [1996, 2001, 2006, 2011, 2016, 2021, 2026]
TOP = 10
EXCLUDED = ['realestate']          # Fortune 500 편입 기업이 0–6곳뿐이라 Top 10을 만들 수 없음

SECTORS = {
    'it': 'IT', 'communication': '커뮤니케이션', 'discretionary': '경기소비재', 'staples': '필수소비재',
    'healthcare': '헬스케어', 'financials': '금융', 'industrials': '산업재', 'energy': '에너지',
    'materials': '소재', 'utilities': '유틸리티', 'realestate': '부동산',
}

# Fortune 업종(연도마다 이름이 조금씩 다름) → 섹터.
INDUSTRY = {
    'Advertising, marketing': 'communication',
    'Aerospace': 'industrials', 'Aerospace & Defense': 'industrials', 'Aerospace and Defense': 'industrials',
    'Airlines': 'industrials',
    'Apparel': 'discretionary',
    'Automotive Retailing, Services': 'discretionary',
    'Beverages': 'staples',
    'Building Materials, Glass': 'materials',
    'Chemicals': 'materials',
    'Commercial Banks': 'financials',
    'Computer And Data Services': 'it', 'Computer Peripherals': 'it', 'Computer Software': 'it',
    'Computers, Office Equipment': 'it',
    'Construction and Farm Machinery': 'industrials',
    'Diversified Financials': 'financials',
    'Diversified Outsourcing Services': 'industrials',
    'Education': 'discretionary',
    'Electronics, Electrical Equip.': 'industrials',
    'Energy': 'energy',
    'Engineering & Construction': 'industrials', 'Engineering, Construction': 'industrials',
    'Entertainment': 'communication',
    'Equipment Leasing': 'industrials',
    'Financial Data Services': 'financials',
    'Food': 'staples', 'Food & Drug Stores': 'staples', 'Food and Drug Stores': 'staples',
    'Food Consumer Products': 'staples', 'Food Production': 'staples',
    'Food Services': 'discretionary',
    'Forest and Paper Products': 'materials',
    'Furniture': 'discretionary',
    'General Merchandisers': 'discretionary',
    'Health Care': 'healthcare', 'Health Care: Insurance and Managed Care': 'healthcare',
    'Health Care: Medical Facilities': 'healthcare', 'Health Care: Pharmacy and Other Services': 'healthcare',
    'Home Equipment, Furnishings': 'discretionary',
    'Homebuilders': 'discretionary',
    'Hotels, Casinos, Resorts': 'discretionary',
    'Household and Personal Products': 'staples',
    'Industrial and Farm Equipment': 'industrials', 'Industrial Machinery': 'industrials',
    'Information Technology Services': 'it',
    'Insurance: Life, Health (Mutual)': 'financials', 'Insurance: Life, Health (stock)': 'financials',
    'Insurance: Life, Health (Stock)': 'financials', 'Insurance: Property and Casualty (Mutual)': 'financials',
    'Insurance: Property and Casualty (Stock)': 'financials',
    'Internet Services and Retailing': 'discretionary',
    'Mail, Package, and Freight Delivery': 'industrials',
    'Marine services': 'industrials',
    'Medical Products and Equipment': 'healthcare',
    'Metal Products': 'materials', 'Metals': 'materials',
    'Mining, Crude-Oil Production': 'energy',
    'Miscellaneous': 'industrials', 'zMiscellaneous': 'industrials',
    'Motor Vehicles & Parts': 'discretionary', 'Motor Vehicles and Parts': 'discretionary',
    'Network and Other Communications Equipment': 'it',
    'Oil and Gas Equipment, Services': 'energy',
    'Packaging, Containers': 'materials',
    'Payroll Services': 'it',
    'Petroleum Refining': 'energy',
    'Pharmaceuticals': 'healthcare',
    'Pipelines': 'energy',
    'Publishing, Printing': 'communication',
    'Railroads': 'industrials',
    'Real estate': 'realestate',
    'Rubber and Plastic Products': 'discretionary',
    'Savings Institutions': 'financials',
    'Scientific,Photographic and Control Equipment': 'industrials',
    'Securities': 'financials',
    'Semiconductors and Other Electronic Components': 'it',
    'Soaps, Cosmetics': 'staples',
    'Specialty Retailers': 'discretionary', 'Specialty Retailers: Apparel': 'discretionary',
    'Specialty Retailers: Other': 'discretionary',
    'Telecommunications': 'communication',
    'Temporary Help': 'industrials',
    'Textiles': 'discretionary',
    'Tobacco': 'staples',
    'Toys, Sporting Goods': 'discretionary',
    'Transportation and Logistics': 'industrials', 'Transportation Equipment': 'industrials',
    'Trucking': 'industrials', 'Trucking, Truck Leasing': 'industrials',
    'Utilities: Gas and Electric': 'utilities',
    'Waste Management': 'industrials',
    'Wholesalers': 'industrials', 'Wholesalers: Diversified': 'industrials',
    'Wholesalers: Electronics and Office Equipment': 'it',
    'Wholesalers: Food and Grocery': 'staples',
    'Wholesalers: Health Care': 'healthcare',
    'X Brokerage': 'financials',
}

# 같은 기업인데 아카이브 주소(slug)가 연도마다 다른 경우 → 하나의 key로 통일.
KEY_ALIAS = {
    # 에너지
    'exxon-corporation': 'exxon-mobil',
    'phillips-petroleum-company': 'conocophillips',
    'usx-corporation': 'marathon-oil',
    'amerada-hess-corporation': 'hess',
    'sun-company-inc': 'sunoco-inc',
    'tesoro-corporation': 'andeavor',
    'plains-all-american-pipeline-l-p': 'plains-gp-holdings',
    # 유틸리티
    'pacific-gas-electric-company': 'pge-corp', 'pge-corporation': 'pge-corp',
    'consolidated-edison-company-of-new-york-inc': 'consolidated-edison',
    'texas-utilities-company': 'txu-corp', 'energy-future-holdings': 'txu-corp',
    'ohio-edison-company': 'firstenergy', 'firstenergy-corp': 'firstenergy',
    'houston-industries-incorporated': 'centerpoint-energy', 'reliant-energy-incorporated': 'centerpoint-energy',
    # 통신 · 미디어
    'sbc-communications-inc': 'att',
    'bell-atlantic-corporation': 'verizon',
    'sprint-corporation': 'sprint-nextel-corporation',
    'the-directv-group-inc': 'directv',
    'news-corporation': 'twenty-first-century-fox',
    'america-online': 'time-warner',
    # 소비재 · 유통
    'morg': 'macys', 'federated-department-stores-inc': 'macys',
    'delphi-automotive-systems-corporation': 'delphi-corporation',
    'the-goodyear-tire-rubber-company': 'goodyear-tire-rubber',
    'kmart-corporation': 'sears-holdings',
    'philip-morris-companies-inc': 'altria-group',
    'conagra-foods': 'conagra-brands', 'conagra-foods-incorporated': 'conagra-brands',
    'walgreen-co': 'walgreens-boots-alliance',
    'albertsons-inc': 'albertsons-cos',
    'the-gillette-company': 'gillette', 'gillette-company': 'gillette',
    # 헬스케어
    'aetna-life-casualty-co': 'aetna', 'aetna-inc': 'aetna',
    'american-home-products-corporation': 'wyeth',
    # 금융
    'prudential-insurance-company-of-america': 'prudential-financial',
    'state-farm-group': 'state-farm-insurance-cos',
    'federal-national-mortgage-association': 'fannie-mae',
    'federal-home-loan-mortgage-corp': 'freddie-mac',
    'merrill-lynch-company-inc': 'merrill-lynch-co-inc',
    'the-travelers-group': 'citigroup',
    'chemical-banking-corporation': 'jpmorgan-chase',
    'norwest-corporation': 'wells-fargo',
    'dean-witter-discover-co': 'morgan-stanley',
    'intl-fcstone': 'stonex-group',
    # 산업재
    'united-technologies-corporation': 'raytheon-technologies',
    'alliedsignal-inc': 'honeywell-international',
    'amr-corporation': 'american-airlines-group',
    'ual-corporation': 'united-continental-holdings',
    'emerson-electric-co': 'emerson-electric',
    'minnesota-mining-and-manufacturing-company': '3m',
    # IT
    'ingram-micro-inc': 'ingram-micro',
    'motorola-inc': 'motorola-solutions',
    # 소재
    'the-dow-chemical-company': 'dow', 'dow-chemical': 'dow',
    'e-i-du-pont-de-nemours-and-company': 'dupont',
    'crown-cork-seal-company-inc': 'crown-holdings',
    'cliffs-natural-resources': 'cleveland-cliffs',
    'jefferson-smurfit-corporation': 'smurfit-stone-container-corporation',
    # 부동산
    'cb-richard-ellis-group-inc': 'cbre-group',
}

# (발표연도, slug) → key. 같은 주소가 그 해에는 다른 기업을 가리키는 경우.
KEY_AT = {
    (1996, 'att'): 'att-corp', (2001, 'att'): 'att-corp',                    # 옛 AT&T Corp. (2005년 SBC가 인수)
    (1996, 'viacom'): 'cbs', (2001, 'viacom'): 'cbs',                        # 옛 Viacom → CBS Corp. → Paramount
    (1996, 'jpmorgan-chase'): 'jp-morgan-co',                                # J.P. Morgan & Co.
    (1996, 'wells-fargo'): 'wells-fargo-co-1852',                            # 옛 Wells Fargo (1998년 Norwest가 인수)
    (1996, 'morgan-stanley'): 'morgan-stanley-group',                        # 옛 Morgan Stanley Group
    (1996, 'raytheon-technologies'): 'raytheon-company', (2001, 'raytheon-technologies'): 'raytheon-company',
    (2006, 'raytheon-technologies'): 'raytheon-company', (2011, 'raytheon-technologies'): 'raytheon-company',
    (2016, 'raytheon-technologies'): 'raytheon-company',                     # 옛 Raytheon Company
    (1996, 'honeywell-international'): 'honeywell-inc',                      # 옛 Honeywell Inc. (1999년 AlliedSignal이 인수)
    (2021, 'dow-chemical'): 'dupont', (2026, 'dow-chemical'): 'dupont',      # DowDuPont → DuPont de Nemours
    (2016, 'arconic'): 'alcoa',                                              # 2016년 분할 전 Alcoa Inc.
}

# 기업별 섹터 지정(Fortune 업종보다 우선). key 기준.
COMPANY = {}
for _s, _keys in {
    'it': ['motorola-solutions', 'intel', 'texas-instruments', 'amp-inc', 'xerox', 'applied-materials', 'corning',
           'arrow-electronics', 'merisel-inc', 'anixter-international', 'tech-data', 'avnet'],
    'communication': ['alphabet', 'facebook', 'yahoo', 'time-warner', 'netflix'],
    'staples': ['walmart', 'target', 'costco', 'pepsico', 'kimberly-clark', 'fleming-companies-inc', 'supervalu',
                'sysco', 'gillette', 'dollar-general', 'dollar-tree', 'bjs-wholesale-club'],
    'healthcare': ['cvs-health', 'mckesson', 'bergen-brunswig-corporation', 'cardinal-health',
                   'foxmeyer-health-corporation', 'bindley-western-industries', 'amerisourcebergen',
                   'baxter-international', 'danaher', 'thermo-fisher-scientific', 'agilent-technologies', 'avantor',
                   'fisher-scientific-international-inc'],
    'industrials': ['general-electric', '3m', 'illinois-tool-works', 'masco', 'tyco-international-ltd',
                    'owens-corning', 'usg', 'builders-firstsource', 'resideo-technologies', 'uber-technologies',
                    'gevernova', 'r-r-donnelley-sons', 'cendant-corporation', 'paccar', 'cummins', 'navistar-international'],
    'energy': ['occidental-petroleum', 'world-fuel-services', 'ngl-energy-partners', 'global-partners',
               'halliburton', 'oneok'],
    'utilities': ['duke-energy', 'centerpoint-energy', 'reliant-energy-inc', 'utilicorp-united-inc',
                  'avista-corp', 'northwestern-corporation', 'constellation-energy', 'american-electric-power',
                  'txu-corp', 'calpine', 'wps-resources-corporation', 'ugi', 'aes', 'nrg-energy',
                  'vistra-energy', 'mdu-resources-group'],
    'materials': ['freeport-mcmoran', 'newmont-mining', 'cleveland-cliffs', 'corteva', 'reliance-steel-aluminum'],
    'discretionary': ['eastman-kodak', 'whirlpool', 'maytag-corporation', 'harman-international-industries', 'nike',
                      'genuine-parts', 'lkq', 'mohawk-industries', 'mattel', 'newell-brands', 'fo',
                      'truserv-corporation', 'lennar', 'pultegroup', 'kb-home', 'd-r-horton',
                      'centex-corporation'],
}.items():
    for _k in _keys:
        COMPANY[_k] = _s

# (발표연도, key)별 섹터 지정 — 그 해의 주력 사업이 달랐던 경우.
COMPANY_AT = {
    (1996, 'moodys'): 'industrials',        # 당시 Dun & Bradstreet(기업정보·마케팅 서비스)
}

# 표시 이름: 당시 사명(짧게). key 기준, 필요하면 (발표연도, key). Top 10에 오른 기업은 모두 직접 지정한다.
NAME = {
    # IT
    'ibm': 'IBM', 'hp': 'Hewlett-Packard', 'motorola-solutions': 'Motorola', 'xerox': 'Xerox', 'intel': 'Intel',
    'compaq-computer-corporation': 'Compaq', 'digital-equipment-corporation': 'Digital Equipment',
    'texas-instruments': 'Texas Instruments', 'apple': 'Apple', 'unisys': 'Unisys', 'microsoft': 'Microsoft',
    'lucent-technologies-inc': 'Lucent', 'dell-technologies': 'Dell', 'ingram-micro': 'Ingram Micro',
    'tech-data': 'Tech Data', 'electronic-data-systems-corporation': 'EDS', 'cisco-systems-inc': 'Cisco',
    'oracle': 'Oracle', 'avnet': 'Avnet', 'arrow-electronics': 'Arrow Electronics', 'jabil-circuit': 'Jabil',
    'nvidia': 'Nvidia', 'broadcom': 'Broadcom', 'synnex': 'TD Synnex',
    # 커뮤니케이션
    'att-corp': 'AT&T', 'gte-corporation': 'GTE', 'bellsouth-corporation': 'BellSouth',
    'mci-communications-corporation': 'MCI', 'sprint-nextel-corporation': 'Sprint', 'verizon': 'Verizon',
    'ameritech-corporation': 'Ameritech', 'nynex-corporation': 'NYNEX', 'att': 'AT&T', 'disney': 'Walt Disney',
    'cbs': 'CBS', 'worldcom-inc': 'WorldCom', 'qwest-communications-international-inc': 'Qwest',
    'comcast': 'Comcast', 'time-warner': 'Time Warner', 'twenty-first-century-fox': 'News Corp.',
    'directv': 'DirecTV', 'alphabet': 'Alphabet', 'time-warner-cable': 'Time Warner Cable',
    'facebook': 'Facebook', 'centurylink': 'CenturyLink', 'charter-communications': 'Charter',
    'netflix': 'Netflix', 'discovery': 'Warner Bros. Disc.',
    # 경기소비재
    'general-motors': 'General Motors', 'ford-motor': 'Ford', 'chrysler-corporation': 'Chrysler',
    'sears-roebuck-and-company': 'Sears', 'sears-holdings': 'Sears Holdings', 'j-c-penney': 'J.C. Penney',
    'home-depot': 'Home Depot', 'eastman-kodak': 'Eastman Kodak', 'macys': "Macy's",
    'goodyear-tire-rubber': 'Goodyear', 'delphi-corporation': 'Delphi', 'auto-nation': 'AutoNation',
    'lowes': "Lowe's", 'johnson-controls': 'Johnson Controls', 'best-buy': 'Best Buy', 'mcdonalds': "McDonald's",
    'chrysler-group-llc': 'Chrysler Group', 'amazon-com': 'Amazon', 'tjx': 'TJX', 'nike': 'Nike',
    'tesla': 'Tesla', 'starbucks': 'Starbucks', 'lithia-motors': 'Lithia Motors',
    # 필수소비재
    'walmart': 'Walmart', 'altria-group': 'Altria', 'procter-gamble': 'P&G', 'pepsico': 'PepsiCo',
    'conagra-brands': 'ConAgra', 'kroger': 'Kroger', 'target': 'Target',
    'american-stores-company': 'American Stores', 'costco': 'Costco', 'coca-cola': 'Coca-Cola',
    'albertsons-cos': 'Albertsons', 'safeway': 'Safeway', 'walgreens-boots-alliance': 'Walgreen',
    'archer-daniels-midland': 'ADM', 'sysco': 'Sysco', 'mondelez-international': 'Mondelez',
    'publix-super-markets': 'Publix',
    # 헬스케어
    'johnson-johnson': 'Johnson & Johnson', 'hca-holdings': 'HCA', 'merck': 'Merck',
    'bristol-myers-squibb': 'Bristol-Myers', 'wyeth': 'Wyeth', 'mckesson': 'McKesson', 'pfizer': 'Pfizer',
    'abbott-laboratories': 'Abbott Labs', 'baxter-international': 'Baxter',
    'bergen-brunswig-corporation': 'Bergen Brunswig', 'cardinal-health': 'Cardinal Health', 'aetna': 'Aetna',
    'unitedhealth-group': 'UnitedHealth', 'cvs-health': 'CVS Health', 'cigna': 'Cigna',
    'amerisourcebergen': 'AmerisourceBergen', 'elevance-health': 'Anthem',
    'medco-health-solutions-inc': 'Medco Health', 'caremark-rx-inc': 'Caremark Rx',
    'express-scripts-holding': 'Express Scripts', 'humana': 'Humana', 'centene': 'Centene',
    # 금융
    'prudential-financial': 'Prudential', 'state-farm-insurance-cos': 'State Farm', 'citicorp': 'Citicorp',
    'metlife': 'MetLife', 'aig': 'AIG', 'allstate': 'Allstate', 'fannie-mae': 'Fannie Mae',
    'merrill-lynch-co-inc': 'Merrill Lynch', 'bankamerica': 'BankAmerica', 'citigroup': 'Citigroup',
    'jpmorgan-chase': 'JPMorgan Chase', 'bank-of-america-corp': 'Bank of America',
    'morgan-stanley': 'Morgan Stanley', 'tiaa': 'TIAA', 'berkshire-hathaway': 'Berkshire Hathaway',
    'goldman-sachs-group': 'Goldman Sachs', 'wells-fargo': 'Wells Fargo', 'freddie-mac': 'Freddie Mac',
    'stonex-group': 'StoneX',
    # 산업재
    'general-electric': 'General Electric', 'lockheed-martin': 'Lockheed Martin',
    'raytheon-technologies': 'United Tech.', 'ups': 'UPS', 'boeing': 'Boeing',
    'american-airlines-group': 'American Airlines', '3m': '3M', 'caterpillar': 'Caterpillar',
    'united-continental-holdings': 'United Airlines', 'honeywell-international': 'Honeywell',
    'raytheon-company': 'Raytheon', 'fedex': 'FedEx', 'northrop-grumman': 'Northrop Grumman', 'deere': 'Deere',
    'general-dynamics': 'General Dynamics', 'delta-air-lines': 'Delta Air Lines',
    # 에너지
    'exxon-mobil': 'Exxon Mobil', 'mobil-corporation': 'Mobil', 'texaco-inc': 'Texaco', 'chevron': 'Chevron',
    'amoco-corporation': 'Amoco', 'marathon-oil': 'Marathon Oil', 'atlantic-richfield-company': 'ARCO',
    'conocophillips': 'ConocoPhillips', 'ashland-global-holdings': 'Ashland',
    'occidental-petroleum': 'Occidental', 'enron': 'Enron', 'conoco-inc': 'Conoco', 'dynegy': 'Dynegy',
    'tosco-corporation': 'Tosco', 'el-paso-corporation': 'El Paso Energy', 'valero-energy': 'Valero',
    'plains-gp-holdings': 'Plains All Amer.', 'sunoco-inc': 'Sunoco', 'hess': 'Hess',
    'halliburton': 'Halliburton', 'andeavor': 'Tesoro', 'enterprise-products-partners': 'Enterprise Prod.',
    'murphy-oil': 'Murphy Oil', 'phillips': 'Phillips 66', 'marathon-petroleum': 'Marathon Petroleum',
    'energy-transfer-equity': 'Energy Transfer', 'world-fuel-services': 'World Fuel Svcs.',
    'baker-hughes': 'Baker Hughes',
    # 소재
    'dupont': 'DuPont', 'dow': 'Dow Chemical', 'international-paper': "Int'l Paper",
    'georgia-pacific-corporation': 'Georgia-Pacific', 'alcoa': 'Alcoa', 'weyerhaeuser': 'Weyerhaeuser',
    'monsanto': 'Monsanto', 'stone-container-corporation': 'Stone Container',
    'reynolds-metals-company': 'Reynolds Metals', 'ppg-industries': 'PPG',
    'smurfit-stone-container-corporation': 'Smurfit-Stone', 'boise-cascade': 'Boise Cascade',
    'lyondell-chemical-company': 'Lyondell', 'united-states-steel': 'U.S. Steel', 'huntsman': 'Huntsman',
    'nucor': 'Nucor', 'freeport-mcmoran': 'Freeport-McMoRan', 'linde': 'Praxair', 'ecolab': 'Ecolab',
    'westrock': 'WestRock', 'sherwin-williams': 'Sherwin-Williams', 'corteva': 'Corteva',
    'newmont-mining': 'Newmont', 'cleveland-cliffs': 'Cleveland-Cliffs', 'steel-dynamics': 'Steel Dynamics',
    # 유틸리티
    'pge-corp': 'PG&E', 'southern': 'Southern Co.', 'edison-international': "Edison Int'l",
    'unicom-corporation': 'Unicom', 'consolidated-edison': 'Con Edison', 'entergy': 'Entergy',
    'public-service-enterprise-group': 'PSEG', 'american-electric-power': 'AEP', 'txu-corp': 'TXU',
    'nextera-energy': 'NextEra Energy', 'duke-energy': 'Duke Energy', 'dominion-resources': 'Dominion',
    'centerpoint-energy': 'CenterPoint', 'utilicorp-united-inc': 'UtiliCorp', 'xcel-energy': 'Xcel Energy',
    'constellation-energy': 'Constellation', 'exelon': 'Exelon', 'firstenergy': 'FirstEnergy', 'aes': 'AES',
    'nrg-energy': 'NRG Energy', 'dte-energy': 'DTE Energy', 'vistra-energy': 'Vistra',
}
NAME_AT = {}
for _k, _name, _years in [
    ('hp', 'HP', (2016, 2021, 2026)),                                   # 2015년 HP Inc. · HPE 분할
    ('apple', 'Apple Computer', (1996, 2001, 2006)),
    ('dell-technologies', 'Dell Computer', (1996, 2001)),
    ('dell-technologies', 'Dell Technologies', (2021, 2026)),
    ('sprint-nextel-corporation', 'Sprint Nextel', (2006, 2011)),
    ('verizon', 'Bell Atlantic', (1996,)),
    ('att', 'SBC', (1996, 2001)),
    ('cbs', 'Viacom', (1996, 2001)),
    ('cbs', 'ViacomCBS', (2021,)),
    ('cbs', 'Paramount Skydance', (2026,)),
    ('time-warner', 'AOL Time Warner', (2001,)),
    ('twenty-first-century-fox', '21st Century Fox', (2016,)),
    ('alphabet', 'Google', (2006, 2011)),
    ('facebook', 'Meta', (2026,)),
    ('centurylink', 'Lumen', (2021, 2026)),
    ('discovery', 'Discovery', (2016, 2021)),
    ('sears-holdings', 'Kmart', (1996, 2001)),
    ('macys', 'Federated', (1996, 2001, 2006)),
    ('altria-group', 'Philip Morris', (1996, 2001)),
    ('target', 'Dayton Hudson', (1996,)),
    ('costco', 'Price/Costco', (1996,)),
    ('albertsons-cos', "Albertson's", (1996, 2001, 2006)),
    ('walgreens-boots-alliance', 'Walgreens Boots', (2016, 2021)),
    ('mondelez-international', 'Kraft Foods', (2011,)),
    ('hca-holdings', 'Columbia/HCA', (1996,)),
    ('wyeth', 'Amer. Home Prod.', (1996, 2001)),
    ('mckesson', 'McKesson HBOC', (2001,)),
    ('cvs-health', 'CVS', (2001, 2006)),
    ('cvs-health', 'CVS Caremark', (2011,)),
    ('amerisourcebergen', 'AmeriSource', (1996, 2001)),
    ('amerisourcebergen', 'Cencora', (2026,)),
    ('elevance-health', 'Anthem Insurance', (2001,)),
    ('elevance-health', 'WellPoint', (2006, 2011)),
    ('elevance-health', 'Elevance Health', (2026,)),
    ('metlife', 'Metropolitan Life', (1996,)),
    ('citigroup', 'Travelers Group', (1996,)),
    ('jpmorgan-chase', 'Chemical Banking', (1996,)),
    ('jpmorgan-chase', 'J.P. Morgan Chase', (2001,)),
    ('bank-of-america-corp', 'NationsBank', (1996,)),
    ('morgan-stanley', 'Dean Witter Discover', (1996,)),
    ('morgan-stanley', 'Morgan Stanley DW', (2001,)),
    ('wells-fargo', 'Norwest', (1996,)),
    ('tiaa', 'TIAA-CREF', (1996, 2001, 2006, 2011)),
    ('general-electric', 'GE Aerospace', (2026,)),
    ('raytheon-technologies', 'Raytheon Tech.', (2021,)),
    ('raytheon-technologies', 'RTX', (2026,)),
    ('american-airlines-group', 'AMR', (1996, 2001, 2006, 2011)),
    ('united-continental-holdings', 'UAL', (1996, 2001, 2006)),
    ('united-continental-holdings', 'United Continental', (2011, 2016)),
    ('honeywell-international', 'AlliedSignal', (1996,)),
    ('exxon-mobil', 'Exxon', (1996,)),
    ('marathon-oil', 'USX', (1996, 2001)),
    ('conocophillips', 'Phillips Petroleum', (1996, 2001)),
    ('plains-gp-holdings', 'Plains GP', (2016, 2021, 2026)),
    ('sunoco-inc', 'Sun Company', (1996,)),
    ('hess', 'Amerada Hess', (1996, 2001, 2006)),
    ('world-fuel-services', 'World Kinect', (2026,)),
    ('dow', 'Dow', (2021, 2026)),
    ('edison-international', 'SCEcorp', (1996,)),
    ('txu-corp', 'Texas Utilities', (1996,)),
    ('txu-corp', 'Energy Future', (2011, 2016)),
    ('nextera-energy', 'FPL Group', (1996, 2001, 2006)),
    ('duke-energy', 'Duke Power', (1996,)),
    ('centerpoint-energy', 'Houston Industries', (1996,)),
    ('centerpoint-energy', 'Reliant Energy', (2001,)),
    ('exelon', 'PECO Energy', (1996,)),
    ('xcel-energy', 'Northern States Power', (1996,)),
]:
    for _y in _years:
        NAME_AT[(_y, _k)] = _name


def money(s):
    return float(re.sub(r'[^0-9.\-]', '', str(s)))


def canon(k, y):
    k = KEY_AT.get((y, k), k)
    return KEY_ALIAS.get(k, k)


def slug_tail(slug):
    return [p for p in str(slug).split('/') if p][-1]


def load_year(y, gaps):
    raw = json.loads((P / 'research' / ('fortune%d_next.json' % y)).read_text(encoding='utf-8'))
    drop = {(d['listYear'], d['slug'], d['rank']) for d in gaps.get('drop', [])}
    rows = []
    for x in raw['props']['pageProps']['franchiseSearch']['items']:
        rk = int(x['rank'])
        tail = slug_tail(x['slug'])
        if rk > 500 or (y, tail, rk) in drop:
            continue
        rows.append(dict(year=y, rank=rk, source=x['name'], revenue=money(x['data']['Revenues ($M)']) / 1000,
                         industry=x['data'].get('Industry') or '', key=canon(tail, y), slug=tail,
                         origin='fortune.com'))
    for g in gaps['rows']:
        if g['listYear'] == y:
            rows.append(dict(year=y, rank=g['rank'], source=g['name'], revenue=g['revenueUsdM'] / 1000,
                             industry='', key=canon(g['key'], y), slug=g['key'], origin='gap', sector=g['sector']))
    return rows


def sector_of(r):
    k = (r['year'], r['key'])
    if k in COMPANY_AT:
        return COMPANY_AT[k]
    if r['key'] in COMPANY:
        return COMPANY[r['key']]
    if r.get('sector'):
        return r['sector']
    return INDUSTRY.get(r['industry'])


def display(r):
    return NAME_AT.get((r['year'], r['key'])) or NAME.get(r['key']) or r['source']


def build():
    gaps = json.loads((P / 'research' / 'fortune500_gap_rows.json').read_text(encoding='utf-8'))
    table, allrows = {}, {}
    for y in LIST_YEARS:
        rows = load_year(y, gaps)
        unmapped = [(r['source'], r['industry']) for r in rows if sector_of(r) not in SECTORS]
        if unmapped:
            raise SystemExit('unmapped %d: %s' % (y, unmapped))
        seen = {}
        for r in rows:
            if r['key'] in seen:
                raise SystemExit('duplicate key %d: %s (%s / %s)' % (y, r['key'], seen[r['key']], r['source']))
            seen[r['key']] = r['source']
        allrows[y] = rows
        for s in SECTORS:
            g = sorted((r for r in rows if sector_of(r) == s), key=lambda r: (-r['revenue'], r['rank']))
            table[(y, s)] = g
    return table, allrows


def dump(table, n=14):
    for s in SECTORS:
        for y in LIST_YEARS:
            g = table[(y, s)]
            print('\n## %s %d (FY%d) · %d곳' % (s, y, y - 1, len(g)))
            for i, r in enumerate(g[:n]):
                nm = display(r)
                print('%2d %3d %7.1f  %-26s %-30s %-28s %s%s' % (
                    i + 1, r['rank'], r['revenue'], nm[:26], ('' if nm == r['source'] else r['source'])[:30],
                    r['industry'][:28], r['key'], ' [gap]' if r['origin'] == 'gap' else ''))


def flow(table, allrows, n=12, only=None):
    where = {}
    for (y, s), g in table.items():
        for i, r in enumerate(g):
            where[(y, r['key'])] = (s, i + 1, r)
    for s in SECTORS:
        if only and s not in only:
            continue
        keys = []
        for y in LIST_YEARS:
            for r in table[(y, s)][:n]:
                if r['key'] not in keys:
                    keys.append(r['key'])
        print('\n## %s' % s)
        for k in keys:
            cells = []
            for y in LIST_YEARS:
                w = where.get((y, k))
                if not w:
                    cells.append('%-22s' % '·')
                elif w[0] != s:
                    cells.append('%-22s' % ('(%s %d)' % (w[0][:5], w[1])))
                else:
                    cells.append('%-22s' % ('%2d %5.1f %s' % (w[1], w[2]['revenue'], display(w[2])[:12])))
            print('%-34s|%s' % (k[:34], '|'.join(cells)))


def metrics(table, s):
    """섹터 하나의 순위 안정성 지표(모두 Top 10 기준, key = 같은 기업)."""
    keys = {y: [r['key'] for r in table[(y, s)][:TOP]] for y in LIST_YEARS}
    first, last = LIST_YEARS[0], LIST_YEARS[-1]
    lead = [keys[y][0] for y in LIST_YEARS]
    ever = []
    for y in LIST_YEARS:
        for k in keys[y]:
            if k not in ever:
                ever.append(k)
    steps = []
    for a, b in zip(LIST_YEARS, LIST_YEARS[1:]):
        both = [k for k in keys[a] if k in keys[b]]
        steps.append(dict(new=TOP - len(both), kept=len(both),
                          move=sum(abs(keys[a].index(k) - keys[b].index(k)) for k in both)))
    kept = sum(x['kept'] for x in steps)
    top3 = {y: keys[y][:3] for y in LIST_YEARS}
    return dict(
        leaderChanges=sum(1 for a, b in zip(lead, lead[1:]) if a != b),
        leaderCount=len(set(lead)),
        stay30=len([k for k in keys[first] if k in keys[last]]),
        top3Stay30=len([k for k in top3[first] if k in top3[last]]),
        everTop10=len(ever),
        newPerStep=round(sum(x['new'] for x in steps) / len(steps), 2),
        movePerStep=round(sum(x['move'] for x in steps) / kept, 2) if kept else None,
        steps=steps,
    )


def check_tables():
    for k in COMPANY:
        assert k not in KEY_ALIAS, 'COMPANY key is an alias source: ' + k
    for k in list(NAME) + [k for _, k in NAME_AT]:
        assert k not in KEY_ALIAS, 'NAME key is an alias source: ' + k


def payload(table):
    gaps = json.loads((P / 'research' / 'fortune500_gap_rows.json').read_text(encoding='utf-8'))
    missing = sorted({r['key'] for (y, s), g in table.items() if s not in EXCLUDED for r in g[:TOP]
                      if r['key'] not in NAME and (y, r['key']) not in NAME_AT})
    if missing:
        raise SystemExit('표시 이름이 없는 Top %d 기업: %s' % (TOP, missing))
    sectors = []
    for s, label in SECTORS.items():
        if s in EXCLUDED:
            continue
        snaps = {}
        for y in LIST_YEARS:
            g = table[(y, s)]
            assert len(g) >= TOP, (s, y, len(g))
            snaps[str(y - 1)] = dict(listYear=y, count=len(g), rows=[
                dict(key=r['key'], name=display(r), revenue=round(r['revenue'], 1), rankOverall=r['rank'],
                     **({'gap': True} if r['origin'] == 'gap' else {})) for r in g[:TOP]])
        m = metrics(table, s)
        m.pop('steps')
        sectors.append(dict(id=s, name=label, metrics=m, snapshots=snaps))
    return dict(
        title='미국 Fortune 500 · 섹터별 매출 Top %d' % TOP,
        unit='USD bn (Fortune 500 발표 매출)',
        years=[y - 1 for y in LIST_YEARS], listYears=LIST_YEARS, top=TOP,
        note='Fortune 500 N년판 = 직전 회계연도(N−1) 매출 순위. 화면의 연도는 매출 연도.',
        classification=[
            '당시 Fortune 업종을 경제 섹터로 묶은 분석용 분류(공식 GICS 과거 시계열 아님).',
            'Fortune 업종만으로 섹터가 갈리지 않는 기업은 현재 섹터 기준으로 직접 지정(예: Walmart·Target·Costco = 필수소비재, McKesson·CVS = 헬스케어, Alphabet·Meta = 커뮤니케이션, Amazon = 경기소비재).',
            '당시 주력 사업이 달랐던 기업은 당시 Fortune 업종을 따름(예: 1995년 Cigna = 금융, Ashland = 에너지).',
        ],
        continuity=[
            '합병은 존속 법인(인수 주체), 분할은 본업과 사명을 이어 간 쪽을 같은 기업으로 연결.',
            '표시 이름은 당시 사명(예: Dayton Hudson → Target, Philip Morris → Altria, SBC → AT&T).',
        ],
        caveats=[
            'Fortune 500은 미국 법인만 포함하며, 다른 상장사에 연결되는 자회사·비공개 기업은 빠진다(예: T-Mobile US, 2015년 Dell, 2025년 Walgreens).',
            '2006년판에는 결산을 제때 내지 못한 Fannie Mae·Freddie Mac이 없다.',
            '2000년 유틸리티 매출은 에너지 트레이딩 총액 계상으로 부풀려져 있다(Duke Energy · Reliant · UtiliCorp).',
        ],
        excluded=dict(realestate=dict(
            reason='Fortune 500 편입 기업이 적어 Top %d을 만들 수 없음' % TOP,
            counts={str(y - 1): len(table[(y, 'realestate')]) for y in LIST_YEARS})),
        gapRows=dict(source=gaps['source'], added=len(gaps['rows']), dropped=len(gaps.get('drop', [])),
                     inTop=sorted('%d %s' % (y - 1, r['source']) for (y, s), g in table.items() if s not in EXCLUDED
                                  for r in g[:TOP] if r['origin'] == 'gap')),
        sectors=sectors,
    )


def show_metrics(table):
    print('%-14s %5s %5s %6s %7s %5s %7s %7s  %s' % ('sector', '1위교체', '1위수', '잔류30', 'Top3잔류', '진입수', '신규/회', '이동/회', '1위'))
    for s in SECTORS:
        if s in EXCLUDED:
            continue
        m = metrics(table, s)
        lead = []
        for y in LIST_YEARS:
            nm = display(table[(y, s)][0])
            if not lead or lead[-1] != nm:
                lead.append(nm)
        print('%-14s %5d %5d %6d %7d %5d %7.2f %7.2f  %s   steps new=%s' % (
            s, m['leaderChanges'], m['leaderCount'], m['stay30'], m['top3Stay30'], m['everTop10'],
            m['newPerStep'], m['movePerStep'], ' → '.join(lead), [x['new'] for x in m['steps']]))


if __name__ == '__main__':
    check_tables()
    T, A = build()
    if '--dump' in sys.argv:
        dump(T)
    elif '--flow' in sys.argv:
        flow(T, A, only=[a for a in sys.argv[1:] if a in SECTORS] or None)
    elif '--metrics' in sys.argv:
        show_metrics(T)
    else:
        out = payload(T)
        (P / 'sector_us.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print('sector_us.json · %d sectors × %d years × Top %d · gap rows in Top %d: %s' % (
            len(out['sectors']), len(LIST_YEARS), TOP, TOP, out['gapRows']['inTop']))

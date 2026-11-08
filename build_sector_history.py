import pathlib,json,csv,re
P=pathlib.Path(__file__).parent
sectors={'staples':'필수소비재','discretionary':'경기소비재','energy':'에너지','utilities':'유틸리티','it':'IT','healthcare':'헬스케어','financials':'금융','industrials':'산업재','materials':'소재','communication':'커뮤니케이션','realestate':'부동산'}
# Analytical 11-sector crosswalk; this is NOT an official historic GICS series.
def classify(x):
 n=x['name'].lower(); d=x['data']; i=d.get('Industry','').lower(); s=d.get('Sector','').lower()
 if any(k in n for k in ['alphabet','google','meta platforms','facebook','tencent','netease','baidu']):return 'communication'
 if any(k in n for k in ['amazon','alibaba','jd.com','rakuten','pdd holdings']):return 'discretionary'
 if any(k in n for k in ['walmart','wal-mart','costco','target','carrefour','kroger','tesco','metro ag','ahold','seven & i','aeon','woolworth','j. sainsbury','albertson','safeway','daiei','walgreen','rite aid']):return 'staples'
 if any(k in n for k in ['cvs','cencora','mckesson','cardinal health','amerisourcebergen','medipal','suzuken','alfresa']):return 'healthcare'
 if any(k in n for k in ['glencore','bhp','rio tinto','vale s.a','china minmetals','china baowu','arcelormittal','posco','thyssen']):return 'materials'
 if any(k in n for k in ['e.on','engie','rwe','veba','suez','enel','edf','electricité','electricite','china energy investment','china huaneng','china datan','china huadian']):return 'utilities'
 if any(k in n for k in ['trafigura','vitol','gunvor','mercuria','world fuel','marubeni energy']):return 'energy'
 if any(k in n for k in ['ge aerospace','general electric','siemens','hitachi','mitsubishi electric','abb ltd','toshiba','daewoo']):return 'industrials'
 if any(k in n for k in ['sony','panasonic','matsushita','lg electronics','philips electronics']):return 'discretionary'
 if any(k in n for k in ['samsung electronics','hon hai','fujitsu','nec','lg display']):return 'it'
 if n.startswith('abb '):return 'industrials'
 if n=='vale':return 'materials'
 if 'real estate' in i:return 'realestate'
 if 'health care' in i or 'pharmaceutical' in i or 'medical products' in i:return 'healthcare'
 if any(k in i for k in ['insurance','bank','securities','financial','savings','brokerage']):return 'financials'
 if 'utilities' in i:return 'utilities'
 if any(k in i for k in ['petroleum','energy','crude-oil','pipelines','oil and gas','oil & gas']):return 'energy'
 if any(k in i for k in ['chemical','metal','forest','paper','packaging','building materials','rubber and plastic']):return 'materials'
 if any(k in i for k in ['telecommunication','entertainment','publishing','advertising']):return 'communication'
 if any(k in i for k in ['computer','semiconductor','network','information technology','electronics, electrical','wholesalers: electronics','scientific,']):return 'it'
 if any(k in i for k in ['food and drug','food & drug','food production','food consumer','beverages','tobacco','household and personal','soaps','wholesalers: food']) or i=='food':return 'staples'
 if any(k in i for k in ['motor vehicles','specialty retail','general merchandiser','internet services','apparel','food services','home equipment','furniture','homebuilders','hotels','toys','textiles','automotive retail']):return 'discretionary'
 if any(k in i for k in ['aerospace','airlines','industrial','construction','farm','mail,','railroads','shipping','trading','transport','trucking','outsourcing','temporary help','waste','equipment leasing','wholesalers','miscellaneous','education']):return 'industrials'
 return None

def extract(prefix,ys):
 snapshots=[]
 for y in ys:
  source=P/'research'/f'{prefix}{y}_next.json'
  j=json.loads(source.read_text(encoding='utf-8'))['props']['pageProps']
  a=[x for x in j['franchiseSearch']['items'] if int(x['rank'])<=500]
  missing=sorted(set(range(1,501))-{int(x['rank']) for x in a})
  groups={k:[] for k in sectors};unmapped=[]
  for x in a:
   k=classify(x)
   if not k:unmapped.append((x['name'],x['data'].get('Industry')));continue
   revenue=float(re.sub(r'[^0-9.\-]','',x['data']['Revenues ($M)']))/1000
   name=x['name']
   # Source platform sometimes links history to today's entity name; fix only obvious aliases.
   if y<=2010 and name=='GE Aerospace':name='General Electric'
   if y<=2020 and name=='Cencora':name='AmerisourceBergen'
   if y<=2010 and name=='Mercedes-Benz Group':name='Daimler-Benz' if y==1995 else 'Daimler'
   if y==2010 and name=='HP':name='Hewlett-Packard'
   if y==2000 and name=='HP':name='Hewlett-Packard'
   if y==2000 and name=='State Grid Corporation of China':name='State Power Corporation of China'
   if y==2010 and name=='Engie':name='GDF Suez'
   if y==2010 and name=='DHL Group':name='Deutsche Post'
   if y==2020 and name=='Mercedes-Benz Group':name='Daimler'
   if y<=2000 and name=='MSD':name='Merck & Co.'
   groups[k].append({'name':name,'sourceName':x['name'],'revenue':revenue,'rankOverall':int(x['rank']),'industry':x['data'].get('Industry'),'country':x['data'].get('Country / Territory','U.S.'),'url':'https://fortune.com'+x['slug']})
  out={}
  for k,g in groups.items():
   g.sort(key=lambda x:-x['revenue'])
   out[k]={'companies':[dict(x,rank=z+1) for z,x in enumerate(g[:5])],'sectorCount':len(g),'status':'observed_archive' if g else 'not_available','note':('아카이브 누락 순위가 있어 완전한 당시 모집단 순위와 다를 수 있음. ' if missing else '')+('Global500 편입기업이 5개 미만이므로 빈 순위를 채우지 않음.' if prefix=='global' and len(g)<5 else '')}
  snapshots.append({'year':y,'sourceUrl':f'https://fortune.com/ranking/{"global500" if prefix=="global" else "fortune500"}/{y}/','sourceRows':len(a),'missingOverallRanks':missing,'sectors':out})
  print(prefix,y,'rows',len(a),'unmapped',unmapped)
 return snapshots
out={'asOf':'2026-11-08','unit':'USD billion','yearMeaning':'Fortune 발표연도. 주로 전년도 회계연도 매출이며 기업별 결산월 다름.','defaultMarket':'global','sectors':[{'id':k,'label':v} for k,v in sectors.items()], 'years':[1990,1995,2000,2010,2020,2026], 'methodology':['현재 생존기업만 역추적하지 않고 각 발표연도에 실린 기업을 사용함.','회사 전체 연결매출 기준임. 반도체 매출·시가총액 순위와 다름.','Fortune 업종을 11개 경제 섹터로 분석자가 재분류함. GICS 명칭을 참고했으나 공식 GICS 과거 시계열 아님.','아카이브상 현재 사명으로 연결된 일부 회사는 알려진 당시 명칭으로 표시함. 합병 전후 사업 범위·회계기준·환율이 달라 성장률로 해석하면 안 됨.','일본 종합상사의 과거 총액 매출과 현재 순액 매출은 인식 기준 차이가 큼. 산업재 순위 하락 전체를 경쟁력 상실로 해석하지 않음.','공식 아카이브의 일부 과거 순위 누락은 보간하지 않음. 표는 확인된 기업 중 매출 상위5임.','1990년 비교 가능한 글로벌 11개 섹터 자료는 확보하지 못했음. 1995년부터 확인 가능한 스냅샷 제공.'],'markets':{}}
for prefix,label,ys in [('global','글로벌 · Fortune Global500',[1995,2000,2010,2020,2026]),('fortune','미국 · Fortune500',[2000,2010,2020,2026])]:
 sn=extract(prefix,ys)
 sn.insert(0,{'year':1990,'sourceUrl':'https://fortune.com/ranking/global500/1995/','sourceRows':0,'missingOverallRanks':[],'sectors':{k:{'companies':[],'sectorCount':0,'status':'not_available','note':'1990년 동일 기준 자료 미확보. 0 또는 순위 없음이라는 뜻이 아님.'} for k in sectors}})
 out['markets']['global' if prefix=='global' else 'us']={'label':label,'snapshots':sn}
(P/'sector_history.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'research/sector_crosswalk.json').write_text(json.dumps({'note':'Function classify in build_sector_history.py defines analytic sector mapping.','sectors':sectors},ensure_ascii=False,indent=2),encoding='utf-8')
print('WROTE sector_history.json')

const fs=require('fs'),path=require('path'),assert=require('assert');
const {JSDOM,VirtualConsole}=require(path.join(process.env.TEMP,'codex-html-qa/node_modules/jsdom'));
let errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const page=fs.readFileSync(path.join(__dirname,'기업재무_발표자료_12조_v3.html'),'utf8');
const dom=new JSDOM(page,{runScripts:'dangerously',url:'http://localhost/',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'))}}});
const w=dom.window,d=w.document,ev=s=>w.eval(s);
let count=ev('SLIDES.length'),checks=0;
for(let i=0;i<count;i++){
 ev(`goto(${i})`);assert(d.querySelector('.slide'));assert(!d.querySelector('#stage').textContent.match(/NaN|undefined|\?\?\?\?/),`invalid content ${i}`);
 assert(!d.querySelector('.slide .foot button'),`slide ${i}: the per-slide source link was removed`);
 ev(`SLIDES[${i}].sources.forEach(id=>{if(!SOURCES[id])throw new Error('missing source '+id)})`);checks++;
}
const click=e=>e.dispatchEvent(new w.MouseEvent('click',{bubbles:true,cancelable:true}));
// 장표 구성: v3는 26장. 합치거나 뺀 장표의 id는 남아 있지 않다 (v3에서 ② 금리 · ③ 정치·규제의 세 장을 us-china 한 장으로 합침)
assert.equal(count,26);const ids=ev('SLIDES.map(s=>s.id)');for(const gone of ['era0-capital','buyer-checklist','rates-china','life-cycle','circular-flow','circular-compare','rates-2026','politics','china-race'])assert(!ids.includes(gone),gone+' should be gone');
// PART 3 은 이슈 세 개: 간지의 목록 · 번호가 붙은 장표 제목(①②③) · 마무리 표의 열이 모두 셋
ev("goto(SLIDES.findIndex(s=>s.id==='part3'))");assert.equal(d.querySelectorAll('.issues span').length,3);assert(!d.querySelector('.issues').textContent.match(/순환|④/));
assert.deepEqual(ev("SLIDES.filter(s=>/^[①-⑨]/.test(s.title)).map(s=>s.title[0]+s.id)"),['①buyer-cash','②us-china','③cash-allocation']);
ev("goto(SLIDES.findIndex(s=>s.id==='closing'))");assert.equal(d.querySelectorAll('.closing .hd').length,3);assert(!d.querySelector('.closing').textContent.includes('거래 구조'));
assert(ev("SLIDES.find(s=>s.id==='linear-context').take").includes('좋은 회사도 사라질 수 있다'));checks+=4;
// 참고 장표: 5 · 7쪽의 제목이 (참고)로 시작하고 목차에서도 표시된다. 다른 장표에는 붙지 않는다
assert.deepEqual(ev('SLIDES.map((s,i)=>s.ref?i+1:0).filter(Boolean)'),[5,7]);
for(const [n,id] of [[5,'linear-deal'],[7,'sector-ranking']]){ev(`goto(${n-1})`);assert.equal(d.querySelector('.slide').dataset.id,id);assert(d.querySelector('.shead h1').textContent.startsWith('(참고) '));assert(d.querySelector('.slide').classList.contains('ref'))}
assert.equal(ev("SLIDES.filter(s=>!s.ref&&String(s.title).includes('참고')).length"),0);
d.querySelector('#toc').click();assert.deepEqual([...d.querySelectorAll('.toc-grid button.ref')].map(b=>b.textContent.slice(0,6)),['05(참고)','07(참고)']);d.querySelector('#modal').close();checks+=2;
// 발표 흐름에 맞춘 틀: 표지의 핵심 메시지 · PART 2 간지와 정리 장표의 두 축 · ③ 장표의 리니어 되짚기
ev('goto(0)');assert(d.querySelector('.cover .lede').textContent.includes('산업과 거시 환경의 변화'));
ev("goto(SLIDES.findIndex(s=>s.id==='part2'))");assert.deepEqual([...d.querySelectorAll('.axrow b')].map(b=>b.textContent),['수요의 이동','거시 환경 · 자본력']);
ev("goto(SLIDES.findIndex(s=>s.id==='industry-lessons'))");assert.deepEqual([...d.querySelectorAll('.axes .axis b')].map(b=>b.textContent),['수요의 이동','거시 환경 · 자본력']);assert.equal(d.querySelectorAll('.lessons .panel').length,4);
ev("goto(SLIDES.findIndex(s=>s.id==='cash-allocation'))");assert(d.querySelector('.recall').textContent.includes('$0.21 → $1.24'));assert.equal(d.querySelectorAll('.alloc .panel').length,2);checks+=4;
// 대시보드: 10개사(빅테크 4사 + 추가 6사). 기업을 바꿔도 지표 타일 8개가 같은 분기 축(2023Q1–2026Q3, 15개 분기)에 그려진다.
// 타일 묶음: 위 4개(테두리 없음) · CAPEX/FCF(key) · 이자보상배율/부채비율(debt). 공시되지 않은 분기는 비고, 큰 숫자는 회사의 최근 공시 분기 값
ev("goto(SLIDES.findIndex(s=>s.id==='buyer-dashboard'))");
const companies=ev('Object.keys(FIN.dash)');assert.deepEqual(companies,['Microsoft','Alphabet','Amazon','Meta','Oracle','Apple','Tesla','CoreWeave','Nebius','SpaceX']);
assert.deepEqual([...d.querySelectorAll('#companySelect option')].map(o=>o.textContent),companies);assert.equal(d.querySelectorAll('.dash-legend span').length,3);
for(const c of companies){let e=d.querySelector('#companySelect');e.value=c;e.dispatchEvent(new w.Event('change'));assert.equal(d.querySelectorAll('#dashboard .tile').length,8);assert(!d.querySelector('#dashboard').innerHTML.match(/NaN|undefined|Infinity/));
 assert.deepEqual([...d.querySelectorAll('#dashboard .tile')].map(t=>t.classList.contains('key')?'key':t.classList.contains('debt')?'debt':''),['','','','','key','key','debt','debt']);
 assert.deepEqual([...d.querySelectorAll('#dashboard .tile.debt .tile-h span')].map(s=>s.textContent),['이자보상배율','부채비율']);
 const rows=ev(`FIN.dash[${JSON.stringify(c)}].quarters`),q=rows.map(x=>x.q);assert.equal(q.length,15);assert.equal(q[0],'2023Q1');assert.equal(q[14],'2026Q3');assert(d.querySelector('#dashNote').textContent.includes('역년 분기 2023Q1–2026Q3'));
 const keys=['revenue','revenueGrowth','netIncome','operatingMargin','capex','fcf','interestCoverage','debtRatio'],has=k=>rows.some(x=>Number.isFinite(x[k]));
 assert.equal(d.querySelectorAll('#dashboard .tile-c svg').length,keys.filter(has).length);assert.equal(d.querySelectorAll('#dashboard .tile-none').length,keys.filter(k=>!has(k)).length);
 const latest=rows.filter(x=>Number.isFinite(x.revenue)).pop();assert(latest,c+' has no reported quarter');assert(d.querySelector('#dashboard .tile-v em').textContent.startsWith(latest.q.slice(2)));
 [...d.querySelectorAll('#dashboard .tile-v')].forEach((t,i)=>assert.equal(t.textContent.startsWith('N/A'),!Number.isFinite(latest[keys[i]]),c+' '+keys[i]));checks++}
// 기존 4사는 15개 분기가 모두 있고(Meta 이자보상배율 2개 분기 제외), ① 투자 경쟁 장표의 연간 FCF 차트는 4사만 쓴다
assert.deepEqual(ev('Object.keys(FIN.companies)'),companies.slice(0,4));for(const c of companies.slice(0,4))assert.equal(ev(`FIN.dash[${JSON.stringify(c)}].quarters.filter(x=>Number.isFinite(x.revenue)&&Number.isFinite(x.capex)&&Number.isFinite(x.debtRatio)).length`),15);
// 섹터 순위(미국 Fortune 500 · 매출 연도 1995–2025, 5년 간격 7개 시점): 10개 섹터 버튼, 섹터마다 Top 10 × 7 = 70칸, 자동 순환
ev("goto(SLIDES.findIndex(s=>s.id==='sector-ranking'))");
const pills=[...d.querySelectorAll('#sectorPills [data-sector]')],years=ev('SECTOR.years.length');assert.equal(pills.length,10);assert.equal(years,7);assert.deepEqual(ev('SECTOR.years'),[1995,2000,2005,2010,2015,2020,2025]);
assert.equal(d.querySelector('#sectorPills .active span').textContent,'IT');
for(const p of pills){p.click();assert(p.classList.contains('active'));assert.equal(d.querySelectorAll('#bump svg').length,1);assert.equal(d.querySelectorAll('#bump g.cell').length,10*years);assert(d.querySelector('#sectorChain').textContent.length>0);assert(!(d.querySelector('#bump').innerHTML+d.querySelector('#sectorStat').innerHTML).match(/NaN|undefined/));checks+=years}
d.querySelector('#sectorPlay').click();assert(ev('!!playTimer'));d.querySelector('#sectorPlay').click();assert(ev('!playTimer'));
// 합친 장표: 사진 띠 + 군사비 차트 / 거시환경(원인) → 1990 순위(결과) + 덧붙임 / ② 미·중 (1980s 미·일과 같은 틀 두 줄 + 다른 점 · 같은 점)
ev("goto(SLIDES.findIndex(s=>s.id==='era0-invention'))");assert.equal(d.querySelectorAll('.strip .frame img').length,7);assert(d.querySelector('[data-chart="milex"] svg'));
ev("goto(SLIDES.findIndex(s=>s.id==='era1-leaders'))");assert.equal(d.querySelectorAll('.mside').length,2);assert.equal(d.querySelectorAll('.hb.c10 .hb-row').length,10);assert.equal(d.querySelectorAll('.segbar i').length,3);assert(d.querySelector('.band.aside').textContent.includes('삼성'));
ev("goto(SLIDES.findIndex(s=>s.id==='us-china'))");assert.deepEqual([...d.querySelectorAll('.replay .rrow')].map(r=>r.className.replace('rrow ','')+':'+r.querySelector('.yr').textContent),['past:1980s','now:2020s']);
assert.deepEqual([...d.querySelectorAll('.rside-h em')].map(e=>e.textContent),['미국','일본','미국','중국']);assert.deepEqual([...d.querySelectorAll('.rgap b')].map(e=>e.textContent),['12.9%p','2.5%p']);
assert.equal(d.querySelectorAll('.replay .panel').length,2);assert(d.querySelector('.replay').textContent.includes('31/35건'));assert(d.querySelector('.replay').textContent.includes('39점'));assert(!ev('"ratesNow" in CHARTS'));
d.querySelector('#sources').click();assert.equal(d.querySelectorAll('#modalBody table').length,3);assert(d.querySelector('#modalBody').textContent.includes('AsianBondsOnline'));d.querySelector('#modal').close();checks+=3;
// 시간축 지도: 시대 팝업과 레이어 끄기
ev("goto(SLIDES.findIndex(s=>s.id==='industry-map'))");assert.equal(d.querySelectorAll('[data-era]').length,ev('ERAS.length'));click(d.querySelector('[data-era]'));assert(d.querySelector('#modal').open);d.querySelector('#modal').close();
let layers=d.querySelectorAll('[data-layer]');assert.equal(layers.length,4);assert.equal(d.querySelectorAll('#timeline .lane.off').length,0);layers[0].checked=false;layers[0].dispatchEvent(new w.Event('change'));assert(d.querySelectorAll('#timeline .lane.off').length>0);
// Linear 매출 성장률 보기: 0% 눈금이 있어야 역성장을 읽을 수 있다
ev("goto(SLIDES.findIndex(s=>s.id==='linear-cash'))");d.querySelector('.pills [data-linear="linearGrowth"]').click();assert([...d.querySelectorAll('#linearChart svg text')].some(t=>t.textContent==='0%'),'growth chart needs a 0% tick');
// 펜: 켜고, 한 획 긋고, 장표를 넘기면 지워진다 (저장하지 않음)
const pe=(t,x,y)=>d.querySelector('#ink').dispatchEvent(new w.MouseEvent(t,{bubbles:true,cancelable:true,clientX:x,clientY:y,button:0}));
d.querySelector('#pen').click();assert(d.body.classList.contains('drawing'));pe('pointerdown',10,10);pe('pointermove',60,40);pe('pointerup',60,40);assert.equal(d.querySelectorAll('#ink path').length,1);
d.querySelector('#next').click();assert.equal(d.querySelectorAll('#ink path').length,0,'ink must be cleared on slide change');d.querySelector('#pen').click();assert(!d.body.classList.contains('drawing'));checks++;
ev('goto(0)');d.querySelector('#next').click();assert.equal(ev('index'),1);d.querySelector('#toc').click();assert.equal(d.querySelectorAll('.toc-grid button').length,count);d.querySelector('#modal').close();
ev("goto(SLIDES.findIndex(s=>s.id==='era4-ai'))");d.querySelector('#sources').click();assert(d.querySelector('#modal').open);assert(d.querySelectorAll('#modalBody .source a').length>0);assert(d.querySelectorAll('#modalBody table').length>0);d.querySelector('#modal').close();
w.dispatchEvent(new w.Event('beforeprint'));assert.equal(d.querySelectorAll('.slide').length,count);assert(!d.querySelector('#stage').textContent.includes('NaN'));w.dispatchEvent(new w.Event('afterprint'));assert.equal(d.querySelectorAll('.slide').length,1);
assert.equal(errors.length,0,errors.join('\n'));
const result={slides:count,checks,sectorCombinations:pills.length*years,companies:companies.length,consoleErrors:errors,visualLayout:'not checked by this script: jsdom has no layout engine. See README for the browser screenshot review.'};
fs.writeFileSync(path.join(__dirname,'qa_v3_results.json'),JSON.stringify(result,null,2));console.log(result);w.close();
const studyHtml=fs.readFileSync(path.join(__dirname,'기업재무_반도체산업.html'),'utf8');
const sv=new VirtualConsole(),se=[];sv.on('jsdomError',e=>se.push(e.message));
const sd=new JSDOM(studyHtml,{runScripts:'dangerously',url:'http://localhost/study.html',virtualConsole:sv,beforeParse(w){w.IntersectionObserver=class{observe(){} unobserve(){} disconnect(){}};w.print=()=>{};}});
const sw=sd.window,ss=sw.document;assert.equal(ss.querySelectorAll('.section').length,39);assert.equal(ss.querySelectorAll('.term').length,67);
for(const term of ['HBM','리니어','없는검색어zzzz']){const q=ss.querySelector('#search');q.value=term;q.dispatchEvent(new sw.Event('input'));const visible=[...ss.querySelectorAll('.section')].filter(s=>!s.hidden);if(term==='없는검색어zzzz')assert.equal(visible.length,0);else assert(visible.length>0)}
ss.querySelector('#clearSearch').click();assert.equal([...ss.querySelectorAll('.section')].filter(s=>!s.hidden).length,39);ss.querySelector('#fontSize').click();assert.equal(ss.querySelector('#fontSize').getAttribute('aria-pressed'),'true');ss.querySelector('#menu').click();assert.equal(ss.querySelector('#menu').getAttribute('aria-expanded'),'true');assert.equal(se.length,0,se.join('\n'));for(const a of ss.querySelectorAll('a[href^="#"]'))assert(ss.getElementById(a.getAttribute('href').slice(1)),'broken anchor '+a.href);sw.close();
console.log('Study passed:39 sections,67 terms, search, font size, mobile menu, internal anchors.');
const qa=JSON.parse(fs.readFileSync(path.join(__dirname,'qa_v3_results.json'),'utf8'));qa.study={sections:39,terms:67,search:true,fontSize:true,mobileMenu:true,anchors:true};fs.writeFileSync(path.join(__dirname,'qa_v3_results.json'),JSON.stringify(qa,null,2));

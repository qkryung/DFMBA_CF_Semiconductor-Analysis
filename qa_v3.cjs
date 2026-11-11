const fs=require('fs'),path=require('path'),assert=require('assert');
const {JSDOM,VirtualConsole}=require(path.join(process.env.TEMP,'codex-html-qa/node_modules/jsdom'));
let errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const page=fs.readFileSync(path.join(__dirname,'기업재무_발표자료_12조_v5.html'),'utf8');
const dom=new JSDOM(page,{runScripts:'dangerously',url:'http://localhost/',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'))}}});
const w=dom.window,d=w.document,ev=s=>w.eval(s);
let count=ev('SLIDES.length'),checks=0;
for(let i=0;i<count;i++){
 ev(`goto(${i})`);assert(d.querySelector('.slide'));assert(!d.querySelector('#stage').textContent.match(/NaN|undefined|\?\?\?\?/),`invalid content ${i}`);
 assert(!d.querySelector('.slide .foot button'),`slide ${i}: the per-slide source link was removed`);
 ev(`SLIDES[${i}].sources.forEach(id=>{if(!SOURCES[id])throw new Error('missing source '+id)})`);checks++;
}
const click=e=>e.dispatchEvent(new w.MouseEvent('click',{bubbles:true,cancelable:true}));
// 장표 구성: v5는 25장 (v4의 28장에서 era2-finance 를 빼고, 제3기의 두 장과 ③ 현금 배분 · 장기계약 두 장을 각각 한 장으로 합침). 합치거나 뺀 장표의 id는 남아 있지 않다
assert.equal(count,25);const ids=ev('SLIDES.map(s=>s.id)');for(const gone of ['era0-capital','buyer-checklist','rates-china','life-cycle','circular-flow','circular-compare','rates-2026','politics','china-race','era2-finance','era3-maturity','contracts'])assert(!ids.includes(gone),gone+' should be gone');
// PART 2 의 순서(v5): 간지 → 시간축 → 태동기 → 제1기 → 제2기(분업) → 제3기(탈락과 인수) → 그 결과인 밸류체인 × 제품군 지도 · M&A 재편 → 제4기 → 정리
assert.deepEqual(ev('SLIDES.filter(s=>s.part===2).map(s=>s.id)'),['part2','industry-map','era0-invention','era1-rates','era1-leaders','era2-split','era3-consolidation','semicon-valuechain','semicon-mna-history','era4-ai','industry-lessons']);
assert.deepEqual(['industry-map','era2-split','era3-consolidation','semicon-valuechain','semicon-mna-history','era4-ai'].map(k=>ids.indexOf(k)+1),[9,13,14,15,16,17]);
assert.deepEqual(ev('SLIDES.filter(s=>s.part===3).map(s=>s.id)'),['part3','market-2026','buyer-cash','buyer-dashboard','us-china','cash-allocation','closing']);checks+=3;
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
// 발표 흐름에 맞춘 틀: 표지의 핵심 메시지(v5: 성패를 단정하지 않는 문장) · PART 2 간지와 정리 장표의 두 축 · ③ 장표의 리니어 되짚기
ev('goto(0)');assert(d.querySelector('.cover .lede').textContent.includes('산업과 거시 환경에 대한 이해'));assert(!d.querySelector('.cover').textContent.includes('성패'));
// v5: 간지의 부제는 v3 의 짧은 문장, 두 축은 v4 그대로(‘수요의 이동과 밸류체인 분업화’ · ‘자본력과 M&A 재편’). 정리 장표도 같은 두 축을 쓴다
ev("goto(SLIDES.findIndex(s=>s.id==='part2'))");assert.deepEqual([...d.querySelectorAll('.axrow b')].map(b=>b.textContent),['수요의 이동과 밸류체인 분업화','자본력과 M&A 재편']);
assert.deepEqual([...d.querySelectorAll('.axrow span')].map(b=>b.textContent),['IDM vs Fabless–Foundry','아날로그 · 팹리스 대형화 → AI 전용 칩 시대로의 진화']);assert.equal(d.querySelector('.dv-desc').textContent,'기술 스펙이 아니라 두 개의 축으로 읽는다.');assert.equal(d.querySelector('.dv-desc strong').textContent,'두 개의 축');
// 정리 장표(v5): 02 카드는 ‘사이클’ — 세계 반도체 매출의 전년 대비 증감률 막대 39개(1987–2025), 가장 큰 호황 · 불황에 이름표
ev("goto(SLIDES.findIndex(s=>s.id==='industry-lessons'))");assert.deepEqual([...d.querySelectorAll('.axes .axis b')].map(b=>b.textContent),['수요의 이동과 밸류체인 분업화','자본력과 M&A 재편']);assert.equal(d.querySelectorAll('.lessons .panel').length,4);
assert.deepEqual([...d.querySelectorAll('.lessons .lhead .kicker')].map(k=>k.textContent),['수요','사이클','자본','정책']);assert.equal(d.querySelectorAll('.lessons .lviz svg rect').length,39);assert.equal(d.querySelectorAll('.lessons .lviz svg rect[data-tip]').length,39);
assert.deepEqual([...d.querySelectorAll('.lessons .lviz svg text')].map(t=>t.textContent).filter(t=>/%/.test(t)),['1995 +42%','2001 −32%']);assert(!d.querySelector('.formula'));assert(d.querySelector('.lessons').textContent.includes('채찍효과'));
// ③ 현금 배분(v5): 장기계약 장표를 합쳐 세 칸 — 쌓이는 현금(차트) · 배분의 선택(리니어 띠 + 두 회사) · 먼저 확인할 것(LTA 14개 고객 · 50% 이상 · 남는 위험 둘)
ev("goto(SLIDES.findIndex(s=>s.id==='cash-allocation'))");assert(d.querySelector('.recall').textContent.includes('$0.21 → $1.24'));assert.equal(d.querySelectorAll('.alloc .panel').length,2);
assert.deepEqual([...d.querySelectorAll('.cash3 .colh b')].map(b=>b.textContent),['분기 영업이익','투자인가, 환원인가','계약의 질']);assert(d.querySelector('[data-chart="supplierOP"] svg'));
assert.deepEqual([...d.querySelectorAll('.panel.lta .hero')].map(h=>h.textContent),['14개 고객','50% 이상']);assert.equal(d.querySelectorAll('.custs i').length,14);assert.equal(d.querySelectorAll('.lrest div').length,2);
// 4쪽(v5): 네 회사의 주력 제품군
ev("goto(SLIDES.findIndex(s=>s.id==='linear-peers'))");assert.deepEqual([...d.querySelectorAll('.choice-row .prod em')].map(e=>e.textContent),['주력','주력','주력','주력']);
assert.deepEqual([...d.querySelectorAll('.choice-row .prod')].map(p=>p.textContent.replace('주력','').split('매출')[0].trim()),['전원 관리 IC','혼합신호 · 전력 관리 IC','아날로그 · 임베디드 프로세서','데이터 컨버터 · 증폭기 · RF']);checks+=7;
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
// v5: 섹터마다 ‘함께 볼 기업’(1–3곳)을 1위 기업과 다른 색으로 칠하고, 순위 이동(처음 → 2025년)을 아래에 적는다. 왼쪽 아래에는 30년 뒤에도 Top 10에 남은 곳의 수
for(const p of pills){p.click();assert(p.classList.contains('active'));assert.equal(d.querySelectorAll('#bump svg').length,1);assert.equal(d.querySelectorAll('#bump g.cell').length,10*years);assert(d.querySelector('#sectorChain').textContent.length>0);assert(!(d.querySelector('#bump').innerHTML+d.querySelector('#sectorStat').innerHTML).match(/NaN|undefined/));
 const fo=ev('SECTOR.sectors[sector].focus');assert(fo.length>=1&&fo.length<=3);assert.equal(d.querySelectorAll('.bump-legend.focus span').length,fo.length);
 const tones=new Set();for(const k of fo){const cells=[...d.querySelectorAll('#bump g.cell.tone')].filter(g=>g.dataset.k===k);assert(cells.length>=1,'focus '+k);tones.add(cells[0].querySelector('rect').getAttribute('stroke'))}
 assert.equal(tones.size,fo.length);assert(!tones.has('#3987e5')&&!tones.has('#d95926'),'focus colours differ from the leader colours');assert(/^\d+ \/ 10곳$/.test(d.querySelector('#sectorKeep b').textContent));checks+=years}
pills.find(p=>p.querySelector('span').textContent==='IT').click();assert.deepEqual([...d.querySelectorAll('.bump-legend.focus span')].map(s=>s.textContent),['HP2위 → 10위','Microsoft’00 9위 → 2위','Motorola3위 → 권외']);assert.equal(d.querySelector('#sectorKeep b').textContent,'3 / 10곳');checks++;
d.querySelector('#sectorPlay').click();assert(ev('!!playTimer'));d.querySelector('#sectorPlay').click();assert(ev('!playTimer'));
// 합친 장표: 사진 띠 + 군사비 차트 / 거시환경(원인) → 1990 순위(결과) + 덧붙임 / ② 미·중 (1980s 미·일과 같은 틀 두 줄 + 다른 점 · 같은 점)
ev("goto(SLIDES.findIndex(s=>s.id==='era0-invention'))");assert.equal(d.querySelectorAll('.strip .frame img').length,7);assert(d.querySelector('[data-chart="milex"] svg'));
ev("goto(SLIDES.findIndex(s=>s.id==='era1-leaders'))");assert.equal(d.querySelectorAll('.mside').length,2);assert.equal(d.querySelectorAll('.hb.c10 .hb-row').length,10);assert.equal(d.querySelectorAll('.segbar i').length,3);assert(d.querySelector('.band.aside').textContent.includes('삼성'));
// 제2기(v5): 분업이 깊어진 이유 세 장(큰 숫자 하나씩) → 이전과 이후의 구조 · 팹리스의 몫. 위험의 이동을 다룬 장표는 없다
ev("goto(SLIDES.findIndex(s=>s.id==='era2-split'))");assert.deepEqual([...d.querySelectorAll('.panel.why .whyn b')].map(b=>b.textContent),['~$20bn','1987','−32%']);
assert.deepEqual([...d.querySelectorAll('.vsplit.duo .chain .lk b')].map(b=>b.textContent),['팹리스','파운드리','OSAT']);assert.deepEqual([...d.querySelectorAll('.fbars b')].map(b=>b.textContent),['13%','32.8%']);assert(d.querySelector('.fshare .fx').textContent.includes('2.5배'));assert(!ev('"dotcom" in CHARTS'));
// 제3기(v5): 두 장을 한 장으로 — 흐름 다섯 단계 · 개념도(자산의 시간과 부채의 시간) · 탈락 둘과 생존 셋
ev("goto(SLIDES.findIndex(s=>s.id==='era3-consolidation'))");assert.equal(d.querySelectorAll('.steps .step').length,5);assert(d.querySelector('.steps').textContent.includes('약 −75%'));assert(d.querySelector('.fitsvg svg'));
assert.deepEqual([...d.querySelectorAll('.choice.tight .choice-row')].map(r=>r.querySelector('.nm').childNodes[1].textContent+(r.classList.contains('gone')?'✕':'')),['Qimonda✕','Elpida✕','Samsung','SK hynix','Micron']);assert(d.querySelector('.take').textContent.includes('만기를 버틴'));assert(!ev('"wsts0619" in CHARTS'));
// ② 미·중(v5): 지금의 두 나라(금리 · 정치 · 자금 = 여섯 칸) → 1980년대 미·일과 닮은 점 · 다른 점 → 결론 둘
ev("goto(SLIDES.findIndex(s=>s.id==='us-china'))");assert.deepEqual([...d.querySelectorAll('.uc-c')].map(e=>e.textContent),['미국','중국']);assert.deepEqual([...d.querySelectorAll('.uc-k')].map(e=>e.textContent),['금리','정치','자금']);
assert.deepEqual([...d.querySelectorAll('.uc-v b')].map(e=>e.textContent),['고금리','저금리','정치 노이즈 심화','정치 일원화','민간 주도','정부 주도']);assert.deepEqual([...d.querySelectorAll('.uc-v strong')].map(e=>e.textContent),['3.88%','1.40%']);
assert.deepEqual([...d.querySelectorAll('.uc-tag')].map(e=>e.textContent),['닮은 점','다른 점']);assert.deepEqual([...d.querySelectorAll('.uc-diff b')].map(e=>e.textContent),['12.9%p → 2.5%p','$954bn vs $336bn']);
assert.deepEqual([...d.querySelectorAll('.uc-end b')].map(e=>e.textContent),['AI 패권이 넘어가기 어렵다','격차는 좁혀질 수 있다']);assert(d.querySelector('.uc').textContent.includes('31/35건'));assert(d.querySelector('.uc').textContent.includes('39점'));assert(!d.querySelector('.replay'));assert(!ev('"ratesNow" in CHARTS'));
d.querySelector('#sources').click();assert.equal(d.querySelectorAll('#modalBody table').length,4);assert(d.querySelector('#modalBody').textContent.includes('AsianBondsOnline'));assert(d.querySelector('#modalBody').textContent.includes('SIPRI'));d.querySelector('#modal').close();checks+=5;
// 밸류체인 × 제품군 지도(v4 신규 · v5 에서 제3기 뒤로): 가로축은 단계 머리글 넷의 화살표 띠, 세로축은 제품군마다 다른 색. 분업 사슬 세 조각, IDM 띠 셋(Intel · 메모리 · 아날로그), 병목 표시 셋, ‘제품 특성 → 구조’ 넷
ev("goto(SLIDES.findIndex(s=>s.id==='semicon-valuechain'))");assert.deepEqual([...d.querySelectorAll('.vmap .hband .h')].map(h=>h.textContent),['IP · EDA','설계','웨이퍼 제조','패키징 · 테스트']);assert.equal(d.querySelector('.vmap .hw').textContent,'제품 특성 → 구조');
assert.deepEqual([...d.querySelectorAll('.vmap .axk b')].map(b=>b.textContent),['밸류체인 →','제품군 ↓']);const rc=e=>(e.getAttribute('style').match(/--rc:([^;]+)/)||[])[1];
assert.equal(new Set([...d.querySelectorAll('.vmap .rl')].map(rc)).size,4,'each product family has its own colour');assert.deepEqual([...d.querySelectorAll('.vmap .why')].map(rc),[...d.querySelectorAll('.vmap .rl')].map(rc));assert(d.querySelector('.shead .sub').textContent.includes('분업(제2기)과 재편(제3기)'));
assert.deepEqual([...d.querySelectorAll('.vmap .chain .lk b')].map(b=>b.textContent),['팹리스','파운드리','OSAT']);assert.deepEqual([...d.querySelectorAll('.vmap .rl b')].map(b=>b.textContent),['로직 · AI','메모리','아날로그 · 전력','장비 · 소재']);
assert.deepEqual([...d.querySelectorAll('.vmap .one b')].map(b=>b.textContent),['Intel','삼성전자 · SK hynix · Micron','TI · ADI · Infineon']);assert.equal(d.querySelectorAll('.vmap .inh .tags span').length,6);
assert.deepEqual([...d.querySelectorAll('.vmap .choke')].map(c=>c.textContent.slice(0,2)+'|'+(c.textContent.match(/선단 공정|HBM|EUV/)||[''])[0]),['병목|선단 공정','병목|HBM','병목|EUV']);
assert.equal(d.querySelectorAll('.vmap .why').length,4);assert(d.querySelector('.vmap .ip').textContent.includes('Synopsys'));assert(d.querySelector('.take').textContent.includes('Fabless–Foundry'));assert(d.querySelectorAll('.vmap [data-tip]').length>=6);
d.querySelector('#sources').click();assert.equal(d.querySelectorAll('#modalBody table').length,2);assert(d.querySelector('#modalBody').textContent.includes('ASML'));d.querySelector('#modal').close();checks+=3;
// M&A 재편(v4 신규 · v5 에서 제3기 뒤로): 네 갈래(줄마다 계보 그림 하나 · 선 둘), 거래마다 툴팁, 무산 둘, 범례 셋. 제목의 & 는 화면 · 목차 · 출처 창 어디서도 &amp; 로 보이지 않는다
ev("goto(SLIDES.findIndex(s=>s.id==='semicon-mna-history'))");assert.deepEqual([...d.querySelectorAll('.mrow-h b')].map(b=>b.textContent),['아날로그 대형화','팹리스 통합','풀스택 로직 결합','파운드리 전문화']);
assert.equal(d.querySelectorAll('.mrow svg').length,4);assert.equal(d.querySelectorAll('.mrow-out b').length,4);assert.equal(d.querySelectorAll('.mrow svg polygon').length,8);assert.equal(d.querySelectorAll('.mna-ax .legend span').length,3);
const tips=[...d.querySelectorAll('.mrow svg [data-tip]')].map(e=>e.dataset.tip);assert.equal(tips.length,17);assert.equal(tips.filter(t=>t.includes('무산')).length,2);
for(const k of ['Linear Technology','Maxim','National Semiconductor','Avago + Broadcom','NXP','Xilinx','Mellanox','IBM 반도체 제조사업','Intel Foundry'])assert(tips.some(t=>t.includes(k)),'missing deal '+k);
assert.equal(d.querySelector('.shead h1').textContent,'거대 M&A가 만든 반도체 제국: 밸류체인과 제품군의 재편');assert(!d.querySelector('#stage').textContent.includes('&amp;'));assert(d.querySelector('.mna-ax').textContent.includes('약 8배'));assert(d.querySelector('.mna-ax').textContent.includes('2020 $118bn'));assert.equal(d.querySelectorAll('.mna-ax svg rect').length,2);assert.equal(d.querySelectorAll('.mrow svg rect[opacity=".05"]').length,8);
d.querySelector('#toc').click();assert([...d.querySelectorAll('.toc-grid button')].some(b=>b.textContent==='16거대 M&A가 만든 반도체 제국: 밸류체인과 제품군의 재편'));assert(!d.querySelector('#modalBody').textContent.includes('&amp;'));d.querySelector('#modal').close();
d.querySelector('#sources').click();assert.equal(d.querySelector('#modalTitle').textContent,'근거 · 거대 M&A가 만든 반도체 제국: 밸류체인과 제품군의 재편');assert.equal(d.querySelectorAll('#modalBody table tr').length,18);assert(!d.querySelector('#modalBody').textContent.includes('&amp;'));d.querySelector('#modal').close();checks+=4;
// 시간축 지도: 시대 팝업과 레이어 끄기. v4: 시대 축 위의 대형 M&A 마름모 여섯 개(툴팁) — ‘기업 · 산업 구조 · M&A’ 레이어와 함께 꺼진다
ev("goto(SLIDES.findIndex(s=>s.id==='industry-map'))");assert.equal(d.querySelectorAll('[data-era]').length,ev('ERAS.length'));click(d.querySelector('[data-era]'));assert(d.querySelector('#modal').open);d.querySelector('#modal').close();
let layers=d.querySelectorAll('[data-layer]');assert.equal(layers.length,4);assert.equal(d.querySelectorAll('#timeline .lane.off').length,0);
assert.deepEqual(ev('TL.mna.map(m=>m.y)'),[2011,2015,2016,2017,2021,2022]);assert.equal(d.querySelectorAll('#timeline g.deal').length,6);assert(d.querySelector('#timeline g.deal').dataset.tip.startsWith('2011 · TI–National|'));
assert(layers[0].parentNode.textContent.includes('M&A'));assert.equal(d.querySelectorAll('#timeline text[data-tip]').length,ev('TL.events.length'));assert.equal(ev('TL.events.length'),16);
layers[0].checked=false;layers[0].dispatchEvent(new w.Event('change'));assert(d.querySelectorAll('#timeline .lane.off').length>0);assert(d.querySelector('#timeline g.deal').parentNode.classList.contains('off'));
click(d.querySelectorAll('[data-era]')[3]);assert(d.querySelector('#modalBody').textContent.includes('Avago–Broadcom'));d.querySelector('#modal').close();checks+=2;
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

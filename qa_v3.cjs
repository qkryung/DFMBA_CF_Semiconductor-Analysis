const fs=require('fs'),path=require('path'),assert=require('assert');
const {JSDOM,VirtualConsole}=require(path.join(process.env.TEMP,'codex-html-qa/node_modules/jsdom'));
let errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const page=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const dom=new JSDOM(page,{runScripts:'dangerously',url:'http://localhost/',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'))}}});
const w=dom.window,d=w.document,ev=s=>w.eval(s);
let count=ev('SLIDES.length'),checks=0;
for(let i=0;i<count;i++){
 ev(`goto(${i})`);assert(d.querySelector('.slide'));assert(!d.querySelector('#stage').textContent.match(/NaN|undefined|\?\?\?\?/),`invalid content ${i}`);
 ev(`SLIDES[${i}].sources.forEach(id=>{if(!SOURCES[id])throw new Error('missing source '+id)})`);checks++;
}
const click=e=>e.dispatchEvent(new w.MouseEvent('click',{bubbles:true,cancelable:true}));
// 빅테크 대시보드: 기업을 바꿔도 지표 타일 8개가 모두 그려진다
ev("goto(SLIDES.findIndex(s=>s.id==='buyer-dashboard'))");
const companies=ev('Object.keys(FIN.companies)');
for(const c of companies){let e=d.querySelector('#companySelect');e.value=c;e.dispatchEvent(new w.Event('change'));assert.equal(d.querySelectorAll('#dashboard .tile').length,8);assert.equal(d.querySelectorAll('#dashboard .tile-c svg').length,8);assert(!d.querySelector('#dashboard').innerHTML.match(/NaN|undefined/));checks++}
// 섹터 순위(미국 Fortune 500 · 2000/2010/2020/2026): 11개 섹터 버튼과 자동 순환
ev("goto(SLIDES.findIndex(s=>s.id==='sector-ranking'))");
const pills=[...d.querySelectorAll('#sectorPills [data-sector]')],years=ev('SECTOR.years.length');assert.equal(pills.length,11);assert.equal(years,4);
for(const p of pills){p.click();assert(p.classList.contains('active'));assert.equal(d.querySelectorAll('#bump svg').length,1);assert(!(d.querySelector('#bump').innerHTML+d.querySelector('#sectorStat').innerHTML).match(/NaN|undefined/));checks+=years}
d.querySelector('#sectorPlay').click();assert(ev('!!playTimer'));d.querySelector('#sectorPlay').click();assert(ev('!playTimer'));
// 시간축 지도: 시대 팝업과 레이어 끄기
ev("goto(SLIDES.findIndex(s=>s.id==='industry-map'))");assert.equal(d.querySelectorAll('[data-era]').length,ev('ERAS.length'));click(d.querySelector('[data-era]'));assert(d.querySelector('#modal').open);d.querySelector('#modal').close();
let layers=d.querySelectorAll('[data-layer]');assert.equal(layers.length,4);assert.equal(d.querySelectorAll('#timeline .lane.off').length,0);layers[0].checked=false;layers[0].dispatchEvent(new w.Event('change'));assert(d.querySelectorAll('#timeline .lane.off').length>0);
ev("goto(SLIDES.findIndex(s=>s.id==='life-cycle'))");d.querySelector('#lifeToggle').click();assert.equal(d.querySelector('#lifeToggle').getAttribute('aria-pressed'),'false');
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

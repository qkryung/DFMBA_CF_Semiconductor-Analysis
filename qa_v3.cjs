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
ev("goto(SLIDES.findIndex(s=>s.id==='buyer-dashboard'))");
for(const c of ev('Object.keys(FIN.companies)')){let e=d.querySelector('#companySelect');e.value=c;e.dispatchEvent(new w.Event('change'));assert.equal(d.querySelectorAll('#dashboard svg').length,4);assert(!d.querySelector('#dashboard').innerHTML.includes('NaN'));d.querySelector('#dashTable').click();assert(d.querySelector('#modal').open);d.querySelector('#modal').close();checks++}
ev("goto(SLIDES.findIndex(s=>s.id==='sector-ranking'))");
for(let i=0;i<11;i++){let s=d.querySelector('#sectorSelect');s.value=i;s.dispatchEvent(new w.Event('change'));for(let y=0;y<6;y++){d.querySelector(`[data-year="${y}"]`).click();assert(!d.querySelector('#rankRows').innerHTML.includes('NaN'));checks++}}
d.querySelector('#sectorMethod').click();assert(d.querySelector('#modalBody').textContent.includes('Fortune'));d.querySelector('#modal').close();
ev("goto(SLIDES.findIndex(s=>s.id==='industry-map'))");assert.equal(d.querySelectorAll('[data-detail]').length,20);d.querySelector('[data-detail]').click();assert(d.querySelector('#modal').open);d.querySelector('#modal').close();let layer=d.querySelector('[data-layer]');layer.checked=false;layer.dispatchEvent(new w.Event('change'));assert.equal(d.querySelectorAll('[data-detail]').length,15);
ev("goto(SLIDES.findIndex(s=>s.id==='life-cycle'))");d.querySelector('#lifeToggle').click();assert.equal(d.querySelector('#lifeToggle').getAttribute('aria-pressed'),'false');
ev('goto(0)');d.querySelector('#next').click();assert.equal(ev('index'),1);d.querySelector('#toc').click();assert.equal(d.querySelectorAll('.toc-grid button').length,count);d.querySelector('#modal').close();
w.dispatchEvent(new w.Event('beforeprint'));assert.equal(d.querySelectorAll('.slide').length,count);assert(!d.querySelector('#stage').textContent.includes('NaN'));w.dispatchEvent(new w.Event('afterprint'));assert.equal(d.querySelectorAll('.slide').length,1);
assert.equal(errors.length,0,errors.join('\n'));
const result={slides:count,checks,sectorCombinations:66,companies:4,consoleErrors:errors,visualLayout:'not verified: Windows browser URL safety check stopped Computer Use'};
fs.writeFileSync(path.join(__dirname,'qa_v3_results.json'),JSON.stringify(result,null,2));console.log(result);w.close();
const studyHtml=fs.readFileSync(path.join(__dirname,'기업재무_반도체산업.html'),'utf8');
const sv=new VirtualConsole(),se=[];sv.on('jsdomError',e=>se.push(e.message));
const sd=new JSDOM(studyHtml,{runScripts:'dangerously',url:'http://localhost/study.html',virtualConsole:sv,beforeParse(w){w.IntersectionObserver=class{observe(){} unobserve(){} disconnect(){}};w.print=()=>{};}});
const sw=sd.window,ss=sw.document;assert.equal(ss.querySelectorAll('.section').length,39);assert.equal(ss.querySelectorAll('.term').length,67);
for(const term of ['HBM','리니어','없는검색어zzzz']){const q=ss.querySelector('#search');q.value=term;q.dispatchEvent(new sw.Event('input'));const visible=[...ss.querySelectorAll('.section')].filter(s=>!s.hidden);if(term==='없는검색어zzzz')assert.equal(visible.length,0);else assert(visible.length>0)}
ss.querySelector('#clearSearch').click();assert.equal([...ss.querySelectorAll('.section')].filter(s=>!s.hidden).length,39);ss.querySelector('#fontSize').click();assert.equal(ss.querySelector('#fontSize').getAttribute('aria-pressed'),'true');ss.querySelector('#menu').click();assert.equal(ss.querySelector('#menu').getAttribute('aria-expanded'),'true');assert.equal(se.length,0,se.join('\n'));for(const a of ss.querySelectorAll('a[href^="#"]'))assert(ss.getElementById(a.getAttribute('href').slice(1)),'broken anchor '+a.href);sw.close();
console.log('Study passed:39 sections,67 terms, search, font size, mobile menu, internal anchors.');
const qa=JSON.parse(fs.readFileSync(path.join(__dirname,'qa_v3_results.json'),'utf8'));qa.study={sections:39,terms:67,search:true,fontSize:true,mobileMenu:true,anchors:true};fs.writeFileSync(path.join(__dirname,'qa_v3_results.json'),JSON.stringify(qa,null,2));

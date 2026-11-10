'use strict';
/* 기업재무 12조 발표 덱 런타임.
   build_v3.py가 SLIDES / CHARTS / SOURCES / PARTS / ERAS / FIN / SECTOR / TL 상수를 이 스크립트 앞에 주입한다. */

/* ───────── 공통 도구 ───────── */
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>Array.from(r.querySelectorAll(s));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const mn=s=>String(s).replace(/-/g,'−');
/* 제목에서 태그(<br> · 참고 표시의 <span>)를 걷어낸 한 줄 글자 */
const plain=s=>String(s??'').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim();
/* d = 최대 소수 자릿수, m = 최소 소수 자릿수(같은 값을 주면 자릿수가 고정된다) */
function num(n,d=1,m=0){return n==null||!Number.isFinite(+n)?'N/A':mn(Number(n).toLocaleString('en-US',{minimumFractionDigits:Math.min(m,d),maximumFractionDigits:d}))}
/* 차트 색: dataviz 검증 팔레트(어두운 바탕 #081421 기준 통과). 글자는 항상 잉크 토큰, 색은 마크에만 쓴다. */
const K={s:['#3987e5','#d95926','#199e70','#c98500','#d55181','#008300','#9085e9','#e66767'],pos:'#3987e5',neg:'#e66767',mute:'#566b7e',grid:'#142536',axis:'#33495d',zero:'#9db4c6',ink:'#edf7ff',ink2:'#a8bbcb',ink3:'#7f97aa',surf:'#07121f'};
let index=0,company='Microsoft',sector=null,playTimer=null,clockTimer=null,elapsed=0,lastFocus=null,linearView='linear';
let PSEQ=0,PLOTS={},slidePlots=[];
const tw=(t,fs)=>[...String(t)].reduce((a,c)=>a+(c.charCodeAt(0)>0x2e7f?1:c===' '?.3:/[.,:;·'|il1()]/.test(c)?.32:/[A-Z%$MW−+]/.test(c)?.7:.57),0)*fs;

/* ───────── 차트 엔진 ───────── */
function niceStep(span,n){const raw=span/Math.max(1,n),p=10**Math.floor(Math.log10(raw)),f=raw/p;return(f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*p}
function barPath(x0,x1,yb,yv){const h=Math.abs(yv-yb),r=Math.min(4,h,(x1-x0)/2),d=yv<yb?1:-1;return `M${x0},${yb}V${yv+d*r}Q${x0},${yv} ${x0+r},${yv}H${x1-r}Q${x1},${yv} ${x1},${yv+d*r}V${yb}Z`}
function legendHTML(c,S){
  if(c.legend===false)return '';
  const items=c.legendItems||(S.length>1?S.map(s=>({c:s.dim?K.mute:s.color,t:s.name,bar:s.type==='bar'})):[]);
  if(!items.length)return '';
  return `<div class="legend">${items.map(i=>`<span><i class="${i.bar?'sq':'ln'}" style="background:${i.c}"></i>${esc(i.t)}</span>`).join('')}</div>`}
function plot(spec,W,H){
  const id='p'+(++PSEQ),fs=spec.fs||12,n=spec.labels.length,yo=spec.y||{},xo=spec.x||{};
  const S=spec.series.map((s,j)=>Object.assign({type:spec.type||'line',color:K.s[j%8]},s));
  const lg=legendHTML(spec,S);if(lg)H-=26;
  /* 통화 기호가 붙는 음수는 '$−46.9'가 아니라 '−$46.9'로 쓴다 */
  const signed=(p,v,d,m=d)=>{const neg=p&&v<0;return (neg?'−':'')+p+num(neg?-v:v,d,m)};
  const fv=(s,v)=>signed(s.pre??spec.pre??'',v,s.dec??spec.dec??1)+(s.suf??spec.suf??'');
  const all=S.flatMap(s=>s.values).filter(Number.isFinite).concat((spec.refs||[]).map(r=>r.v));
  const hasBar=S.some(s=>s.type==='bar');
  let lo=Math.min(...all),hi=Math.max(...all);
  if(!yo.fit||hasBar){lo=Math.min(0,lo);hi=Math.max(0,hi)}
  if(lo===hi)hi=lo+1;
  const span0=hi-lo;
  if(yo.max==null)hi+=span0*(yo.head??.1);
  if(yo.min==null&&(lo<0||yo.fit))lo-=span0*(yo.foot??.08);
  if(yo.min!=null)lo=yo.min;if(yo.max!=null)hi=yo.max;
  const st=yo.step||niceStep(hi-lo,yo.n||4);
  const d0=yo.min!=null?yo.min:(lo<0||yo.fit?Math.floor(lo/st+1e-9)*st:0),d1=hi;
  const tk=[];for(let v=Math.ceil(d0/st-1e-9)*st;v<=d1+st*1e-9;v+=st)tk.push(Math.abs(v)<st*1e-9?0:+v.toPrecision(12));
  const dec=yo.dec??(st>=1?(Number.isInteger(st)?0:1):Math.ceil(-Math.log10(st)-1e-9));
  const tf=v=>signed(yo.pre||'',v,dec,yo.dec!=null?dec:0)+(yo.suf||'');
  const lastPt=s=>{for(let i=s.values.length-1;i>=0;i--)if(Number.isFinite(s.values[i]))return i;return -1};
  const ends=S.filter(s=>s.end&&lastPt(s)>=0),endTxt=s=>s.end===true?`${s.name} ${fv(s,s.values[lastPt(s)])}`:String(s.end);
  const P=spec.pad||{};
  const L=P.l??Math.ceil(Math.max(...tk.map(v=>tw(tf(v),fs)))+12);
  const R=P.r??(ends.length?Math.ceil(Math.max(...ends.map(s=>tw(endTxt(s),fs+1)))+30):14);
  const topLab=(spec.marks||[]).some(m=>m.label)||(spec.bands||[]).some(b=>b.label);
  const T=P.t??((spec.cap?24:10)+(topLab?16:0));
  const B=P.b??(xo.hide?8:26);
  const pw=W-L-R,ph=H-T-B,bw=pw/n,x=i=>L+(i+.5)*bw,y=v=>T+(d1-v)/(d1-d0)*ph;
  const yb=y(Math.max(d0,Math.min(d1,0)));
  let g='';
  if(spec.cap)g+=`<text x="0" y="13" fill="${K.ink2}" font-size="${fs+1}" font-weight="700">${esc(spec.cap)}</text>`;
  (spec.bands||[]).forEach(b=>{const xa=x(b.a)-bw/2,xb=x(b.b)+bw/2;g+=`<rect x="${xa}" y="${T}" width="${xb-xa}" height="${ph}" fill="${b.color||'#ffffff'}" opacity="${b.op??.05}"/>`;if(b.label)g+=`<text x="${(xa+xb)/2}" y="${T-6}" text-anchor="middle" fill="${K.ink2}" font-size="${fs}">${esc(b.label)}</text>`});
  tk.forEach(v=>{const yy=y(v),z=v===0&&d0<0;if(!z)g+=`<line x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}" stroke="${v===d0?K.axis:K.grid}"/>`;if(!yo.hide)g+=`<text x="${L-8}" y="${yy+4}" text-anchor="end" fill="${z?K.ink:K.ink3}" font-size="${fs}" ${z?'font-weight="700"':''} class="tn">${esc(tf(v))}</text>`});
  if(d0>0||!tk.includes(d0))g+=`<line x1="${L}" x2="${W-R}" y1="${T+ph}" y2="${T+ph}" stroke="${K.axis}"/>`;
  if(!xo.hide){const show=xo.ticks?new Set(xo.ticks):null,every=xo.every||(n<=16?1:Math.ceil(n/8));
    spec.labels.forEach((l,i)=>{if(show?show.has(i):(i%every===0||i===n-1&&every===1))g+=`<text x="${x(i)}" y="${H-7}" text-anchor="middle" fill="${K.ink3}" font-size="${fs}" class="tn">${esc(xo.map?xo.map[i]??l:l)}</text>`})}
  (spec.refs||[]).forEach(r=>{const yy=y(r.v);g+=`<line x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}" stroke="${r.color||'#6f8aa0'}" stroke-width="1.25"/>`;if(r.label)g+=`<text x="${r.left?L+6:W-R-6}" y="${yy-6}" text-anchor="${r.left?'start':'end'}" fill="${K.ink2}" font-size="${fs}">${esc(r.label)}</text>`});
  /* 막대 */
  const bars=S.filter(s=>s.type==='bar'),nb=bars.length,bwid=nb?Math.max(2,Math.min(spec.barW||24,(bw*.74-(nb-1)*2)/nb)):0,gw=nb*bwid+(nb-1)*2;
  const colorAt=(s,i)=>s.div?(s.values[i]>=0?K.pos:K.neg):s.colors?.[i]||(s.hi&&!s.hi.includes(i)?K.mute:(s.dim?K.mute:s.color));
  let lab='';
  const ptLabel=(s,i,X,Y,up)=>{const t=s.ptText?.[i]??fv(s,s.values[i]);lab+=`<text x="${X}" y="${up?Y-7:Y+fs+5}" text-anchor="${s.ptAnchor?.[i]||'middle'}" fill="${K.ink}" font-size="${fs+1}" font-weight="700" class="halo">${esc(t)}</text>`};
  const wants=(s,i)=>s.pts==='all'||Array.isArray(s.pts)&&s.pts.includes(i);
  bars.forEach((s,k)=>s.values.forEach((v,i)=>{if(!Number.isFinite(v))return;const x0=x(i)-gw/2+k*(bwid+2),yv=y(v);g+=`<path d="${barPath(x0,x0+bwid,yb,yv)}" fill="${colorAt(s,i)}"/>`;if(wants(s,i))ptLabel(s,i,x0+bwid/2,yv,v>=0)}));
  if(d0<0&&d1>0)g+=`<line x1="${L}" x2="${W-R}" y1="${yb}" y2="${yb}" stroke="${K.zero}" stroke-width="1.5"/>`;
  /* 선 · 영역 · 계단 */
  const endDots=[];
  S.filter(s=>s.type!=='bar').forEach(s=>{const col=s.dim?K.mute:s.color;let d='',seg=[],segs=[];
    s.values.forEach((v,i)=>{if(!Number.isFinite(v)){if(seg.length)segs.push(seg);seg=[];return}seg.push([x(i),y(v),i])});if(seg.length)segs.push(seg);
    /* 앞뒤가 비어 혼자 남은 값은 선이 그려지지 않으므로 점으로 찍는다 */
    const solo=new Set(segs.filter(q=>q.length===1).map(q=>q[0][2]));
    segs.forEach(q=>{q.forEach((p,k)=>{d+=k===0?`M${p[0].toFixed(1)},${p[1].toFixed(1)}`:s.type==='step'?`H${p[0].toFixed(1)}V${p[1].toFixed(1)}`:`L${p[0].toFixed(1)},${p[1].toFixed(1)}`});
      if(s.area){let a=`M${q[0][0].toFixed(1)},${yb}`;q.forEach((p,k)=>{a+=s.type==='step'&&k?`H${p[0].toFixed(1)}V${p[1].toFixed(1)}`:`L${p[0].toFixed(1)},${p[1].toFixed(1)}`});g+=`<path d="${a}L${q[q.length-1][0].toFixed(1)},${yb}Z" fill="${col}" opacity=".12"/>`}});
    g+=`<path d="${d}" fill="none" stroke="${col}" stroke-width="${s.w||2}" stroke-linejoin="round" stroke-linecap="round"${s.dash?' stroke-dasharray="6 5"':''}/>`;
    const mk=s.markers??(n<=(spec.markerMax||24));
    s.values.forEach((v,i)=>{if(!Number.isFinite(v))return;const X=x(i),Y=y(v),want=wants(s,i);if(mk||want||solo.has(i))g+=`<circle cx="${X}" cy="${Y}" r="${want?4.5:3.5}" fill="${col}" stroke="${K.surf}" stroke-width="2"/>`;if(want)ptLabel(s,i,X,Y,!(s.ptBelow||[]).includes(i))});
    const li=lastPt(s);if(s.end&&li>=0)endDots.push({s,X:x(li),Y:y(s.values[li]),col})});
  (spec.marks||[]).forEach(m=>{const X=x(m.i);g+=`<line x1="${X}" x2="${X}" y1="${T}" y2="${T+ph}" stroke="${m.color||K.ink3}" stroke-width="1.25"/>`;if(m.label)lab+=`<text x="${X+(m.anchor==='end'?-6:m.anchor==='middle'?0:6)}" y="${m.y!=null?T+m.y:T-6}" text-anchor="${m.anchor||'start'}" fill="${K.ink}" font-size="${fs}" font-weight="700" class="halo">${esc(m.label)}</text>`});
  (spec.notes||[]).forEach(o=>{const X=x(o.i)+(o.dx||0),Y=y(o.v)+(o.dy||0);lab+=`<text x="${X}" y="${Y}" text-anchor="${o.anchor||'start'}" fill="${o.strong?K.ink:K.ink2}" font-size="${o.fs||fs}" ${o.strong?'font-weight="700"':''} class="halo">${esc(o.text)}</text>`});
  /* 끝점 직접 라벨: 겹치면 아래로 밀고 연결선을 붙인다 */
  const E=endDots.map(e=>({...e,ly:e.Y})).sort((a,b)=>a.ly-b.ly);
  for(let k=1;k<E.length;k++)if(E[k].ly-E[k-1].ly<fs+6)E[k].ly=E[k-1].ly+fs+6;
  const over=E.length?E[E.length-1].ly-(T+ph):0;if(over>0)for(let k=E.length-1;k>=0;k--){E[k].ly-=over;if(k&&E[k].ly-E[k-1].ly>=fs+6)break}
  E.forEach(e=>{g+=`<circle cx="${e.X}" cy="${e.Y}" r="4.5" fill="${e.col}" stroke="${K.surf}" stroke-width="2"/>`;const lx=e.X+12;if(Math.abs(e.ly-e.Y)>3)g+=`<path d="M${e.X+5},${e.Y}L${lx-2},${e.ly}" stroke="${K.axis}" fill="none"/>`;lab+=`<circle cx="${lx+3}" cy="${e.ly}" r="3.5" fill="${e.col}"/><text x="${lx+11}" y="${e.ly+4.5}" fill="${K.ink}" font-size="${fs+1}" font-weight="${e.s.w>2?700:500}">${esc(endTxt(e.s))}</text>`});
  g+=lab+`<line class="xh" x1="0" x2="0" y1="${T}" y2="${T+ph}" stroke="${K.ink2}" stroke-width="1" opacity="0"/>`;
  PLOTS[id]={S,n,L,R,T,B,W,H,bw,fv,colorAt,labels:spec.tipLabels||spec.labels,title:spec.title};
  return `<div class="plot" data-plot="${id}">${lg}<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(spec.title||'')}">${g}</svg></div>`}
function drawInto(el,c){if(!c||!el)return;const W=el.clientWidth||+el.dataset.w||640,H=+el.dataset.h||el.clientHeight||300;
  if(c.panels){el.innerHTML=c.panels.map(p=>plot(p,W,Math.round(H*p.share))).join('');c.panels.forEach(p=>slidePlots.push(p))}
  else{el.innerHTML=plot(c,W,H);slidePlots.push(c)}}
function mountCharts(root=document){$$('[data-chart]',root).forEach(el=>drawInto(el,CHARTS[el.dataset.chart]))}

/* ───────── 툴팁 ───────── */
function tipAt(e,html){const t=$('#tip'),st=$('#stage').getBoundingClientRect(),k=st.width/1440;t.innerHTML=html;t.hidden=false;
  let X=(e.clientX-st.left)/k+16,Y=(e.clientY-st.top)/k+16;const w=t.offsetWidth,h=t.offsetHeight,HH=st.height/k;
  if(X+w>1432)X=X-w-32;if(Y+h>HH-8)Y=Y-h-32;t.style.left=Math.max(4,X)+'px';t.style.top=Math.max(4,Y)+'px'}
function tipOff(){const t=$('#tip');if(t&&!t.hidden)t.hidden=true;$$('.xh').forEach(x=>x.style.opacity=0)}
document.addEventListener('pointermove',e=>{
  if(ink.on||!e.target.closest)return;
  const p=e.target.closest('.plot');
  if(p){const g=PLOTS[p.dataset.plot],svg=$('svg',p),r=svg.getBoundingClientRect(),px=(e.clientX-r.left)/r.width*g.W,py=(e.clientY-r.top)/r.height*g.H;
    if(g&&px>=g.L&&px<=g.W-g.R&&py>=g.T-8&&py<=g.H-g.B+8){const i=Math.max(0,Math.min(g.n-1,Math.floor((px-g.L)/g.bw))),cx=g.L+(i+.5)*g.bw;
      $$('.xh').forEach(x=>x.style.opacity=0);const xh=$('.xh',svg);xh.setAttribute('x1',cx);xh.setAttribute('x2',cx);xh.style.opacity=.55;
      const rows=g.S.map(s=>Number.isFinite(s.values[i])?`<div><i style="background:${g.colorAt(s,i)}"></i><span>${esc(s.name)}</span><em>${esc(g.fv(s,s.values[i]))}</em></div>`:'').join('');
      if(rows){tipAt(e,`<b>${esc(g.labels[i])}</b>${rows}`);return}}}
  const d=e.target.closest('[data-tip]');
  if(d){tipAt(e,d.dataset.tip.split('|').map((x,k)=>k?`<div><span>${esc(x)}</span></div>`:`<b>${esc(x)}</b>`).join(''));return}
  tipOff()});
document.addEventListener('pointerleave',tipOff);

/* ───────── 장표 렌더 · 이동 ───────── */
function view(s,i){const bare=s.kind==='cover'||s.kind==='divider';
  return `<section class="slide ${s.kind||''}${s.ref?' ref':''}" aria-label="${i+1}. ${esc(plain(s.title))}" data-id="${s.id}" data-part="${s.part}">`
    +(bare?'':`<header class="shead"><div class="eyebrow">${esc(s.part===0?'12조 · 기업재무':'PART '+s.part+' · '+PARTS[s.part])}</div><h1>${s.title}</h1>${s.sub?`<p class="sub">${s.sub}</p>`:''}</header>`)
    +`<div class="body">${s.html}</div>`
    +(s.take?`<div class="take"><p>${s.take}</p></div>`:'')
    +(s.kind==='cover'?'':`<div class="foot"><span class="tn">12조 · ${String(i+1).padStart(2,'0')} / ${SLIDES.length}</span></div>`)
    +'</section>'}
function stopPlay(){clearInterval(playTimer);playTimer=null;const b=$('#sectorPlay');if(b)b.textContent='▶ 산업 순환'}
function render(){stopPlay();tipOff();inkClear();PLOTS={};slidePlots=[];
  $('#slideHost').innerHTML=view(SLIDES[index],index);
  $('#position').textContent=`${index+1} / ${SLIDES.length}`;$('#progress').style.width=(index+1)/SLIDES.length*100+'%';
  $('#prev').disabled=index===0;$('#next').disabled=index===SLIDES.length-1;
  $$('button[data-part]').forEach(b=>b.classList.toggle('active',+b.dataset.part===SLIDES[index].part));
  try{history.replaceState(null,'','#'+SLIDES[index].id)}catch(_){}
  mountCharts();mountSpecial();scale()}
function goto(i){if(i<0||Number.isNaN(i))return;index=Math.max(0,Math.min(SLIDES.length-1,i));render()}
function scale(){const b=$('.viewport');$('#stage').style.transform=`scale(${Math.min(b.clientWidth/1440,b.clientHeight/810)})`}

/* ───────── 모달 · 출처 · 차트 데이터 표 ───────── */
function modal(title,html){lastFocus=document.activeElement;$('#modalTitle').textContent=title;$('#modalBody').innerHTML=html;if(!$('#modal').open)$('#modal').showModal();$('#close').focus()}
function dataTables(i){if(i!==index)return '';
  const fromPlots=slidePlots.map(c=>({title:c.title||c.cap||'',head:[''].concat(c.series.map(s=>s.name+((s.suf??c.suf)?' ('+String(s.suf??c.suf).trim()+')':''))),rows:(c.tipLabels||c.labels).map((l,k)=>[l].concat(c.series.map(s=>Number.isFinite(s.values[k])?num(s.values[k],s.dec??c.dec??2,s.dec??c.dec??2):'')))}));
  const all=fromPlots.concat(SLIDES[i].tables||[]);if(!all.length)return '';
  return `<h3 class="dt-h">차트 데이터</h3>`+all.map(t=>`<details class="dt"><summary>${esc(t.title||'표')}</summary><div class="dt-wrap"><table class="table mini"><tr>${t.head.map(h=>`<th>${esc(h)}</th>`).join('')}</tr>${t.rows.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</table></div></details>`).join('')}
function sources(i=index){const s=SLIDES[i];
  modal('근거 · '+plain(s.title),(s.sources||[]).map(id=>{const x=SOURCES[id];return x?`<div class="source"><a href="${esc(x.url||'#')}" target="_blank" rel="noopener">${esc(x.title)} ↗</a><p>${esc(x.publisher||'')} ${esc(x.published||'')}<br>${esc(x.note||'')}</p></div>`:''}).join('')
    +`<p class="method">${s.method||'금액 단위·실제치와 전망은 해당 차트에 표시. 조사 기준 2026-11-08.'}</p>`+dataTables(i))}
function toc(){modal('전체 흐름',[0,1,2,3].map(p=>{const list=SLIDES.map((s,i)=>[s,i]).filter(([s])=>s.part===p);return list.length?`<div class="toc-part"><h3>${p?'PART '+p+' · ':''}${esc(PARTS[p])}</h3><div class="toc-grid">${list.map(([s,i])=>`<button data-jump="${i}" class="${i===index?'active':''}${s.ref?' ref':''}"><span>${String(i+1).padStart(2,'0')}</span>${esc(plain(s.title))}</button>`).join('')}</div></div>`:''}).join(''))}

/* ───────── 장표별 인터랙션 ───────── */
function mountSpecial(){
  if($('#timeline'))timeline();
  if($('#bump'))mountSectors();
  if($('#companySelect')){$('#companySelect').value=company;$('#companySelect').onchange=e=>{company=e.target.value;dashboard()};dashboard()}
  if($('#financialOverview'))financialOverview();
  if($('#linearChart'))setLinear(linearView)}
function setLinear(k){linearView=k;$$('[data-linear]').forEach(b=>b.classList.toggle('active',b.dataset.linear===k));const el=$('#linearChart');slidePlots=[];drawInto(el,CHARTS[k])}

/* 시간축 인포그래픽: 가운데 시대 축을 두고 위에는 산업 안쪽(기업·수요·매출), 아래에는 바깥 환경(사건·금리·거시·구조)을 겹쳐 놓는다 */
function timeline(){
  const el=$('#timeline'),W=el.clientWidth||1328,H=+el.dataset.h||500,G=66,x0=G,x1=W-8,Y0=TL.start,Y1=TL.end,X=v=>x0+(Math.max(Y0,Math.min(Y1,v))-Y0)/(Y1-Y0)*(x1-x0);
  const off=new Set($$('[data-layer]').filter(c=>!c.checked).map(c=>c.dataset.layer)),ln=k=>`class="lane${off.has(k)?' off':''}"`;
  const yLead=15,hTop=28,hBase=114,rTop=124,rBase=194,aTop=202,aH=36,aB=aTop+aH,yYear=262,eY=[282,300,318,336],fTop=352,fBase=404,rowH=18,mY=[414,436],sY=[460,482];
  const gut=(t,y,strong)=>`<text x="0" y="${y}" fill="${strong?K.ink:K.ink3}" font-size="${strong?12.5:11}"${strong?' font-weight="800"':''} letter-spacing=".5">${t}</text>`;
  let s='';
  /* 시대 경계선: 모든 층을 가로질러 위·아래를 같은 시대로 묶는다 */
  TL.eras.slice(1).forEach(e=>{s+=`<line x1="${X(e.a)}" x2="${X(e.a)}" y1="${yLead+8}" y2="${H-4}" stroke="#1c3246"/>`});
  /* 기업 */
  s+=`<g ${ln('leaders')}>${gut('주도 기업',yLead)}${TL.eras.map((e,i)=>`<text x="${(X(e.a)+X(e.b))/2}" y="${yLead}" text-anchor="middle" fill="${K.ink2}" font-size="12.5" font-weight="700">${esc(e.lead||ERAS[i].leaders.short)}</text>`).join('')}</g>`;
  /* 수요의 물결 */
  s+=`<g ${ln('demand')}>${gut('수요의 물결',hTop+34)}`;
  TL.waves.forEach((w,i)=>{const xa=X(w.a),xb=X(w.b),top=hTop+(i%2)*17,r=Math.min((xb-xa)*.36,64),open=w.b>=Y1,col=K.s[i%8];
    const d=open?`M${xa},${hBase}C${xa+r*.55},${hBase} ${xa+r*.45},${top} ${xa+r},${top}H${xb}V${hBase}Z`:`M${xa},${hBase}C${xa+r*.55},${hBase} ${xa+r*.45},${top} ${xa+r},${top}H${xb-r}C${xb-r*.45},${top} ${xb-r*.55},${hBase} ${xb},${hBase}Z`;
    s+=`<path d="${d}" fill="${col}" fill-opacity=".13" stroke="${col}" stroke-width="1.5" data-tip="${esc(w.name+'|'+w.tip)}"/><text x="${open?Math.min(xa+r+4,xb-tw(w.name,13)-6):(xa+xb)/2}" y="${top+17}" text-anchor="${open?'start':'middle'}" fill="${K.ink}" font-size="13" font-weight="700" class="halo">${esc(w.name)}</text>`});
  s+='</g>';
  /* 세계 반도체 매출 */
  const rv=TL.wsts,rmax=Math.max(...rv.map(d=>d[1])),ry=v=>rBase-v/rmax*(rBase-rTop),full=rv.filter(d=>!d[2]);
  s+=`<g ${ln('demand')}>${gut('세계 매출',rBase-26)}${gut('($bn)',rBase-12)}<path d="M${X(full[0][0]+.5)},${rBase}${full.map(d=>`L${X(d[0]+.5).toFixed(1)},${ry(d[1]).toFixed(1)}`).join('')}L${X(full[full.length-1][0]+.5)},${rBase}Z" fill="${K.s[0]}" opacity=".16"/><path d="M${full.map(d=>`${X(d[0]+.5).toFixed(1)},${ry(d[1]).toFixed(1)}`).join('L')}" fill="none" stroke="${K.s[0]}" stroke-width="2"/>`;
  rv.forEach(d=>{s+=`<rect x="${X(d[0])}" y="${rTop-4}" width="${X(d[0]+1)-X(d[0])}" height="${rBase-rTop+4}" fill="transparent" data-tip="${d[0]}년${d[2]?' ('+esc(d[2])+')':''}|세계 반도체 매출 $${num(d[1],0)}bn"/>`});
  TL.wstsNotes.forEach(o=>{const d=rv.find(q=>q[0]===o.y);if(!d)return;const cx=X(d[0]+.5),cy=ry(d[1]);s+=`<circle cx="${cx}" cy="${cy}" r="${d[2]?4.5:3.5}" fill="${d[2]?K.surf:K.s[0]}" stroke="${d[2]?K.s[0]:K.surf}" stroke-width="2"/><text x="${cx+(o.dx||0)}" y="${cy+(o.dy||-8)}" text-anchor="${o.anchor||'middle'}" fill="${K.ink}" font-size="12" font-weight="700" class="halo">${esc(o.t)}</text>`});
  s+='</g>';
  /* 시대 축: 오른쪽 끝이 화살표인 띠 하나. 시대 사이는 바탕색 틈으로만 나누고, 아래에 1년 · 5년 · 10년 눈금자를 단다 */
  s+=`<g>${gut('시대 구분',aTop+aH/2+4,1)}`;
  const nE=TL.eras.length,tipW=14,aM=aTop+aH/2;
  TL.eras.forEach((e,i)=>{const last=i===nE-1,xa=X(e.a)+(i?1:0),xb=X(e.b)-(last?0:1),w=xb-xa,mid=xa+(w-(last?tipW:0))/2;
    const d=i===0?`M${xa+7},${aTop}H${xb}V${aB}H${xa+7}Q${xa},${aB} ${xa},${aB-7}V${aTop+7}Q${xa},${aTop} ${xa+7},${aTop}Z`:last?`M${xa},${aTop}H${xb-tipW}L${xb},${aM}L${xb-tipW},${aB}H${xa}Z`:`M${xa},${aTop}H${xb}V${aB}H${xa}Z`;
    s+=`<g class="era" data-era="${i}" tabindex="0" role="button" aria-label="${esc(e.name)} 세부 보기"><path d="${d}" fill="${i%2?'#216f95':'#1a5d80'}"/><text x="${mid}" y="${aM+6}" text-anchor="middle" fill="#fff" font-size="16.5" font-weight="800">${esc(e.name)}<tspan fill="#e2f1fa" font-size="12.5" font-weight="600" dx="8">${esc(w>170?e.years:e.yearsShort)}</tspan></text></g>`});
  for(let yv=Y0;yv<=Y1;yv++){const dec=yv%10===0,five=yv%5===0,xx=X(yv);
    s+=`<line x1="${xx}" x2="${xx}" y1="${aB}" y2="${aB+(dec?9:five?6:3)}" stroke="${dec?K.ink2:five?K.ink3:K.axis}"${dec?' stroke-width="1.5"':''}/>`;
    if(dec)s+=`<text x="${xx}" y="${yYear}" text-anchor="middle" fill="${K.ink}" font-size="13" font-weight="700" class="tn">${yv}</text>`}
  s+='</g>';
  /* 사건 핀: 겹치면 아래 단으로 내린다 */
  s+=`<g ${ln('events')}>${gut('주요 사건',eY[0])}`;
  const used=eY.map(()=>-1e9);let pins='',labs='';
  TL.events.forEach(ev=>{const px=X(ev.y+.5),t=String(ev.y)+' '+ev.t,w=tw(t,12)+8,right=px+w>x1;let lv=used.findIndex(u=>(right?px-w:px)>u+6);if(lv<0)lv=used.indexOf(Math.min(...used));
    const lx=right?px-4:px+4;used[lv]=right?px:px+w;
    pins+=`<line x1="${px}" x2="${px}" y1="${aTop+aH}" y2="${eY[lv]-10}" stroke="${ev.key?K.ink2:K.axis}"/><circle cx="${px}" cy="${aTop+aH}" r="${ev.key?4:3}" fill="${ev.key?K.ink:K.ink3}" stroke="${K.surf}" stroke-width="1.5"/>`;
    labs+=`<text x="${lx}" y="${eY[lv]}" text-anchor="${right?'end':'start'}" font-size="12" class="halo" fill="${ev.key?K.ink:K.ink2}" ${ev.key?'font-weight="700"':''} data-tip="${esc(ev.y+' · '+ev.t+'|'+ev.tip)}"><tspan fill="${K.ink3}" class="tn">${ev.y}</tspan> ${esc(ev.t)}</text>`});
  s+=pins+labs+'</g>';
  /* 미국 기준금리 */
  const ff=TL.ff,fmax=20,fy=v=>fBase-Math.min(v,fmax)/fmax*(fBase-fTop);
  s+=`<g ${ln('macro')}>${gut('미국 금리',fBase-24)}${gut('(FF, %)',fBase-10)}<line x1="${x0}" x2="${x1}" y1="${fBase}" y2="${fBase}" stroke="${K.axis}"/><path d="M${X(ff[0][0])},${fBase}${ff.map(d=>`L${X(d[0]).toFixed(1)},${fy(d[1]).toFixed(1)}`).join('')}L${X(ff[ff.length-1][0])},${fBase}Z" fill="${K.s[1]}" opacity=".16"/><path d="M${ff.map(d=>`${X(d[0]).toFixed(1)},${fy(d[1]).toFixed(1)}`).join('L')}" fill="none" stroke="${K.s[1]}" stroke-width="1.75"/>`;
  TL.ffNotes.forEach(o=>{s+=`<text x="${X(o.y)+(o.dx||0)}" y="${fy(o.v)+(o.dy||-6)}" text-anchor="${o.anchor||'middle'}" fill="${K.ink}" font-size="12" font-weight="700" class="halo">${esc(o.t)}</text>`});
  s+='</g>';
  /* 거시 환경 · 산업 구조 막대 */
  const bandRow=(items,ys,col,k,label)=>`<g ${ln(k)}>${gut(label,ys[0]+13)}${items.map(b=>{const xa=X(b.a),xb=X(b.b),w=xb-xa,yy=ys[b.row||0],open=b.b>=Y1;return `<g data-tip="${esc(b.name+'|'+b.tip)}"><rect x="${xa}" y="${yy}" width="${w}" height="${rowH}" rx="4" fill="${col}" opacity="${b.soft?.16:.3}"/><rect x="${xa}" y="${yy}" width="3" height="${rowH}" fill="${col}"/>${open?`<path d="M${xb-7},${yy+4}l5,5l-5,5" fill="none" stroke="${K.ink2}" stroke-width="1.5"/>`:''}<text x="${xa+9}" y="${yy+13}" fill="${K.ink}" font-size="12" font-weight="600">${esc(tw(b.name,12)+16<w?b.name:b.short||b.name)}</text></g>`}).join('')}</g>`;
  s+=bandRow(TL.macro,mY,K.s[1],'macro','거시 환경')+bandRow(TL.structure,sY,K.s[2],'leaders','산업 구조');
  el.innerHTML=`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="1947년부터 2026년까지 반도체 산업의 수요, 매출, 사건, 금리, 거시 환경, 산업 구조를 한 시간축에 겹친 그림">${s}</svg>`;
  $$('[data-layer]').forEach(c=>c.onchange=timeline)}
function eraModal(i){const e=ERAS[i],L=[['demand','주요 수요'],['macro','거시 환경'],['events','전환점'],['leaders','주도 기업']];
  modal(e.name+' · '+e.years,L.map(([k,t])=>`<div class="source"><b class="era-k">${t} — ${esc(e[k].short)}</b><p>${esc(e[k].detail)} <a href="${esc(e[k].source||'#')}" target="_blank" rel="noopener">근거 ↗</a></p></div>`).join(''))}

/* 섹터 Top 10 범프 차트: 5년 간격의 시점을 나란히 두고 같은 기업을 선으로 잇는다 */
function mountSectors(){
  if(sector==null||!SECTOR.sectors[sector])sector=Math.max(0,SECTOR.sectors.findIndex(s=>s.id==='it'));
  $('#sectorPills').innerHTML=SECTOR.sectors.map((s,i)=>`<button data-sector="${i}"><span>${esc(s.name)}</span><em class="tn">${s.changes}<small>회</small></em></button>`).join('');
  $$('[data-sector]').forEach(b=>b.onclick=()=>{stopPlay();sector=+b.dataset.sector;drawSector()});
  $('#sectorPlay').onclick=()=>{if(playTimer){stopPlay();return}$('#sectorPlay').textContent='Ⅱ 정지';playTimer=setInterval(()=>{sector=(sector+1)%SECTOR.sectors.length;drawSector()},2600)};
  /* 기업 하나에 포인터를 올리면 그 기업의 칸과 선만 남긴다 */
  const el=$('#bump'),trace=k=>{const svg=$('svg',el);if(!svg)return;svg.classList.toggle('trace',k!=null);$$('[data-k]',svg).forEach(n=>n.classList.toggle('on',k!=null&&n.dataset.k===k))};
  el.onpointerover=e=>{const g=e.target.closest?.('[data-k]');trace(g&&!ink.on?g.dataset.k:null)};
  el.onpointerleave=()=>trace(null);
  drawSector()}
function drawSector(){
  const s=SECTOR.sectors[sector],Y=SECTOR.years,el=$('#bump'),W=el.clientWidth||1154,H=+el.dataset.h||464;
  $$('[data-sector]').forEach(b=>b.classList.toggle('active',+b.dataset.sector===sector));
  const cols=Y.map(y=>s.snapshots[String(y)].rows),nc=Y.length,nr=cols[0].length,G=26,gap=34,cw=(W-G-(nc-1)*gap)/nc,top=30,rh=(H-top)/nr,ch=rh-6,pad=8,inner=cw-2*pad;
  const cx=k=>G+k*(cw+gap),cy=r=>top+r*rh+3,k0=cols[0][0].key,k1=cols[nc-1][0].key,tone=key=>key===k1?K.s[0]:key===k0?K.s[1]:null;
  /* 1위 줄은 옅은 띠로 받치고, 왼쪽에 순위를 적는다 */
  let guide=`<rect x="0" y="${cy(0)-3}" width="${W}" height="${ch+6}" rx="8" fill="#fff" opacity=".045"/>`,links='',hot='',cells='';
  for(let r=0;r<nr;r++)guide+=`<text x="${G-9}" y="${cy(r)+ch/2+5}" text-anchor="end" fill="${r?K.ink3:K.ink}" font-size="${r?12.5:15}" font-weight="${r?500:800}" class="tn">${r+1}</text>`;
  for(let k=0;k<nc-1;k++)cols[k].forEach((r,a)=>{const b=cols[k+1].findIndex(q=>q.key===r.key);if(b<0)return;const xa=cx(k)+cw,xb=cx(k+1),ya=cy(a)+ch/2,yb=cy(b)+ch/2,t=tone(r.key);
    const p=`<path class="lk${t?' tone':''}" data-k="${esc(r.key)}" d="M${xa.toFixed(1)},${ya.toFixed(1)}C${(xa+gap*.5).toFixed(1)},${ya.toFixed(1)} ${(xb-gap*.5).toFixed(1)},${yb.toFixed(1)} ${xb.toFixed(1)},${yb.toFixed(1)}" fill="none" stroke="${t||K.mute}" stroke-width="${t?3:1.5}" opacity="${t?1:.75}"/>`;if(t)hot+=p;else links+=p});
  cols.forEach((c,k)=>{cells+=`<text x="${(cx(k)+cw/2).toFixed(1)}" y="20" text-anchor="middle" fill="${K.ink}" font-size="19" font-weight="800" class="tn">${Y[k]}</text>`;
    c.forEach((r,a)=>{const x=cx(k),yy=cy(a),t=tone(r.key),strong=t||a===0,f=Math.max(11,Math.min(13.5,13.5*inner/tw(r.name,13.5)));
      const tip=Y[k]+'년 · '+(a+1)+'위 '+r.name+'|매출 $'+num(r.revenue,1,1)+'bn'+(r.rankOverall?'|Fortune 500 전체 '+r.rankOverall+'위':'')+(r.gap?'|아카이브에 빠져 있던 순위 — 보완 자료의 값':'');
      cells+=`<g class="cell${t?' tone':''}" data-k="${esc(r.key)}" data-tip="${esc(tip)}"><rect x="${x.toFixed(1)}" y="${yy.toFixed(1)}" width="${cw.toFixed(1)}" height="${ch.toFixed(1)}" rx="6" fill="${t?'#10283f':'#0c1c2c'}" stroke="${t||'#21394c'}" stroke-width="${t?2:1}"/><text class="nm" x="${(x+pad).toFixed(1)}" y="${(yy+ch/2-2).toFixed(1)}" fill="${strong?K.ink:K.ink2}" font-size="${f.toFixed(1)}" font-weight="${strong?800:600}">${esc(r.name)}</text><text x="${(x+pad).toFixed(1)}" y="${(yy+ch/2+12).toFixed(1)}" fill="${K.ink3}" font-size="10.5" class="tn">$${num(r.revenue,1,1)}bn${r.gap?' †':''}</text></g>`})});
  el.innerHTML=`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(s.name)} 섹터 매출 상위 ${nr}개 기업의 ${Y[0]}–${Y[nc-1]}년 순위">${guide}${links}${hot}${cells}</svg>`;
  /* 추정한 폭보다 실제 글자가 넓으면 글자 크기를 실제 폭에 맞춰 줄인다. 그래도 넘칠 때만 칸 안쪽 폭으로 좁힌다 (글자가 칸 밖으로 나가지 않게) */
  $$('text.nm',el).forEach(t=>{if(!t.getComputedTextLength)return;let L=t.getComputedTextLength();if(L<=inner)return;
    t.setAttribute('font-size',Math.max(10.5,Math.floor(+t.getAttribute('font-size')*inner/L*10)/10));L=t.getComputedTextLength();
    if(L>inner){t.setAttribute('textLength',inner.toFixed(1));t.setAttribute('lengthAdjust','spacingAndGlyphs')}});
  const lg=(c,t,ln)=>`<span><i class="${ln?'ln':'sq'}" style="background:${c}"></i>${t}</span>`;
  $('#sectorStat').innerHTML=`<div class="sstat wide"><span class="k">매출 1위 · ${nc}개 시점에서 ${s.changes?'교체 '+s.changes+'회':'교체 없음'}</span><b id="sectorChain">${s.leaders.map(esc).join(' <i>→</i> ')}</b></div>`
    +`<div class="sstat"><span class="k">${Y[0]}년 Top ${nr} 중 ${Y[nc-1]}년에도 Top ${nr}</span><b>${s.stay} <small>/ ${nr}곳</small></b></div>`
    +`<div class="legend bump-legend">${k0===k1?lg(K.s[0],Y[0]+' · '+Y[nc-1]+'년 모두 1위'):lg(K.s[1],Y[0]+'년 1위 기업')+lg(K.s[0],Y[nc-1]+'년 1위 기업')}${lg(K.mute,'같은 기업의 순위 이동',1)}</div>`;
  const chain=$('#sectorChain');for(let f=20;f>13&&chain.scrollWidth>chain.clientWidth;)chain.style.fontSize=(--f)+'px';
  $('#sectorScope').textContent=SECTOR.scope+(s.note?' · '+s.note:'')+(cols.some(c=>c.some(r=>r.gap))?' · †는 보완 자료의 값':'')}

/* 재무 타일: 역년 분기 추이. 지표마다 축을 하나씩만 쓴다.
   타일은 세 묶음 — 위 4개 = 버는 힘, key = 투자와 FCF, debt = 부채 부담 (테두리 색으로 구분) */
function dashboard(){
  const c=FIN.dash[company],d=c.quarters,n=d.length,labels=d.map(x=>x.q.slice(2)),tips=d.map(x=>x.q.slice(0,4)+' '+x.q.slice(4));
  const ticks=labels.map((l,i)=>l.endsWith('Q1')?i:-1).filter(i=>i>=0);
  const specs=[['매출','revenue','$bn','bar'],['매출 성장률','revenueGrowth','%','line'],['순이익','netIncome','$bn','bar'],['영업이익률','operatingMargin','%','line'],['CAPEX','capex','$bn','bar','key'],['FCF','fcf','$bn','bar','key'],['이자보상배율','interestCoverage','배','line','debt'],['부채비율','debtRatio','%','line','debt']];
  const val=(x,k)=>Number.isFinite(x[k])?x[k]:null;
  /* 회사의 최근 분기 = 매출이 공시된 마지막 분기. 상장 전이거나 아직 발표되지 않은 분기는 비어 있다 */
  const li=d.reduce((a,x,i)=>val(x,'revenue')!=null?i:a,-1);
  /* 지표별: 값, 값이 있는 처음(fi) · 마지막(lk) 분기, 금액 자릿수(분기 금액이 $10bn 미만인 회사는 둘째 자리까지) */
  const T=specs.map(s=>{const v=d.map(x=>val(x,s[1])),u=s[2],has=v.map((x,i)=>x!=null?i:-1).filter(i=>i>=0),money=u==='$bn';
    const dec=money&&Math.max(0,...has.map(i=>Math.abs(v[i])))<10?2:1;
    return {s,v,u,unit:money?'bn':u,fi:has.length?has[0]:-1,lk:has.length?has[has.length-1]:-1,dec,show:x=>money?(x<0?'−$':'$')+num(Math.abs(x),dec,dec):num(x,1,1)}});
  slidePlots=[];
  /* 큰 숫자는 회사의 최근 분기 값, 옆의 작은 글씨는 그 지표가 처음 공시된 분기와의 비교.
     최근 분기에 값이 없는 지표는 N/A 로 두고 마지막으로 공시된 분기를 적는다 */
  $('#dashboard').innerHTML=T.map((t,k)=>{const {s,v,u,unit,fi,lk}=t,last=li>=0?v[li]:null,first=fi>=0?v[fi]:null,money=u==='$bn';
    const cmp=last==null?(lk>=0?`${labels[lk]}까지 공시 · ${t.show(v[lk])}${unit}`:'공시된 분기 값 없음')
      :labels[li]+(fi===li?'':money&&first>0&&last>0?` · ${labels[fi]}의 ${num(last/first,1,1)}배`:` · ${labels[fi]} ${t.show(first)}${unit}`);
    return `<div class="tile${s[4]?' '+s[4]:''}"><div class="tile-h"><span>${s[0]}</span><small>${u}</small></div><div class="tile-v">${last==null?'N/A':t.show(last)+`<small>${unit}</small>`}<em>${cmp}</em></div><div class="tile-c" data-k="${k}"></div></div>`}).join('');
  $$('.tile-c').forEach(el=>{const t=T[+el.dataset.k],s=t.s,u=t.u,line=s[3]==='line';
    if(t.lk<0){el.innerHTML='<p class="tile-none">공시된 분기 값 없음</p>';return}
    const spec={title:company+' · '+s[0]+' (분기)',labels,tipLabels:tips,type:s[3],fs:11,suf:u==='$bn'?'':u,pre:u==='$bn'?'$':'',dec:t.dec,x:{ticks},y:{n:2,head:.18},
      series:[{name:s[0],values:t.v,color:K.s[0],div:s[1]==='fcf',area:line,markers:false,pts:line?[t.lk]:null,ptText:{[t.lk]:''}}],legend:false};
    el.innerHTML=plot(spec,el.clientWidth||290,+el.dataset.h||el.clientHeight||138);slidePlots.push(spec)});
  $('#dashNote').textContent=`${company} · 역년 분기 ${d[0].q}–${d[n-1].q}${c.fiscalNote?' ('+c.fiscalNote+')':''} · 성장률 = 전년 동기 대비 · FCF = 영업CF − CAPEX · 이자보상 = 분기 영업이익 ÷ 이자비용 · 부채비율 = 총부채 ÷ 자본(분기 말) · 순이익은 영업외손익 포함.${c.quarterNote?' '+c.quarterNote:''}`}
function financialOverview(){
  const names=Object.keys(FIN.companies),labels=['FY21','FY22','FY23','FY24','FY25','26TTM'];
  const fcf={title:'빅테크 4사 FCF',labels,pre:'$',dec:1,series:names.map(n=>{const c=FIN.companies[n];return {name:n,values:c.annual.filter(x=>x.year<=2025).map(x=>x.fcf).concat((c.ttm2026||c.ttm)?.fcf??null),end:true,w:n==='Amazon'?3.5:2}})};
  /* 축 범위를 자료에 맞춘다: 20 단위로 올림·내림 (기본 눈금은 아래쪽에 빈 띠를 크게 남긴다) */
  const fv=fcf.series.flatMap(s=>s.values).filter(Number.isFinite),fs=20;
  fcf.y={pre:'$',step:fs,min:Math.floor(Math.min(0,...fv)/fs)*fs,max:Math.ceil(Math.max(0,...fv)/fs)*fs};
  drawInto($('#financialOverview'),fcf);
  const m=FIN.companies.Meta||FIN.companies['Meta Platforms'];
  if(m&&$('#debtChart')){const a=m.chartSeries;drawInto($('#debtChart'),{title:'Meta 장기차입 조달액',labels:a.map(x=>String(x.label).includes('TTM')?'26TTM':'FY'+String(x.year).slice(2)),type:'bar',pre:'$',dec:1,y:{n:4,pre:'$'},series:[{name:'장기차입 조달액',values:a.map(x=>x.debtIssuance),color:K.s[Math.max(0,names.indexOf('Meta'))],hi:[a.length-1],pts:[a.length-2,a.length-1]}]})}}

/* ───────── 펜(그리기) : 장표를 넘기면 지워지고 저장하지 않는다 ───────── */
const ink={on:false,tool:'pen',color:'#ffd84d',cur:null,pts:[]};
const inkXY=e=>{const r=$('#ink').getBoundingClientRect();return[(e.clientX-r.left)/r.width*1440,(e.clientY-r.top)/r.height*810]};
function inkD(p){if(p.length<2)return `M${p[0][0].toFixed(1)},${p[0][1].toFixed(1)}l.01,0`;let d=`M${p[0][0].toFixed(1)},${p[0][1].toFixed(1)}`;
  for(let i=1;i<p.length-1;i++)d+=`Q${p[i][0].toFixed(1)},${p[i][1].toFixed(1)} ${((p[i][0]+p[i+1][0])/2).toFixed(1)},${((p[i][1]+p[i+1][1])/2).toFixed(1)}`;
  const l=p[p.length-1];return d+`L${l[0].toFixed(1)},${l[1].toFixed(1)}`}
function setDraw(on){ink.on=on;document.body.classList.toggle('drawing',on);$('#pen').setAttribute('aria-pressed',String(on));$('#penTools').hidden=!on;if(on)tipOff();else ink.cur=null}
function inkUndo(){const p=$('#ink').lastElementChild;if(p)p.remove()}
function inkClear(){const s=$('#ink');if(s)s.replaceChildren();ink.cur=null}
function inkStyle(){$$('[data-ink-color]').forEach(b=>b.classList.toggle('active',b.dataset.inkColor===ink.color));$$('[data-ink-tool]').forEach(b=>b.classList.toggle('active',b.dataset.inkTool===ink.tool))}
function initInk(){const sv=$('#ink');
  sv.addEventListener('pointerdown',e=>{if(!ink.on||e.button>0)return;e.preventDefault();try{sv.setPointerCapture(e.pointerId)}catch(_){}
    ink.pts=[inkXY(e)];const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('class',ink.tool);p.setAttribute('stroke',ink.color);p.setAttribute('d',inkD(ink.pts));sv.append(p);ink.cur=p});
  sv.addEventListener('pointermove',e=>{if(!ink.cur)return;
    if(e.shiftKey){ink.pts=[ink.pts[0],inkXY(e)]}
    else{const ev=e.getCoalescedEvents?e.getCoalescedEvents():[];for(const c of(ev.length?ev:[e])){const q=inkXY(c),l=ink.pts[ink.pts.length-1];if(Math.hypot(q[0]-l[0],q[1]-l[1])>1.2)ink.pts.push(q)}}
    ink.cur.setAttribute('d',inkD(ink.pts))});
  const end=()=>{ink.cur=null};sv.addEventListener('pointerup',end);sv.addEventListener('pointercancel',end);
  $('#pen').onclick=()=>setDraw(!ink.on);$('#inkUndo').onclick=inkUndo;$('#inkClear').onclick=inkClear;
  $$('[data-ink-color]').forEach(b=>b.onclick=()=>{ink.color=b.dataset.inkColor;inkStyle()});
  $$('[data-ink-tool]').forEach(b=>b.onclick=()=>{ink.tool=b.dataset.inkTool;inkStyle()});inkStyle()}

/* ───────── 이벤트 ───────── */
document.addEventListener('click',e=>{const b=e.target.closest('[data-goto],button[data-part],[data-era],[data-jump],[data-linear]');if(!b)return;
  if(b.dataset.goto)goto(SLIDES.findIndex(s=>s.id===b.dataset.goto));
  else if(b.dataset.part)goto(SLIDES.findIndex(s=>s.part===+b.dataset.part));
  else if(b.dataset.era)eraModal(+b.dataset.era);
  else if(b.dataset.jump){$('#modal').close();goto(+b.dataset.jump)}
  else if(b.dataset.linear)setLinear(b.dataset.linear)});
$('#prev').onclick=()=>goto(index-1);$('#next').onclick=()=>goto(index+1);
$('#close').onclick=()=>$('#modal').close();$('#modal').addEventListener('close',()=>lastFocus?.focus?.());
$('#modal').addEventListener('click',e=>{if(e.target===$('#modal'))$('#modal').close()});
$('#sources').onclick=()=>sources();$('#toc').onclick=toc;
$('#full').onclick=()=>document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen?.();
document.addEventListener('fullscreenchange',()=>{document.body.classList.toggle('fs',!!document.fullscreenElement);scale()});
$('#timer').onclick=()=>{if(clockTimer){clearInterval(clockTimer);clockTimer=null;$('#timer').textContent='타이머 재개'}else{clockTimer=setInterval(()=>{elapsed++;$('#clock').textContent=String(Math.floor(elapsed/60)).padStart(2,'0')+':'+String(elapsed%60).padStart(2,'0')},1000);$('#timer').textContent='일시정지'}};
document.addEventListener('keydown',e=>{
  if($('#modal').open||/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName))return;
  const k=e.key.toLowerCase();
  if((e.ctrlKey||e.metaKey)&&k==='z'){e.preventDefault();inkUndo();return}
  if(e.ctrlKey||e.metaKey||e.altKey)return;
  if(e.key==='Enter'&&document.activeElement.dataset?.era!=null){eraModal(+document.activeElement.dataset.era);return}
  if(e.key==='ArrowRight'||e.key==='PageDown'||(e.key===' '&&document.activeElement.tagName!=='BUTTON')){e.preventDefault();goto(index+1)}
  else if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();goto(index-1)}
  else if(e.key==='Home')goto(0);else if(e.key==='End')goto(SLIDES.length-1);
  else if(k==='t')toc();else if(k==='s')sources();else if(k==='f')$('#full').click();
  else if(k==='d')setDraw(!ink.on);
  else if(ink.on&&k==='z')inkUndo();
  else if(ink.on&&(k==='x'||e.key==='Delete'||e.key==='Backspace')){e.preventDefault();inkClear()}
  else if(e.key==='Escape'){const b=$('.blackout');if(b)b.remove();else if(ink.on)setDraw(false)}
  else if(k==='b'){let b=$('.blackout');if(b)b.remove();else{b=document.createElement('div');b.className='blackout';b.onclick=()=>b.remove();document.body.append(b)}}});
window.addEventListener('resize',scale);
window.addEventListener('hashchange',()=>{const i=SLIDES.findIndex(s=>s.id===location.hash.slice(1));if(i>=0&&i!==index)goto(i)});
window.addEventListener('beforeprint',()=>{stopPlay();setDraw(false);inkClear();tipOff();PLOTS={};slidePlots=[];document.body.classList.add('printing');$('#slideHost').innerHTML=SLIDES.map(view).join('');mountCharts();mountSpecial()});
window.addEventListener('afterprint',()=>{document.body.classList.remove('printing');render()});
initInk();
index=Math.max(0,SLIDES.findIndex(s=>s.id===location.hash.slice(1)));render();

"""Rebuild current v3 presentation and standalone study. Original builder is backed up in archive/before_revision_* ."""
from pathlib import Path
import subprocess,sys,json,re
P=Path(__file__).parent
if '--check' in sys.argv:
 d=json.loads((P/'v3_deck_content.json').read_text(encoding='utf-8'))
 assert len(d['slides'])==len({s['id'] for s in d['slides']})
 for f in ['기업재무_발표자료_12조.html','기업재무_반도체산업.html']:
  t=(P/f).read_text(encoding='utf-8');assert t.startswith('<!');assert not re.search(r'\?{4}',re.sub(r'data:image/[^\"]+','',t))
 print('Current artifacts and unique slide IDs verified. Run qa_v3.cjs for interaction checks (jsdom required).')
else:
 if '--study-only' not in sys.argv:subprocess.run([sys.executable,str(P/'build_v3.py')],check=True)
 subprocess.run([sys.executable,str(P/'build_study_v3.py')],check=True)
 (P/'study.html').write_bytes((P/'기업재무_반도체산업.html').read_bytes())

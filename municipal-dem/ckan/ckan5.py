# 林野庁加工データの「データ諸元」PDF を落として、DEM の解像度の記述を抜く
import json,sys,urllib.request,re,os
W=sys.argv[1]
from pypdf import PdfReader
sys.stdout.reconfigure(encoding="utf-8")
for i in sys.argv[2:]:
    p=json.load(urllib.request.urlopen('https://www.geospatial.jp/ckan/api/3/action/package_show?id='+i,timeout=60))['result']
    for k,r in enumerate(x for x in p['resources'] if '諸元' in (x.get('name') or '')):
        f=os.path.join(W,f'{i}_{k}.pdf')
        if not os.path.exists(f): urllib.request.urlretrieve(r['url'],f)
        t=' '.join((pg.extract_text() or '') for pg in PdfReader(f).pages)
        t=re.sub(r'\s+',' ',t)
        hits=[m.group(0) for m in re.finditer(r'.{0,30}(?:DEM|ＤＥＭ|格子|メッシュ|解像度|グリッド).{0,40}',t)]
        yrs=sorted(set(re.findall(r'(?:平成|令和)\s*\d+\s*年度?',t)))[:6]
        print('###',i,k,'|',' / '.join(yrs)); [print('   ',h) for h in hits[:6]]

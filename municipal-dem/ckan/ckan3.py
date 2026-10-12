# 指定データセットの説明文・リソース名から解像度らしき記述を抜き出す
import json,sys,urllib.request,re
out=open(sys.argv[1],'w',encoding='utf-8')
pat=re.compile(r'[^。\n]{0,40}(\d+(?:\.\d+)?\s*(?:m|ｍ|cm|㎝|メートル)\s*(?:メッシュ|格子|間隔|解像度|グリッド|DEM)|(?:メッシュ|格子|間隔|解像度|グリッド)[^。]{0,10}\d+(?:\.\d+)?\s*(?:m|ｍ|cm|㎝))[^。\n]{0,40}')
for i in sys.argv[2:]:
    try: p=json.load(urllib.request.urlopen('https://www.geospatial.jp/ckan/api/3/action/package_show?id='+i,timeout=60))['result']
    except Exception as e: out.write(f'### {i} ERR {e}\n\n'); continue
    txt=(p.get('notes') or '')+'\n'+'\n'.join((r.get('name') or '')+' '+(r.get('description') or '') for r in p['resources'])
    hits=sorted({m.group(0).strip() for m in pat.finditer(txt)})
    out.write(f"### {i} | {p['title']}\n")
    for h in hits[:12]: out.write('  * '+re.sub(r'\s+',' ',h)+'\n')
    out.write('  resources: '+' / '.join((r.get('name') or '')[:40] for r in p['resources'][:25])+'\n\n')

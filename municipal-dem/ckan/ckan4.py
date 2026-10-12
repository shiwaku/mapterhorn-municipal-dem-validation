# 指定データセットのリソース説明（グリッド・DEM 関連）と諸元 PDF の URL を出す
import json,sys,urllib.request
for i in sys.argv[1:]:
    p=json.load(urllib.request.urlopen('https://www.geospatial.jp/ckan/api/3/action/package_show?id='+i,timeout=60))['result']
    print('###',i)
    for r in p['resources']:
        n=(r.get('name') or '')
        if any(k in n for k in ['グリッド','DEM','諸元','仕様']):
            print('  -',n,'|',(r.get('description') or '').replace('\n',' ')[:300],'|',r.get('url'))

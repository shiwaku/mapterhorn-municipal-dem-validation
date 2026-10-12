import json,sys,urllib.request,re
S=sys.argv[1]
ids=sys.argv[2:]
out=open(S+'/ckan_detail.txt','w',encoding='utf-8')
for i in ids:
    try: p=json.load(urllib.request.urlopen('https://www.geospatial.jp/ckan/api/3/action/package_show?id='+i,timeout=60))['result']
    except Exception as e: out.write(f'### {i} ERR {e}\n'); continue
    sz=sum((r.get('size') or 0) for r in p['resources'] if isinstance(r.get('size'),int))
    out.write(f"### {i} | {p['title']} | {p.get('license_title')} | res={len(p['resources'])} | size={sz/1e9:.1f}GB | mod={p['metadata_modified'][:10]}\n")
    out.write(re.sub(r'\s+',' ',(p.get('notes') or ''))[:1200]+'\n')
    ex={e['key']:e['value'] for e in p.get('extras',[])}
    for k in ex:
        if any(w in k for w in ['座標','空間','CRS','spatial','解像','精度','期間','時間','temporal']): out.write(f'  extra {k}: {ex[k][:150]}\n')
    for r in p['resources'][:6]: out.write(f"  - {r.get('name')} [{r.get('format')}] {r.get('size')} {r.get('url')[:110]}\n")
    out.write('\n')

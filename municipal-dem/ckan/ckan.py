import json,sys,urllib.request,urllib.parse
S=sys.argv[1]; seen={}
for q in ['DEM','数値標高モデル','標高','点群','航空レーザ','グリッドデータ','DTM','地形']:
    u='https://www.geospatial.jp/ckan/api/3/action/package_search?'+urllib.parse.urlencode({'q':q,'rows':1000})
    r=json.load(urllib.request.urlopen(u,timeout=60))['result']
    print(q,r['count'])
    for p in r['results']: seen[p['name']]=p
json.dump(seen,open(S+'/ckan_all.json','w',encoding='utf-8'),ensure_ascii=False)
rows=[]
for n,p in seen.items():
    t=p['title']; txt=t+(p.get('notes') or '')
    if not any(k in txt for k in ['DEM','標高','点群','グリッド','DTM','地形']): continue
    org=(p.get('organization') or {}).get('title','')
    fm=sorted({(x.get('format') or '').upper() for x in p['resources']})
    rows.append((org,t,p.get('license_title'),len(p['resources']),','.join(fm)[:40],p['metadata_modified'][:10],n))
rows.sort()
with open(S+'/ckan_rows.tsv','w',encoding='utf-8') as f:
    for r in rows: f.write('\t'.join(map(str,r))+'\n')
print(len(rows))

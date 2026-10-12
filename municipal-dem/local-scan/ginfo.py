import sys,subprocess,json,os,datetime
G=r"C:\Program Files\QGIS 3.34.12\bin\gdalinfo.exe"
for p in open(sys.argv[1],encoding='utf-8').read().split('\n'):
    if not p: continue
    w=p[1]+':'+p[2:]
    try:
        j=json.loads(subprocess.run([G,'-json',w],capture_output=True,timeout=120).stdout.decode('utf-8','replace'))
    except Exception as e:
        print(f'{p}\tERR {e}'); continue
    gt=j.get('geoTransform',[0,0,0,0,0,0]); sz=j.get('size',[0,0])
    wkt=j.get('coordinateSystem',{}).get('wkt','')
    import re
    epsg=(re.findall(r'ID\["EPSG",(\d+)\]\]\s*$',wkt) or ['?'])[0]
    b=j.get('bands',[{}])[0]
    ext=j.get('wgs84Extent',{}).get('coordinates',[[]])[0]
    if ext: xs=[c[0] for c in ext]; ys=[c[1] for c in ext]; bb=f'{min(xs):.3f},{min(ys):.3f},{max(xs):.3f},{max(ys):.3f}'
    else: bb='-'
    st=os.stat(w)
    md=j.get('metadata',{}).get('IMAGE_STRUCTURE',{}).get('COMPRESSION','-')
    print('\t'.join(map(str,[p,f'{abs(gt[1]):.4g}',epsg,f'{sz[0]}x{sz[1]}',b.get('type'),b.get('noDataValue'),md,f'{st.st_size/1e9:.1f}GB',datetime.date.fromtimestamp(st.st_mtime),bb])))

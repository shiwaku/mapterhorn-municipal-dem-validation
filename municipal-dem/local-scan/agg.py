import sys,glob,os,collections
S=sys.argv[1]; depth=int(sys.argv[2])
agg=collections.defaultdict(lambda:[0,0,collections.Counter()])
for f in glob.glob(S+'/*.tsv'):
    for line in open(f,encoding='utf-8',errors='replace'):
        try: sz,d,n=line.rstrip('\n').split('\t')
        except ValueError: continue
        parts=d.split('/'); key='/'.join(parts[:depth+1])
        a=agg[key]; a[0]+=1; a[1]+=int(sz); a[2][os.path.splitext(n)[1].lower()]+=1
rows=sorted(agg.items(),key=lambda x:-x[1][1])
for k,(c,s,e) in rows:
    if s<2e8: continue
    print(f'{s/1e9:8.1f}GB {c:7d}  {k}  {dict(e.most_common(4))}')

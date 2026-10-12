import sys,glob,collections,re,os
S=sys.argv[1]
agg=collections.defaultdict(lambda:[0,0,[]])
for f in glob.glob(S+'/*.tsv'):
    for line in open(f,encoding='utf-8',errors='replace'):
        try: sz,d,n=line.rstrip('\n').split('\t')
        except ValueError: continue
        full=(d+'/'+n)
        if not re.search(r'dem|las2|grid|標高|terrain|csmap-py',full,re.I): continue
        if re.search(r'node_modules|\.git/|/AppData/',full): continue
        a=agg[d]; a[0]+=1; a[1]+=int(sz)
        if len(a[2])<5: a[2].append(n)
for k,(c,s,e) in sorted(agg.items(),key=lambda x:x[0]):
    if s<5e7: continue
    print(f'{s/1e9:7.1f}GB {c:6d} {k} :: {", ".join(e)}')

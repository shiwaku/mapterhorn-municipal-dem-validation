# test_tiles.txt（/vsizip/ パスの一覧）にある図郭を ZIP から取り出す
import zipfile, collections, sys
src, dst = sys.argv[1], sys.argv[2]
d = collections.defaultdict(list)
for l in open(src, encoding='utf-8'):
    p = l.strip()[len('/vsizip/'):].replace(chr(92), '/')
    z, n = p.rsplit('.zip/', 1)
    d[z + '.zip'].append(n)
for z, ns in d.items():
    with zipfile.ZipFile(z) as zf:
        for n in ns:
            zf.extract(n, dst)
print(sum(map(len, d.values())))

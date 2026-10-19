# Pool() の既定のプロセス数を MAPTERHORN_CPUS に抑える（pipelines は Pool() を引数なしで呼ぶため）
import os

_n = int(os.environ.get('MAPTERHORN_CPUS', '0'))
if _n > 0:
    os.cpu_count = lambda: _n
    if hasattr(os, 'process_cpu_count'):
        os.process_cpu_count = lambda: _n

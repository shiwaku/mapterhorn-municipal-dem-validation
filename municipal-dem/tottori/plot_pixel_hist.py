"""pixel_before_after.py・pixel_vs_gsi.py・pixel_tiles.py が残したヒストグラム（*_hist.npz）から、差の分布の図を描く。

使い方（work-full で実行）:
  python ../plot_pixel_hist.py <出力.png>

縦軸は「その幅に入る画素の割合（%）」。比べる 2 つの分布は同じ幅で集計し直して重ねる。
"""
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.family'] = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'sans-serif']
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'
BLUE, ORANGE = '#2a78d6', '#eb6834'  # 参照パレットのカテゴリ 1・2（補正前・補正後、範囲の中・外）


def rebin(h, lo, width_in, width_out, xmin, xmax):
    """細かいヒストグラムを width_out 刻みに集め直し、[xmin, xmax] だけを返す（割合 %）。"""
    k = int(round(width_out / width_in))
    n = h.size // k * k
    hh = h[:n].reshape(-1, k).sum(axis=1)
    centers = lo + (np.arange(hh.size) + 0.5) * width_out
    m = (centers >= xmin) & (centers <= xmax)
    return centers[m], hh[m] / h.sum() * 100


def median(h, lo, w):
    c = h.cumsum()
    return lo + (np.searchsorted(c, c[-1] / 2) + 0.5) * w


def style(ax, title, xlabel):
    ax.set_title(title, loc='left', fontsize=11, color=INK, pad=8)
    ax.set_xlabel(xlabel, color=INK2, fontsize=9)
    ax.set_ylabel('画素の割合（%）', color=INK2, fontsize=9)
    ax.grid(axis='y', color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)


def quantized(h, lo, w, step, xmin, xmax):
    """値が step の倍数に丸められている分布（Mapterhorn の z16 は 1/32m）を、step ごとに集める。"""
    centers = lo + (np.arange(h.size) + 0.5) * w
    ks = np.arange(int(np.floor(xmin / step)), int(np.ceil(xmax / step)) + 1)
    k = np.round(centers / step).astype(int)
    y = np.array([h[k == kk].sum() for kk in ks]) / h.sum() * 100
    return ks * step, y


def pair(ax, ha, hb, lo, w, out_w, xmin, xmax, la, lb, ca=BLUE, cb=ORANGE, log=False, step=None):
    meds = [median(h, lo, w) for h in (ha, hb)]
    for i, (h, label, c) in enumerate(((ha, la, ca), (hb, lb, cb))):
        x, y = quantized(h, lo, w, step, xmin, xmax) if step else rebin(h, lo, w, out_w, xmin, xmax)
        ax.plot(x, y, color=c, linewidth=2, label=label, marker='o' if step else None, markersize=3)
        med = meds[i]
        ax.axvline(med, color=c, linewidth=1, linestyle=(0, (3, 3)))
        # 小さいほうの中央値は線の左、大きいほうは右に書く（重ならないように）
        left = (i == 0) == (meds[0] <= meds[1])
        ax.annotate(f'{label}\n中央値 {med:+.3f}m', xy=(med, 1), xycoords=('data', 'axes fraction'),
                    xytext=(-6 if left else 6, -40), textcoords='offset points',
                    fontsize=8, color=INK, va='top', ha='right' if left else 'left')
    if log:
        ax.set_yscale('log')
    ax.legend(frameon=False, fontsize=8, loc='upper left')
    ax.set_xlim(xmin, xmax)


def main():
    out = sys.argv[1]
    ba = np.load('pixel_before_after_hist.npz')
    g = np.load('pixel_vs_jpdem1a_hist.npz')
    t = np.load('pixel_tiles_z16_hist.npz')
    fig, axes = plt.subplots(3, 2, figsize=(13, 13))
    fig.patch.set_facecolor('#fcfcfb')

    # ① 補正後 − 補正前
    ax = axes[0, 0]
    lo, w = float(ba['diff_range'][0]), float(ba['bin'])
    x, y = rebin(ba['diff'], lo, w, 0.001, -0.245, -0.17)
    ax.bar(x, y, width=0.001 * 0.8, color=BLUE)
    style(ax, '① 補正後 − 補正前（鳥取どうし、0.5m の全画素）', '差（m）')
    med = median(ba['diff'], lo, w)
    ax.axvline(med, color=INK2, linewidth=1, linestyle=(0, (3, 3)))
    ax.annotate(f'中央値 {med:+.4f}m', xy=(med, y.max()), xytext=(6, -4), textcoords='offset points', fontsize=8, color=INK, va='top')

    ax = axes[0, 1]
    lo, w = float(ba['resid_range'][0]), float(ba['bin'])
    x, y = rebin(ba['resid'], lo, w, 0.0001, -0.003, 0.003)
    ax.bar(x * 1000, y, width=0.1 * 0.8, color=BLUE)
    style(ax, '① の差 − 補正量 dH（COG の圧縮誤差）', 'ずれ（mm）')
    ax.annotate('LERC 圧縮（許容誤差 1mm）を 2 回通すので、\n0 と ±1mm 付近に分かれる', xy=(0.02, 0.97), xycoords='axes fraction',
                fontsize=8, color=INK2, va='top')

    # ②③ 鳥取 − 地理院 1m
    lo, w = -float(g['hist_max']), float(g['bin'])
    ax = axes[1, 0]
    pair(ax, g['before'], g['after'], lo, w, 0.01, -1, 1, '補正前 − 地理院', '補正後 − 地理院')
    style(ax, '②③ 鳥取 − 地理院 DEM1A（1m 格子、全画素）', '差（m、1cm 刻み）')
    ax = axes[1, 1]
    pair(ax, g['before_flat'], g['after_flat'], lo, w, 0.005, -0.5, 0.5, '補正前 − 地理院', '補正後 − 地理院')
    style(ax, '②③ 同じ比較を平地（勾配 5% 未満）だけで', '差（m、5mm 刻み）')

    # ④ 作ったタイル − 本家
    lo, w = -float(t['hist_max']), float(t['bin'])
    ax = axes[2, 0]
    pair(ax, t['inside'], t['outside'], lo, w, None, -1, 1, '鳥取 0.5m の範囲の中', '範囲の外', log=True, step=1 / 32)
    style(ax, '④ 作った PMTiles − 本家（z16）', '差（m、z16 の標高の刻み 1/32m ごと）')
    ax.set_ylabel('画素の割合（%、対数）', color=INK2, fontsize=9)
    axes[2, 1].axis('off')
    axes[2, 1].text(0, 0.95, '\n'.join([
        '読み方',
        '・① はどの画素も補正量 dH（約 −0.21m）だけ動いた。',
        '   幅があるのは dH が場所で −0.23〜−0.18m と変わるため。',
        '・②③ 補正で分布の山が +0.21m から 0 へ移った。',
        '   形（幅）は変わらない。平地では山が鋭い。',
        '・④ 範囲の外は本家とほぼ同じ（0 に鋭い山）。',
        '   範囲の中は、本家が 5m・10m の所で差が広がる。',
        '・グラフの外（|差| > 1m）の画素もある。統計は #2 の表。',
    ]), va='top', fontsize=9, color=INK, transform=axes[2, 1].transAxes, linespacing=1.6)
    for ax in axes.flat:
        ax.set_facecolor('#fcfcfb')
    fig.tight_layout(pad=2)
    fig.savefig(out, dpi=110, facecolor=fig.get_facecolor())
    print(out)


if __name__ == '__main__':
    main()

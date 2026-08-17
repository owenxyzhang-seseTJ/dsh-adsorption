#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iast_selectivity.py — 二元 IAST 混合吸附与选择性（解析铺展压力 + 二分求根）。

方法：对每个组分先拟合 DSLF（q = M1·ln(1+K1·P) + M2·ln(1+K2·P)，bar 制），
再解铺展压力方程 Ψ1(p1/x1) = Ψ2(p2/(1−x1))，其中
    Ψ(P) = −Σ M_i·spence(1 + K_i·P)   （spence = scipy.special.spence = Li₂(1−z)，注意负号）

用法:
  iast_selectivity.py iso1.csv iso2.csv --y1 0.15 --p-max-bar 1.0 --n-points 30 --out-dir out
输出: iast_选择性_vs_压力.csv（P_bar, S, x1, x2, n1_mmol_g, n2_mmol_g）
"""
import argparse
import pathlib

import numpy as np
import pandas as pd
from scipy.optimize import brentq, least_squares
from scipy.special import spence


def dslf(P, M1, K1, M2, K2):
    return M1 * np.log(1 + K1 * P) + M2 * np.log(1 + K2 * P)


def psi(P, Ms, Ks):
    return float(-sum(M * spence(1.0 + K * P) for M, K in zip(Ms, Ks)))


def fit_dslf(path):
    df = pd.read_csv(path).dropna().sort_values("P_bar")
    P = df["P_bar"].to_numpy()
    n = df["n_mmol_g"].to_numpy()
    res = least_squares(lambda th: dslf(P, *th) - n, x0=[5.0, 1.0, 2.0, 100.0],
                        bounds=([0, 1e-6, 0, 1e-6], [200, 1e6, 200, 1e6]), max_nfev=20000)
    if not res.success:
        raise SystemExit(f"DSLF 拟合失败 {path}: {res.message}")
    return res.x


def iast_binary(p1, p2, iso1, iso2):
    """返回 (n1, n2, x1, x2)；iso = (Ms, Ks)，分压 bar。"""
    def f(x1):
        return psi(p1 / x1, iso1[::2], iso1[1::2]) - psi(p2 / (1.0 - x1), iso2[::2], iso2[1::2])
    x1 = brentq(f, 1e-9, 1.0 - 1e-9, xtol=1e-12)
    x2 = 1.0 - x1
    return dslf(p1 / x1, *iso1), dslf(p2 / x2, *iso2), x1, x2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iso1", help="组分 1 标准等温线 CSV")
    ap.add_argument("iso2", help="组分 2 标准等温线 CSV")
    ap.add_argument("--y1", type=float, default=0.15, help="组分 1 进料摩尔分数")
    ap.add_argument("--p-max-bar", type=float, default=1.0, help="最大总压 bar")
    ap.add_argument("--p-min-bar", type=float, default=1e-2, help="最小总压 bar")
    ap.add_argument("--n-points", type=int, default=30)
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()
    if not (0 < args.y1 < 1):
        raise SystemExit("--y1 必须在 (0,1)")

    iso1 = fit_dslf(args.iso1)
    iso2 = fit_dslf(args.iso2)
    print(f"组分1 DSLF: M1={iso1[0]:.4g} K1={iso1[1]:.4g} M2={iso1[2]:.4g} K2={iso1[3]:.4g}")
    print(f"组分2 DSLF: M1={iso2[0]:.4g} K1={iso2[1]:.4g} M2={iso2[2]:.4g} K2={iso2[3]:.4g}")

    rows = []
    for Ptot in np.logspace(np.log10(args.p_min_bar), np.log10(args.p_max_bar), args.n_points):
        n1, n2, x1, x2 = iast_binary(Ptot * args.y1, Ptot * (1 - args.y1), iso1, iso2)
        S = (x1 / args.y1) / (x2 / (1 - args.y1))
        rows.append((Ptot, S, x1, x2, n1, n2))
    df = pd.DataFrame(rows, columns=["P_bar", "S", "x1", "x2", "n1_mmol_g", "n2_mmol_g"])
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv = out / "iast_选择性_vs_压力.csv"
    df.to_csv(csv, index=False)

    print(f"\n{'P (bar)':>9} {'S':>10} {'x1':>8} {'x2':>8} {'n1':>8} {'n2':>8}")
    for r in rows[:: max(1, len(rows) // 8)]:
        print(f"{r[0]:9.4g} {r[1]:10.3f} {r[2]:8.4f} {r[3]:8.4f} {r[4]:8.3f} {r[5]:8.3f}")
    print(f"\n已写出: {csv}")


if __name__ == "__main__":
    main()

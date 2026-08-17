#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bet_area.py — BET 比表面积（pyGAPS，含 Rouquerol 判据输出）。

输入（标准格式）: P_bar, n_mmol_g  → 按 P0 换算为相对压力后计算。
P0 默认: N2 77K = 1.0 bar、Ar 87K = 1.0 bar、CO2 273K = 34.85 bar（可 --p0-bar 覆盖）。
输出: BET_数据.csv（P/P0、1/(n(1−P/P0))、拟合段标记）与参数打印。
"""
import argparse
import pathlib

import numpy as np
import pandas as pd

import pygaps
from pygaps.characterisation import area_BET

DEFAULT_P0 = {("N2", 77.0): 1.0, ("Ar", 87.0): 1.0, ("CO2", 273.0): 34.85}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data", help="标准格式等温线 CSV（P_bar, n_mmol_g）")
    ap.add_argument("--temp-k", type=float, default=77.0)
    ap.add_argument("--adsorbate", default="N2")
    ap.add_argument("--p0-bar", type=float, help="饱和蒸气压 bar")
    ap.add_argument("--p-limits", default="0.01,0.30", help='P/P0 区间 "lo,hi"')
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    if not {"P_bar", "n_mmol_g"} <= set(df.columns):
        raise SystemExit(f"输入必须是标准格式（P_bar, n_mmol_g），实际列: {list(df.columns)}")
    df = df.dropna().sort_values("P_bar").reset_index(drop=True)
    p0 = args.p0_bar or DEFAULT_P0.get((args.adsorbate, round(args.temp_k)))
    if p0 is None:
        raise SystemExit(f"未知 P0({args.adsorbate}, {args.temp_k}K)，必须给 --p0-bar")
    lo, hi = (float(x) for x in args.p_limits.split(","))

    iso = pygaps.PointIsotherm(
        pressure=df["P_bar"].to_numpy() / p0, loading=df["n_mmol_g"].to_numpy(),
        material=pathlib.Path(args.data).stem, adsorbate=args.adsorbate,
        temperature=args.temp_k, pressure_mode="relative", loading_unit="mmol",
    )
    bet = area_BET(iso, branch="ads", p_limits=(lo, hi))

    area = bet["area"]
    C = bet.get("C", float("nan"))
    corr = bet.get("corr_coef", float("nan"))
    n_mono = bet.get("n_monolayer", float("nan"))
    # Rouquerol: 选点区间内 n(1−P/P0) 单调递增
    P = iso.pressure(branch="ads")
    n = iso.loading(branch="ads")
    rouq = n * (1 - P)
    in_range = (P >= lo) & (P <= hi)
    rouq_inc = bool(np.all(np.diff(rouq[in_range]) > 0)) if in_range.sum() >= 3 else False

    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "P_P0": P, "n_mmol_g": n,
        "inv_n_1_minus_P": 1.0 / (n * (1 - P)),
        "in_fit_range": in_range,
    }).to_csv(out / f"{pathlib.Path(args.data).stem}_BET_数据.csv", index=False)

    print(f"BET 面积 = {area:.2f} m2/g   C = {C:.3g}   相关系数 = {corr:.5f}")
    print(f"单层吸附量 n_monolayer = {n_mono:.4f} mmol/g")
    print(f"P/P0 区间 = ({lo}, {hi})   Rouquerol 判据（n(1−P/P0) 单调递增）: {'满足' if rouq_inc else '不满足'}")
    print(f"注意: C ≤ 0 或 r < 0.999 时结果不可信；微孔材料应报告收窄区间结果")


if __name__ == "__main__":
    main()

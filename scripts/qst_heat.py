#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qst_heat.py — 等量吸附热 Qst（pyGAPS Clausius–Clapeyron，多温度等温线）。

输入: 目录（含多个 *_<T>K.csv 标准等温线）或逗号分隔文件列表。
      温度从文件名 <数字>K 提取；取不到时用 --temps "298,313,333"（与文件顺序对应）。
输出: Qst_vs_loading.csv（n_mmol_g, Qst_kJ_mol, err_kJ_mol）
"""
import argparse
import pathlib
import re

import numpy as np
import pandas as pd

import pygaps
from pygaps.characterisation import enthalpy_sorption_clapeyron


def load(path):
    df = pd.read_csv(path)
    if not {"P_bar", "n_mmol_g"} <= set(df.columns):
        raise SystemExit(f"文件 {path} 不是标准格式（P_bar, n_mmol_g）")
    return df.dropna().sort_values("P_bar").reset_index(drop=True)


def temp_from_name(path, fallback=None):
    m = re.search(r"(\d+(?:\.\d+)?)K", pathlib.Path(path).stem)
    if m:
        return float(m.group(1))
    if fallback is not None:
        return fallback
    raise SystemExit(f"无法从文件名提取温度: {path}（给 --temps 按顺序指定）")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="多温度等温线目录或逗号分隔文件列表")
    ap.add_argument("--adsorbate", default="N2")
    ap.add_argument("--p0-bar", type=float, help="饱和蒸气压 bar（默认按吸附质/温度表）")
    ap.add_argument("--loading-points", default="0.5,1,2,3,5", help="吸附量点 mmol/g，逗号分隔")
    ap.add_argument("--temps", help="温度列表 K（与文件顺序对应；文件名含 <T>K 时自动提取）")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    p = pathlib.Path(args.input)
    if p.is_dir():
        files = sorted(p.glob("*.csv"))
        files = [f for f in files if re.search(r"(\d+(?:\.\d+)?)K", f.stem)]
        if not files:
            raise SystemExit(f"目录 {p} 中没有文件名含 <温度>K 的 CSV")
    else:
        files = [pathlib.Path(x.strip()) for x in args.input.split(",") if x.strip()]
    if len(files) < 3:
        raise SystemExit(f"需要至少 3 条温度等温线，当前 {len(files)} 个")
    temps = None
    if args.temps:
        temps = [float(x) for x in args.temps.split(",")]
    if temps and len(temps) != len(files):
        raise SystemExit("--temps 数量与文件数量不一致")

    isos = []
    for i, f in enumerate(files):
        df = load(f)
        T = temp_from_name(f, temps[i] if temps else None)
        p0 = args.p0_bar
        if p0 is None:
            p0 = {("N2", round(T)): 1.0, ("Ar", round(T)): 1.0, ("CO2", round(T)): 34.85}.get((args.adsorbate, round(T)))
        if p0 is None:
            raise SystemExit(f"未知 P0({args.adsorbate}, {T}K)，给 --p0-bar")
        isos.append(pygaps.PointIsotherm(
            pressure=df["P_bar"].to_numpy() / p0, loading=df["n_mmol_g"].to_numpy(),
            material="sample", adsorbate=args.adsorbate, temperature=T,
            pressure_mode="relative", loading_unit="mmol",
        ))
        print(f"载入 {f.name}: T = {T} K, {len(df)} 点")

    points = [float(x) for x in args.loading_points.split(",")]
    qst = enthalpy_sorption_clapeyron(isos, loading_points=points, branch="ads")
    n_arr = np.asarray(qst["loading_points"])
    q_arr = np.asarray(qst["enthalpy_sorption"])
    err_arr = np.asarray(qst["enthalpy_sorption_err"]) if "enthalpy_sorption_err" in qst else np.full_like(q_arr, np.nan)

    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv = out / "Qst_vs_loading.csv"
    pd.DataFrame({"n_mmol_g": n_arr, "Qst_kJ_mol": q_arr, "err_kJ_mol": err_arr}).to_csv(csv, index=False)

    print(f"\n{'n (mmol/g)':>12} {'Qst (kJ/mol)':>14} {'±err':>10}")
    for n_, q_, e_ in zip(n_arr, q_arr, err_arr):
        print(f"{n_:12.3f} {q_:14.3f} {e_:10.3f}")
    print(f"\n已写出: {csv}")


if __name__ == "__main__":
    main()

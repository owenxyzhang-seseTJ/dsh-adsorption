#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把仪器原始/任意格式的吸附数据转换为预设标准格式 CSV。

标准格式（本预设统一约定，后续所有计算都吃这种文件）：
  - 等温线：UTF-8 CSV，表头 `P_bar,n_mmol_g[,T_K]`
    · P_bar    压力，bar
    · n_mmol_g 吸附量，mmol/g
    · T_K      （可选）温度，K；多温度等温线一文件三列
  - 穿透曲线：UTF-8 CSV，表头 `time_min,<组分>_C_C0,...`
    · time_min 时间，min
    · <组分>_C_C0 各组分出口浓度比 C/C0（0~1）

用法示例：
  # 仪器导出 xlsx，第 2 张表，压力列 "P (Torr)"，吸附量列 "n (cc/g)"，温度 298 K
  standardize_isotherm.py raw.xlsx --sheet 1 --pressure-col "P (Torr)" --pressure-unit torr \
      --loading-col "n (cc/g)" --loading-unit cm3stp_g --temp-k 298 --out CO2_298K.csv

  # 三列文本（P_kPa, n_mg_g, T_K）
  standardize_isotherm.py raw.txt --pressure-col P_kPa --pressure-unit kpa \
      --loading-col n_mg_g --loading-unit mg_g --molar-mass-g-mol 44.01 \
      --temp-col T_K --out CO2_multiT.csv
"""
import argparse

import pandas as pd

# 单位换算到标准单位（bar / mmol/g）
PRESSURE_TO_BAR = {
    "bar": 1.0,
    "pa": 1e-5,
    "kpa": 1e-2,
    "mpa": 10.0,
    "torr": 1.0 / 750.062,
    "mmhg": 1.0 / 750.062,
    "atm": 1.01325,
    "mbar": 1e-3,
    "psi": 0.0689476,
}
LOADING_TO_MMOL_G = {
    "mmol_g": 1.0,
    "mol_g": 1000.0,
    "mol_kg": 1.0,
    "cm3stp_g": 1000.0 / 22.414,   # cm³(STP)/g → mmol/g
    "cc_g": 1000.0 / 22.414,
    "cm3_g": 1000.0 / 22.414,
    "ml_g": 1000.0 / 22.414,
}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("data", help="原始数据文件（csv/xlsx/xls/txt）")
    ap.add_argument("--sheet", type=int, default=0, help="Excel 工作表序号（0 起，默认 0）")
    ap.add_argument("--skiprows", type=int, default=0, help="跳过表头前若干行")
    ap.add_argument("--pressure-col", required=True, help="压力列名")
    ap.add_argument("--pressure-unit", required=True,
                    help="压力单位: bar|pa|kpa|mpa|torr|mmhg|atm|mbar|psi")
    ap.add_argument("--loading-col", required=True, help="吸附量列名")
    ap.add_argument("--loading-unit", required=True,
                    help="吸附量单位: mmol_g|mol_g|mol_kg|cm3stp_g|cc_g|cm3_g|ml_g|mg_g")
    ap.add_argument("--molar-mass-g-mol", type=float,
                    help="mg_g 单位时必填：吸附质摩尔质量 g/mol")
    ap.add_argument("--temp-col", help="可选：温度列名（输出 T_K 列）")
    ap.add_argument("--temp-k", type=float, help="可选：固定温度 K（无温度列时写入元信息）")
    ap.add_argument("--out", required=True, help="输出标准 CSV 路径")
    ap.add_argument("--drop-nonpositive", action="store_true",
                    help="删除 P<=0 或 n<0 的行（默认保留，只警告）")
    args = ap.parse_args()

    if args.pressure_unit not in PRESSURE_TO_BAR:
        raise SystemExit(f"不支持的压力单位: {args.pressure_unit}，可选 {list(PRESSURE_TO_BAR)}")
    lu = args.loading_unit
    if lu == "mg_g":
        if args.molar_mass_g_mol is None:
            raise SystemExit("--loading-unit mg_g 必须给 --molar-mass-g-mol")
        load_factor = 1000.0 / args.molar_mass_g_mol   # mg/g → mmol/g
    elif lu not in LOADING_TO_MMOL_G:
        raise SystemExit(f"不支持的吸附量单位: {lu}，可选 {list(LOADING_TO_MMOL_G)} + mg_g")
    else:
        load_factor = LOADING_TO_MMOL_G[lu]

    # ── 读入 ──
    if args.data.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(args.data, sheet_name=args.sheet, skiprows=args.skiprows)
    else:
        df = pd.read_csv(args.data, skiprows=args.skiprows)
    for col in [args.pressure_col, args.loading_col] + ([args.temp_col] if args.temp_col else []):
        if col not in df.columns:
            raise SystemExit(f"列 {col!r} 不在文件中，实际列: {list(df.columns)}")

    P = pd.to_numeric(df[args.pressure_col], errors="coerce")
    n = pd.to_numeric(df[args.loading_col], errors="coerce")
    out = pd.DataFrame({
        "P_bar": P * PRESSURE_TO_BAR[args.pressure_unit],
        "n_mmol_g": n * load_factor,
    })
    if args.temp_col:
        out["T_K"] = pd.to_numeric(df[args.temp_col], errors="coerce")

    bad = out.isna().any(axis=1)
    neg = (out["P_bar"] <= 0) | (out["n_mmol_g"] < 0)
    n_bad = int((bad | neg).sum())
    if n_bad:
        print(f"警告: {n_bad} 行无效（NaN 或 P<=0 / n<0）")
        if args.drop_nonpositive:
            out = out[~(bad | neg)]
            print("      已按 --drop-nonpositive 删除")
        else:
            print("      保留原始行（NaN 会在后续计算中被质控剔除）；加 --drop-nonpositive 可删除")

    out = out.dropna().sort_values("P_bar").reset_index(drop=True)
    out.to_csv(args.out, index=False, encoding="utf-8")

    print(f"已写出标准 CSV: {args.out}")
    print(f"  行数: {len(out)}")
    print(f"  P 范围: {out['P_bar'].min():.6g} ~ {out['P_bar'].max():.6g} bar")
    print(f"  n 范围: {out['n_mmol_g'].min():.6g} ~ {out['n_mmol_g'].max():.6g} mmol/g")
    if args.temp_k and not args.temp_col:
        print(f"  温度: {args.temp_k} K（写入文件名/报告时注明）")
    if args.temp_col:
        print(f"  T 范围: {out['T_K'].min():.1f} ~ {out['T_K'].max():.1f} K")


if __name__ == "__main__":
    main()

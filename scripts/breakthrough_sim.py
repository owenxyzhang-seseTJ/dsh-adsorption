#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
breakthrough_sim.py — RUPTURA 二元穿透曲线模拟。

输入: 两个标准等温线 CSV（组分 1/2，P_bar, n_mmol_g）。
流程: 对每个组分按 RUPTURA 双曲式双位点 Langmuir（q = q1·b1·P/(1+b1·P) + q2·b2·P/(1+b2·P)，
      SI 单位: P 用 Pa，q 用 mol/kg（1 mmol/g = 1 mol/kg））用 least_squares 拟合，
      再构建 RUPTURA Components + Breakthrough 模拟。
输出: 穿透模拟_<条件>.csv（time_min, <组分1>_C_C0, <组分2>_C_C0）+ PNG
"""
import argparse
import pathlib

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from ruptura.ruptura import Components, Breakthrough


def dslf_hyper(P, q1, b1, q2, b2):
    return q1 * b1 * P / (1 + b1 * P) + q2 * b2 * P / (1 + b2 * P)


def fit_ruptura(path, name):
    df = pd.read_csv(path).dropna().sort_values("P_bar")
    P_pa = df["P_bar"].to_numpy() * 1e5          # bar → Pa
    q_molkg = df["n_mmol_g"].to_numpy()          # mmol/g = mol/kg
    res = least_squares(lambda th: dslf_hyper(P_pa, *th) - q_molkg,
                        x0=[2.0, 1e-6, 2.0, 1e-8],
                        bounds=([0, 1e-10, 0, 1e-12], [200, 1e-2, 200, 1e-4]))
    if not res.success:
        raise SystemExit(f"{name} 双曲 DSLF 拟合失败: {res.message}")
    print(f"{name} 拟合: q1={res.x[0]:.4g} mol/kg b1={res.x[1]:.4g} 1/Pa, "
          f"q2={res.x[2]:.4g} mol/kg b2={res.x[3]:.4g} 1/Pa")
    return [["Langmuir", res.x[0], res.x[1]], ["Langmuir", res.x[2], res.x[3]]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iso1", help="组分 1 标准等温线 CSV")
    ap.add_argument("iso2", help="组分 2 标准等温线 CSV")
    ap.add_argument("--name1", default="comp1")
    ap.add_argument("--name2", default="comp2")
    ap.add_argument("--y1", type=float, default=0.15)
    ap.add_argument("--temp-k", type=float, default=298.0)
    ap.add_argument("--pressure-bar", type=float, default=1.0)
    ap.add_argument("--col-length-m", type=float, default=0.5)
    ap.add_argument("--void-frac", type=float, default=0.4)
    ap.add_argument("--density-kg-m3", type=float, default=1000.0)
    ap.add_argument("--time-step-s", type=float, default=0.05)
    ap.add_argument("--n-steps", type=int, default=2000)
    ap.add_argument("--write-every", type=int, default=0,
                    help="输出时间点数间隔（默认 n_steps//100；不设则 RUPTURA 只返回末步）")
    ap.add_argument("--mtc", type=float, default=0.1, help="传质系数 1/s")
    ap.add_argument("--adc", type=float, default=1e-6, help="轴向弥散 m2/s")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    iso1 = fit_ruptura(args.iso1, args.name1)
    iso2 = fit_ruptura(args.iso2, args.name2)
    components = Components([
        {"MoleculeName": args.name1, "GasPhaseMolFraction": args.y1, "isotherms": iso1,
         "MassTransferCoefficient": args.mtc, "AxialDispersionCoefficient": args.adc, "CarrierGas": False},
        {"MoleculeName": args.name2, "GasPhaseMolFraction": 1 - args.y1, "isotherms": iso2,
         "MassTransferCoefficient": args.mtc, "AxialDispersionCoefficient": args.adc, "CarrierGas": True},
    ])
    bt = Breakthrough(components=components, DisplayName=f"{args.name1}/{args.name2}",
                      Temperature=args.temp_k, TotalPressure=args.pressure_bar * 1e5,
                      ColumnLength=args.col_length_m, ColumnVoidFraction=args.void_frac,
                      ParticleDensity=args.density_kg_m3, NumberOfTimeSteps=args.n_steps,
                      TimeStep=args.time_step_s, WriteEvery=args.write_every or max(1, args.n_steps // 100),
                      MixturePredictionMethod="IAST")
    data = bt.compute()                      # (Nt, Ngrid, 8 + 6*Ncomp)

    t_min = data[:, -1, 1]
    c1 = data[:, -1, 8]
    c2 = data[:, -1, 8 + 6]
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tag = f"{args.name1}_{args.name2}_y{args.y1:.2f}_P{args.pressure_bar:.1f}bar"
    csv = out / f"穿透模拟_{tag}.csv"
    pd.DataFrame({f"time_min": t_min, f"{args.name1}_C_C0": c1, f"{args.name2}_C_C0": c2}).to_csv(csv, index=False)

    # 5% 穿透时间（组分 1）
    idx = np.argmax(c1 >= 0.05)
    t5 = t_min[idx] if c1[idx] >= 0.05 else float("nan")
    print(f"\n模拟完成: {args.n_steps} 步 × {data.shape[1]} 网格点, 出口 {data.shape[2]} 列")
    print(f"组分1 5% 穿透时间 ≈ {t5:.2f} min")
    print(f"已写出: {csv}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(t_min, c1, label=args.name1)
    ax.plot(t_min, c2, label=args.name2)
    ax.axhline(0.05, ls="--", lw=0.8, color="gray")
    ax.set_xlabel("time (min)")
    ax.set_ylabel("C / C$_0$")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / f"穿透模拟_{tag}.png", dpi=300)
    print(f"图已写出: {out / f'穿透模拟_{tag}.png'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fit_isotherm.py — 纯组分等温线模型拟合（bar 单位制，scipy least_squares 带界约束）。

输入（标准格式）: P_bar, n_mmol_g [, T_K]
模型（q = Σ M·ln(1+K·P) 系，与 pyIAST 1.4.3 同形式）:
  DSLF      : q = M1·ln(1+K1·P) + M2·ln(1+K2·P)
  Langmuir  : q = M·ln(1+K·P)
  Quadratic : q = M·(Ka·P + 2·Kb·P²) / (1 + Ka·P + Kb·P²)
输出: <stem>_fit_params.csv（参数+RMSE+R²）、<stem>_fit_compare.csv（P,n_exp,n_fit）
"""
import argparse
import pathlib

import numpy as np
import pandas as pd
from scipy.optimize import least_squares


def dslf(P, M1, K1, M2, K2):
    return M1 * np.log(1 + K1 * P) + M2 * np.log(1 + K2 * P)


def langmuir(P, M, K):
    return M * np.log(1 + K * P)


def quadratic(P, M, Ka, Kb):
    return M * (Ka * P + 2 * Kb * P ** 2) / (1 + Ka * P + Kb * P ** 2)


MODELS = {
    "DSLF":      dict(f=dslf,      names=["M1", "K1", "M2", "K2"], x0=[5.0, 1.0, 2.0, 100.0],
                      lo=[0, 1e-6, 0, 1e-6], hi=[200, 1e6, 200, 1e6]),
    "Langmuir":  dict(f=langmuir,  names=["M", "K"],              x0=[5.0, 1.0],
                      lo=[0, 1e-6], hi=[200, 1e6]),
    "Quadratic": dict(f=quadratic, names=["M", "Ka", "Kb"],       x0=[5.0, 1.0, 1.0],
                      lo=[0, 1e-6, 1e-6], hi=[200, 1e6, 1e6]),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data", help="标准格式等温线 CSV（P_bar, n_mmol_g）")
    ap.add_argument("--model", default="DSLF", choices=list(MODELS))
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    if not {"P_bar", "n_mmol_g"} <= set(df.columns):
        raise SystemExit(f"输入必须是标准格式（P_bar, n_mmol_g），实际列: {list(df.columns)}")
    df = df.dropna().sort_values("P_bar").reset_index(drop=True)
    P = df["P_bar"].to_numpy()
    n = df["n_mmol_g"].to_numpy()

    m = MODELS[args.model]
    res = least_squares(lambda th: m["f"](P, *th) - n, x0=m["x0"], bounds=(m["lo"], m["hi"]))
    if not res.success:
        raise SystemExit(f"拟合未收敛: {res.message}")
    params = dict(zip(m["names"], res.x))
    fit = m["f"](P, *res.x)
    rmse = float(np.sqrt(np.mean((fit - n) ** 2)))
    r2 = 1 - float(np.sum((n - fit) ** 2)) / float(np.sum((n - n.mean()) ** 2))

    stem = pathlib.Path(args.data).stem
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"param": list(params), "value": list(params.values())}).to_csv(
        out / f"{stem}_fit_params.csv", index=False)
    pd.DataFrame({"P_bar": P, "n_exp_mmol_g": n, "n_fit_mmol_g": fit}).to_csv(
        out / f"{stem}_fit_compare.csv", index=False)

    print(f"模型: {args.model}   RMSE = {rmse:.4f} mmol/g   R² = {r2:.4f}")
    for k, v in params.items():
        print(f"  {k} = {v:.6g}")


if __name__ == "__main__":
    main()

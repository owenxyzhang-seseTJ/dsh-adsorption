#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实测穿透曲线后处理：穿透时间、动态容量、工作容量、产率、纯度、回收率。

输入 CSV 要求：
  - 时间列（默认 time_min，单位 min）
  - 各组分 C/C0 列（0~1，无单位）

参数：
  --time-col TIME_COL       时间列名（默认 time_min）
  --cols COLS               C/C0 列名，逗号分隔，如 CO2_C_C0,N2_C_C0
  --feed-fracs FRACS        进料摩尔分数，逗号分隔，顺序与 --cols 一致
  --flow-ml-min FLOW        进料总流量（STP，mL/min）
  --mass-g MASS             吸附剂质量（g）
  --temp-k TEMP             进料温度（K，默认 298，仅用于报告 C0）
  --feed-pressure-bar P     进料总压（bar，默认 1.0，仅用于报告 C0）
  --desorb-from / --desorb-to  解吸段时间窗（min），用于工作容量与产率
  --bt-frac FRAC            穿透判定分数（默认 0.05）
  --plot PNG                可选：输出曲线图（PNG）
  --out CSV                 清洗后的 processed CSV（默认 穿透_processed.csv）

指标定义（报告时原样引用）：
  穿透时间 t_b      : C/C0 首次达到 bt-frac 的时刻（线性插值）
  动态容量 q_dyn    : (Q*y_i/m) * ∫(1 - C/C0)dt ，mmol/g；积分到饱和点，
                      未完全饱和时输出值即下界（会标注）
  残余量 q_res      : (Q*y_i/m) * ∫_解吸段 (C/C0) dt ，mmol/g
  工作容量 q_work   : q_dyn - q_res ，mmol/g
  周期时间 t_cycle  : 吸附开始(0)到解吸结束(desorb-to)，min
  产率 Productivity : q_work / (t_cycle/60) ，mmol/(g·h)
  纯度 Purity_i     : q_dyn_i / Σ q_dyn_j （吸附相摩尔分数）
  回收率 Recovery_i : q_dyn_i*m / (Q*y_i*t_ads) = ∫(1-C/C0)dt / t_ads
"""
import argparse

import numpy as np
import pandas as pd

R = 8.314462618   # J/(mol*K)
V_STP = 22.414    # L/mol @ 273.15 K, 1 atm


def trapz(y, t):
    """数值积分（numpy 2.x 用 trapezoid，旧版回退 trapz）。"""
    try:
        return float(np.trapezoid(y, t))
    except AttributeError:
        return float(np.trapz(y, t))


def first_hit_time(t, c, frac):
    """C/C0 首次达到 frac 的时刻，线性插值；未达到返回 NaN。"""
    c = np.asarray(c, dtype=float)
    t = np.asarray(t, dtype=float)
    mask = c >= frac
    if not mask.any():
        return float("nan")
    idx = int(np.argmax(mask))
    if idx <= 0:
        return float(t[0])
    t0, t1 = t[idx - 1], t[idx]
    c0, c1 = c[idx - 1], c[idx]
    if c1 <= c0:
        return float(t0)
    return float(t0 + (frac - c0) / (c1 - c0) * (t1 - t0))


def saturation_index(c):
    """首次达到终值 99% 的下标（吸附饱和点）；否则取最后一个点。"""
    c = np.asarray(c, dtype=float)
    target = 0.99 * c[-1]
    mask = c >= target
    return int(np.argmax(mask)) if mask.any() else len(c) - 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("data", help="实测穿透曲线 CSV")
    ap.add_argument("--time-col", default="time_min", help="时间列名（min）")
    ap.add_argument("--cols", required=True, help="C/C0 列名，逗号分隔")
    ap.add_argument("--feed-fracs", help="进料摩尔分数，逗号分隔（与 --cols 同序）")
    ap.add_argument("--flow-ml-min", type=float, help="进料总流量 STP mL/min")
    ap.add_argument("--mass-g", type=float, help="吸附剂质量 g")
    ap.add_argument("--temp-k", type=float, default=298.0, help="进料温度 K（仅报告用）")
    ap.add_argument("--feed-pressure-bar", type=float, default=1.0, help="进料总压 bar（仅报告用）")
    ap.add_argument("--desorb-from", type=float, help="解吸开始时间 min")
    ap.add_argument("--desorb-to", type=float, help="解吸结束时间 min")
    ap.add_argument("--bt-frac", type=float, default=0.05, help="穿透判定分数")
    ap.add_argument("--plot", help="可选 PNG 输出路径")
    ap.add_argument("--out", default="穿透_processed.csv", help="processed CSV 输出")
    args = ap.parse_args()

    # ── 读入与质控 ──
    df = pd.read_csv(args.data)
    cols = [c.strip() for c in args.cols.split(",")]
    if args.time_col not in df.columns:
        raise SystemExit(f"时间列 {args.time_col!r} 不在文件列 {list(df.columns)} 中")
    for c in cols:
        if c not in df.columns:
            raise SystemExit(f"组分列 {c!r} 不在文件列 {list(df.columns)} 中")
    df = df[[args.time_col] + cols].dropna().sort_values(args.time_col).reset_index(drop=True)
    if len(df) < 3:
        raise SystemExit("有效数据点太少（<3），请检查输入文件")
    t = df[args.time_col].to_numpy(dtype=float)   # min
    C = df[cols].to_numpy(dtype=float)            # C/C0
    ncomp = C.shape[1]
    if not np.all(np.diff(t) > 0):
        raise SystemExit("时间列必须严格递增，请检查输入")

    names = cols
    fracs = None
    if args.feed_fracs:
        fracs = [float(x) for x in args.feed_fracs.split(",")]
        if len(fracs) != ncomp:
            raise SystemExit("--feed-fracs 数量与 --cols 数量不一致")
        if abs(sum(fracs) - 1.0) > 1e-6:
            print(f"警告: 进料摩尔分数之和 = {sum(fracs):.4f}，不为 1，纯度/回收率仍按给定值计算")

    Q = None  # mol/min
    if args.flow_ml_min is not None:
        Q = args.flow_ml_min * 1e-3 / V_STP
    m = args.mass_g
    has_capacity = (Q is not None) and (m is not None)

    # ── 穿透时间 ──
    t_b = [first_hit_time(t, C[:, i], args.bt_frac) for i in range(ncomp)]

    # ── 动态容量（积分到各组分自身饱和点）──
    q_dyn = [float("nan")] * ncomp
    sat_idx = [saturation_index(C[:, i]) for i in range(ncomp)]
    saturated = [bool(C[sat_idx[i], i] >= 0.97 * C[-1, i]) for i in range(ncomp)]
    if has_capacity:
        for i in range(ncomp):
            idx = sat_idx[i]
            integral = trapz(1.0 - C[: idx + 1, i], t[: idx + 1])   # min
            q_dyn[i] = (Q * (fracs[i] if fracs else 1.0) / m) * integral * 1000.0  # mmol/g

    # ── 解吸段：残余量、工作容量、周期、产率 ──
    q_res = [float("nan")] * ncomp
    q_work = [float("nan")] * ncomp
    prod = [float("nan")] * ncomp
    t_cycle = float("nan")
    if args.desorb_from is not None and args.desorb_to is not None:
        mask = (t >= args.desorb_from) & (t <= args.desorb_to)
        if mask.sum() < 2:
            print("警告: 解吸时间窗内数据点不足（<2），跳过工作容量计算")
        else:
            t_cycle = args.desorb_to  # 吸附从 0 开始
            if has_capacity:
                for i in range(ncomp):
                    integral = trapz(C[mask, i], t[mask])          # min
                    q_res[i] = (Q * (fracs[i] if fracs else 1.0) / m) * integral * 1000.0
                    q_work[i] = q_dyn[i] - q_res[i]
                    prod[i] = q_work[i] / (t_cycle / 60.0)          # mmol/(g·h)
            print("注意: 解吸段按进料流量 Q 与组成 y 计算残余量；")
            print("      若解吸用不同吹扫气流量/组成，需调整计算（请注明）。")
            if has_capacity and any((not np.isnan(w)) and w < 0 for w in q_work):
                print("警告: 存在负工作容量 → 解吸窗内 C/C0 未下降或窗口选取有误，请检查 --desorb-from/--desorb-to")

    # ── 纯度与回收率 ──
    purity = [float("nan")] * ncomp
    recovery = [float("nan")] * ncomp
    if has_capacity and fracs:
        total = sum(q for q in q_dyn if not np.isnan(q))
        if total > 0:
            purity = [q_dyn[i] / total for i in range(ncomp)]
        for i in range(ncomp):
            idx = sat_idx[i]
            t_ads = t[idx]  # min，吸附段时间
            if t_ads > 0:
                fed_per_mass = (Q * fracs[i] / m) * t_ads * 1000.0  # mmol/g 进料
                recovery[i] = q_dyn[i] / fed_per_mass if fed_per_mass > 0 else float("nan")

    # ── processed CSV ──
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"processed CSV 已写出: {args.out}\n")

    # ── 汇总报告 ──
    print("=" * 64)
    print("穿透曲线后处理结果")
    print("=" * 64)
    print(f"输入: {args.data}  数据点数: {len(df)}")
    print(f"判定分数: C/C0 = {args.bt_frac:.3f}")
    if Q is not None:
        print(f"进料总摩尔流量 Q = {Q:.6f} mol/min（{args.flow_ml_min} mL/min @ STP）")
    if fracs:
        print(f"进料组成 y = {['%.3f' % f for f in fracs]}")
    if m is not None:
        print(f"吸附剂质量 m = {m:.4f} g")
    print(f"C0 参考值（T={args.temp_k} K, P={args.feed_pressure_bar} bar）: "
          f"{args.feed_pressure_bar * 1e5 / (R * args.temp_k) * 1000:.3f} mol/m^3")
    print()
    for i in range(ncomp):
        print(f"[{names[i]}]")
        print(f"  穿透时间 t_b (C/C0={args.bt_frac:.2f}): "
              f"{t_b[i]:.3f} min" if not np.isnan(t_b[i]) else "  穿透时间: 未达到判定分数")
        if has_capacity:
            flag = "" if saturated[i] else "（未完全饱和 → 下界值）"
            print(f"  动态容量 q_dyn: {q_dyn[i]:.4f} mmol/g {flag}")
        if not np.isnan(q_work[i]):
            print(f"  解吸残余 q_res: {q_res[i]:.4f} mmol/g")
            print(f"  工作容量 q_work: {q_work[i]:.4f} mmol/g")
            print(f"  产率: {prod[i]:.4f} mmol/(g·h)  (t_cycle = {t_cycle:.1f} min)")
        if not np.isnan(purity[i]):
            print(f"  吸附相纯度: {purity[i] * 100:.2f} %")
            print(f"  回收率: {recovery[i] * 100:.2f} %")
        print()
    if not has_capacity:
        print("提示: 未提供 --flow-ml-min 与 --mass-g，仅计算了穿透时间；")
        print("      补充流量与质量参数后可得到动态容量/产率等指标。")

    # ── 可选绘图 ──
    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.2, 4.6))
        for i in range(ncomp):
            ax.plot(t, C[:, i], label=names[i])
            if not np.isnan(t_b[i]):
                ax.axvline(t_b[i], ls="--", lw=1, alpha=0.6)
        ax.set_xlabel("time (min)")
        ax.set_ylabel("C / C$_0$")
        ax.legend()
        fig.tight_layout()
        fig.savefig(args.plot, dpi=300)
        print(f"图已写出: {args.plot}")


if __name__ == "__main__":
    main()

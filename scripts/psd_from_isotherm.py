#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
孔径分布（PSD）与比表面积计算：NLDFT/QSDFT kernel（pyGAPS psd_dft）+ HK 微孔 + BJH 介孔。

用法示例：
  # NLDFT（内置 kernel 或自定义 kernel 路径；kernel 目录: 本 skill 的 kernels/ 或 Micromeritics 转换产物）
  psd_from_isotherm.py standard_N2_77K.csv --temp-k 77 --adsorbate N2 \
      --kernel DFT-N2-77K-carbon-slit --out-dir psd_results

  # 自定义 kernel（本 skill kernels/ 目录内置 48 个，按文件名直接用；见 SKILL.md 工作流 G 的库清单）
  psd_from_isotherm.py standard_Ar_87K.csv --temp-k 87 --adsorbate Ar \
      --kernel NLDFT-mod203.csv --out-dir psd_results
  psd_from_isotherm.py standard_CO2_273K.csv --temp-k 273 --adsorbate CO2 \
      --kernel NLDFT-mod400.csv --out-dir psd_results

  # 附加 HK 微孔与 BJH 介孔
  psd_from_isotherm.py standard_N2_77K.csv --temp-k 77 --adsorbate N2 \
      --hk --bjh --out-dir psd_results

输入（标准格式 CSV，见 gas-adsorption skill）：P_bar, n_mmol_g [, T_K]
输出（三件套规范）：processed CSV（微分/累积 PSD）+ PNG 图 + 报告由主流程汇总。
"""
import argparse
import pathlib

import numpy as np
import pandas as pd

import pygaps
from pygaps.characterisation import psd_dft, psd_microporous, psd_mesoporous, t_plot, area_langmuir

# 内置 kernel 名（pyGAPS 自带）
BUILTIN_KERNELS = ["DFT-N2-77K-carbon-slit"]
# 本 skill 自带 kernel 目录（转换好的自定义 kernel 放这里，脚本自动搜索）
DEFAULT_KERNEL_DIR = pathlib.Path(__file__).parent.parent / "kernels"
# 常用饱和蒸气压默认值（bar）——P0 不匹配会让 DFT 压力范围错位，不确定时必须显式给 --p0-bar
DEFAULT_P0_BAR = {("N2", 77.0): 1.0, ("Ar", 87.0): 1.0, ("CO2", 273.0): 34.85}


def load_iso(path, temp_k, adsorbate, pressure_mode, p0_bar):
    df = pd.read_csv(path)
    if not {"P_bar", "n_mmol_g"} <= set(df.columns):
        raise SystemExit(f"输入必须是标准格式（P_bar, n_mmol_g[, T_K]），实际列: {list(df.columns)}")
    df = df.dropna().sort_values("P_bar")
    T = float(df["T_K"].iloc[0]) if "T_K" in df.columns else temp_k
    P = df["P_bar"].to_numpy()
    if pressure_mode == "absolute":
        if p0_bar is None:
            p0_bar = DEFAULT_P0_BAR.get((adsorbate, round(T)))
            if p0_bar is None:
                raise SystemExit(
                    f"未知 P0({adsorbate}, {T}K)，必须显式给 --p0-bar（饱和蒸气压 bar）"
                )
        if np.any(P / p0_bar > 1.05):
            print(f"警告: 部分点 P/P0 > 1.05（P0={p0_bar} bar），DFT kernel 会超出范围")
        P = P / p0_bar
        mode = "relative"
        print(f"绝对压力已换算为相对压力: P/P0，P0 = {p0_bar} bar（{adsorbate}, {T} K）")
    else:
        mode = "relative"
    return pygaps.PointIsotherm(
        pressure=P, loading=df["n_mmol_g"].to_numpy(),
        material=pathlib.Path(path).stem, adsorbate=adsorbate, temperature=T,
        pressure_mode=mode, loading_unit="mmol",
    ), df, T


def resolve_kernel(name_or_path):
    if name_or_path in BUILTIN_KERNELS:
        return name_or_path
    p = pathlib.Path(name_or_path)
    if p.is_file():
        return str(p)
    cand = DEFAULT_KERNEL_DIR / name_or_path
    if cand.is_file():
        return str(cand)
    raise SystemExit(f"kernel 未找到: {name_or_path}（内置: {BUILTIN_KERNELS}；自定义放 {DEFAULT_KERNEL_DIR} 或给完整路径）")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data", help="标准格式等温线 CSV（P_bar, n_mmol_g）")
    ap.add_argument("--temp-k", type=float, required=True, help="温度 K（文件无 T_K 列时必填）")
    ap.add_argument("--adsorbate", default="N2", help="吸附质（N2/Ar/CO2…），用于 pyGAPS 物性")
    ap.add_argument("--pressure-mode", default="absolute", choices=["absolute", "relative"],
                    help="输入压力模式；absolute 时按 P0 换算为相对压力")
    ap.add_argument("--p0-bar", type=float,
                    help="饱和蒸气压 bar（默认: N2 77K=1.0, Ar 87K=1.0, CO2 273K=34.85；其他必须显式给出）")
    ap.add_argument("--kernel", default="DFT-N2-77K-carbon-slit", help="kernel 名或 CSV 路径")
    ap.add_argument("--branch", default="ads", choices=["ads", "des"])
    ap.add_argument("--p-limits", nargs=2, type=float, help="PSD 压力范围（相对压力）")
    ap.add_argument("--bspline-order", type=int, default=2, help="bspline 平滑阶数（0=原始数据）")
    ap.add_argument("--hk", action="store_true", help="附加 HK 微孔 PSD")
    ap.add_argument("--bjh", action="store_true", help="附加 BJH 介孔 PSD（脱附支需 des 数据）")
    ap.add_argument("--t-plot", action="store_true", help="附加 t-plot 外比表面积")
    ap.add_argument("--out-dir", default="psd_results", help="输出目录")
    args = ap.parse_args()

    iso, df, T = load_iso(args.data, args.temp_k, args.adsorbate, args.pressure_mode, args.p0_bar)
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = pathlib.Path(args.data).stem

    summary = []

    # ── NLDFT/QSDFT ──
    kernel = resolve_kernel(args.kernel)
    kw = {}
    if args.p_limits:
        kw["p_limits"] = tuple(args.p_limits)
    psd = psd_dft(iso, kernel=kernel, branch=args.branch, bspline_order=args.bspline_order, **kw)
    w, d, cum = psd["pore_widths"], psd["pore_distribution"], psd["pore_volume_cumulative"]
    psd_df = pd.DataFrame({
        "pore_width_nm": w,
        "dV_dw_cm3_g_nm": d,
        "cumulative_volume_cm3_g": cum,
    })
    psd_csv = out / f"{stem}_psd_nldft.csv"
    psd_df.to_csv(psd_csv, index=False)
    ipeak = int(np.argmax(d))
    summary.append(f"NLDFT({pathlib.Path(kernel).name}): 峰位 {w[ipeak]:.2f} nm, 累积孔容 {cum[-1]:.4f} cm3/g")

    # ── 附加方法 ──
    if args.hk:
        hk = psd_microporous(iso, psd_model="HK", pore_geometry="slit", branch=args.branch)
        pd.DataFrame({
            "pore_width_nm": hk["pore_widths"],
            "dV_dw_cm3_g_nm": hk["pore_distribution"],
            "cumulative_volume_cm3_g": hk["pore_volume_cumulative"],
        }).to_csv(out / f"{stem}_psd_hk.csv", index=False)
        ipeak = int(np.argmax(hk["pore_distribution"]))
        summary.append(f"HK 微孔: 峰位 {hk['pore_widths'][ipeak]:.2f} nm, 累积孔容 {hk['pore_volume_cumulative'][-1]:.4f} cm3/g")
    if args.bjh:
        bjh = psd_mesoporous(iso, psd_model="BJH", pore_geometry="cylinder", branch=args.branch)
        pd.DataFrame({
            "pore_width_nm": bjh["pore_widths"],
            "dV_dw_cm3_g_nm": bjh["pore_distribution"],
            "cumulative_volume_cm3_g": bjh["pore_volume_cumulative"],
        }).to_csv(out / f"{stem}_psd_bjh.csv", index=False)
        summary.append(f"BJH 介孔: 累积孔容 {bjh['pore_volume_cumulative'][-1]:.4f} cm3/g, 总面积 {bjh.get('pore_area_total', float('nan')):.1f} m2/g")
    if args.t_plot:
        tp = t_plot(iso, branch=args.branch)
        results = tp["results"]
        # pyGAPS 4.6: results 是区段列表（每区段一个 dict），取相关系数最高的区段
        if results:
            res = max((r for r in results if isinstance(r, dict)), key=lambda r: r.get("corr_coef", -1))
            ext_area = res.get("external_area", float("nan"))
            micro_v = res.get("microporous_volume", float("nan"))
            summary.append(f"t-plot: 外比表面积 {ext_area:.1f} m2/g, 微孔体积 {micro_v:.4f} cm3/g, "
                           f"r={res.get('corr_coef', float('nan')):.4f}")
        else:
            summary.append("t-plot: 未找到线性区段（数据可能不适合 t-plot）")

    # ── 图（PNG 仅此格式交付）──
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.plot(w, d, lw=1.8)
    ax.set_xscale("log")
    ax.set_xlabel("pore width (nm)")
    ax.set_ylabel("dV/dw (cm$^3$/g/nm)")
    ax.set_title(f"{stem} — NLDFT PSD ({pathlib.Path(kernel).name})")
    ax.grid(True, which="both", ls=":", alpha=0.4)
    fig.tight_layout()
    fig_path = out / f"{stem}_psd.png"
    fig.savefig(fig_path, dpi=300)

    print("=" * 60)
    print(f"输入: {args.data}  (T = {T:.1f} K, {args.adsorbate})")
    for s in summary:
        print(" •", s)
    print(f"processed CSV: {psd_csv}")
    print(f"图: {fig_path}")


if __name__ == "__main__":
    main()

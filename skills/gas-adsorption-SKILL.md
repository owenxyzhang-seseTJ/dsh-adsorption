---
name: gas-adsorption
description: 气体吸附数据计算工作流：纯组分等温线拟合（Langmuir/DSLF 等，pyIAST）、IAST 混合吸附预测与选择性、BET 比表面积（pyGAPS，含 Rouquerol 判据）、等量吸附热 Qst（Clausius–Clapeyron）、穿透曲线模拟（RUPTURA）与实测穿透曲线后处理（穿透时间/动态容量/工作容量/产率/纯度/回收率）。处理吸附等温线、穿透曲线数据或需要上述任何计算时使用。
---

# 气体吸附数据计算

## 计算栈（本机固定路径，直接使用，勿另建环境）

- Python：`"$DSH_ADSORPTION_PYTHON"（缺省自动探测 $HOME 下 miniforge3/anaconda3/miniconda3 的 envs/pyiast-env）`
  - pyiast 1.4.3（IAST / 等温线模型拟合）
  - pygaps 4.6.1（BET / Qst / 等温线处理，函数在 `pygaps.characterisation`）
  - ruptura 1.0.4（穿透曲线模拟）
  - numpy / scipy / pandas / matplotlib / openpyxl / CoolProp
- 运行：`"$DSH_ADSORPTION_PYTHON"（缺省自动探测 $HOME 下 miniforge3/anaconda3/miniconda3 的 envs/pyiast-env） script.py` 或 heredoc；**不要**用系统 `python3`（base 环境没有这些包）。
- GCMC 模拟另见 `raspa3-gcmc` skill。

## 输入数据约定

**铁律：任何计算前，先把输入数据转换为标准格式（步骤 0）。** 标准格式统一为：

- 等温线：UTF-8 CSV，表头 `P_bar,n_mmol_g[,T_K]`（压力 bar、吸附量 mmol/g、可选温度 K；多温度等温线一文件三列）
- 穿透曲线：UTF-8 CSV，表头 `time_min,<组分>_C_C0,...`（时间 min、各组分出口 C/C0，0~1）

原始数据（Excel/仪器导出/任意列名单位）先经本 skill 自带脚本转换：

```bash
<SAMPLE_DIR>/standardize_isotherm.py raw.xlsx --sheet 0 \
    --pressure-col "P (Torr)" --pressure-unit torr \
    --loading-col "n (cc/g)" --loading-unit cm3stp_g \
    --temp-k 298 --out CO2_298K.csv
```

支持压力单位 bar/pa/kpa/mpa/torr/mmhg/atm/mbar/psi；吸附量单位 mmol_g/mol_g/mol_kg/cm3stp_g/cc_g/cm3_g/ml_g/mg_g（mg_g 需 `--molar-mass-g-mol`）。转换后按 P 升序排序并质控提示。

常用换算（手算/检查用）：cm³(STP)/g → mmol/g 乘 1000/22.414 = 44.615；mg/g → mmol/g 除以摩尔质量再乘 1000；bar → Pa 乘 1e5。

## 通用流程

0. **格式标准化（强制）**：所有输入 → 标准 CSV（见上），列含义/单位/温度无歧义；原始文件保留不改动。
1. 清点输入：文件、列含义、单位、温度、吸附质 → 有歧义用 ask_user_question 确认。
2. 质控：剔除负吸附点/明显离群点（**记录剔除理由**，写进报告）；压力 0 点按模型需要保留或剔除。
3. 按下方工作流 A–F 计算。
4. 按「交付规范」产出三件套。

## 工作流 A：纯组分等温线拟合（pyIAST）

```python
import pandas as pd
import numpy as np
import pyiast
df = pd.read_csv("CO2_298K.csv")              # 含 pressure / loading 两列（或自定列名）
iso = pyiast.ModelIsotherm(df, pressure_key="pressure", loading_key="loading",
                           model="DSLangmuir", param_guess={"M1": 5.0, "K1": 1e-5, "M2": 5.0, "K2": 1e-3})
iso.print_params()                             # 参数与不确定度
fit = iso.loading(df["pressure"].to_numpy())   # 拟合值 → 手算 RMSE/R²（1.4.3 无 goodness_of_fit）
rmse = float(np.sqrt(np.mean((fit - df["loading"].to_numpy()) ** 2)))
```
- 模型与参数（1.4.3 全部）：`Langmuir`(M,K: q=M·ln(1+K·P)，**对数形式**，非物理双曲 Langmuir)、`DSLangmuir`(M1,K1,M2,K2: 双位点，最常用)、`Quadratic`(M,Ka,Kb)、`BET`(M,Ka,Kb)、`Henry`(KH)、`TemkinApprox`(M,K,theta)。
- 标准双曲 Langmuir（q=qsat·b·P/(1+b·P)）数据用 `Langmuir` 拟合会失真，用 `DSLangmuir` 或自行拟合后走 Interpolator 路径。
- **全流程统一用 bar（标准 CSV 的 P_bar 直接喂入）**：K 参数 O(1) 数值稳定；pyIAST 不强制单位，只要拟合与 IAST 全链路一致即可。若坚持用 Pa，所有 K 相应 ×1e-5。
- **拟合后必须检查参数合理性**（K、Ka、Kb、KH > 0；M > 0）：Nelder-Mead 可能陷入坏极小（负 K 等），异常时给 `param_guess` 重拟或换模型；4 参数 DSLangmuir 用 pyIAST 内置 Nelder-Mead 经常收敛失败 → 用下方 scipy least_squares 模式（推荐）。
- 拟合后产出对比 CSV（P, n_exp, n_fit）与参数表（含不确定度、RMSE/R²）。

**推荐：scipy least_squares 拟合 DSLF（带界约束，收敛可靠）**：

```python
from scipy.optimize import least_squares
def dslf(P, M1, K1, M2, K2): return M1*np.log(1+K1*P) + M2*np.log(1+K2*P)
res = least_squares(lambda th: dslf(P_bar, *th) - n, x0=[5.0, 1.0, 2.0, 100.0],
                    bounds=([0, 1e-6, 0, 1e-6], [100, 1e6, 100, 1e6]))
M1, K1, M2, K2 = res.x          # 检查 res.success 与 res.cost
```
- 拟合参数（bar 单位制）可直接用于工作流 B 的解析 IAST 求解器。

## 工作流 B：IAST 混合吸附与选择性

**主路径：解析铺展压力 + 二分求根（稳健，推荐）**。对 q = Σ M_i·ln(1+K_i·P) 类模型（Langmuir/DSLangmuir 及 scipy 拟合结果），铺展压力有解析式：

`Ψ(P) = −Σ M_i·spence(1 + K_i·P)`，其中 `spence` 是 scipy 的二重对数 `scipy.special.spence`（= Li₂(1−z)，注意负号）。

```python
import numpy as np
from scipy.special import spence
from scipy.optimize import brentq

def psi(P, Ms, Ks):                          # 约化铺展压力（bar 单位制，已验证）
    return float(-sum(M * spence(1.0 + K * P) for M, K in zip(Ms, Ks)))

def q(P, Ms, Ks):                            # 吸附量 q = Σ M·ln(1+K·P)
    return float(sum(M * np.log(1.0 + K * P) for M, K in zip(Ms, Ks)))

def iast_binary(p1, p2, iso1, iso2):         # iso = (Ms, Ks)；分压 bar
    def f(x1): return psi(p1/x1, *iso1) - psi(p2/(1.0-x1), *iso2)
    x1 = brentq(f, 1e-9, 1.0-1e-9, xtol=1e-12)
    x2 = 1.0 - x1
    return q(p1/x1, *iso1), q(p2/x2, *iso2), x1, x2

# 1 bar 总压，y = (0.15, 0.85)
n1, n2, x1, x2 = iast_binary(0.15, 0.85, ([8.0,2.0],[3.0,300.0]), ([2.0],[0.5]))
S = (x1/0.15) / (x2/0.85)                    # IAST 选择性 (x1/y1)/(x2/y2)
```
- 全流程用 **bar 单位制**（拟合与 IAST 一致即可；K 参数 O(1) 数值更稳）。单位一致性比单位本身重要。
- 扫多个总压点得 S–P 曲线；变组成得 S–y 曲线。
- 交付：`iast_选择性_vs_压力.csv`（P, S, x1, x2, n1, n2）+ 图。

**备选路径：pyIAST 自带 iast（简单模型可用，DSLF 强位点可能不收敛）**：

```python
iso1 = pyiast.ModelIsotherm(df1, pressure_key="pressure", loading_key="loading", model="Langmuir")
iso2 = pyiast.ModelIsotherm(df2, pressure_key="pressure", loading_key="loading", model="Langmuir")
n1, n2 = pyiast.iast([0.15, 0.85], [iso1, iso2], warningoff=False,
                     adsorbed_mole_fraction_guess=[0.15, 0.85])
```
- `iast(partial_pressures, isotherms, ...)`：分压在**前**（1.4.3 参数顺序）。
- 报错 "Root finding ... failed" / "Adsorbed mole fraction not in [0,1]" → 换主路径（解析求解器）。
- 模型等温线也可转 `pyiast.InterpolatorIsotherm(df, pressure_key=..., loading_key=...)`（需显式给列名）后再 iast，但同样受其 lm 求解器稳定性限制。
- 扫多个总压点得 S–P 曲线；也可变组成做 S–y 图。
- 交付：`iast_选择性_vs_压力.csv`（P, S, x1, x2, n1, n2）+ 图。

## 工作流 C：BET 比表面积（pyGAPS）

```python
import pygaps
iso = pygaps.PointIsotherm(pressure=P, loading=n, material="MOF", adsorbate="N2",
                           temperature=77.0, pressure_mode="absolute",
                           pressure_unit="bar", loading_unit="mmol")
bet = pygaps.characterisation.area_BET(iso, branch="ads", p_limits=(0.01, 0.30))
print(bet["area"], bet["C"], bet["corr_coef"], bet["n_monolayer"])
```
- **必须报告判据，不能只报数字**：Rouquerol 判据（选点区间内 n(1−P/P0) 随 P/P0 单调递增）、相关系数 ≥ 0.999、C > 0。
- N₂ 77K 分子截面积 0.162 nm²；常规区间 (0.05, 0.30)，微孔材料常收窄到 (0.005, 0.05) 并注明理由。
- 交付：`BET_数据.csv`（P/P0、1/(n(1−P/P0))、拟合段标记）+ 参数表 + 图。

## 工作流 D：等量吸附热 Qst（pyGAPS）

```python
isos = [pygaps.PointIsotherm(pressure=..., loading=..., temperature=T, ...) for T in (298, 313, 333)]
qst = pygaps.characterisation.enthalpy_sorption_clapeyron(
    isos, loading_points=[1, 2, 5], branch="ads")
```
- Clausius–Clapeyron：对每个固定吸附量，lnP 对 1/T 线性拟合，Qst = −R·斜率（kJ/mol）。
- 至少 3 条温度等温线；同吸附量点可用拟合模型插值。
- 交付：`Qst_vs_loading.csv`（n, Qst, 不确定度）+ 图。

## 工作流 E：穿透曲线模拟（RUPTURA）

```python
from ruptura.ruptura import Components, Breakthrough
components = Components([
    {"MoleculeName": "CO2", "GasPhaseMolFraction": 0.15,
     "isotherms": [["Langmuir", qsat, b]],          # q = qsat*b*P/(1+b*P)，SI 单位
     "MassTransferCoefficient": 0.1, "AxialDispersionCoefficient": 1e-6, "CarrierGas": False},
    {"MoleculeName": "N2", "GasPhaseMolFraction": 0.85,
     "isotherms": [["Langmuir", qsat2, b2]], "CarrierGas": True},
])
bt = Breakthrough(components=components, DisplayName="CO2/N2",
                  Temperature=298.0, TotalPressure=1e5, ColumnLength=0.5,
                  ColumnVoidFraction=0.4, ParticleDensity=1000.0,
                  NumberOfTimeSteps="auto", TimeStep=0.05,
                  MixturePredictionMethod="IAST")
data = bt.compute()                 # shape (Nt, Ngrid, 8 + 6*Ncomp)
t_min = data[:, -1, 1]              # 出口时间 (min)
c_c0_i = data[:, -1, 8 + 6*i]       # 组分 i 的出口 C/C0
```
- **RUPTURA 用 SI 单位**：压力 Pa、吸附量 mol/kg（1 mmol/g = 1 mol/kg，数值相同）。
- **模型形式不同**：RUPTURA 的 `Langmuir` 是物理双曲形式 q=q_sat·b·P/(1+b·P)，与 pyIAST 的对数形式不一样；等温线参数要按 RUPTURA 的模型形式**单独拟合**（scipy least_squares，P 用 Pa）再喂入，不能直接复用 pyIAST 参数。可用模型名见 `ruptura.ruptura.isothermMeta`（Langmuir/BET/Henry/Freundlich/Sips/Langmuir-Freundlich/Toth/Quadratic/Temkin 等）。
- 从 bar 制拟合参数换算：q_sat 数值不变；b_Pa = K_bar × 1e-5（仅对同函数形式成立）。
- `MixturePredictionMethod`：`IAST` / `SIAST` / `EI` / `SEI`。
- 时间步太大发散 → 减小 `TimeStep`；用 `PulseTime` 做脉冲进样。
- 交付：`穿透模拟_<条件>.csv`（time_min + 各组分 C/C0）+ 图。

## 工作流 F：实测穿透曲线后处理（产率等）

使用本 skill 自带脚本（路径以运行时解析的 skill 目录为准）：

```bash
<SAMPLE_DIR>/breakthrough_productivity.py 实测穿透.csv \
    --time-col time_min --cols CO2_C_C0,N2_C_C0 \
    --feed-fracs 0.15,0.85 --flow-ml-min 20 --mass-g 0.5 \
    --temp-k 298 --feed-pressure-bar 1.0 \
    --desorb-from 80 --desorb-to 140 --plot 穿透分析.png
```

指标定义（全部写入报告）：
- 穿透时间 t_b：C/C0 首次达到 `--bt-frac`（默认 0.05）的时刻，线性插值。
- 动态容量 q_dyn = (Q_feed·y_i/m)·∫(1 − C/C0)dt，单位 mmol/g；未完全饱和时注明为下界。
- 工作容量 q_work：吸附段动态容量 − 解吸段残余量（残余量 = (Q_feed·y_i/m)·∫_解吸 C/C0 dt）。
- 产率 Productivity = q_work / t_cycle（mmol/(g·h)，t_cycle 为吸附+解吸周期时长）；无解吸窗时用 q_dyn/t_b 近似并注明。
- 纯度（吸附相组成）与回收率：二元进料按各组分积分量给出。
- 输出 processed CSV（t, 各 C/C0）与 `--plot` PNG（可选）。

## 工作流 G：比表面积与孔径分布（BET/t-plot/HK/BJH/NLDFT）

本 skill 自带脚本一键完成 NLDFT + HK + BJH + t-plot：

```bash
<SAMPLE_DIR>/psd_from_isotherm.py standard_N2_77K.csv --temp-k 77 --adsorbate N2 \
    --kernel DFT-N2-77K-carbon-slit --hk --bjh --t-plot --out-dir psd_results
```

输出：`*_psd_nldft.csv`（孔径/微分 dV/dw/累积孔容）、`*_psd_hk.csv`、`*_psd_bjh.csv`、`*_psd.png`。

**关键点（写进报告）：**
- **压力换算**：DFT kernel 的轴是**相对压力 P/P0**。标准 CSV 的 P_bar 是绝对压力，脚本按 P0 换算（默认 N2 77K=1.0、Ar 87K=1.0、CO2 273K=34.85 bar；不确定时必须显式 `--p0-bar`）。换算与 P0 来源写进报告。
- **比表面积多方法互证**：BET（工作流 C，Rouquerol 判据）、Langmuir 面积、t-plot 外比表面积、DR/DA 微孔体积。
- **NLDFT/QSDFT kernel 选择四要素**：吸附质（N2/Ar/CO2/O2…）+ 温度（77/87/273 K）+ 孔型（slit/cylinder/sphere）+ 表面化学（carbon/oxide/zeolite/MOF）必须与样品匹配，不匹配的 kernel 结果不可发表。
- **kernel 库（本 skill `kernels/` 目录，48 个，全部经 pyGAPS psd_dft 验证）**：
  - **N2 @ 77K**：`N2-77K-carbon-slit-NLDFT-mod200.csv`（carbon slit，首选）、`2D-NLDFT-mod201/202/206.csv`（carbon 有限 slit，Aspect=4/6/12）、`N2-77K-carbon-HS-2D-NLDFT-mod255.csv`（carbon 异质表面 HS-2D-NLDFT）、`NLDFT-mod225/226.csv`（carbon 圆柱 SWNT/MWNT）、`N2-77K-carbon-ZTC-cylinder-2D-NLDFT-mod440.csv`（ZTC 圆柱）、`N2-77K-carbon-cylinder-meso-2D-NLDFT-mod450.csv`（carbon 圆柱介孔）、`NLDFT-mod010/013.csv`（oxide 圆柱，强势/Tarazona）、`N2-77K-clay-cylinder-NLDFT-mod014.csv`（柱撑黏土圆柱）
  - **Ar @ 87K**：`Ar-87K-carbon-slit-NLDFT-mod203.csv`（carbon slit，首选）、`2D-NLDFT-mod204/205/207.csv`（carbon 有限 slit As=4/6/12）、`Ar-87K-carbon-HS-2D-NLDFT-mod420.csv`（carbon 异质表面）、`NLDFT-mod227/228.csv`（carbon 圆柱 SWNT/MWNT）、`Ar-87K-oxide-cylinder-NLDFT-mod015.csv`（oxide 圆柱）、`NLDFT-mod251/252.csv`（zeolite H/Me 型）、`Ar-87K-oxide-cylinder-HS-2D-NLDFT-mod610.csv`（oxide 圆柱 HS-2D）
  - **CO2 @ 273K**：`CO2-273K-carbon-slit-NLDFT-mod400.csv`（carbon slit，首选，P/P0 ≤ 0.3）、`CO2-273K-carbon-HS-2D-NLDFT-mod425.csv`（carbon 异质表面）、`CO2-273K-carbon-slit-10atm-NLDFT-mod250.csv`（carbon slit 10 atm）、`CO2-273K-carbon-slit-GCMC-mod241.csv`（GCMC 碳 slit，仅微孔 0.32–1.5 nm，噪声大）、`CO2-273K-carbon-slit-DFT-mod011.csv`（原始 DFT，**P/P0 ≤ 0.039**，仅超微孔段）
  - 来源：Micromeritics DFT 模型库（Jagiello & Olivier 系）逆向转换，原包与转换脚本在 `~/Documents/单晶/plugin/kernels-package/`（`output/manifest.json` 有每个 kernel 的维度/范围/单调性）。值单位 mmol/g（按孔容类归一，饱和≈液态密度），压力轴为相对压力。
  - 注意：`N2-77K-carbon-HS-2D-NLDFT-mod255.csv` 原始文件含重复压力行，已修复（重复行取均值）；`NLDFT-mod225/226/227/228` 压力轴到 1.05。
  - 用法：`--kernel Ar-87K-carbon-slit-NLDFT-mod203.csv`（脚本自动在 `kernels/` 目录查找）。
  - **CIF 不能直接生成 DFT kernel**：kernel 是预计算的 DFT/GCMC 数据表，pyGAPS 只消费不生产；CIF 的作用是判断孔型/化学以选 kernel。无现成 kernel 时：① 联网搜索已发表 kernel 数据表（Jagiello & Olivier 2D-NLDFT 论文 SI，如 Carbon 91 (2015) 330–337；Carbon 144 (2019) 206–215）；② 仪器软件（MicroActive/BELSORP）导出；③ RASPA3 GCMC 在模型孔（slit/cyl）中自算「模拟 kernel」（研究级路线）。
- 交付：三件套（processed CSV + PNG + md 报告），报告中必须给出 kernel 名称/来源、P0 与换算、压力范围、孔径范围与判据。

## 交付规范（三件套，每项计算任务都适用）

1. **processed CSV**：可直接画图的干净数据——表头带单位、UTF-8、无多余元数据行。
2. **PNG 图（仅 PNG）**：绘图遵循 `scientific-figure-team` skill（用户以 /scientific-figure-team 调用）：raw-data 门 → 方法检索 → 英文 pre-plot 计划经用户确认 → matplotlib 绘制（影响视觉的代码行中文注释）→ `validate_python_comments.py` 校验 → QA → 成品渲染检查。不交付 SVG/PDF。
3. **分析报告**：md 或 txt，含输入清单、方法、参数与不确定度、拟合优度/判据、结论。**不允许只给图不给数。**

## 引用规范

报告末尾给出所用软件引用：
- pyIAST: Simon, C. M., Smit, B., Haranczyk, M. *Comput. Phys. Commun.* **200**, 364–380 (2016). https://github.com/CorySimon/pyIAST
- pyGAPS: Iacomi, P., Llewellyn, P. L. *Adsorption* **25**, 1533–1542 (2019). https://github.com/pauliacomi/pyGAPS
- RUPTURA: Sharma, S. et al. *Mol. Simul.* **49**, 893–953 (2023). https://github.com/iRASPA/RUPTURA
- RASPA3: Dubbeldam, D., Calero, S., Vlugt, T. J. H. *J. Chem. Phys.* **161**, 062501 (2024). https://github.com/iRASPA/RASPA3

## 常见陷阱

- 单位混乱：pyIAST 用 Pa+mmol/g；pyGAPS 建等温线要显式声明单位；RUPTURA 总压 Pa；RASPA3 用 K/Å/kJ/mol。
- BET 误用：微孔材料直接套 0.05–0.30 失真；必须报 Rouquerol 判据。
- IAST 理想假设：强吸附质/高负载可能偏离，必要时与 GCMC 对比。
- 拟合：多参数模型给初值；fit 前剔除异常点并记录。
- 穿透模拟：TimeStep 过大发散；`NumberOfTimeSteps="auto"` 时按柱长/流速估总时长。
- 负吸附点/漏气段：质控删除并记录理由，不静默修改。

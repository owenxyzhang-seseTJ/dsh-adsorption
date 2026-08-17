# dsh-adsorption

气体吸附数据计算工作台 —— DSH 持久宿主插件（注册 `adsorption` 工具，10 个动作）。

基于 pyIAST / pyGAPS / RUPTURA / RASPA3 的完整吸附计算管线：
**等温线拟合 → IAST 混合吸附与选择性 → BET → Qst → NLDFT 孔径分布 → 穿透曲线模拟/实测产率**。

## 安装

```bash
# 1. 安装到 DSH 本地插件目录（NODE_PATH 可见）
cp -R dsh-adsorption ~/.dsh/profiles/node_modules/

# 2. 在 agent 预设（~/.dsh/.agent-presets/<id>/agent.cordis.yml）加一行：
#    - id: adsorption-plugin
#      name: 'dsh-adsorption'
```

依赖（固定路径，本机已验证）：
- Python 3.12 环境 `~/.dsh/profiles/../miniforge3/envs/pyiast-env/`（pyiast 1.4.3 / pygaps 4.6.1 / ruptura 1.0.4 / scipy / numpy / pandas / matplotlib / openpyxl / CoolProp）
- RASPA3 3.1.0（arm64）：`~/.tclaw/runtimes/raspa3-macos/bin/raspa3`

## 动作一览

| action | 说明 |
|---|---|
| `env` | 检查计算环境（Python 包 + RASPA3 二进制） |
| `guide` | 获取工作流判据（stage: data/fit/iast/bet/qst/psd/breakthrough/productivity/raspa3/guardrails） |
| `standardize` | 任意仪器格式 → 标准 CSV（`P_bar,n_mmol_g`；支持 torr/pa/kpa/mpa/bar/atm/mbar/psi × mmol_g/mol_g/mol_kg/cm3stp_g/cc_g/mg_g） |
| `fit` | 等温线拟合（DSLF / Langmuir / Quadratic，scipy least_squares 带界，bar 制） |
| `iast` | 二元 IAST 选择性（解析铺展压力 Ψ=−ΣM·spence(1+K·P) + brentq，扫压输出 CSV） |
| `bet` | BET 比表面积（pyGAPS，Rouquerol 判据必报） |
| `qst` | 等量吸附热（Clausius–Clapeyron，多温度等温线） |
| `psd` | NLDFT/2D-NLDFT 孔径分布（48 个 Micromeritics kernel；N2 77K/Ar 87K/CO2 273K 全覆盖；可选 HK/BJH/t-plot） |
| `breakthrough` | RUPTURA 穿透曲线模拟（双曲双位点 Langmuir 拟合 → IAST 混合模拟） |
| `productivity` | 实测穿透曲线后处理（穿透时间/动态容量/工作容量/产率/纯度/回收率） |

## 标准格式

- 等温线：UTF-8 CSV，`P_bar,n_mmol_g[,T_K]`
- 穿透曲线：UTF-8 CSV，`time_min,<组分>_C_C0,...`

## 交付规范

每个计算任务交付三件套：**可直接画图的 CSV + PNG 图（仅 PNG，scientific-figure-team 规范）+ md/txt 分析报告**（输入清单、方法、参数与不确定度、判据、结论、软件引用）。

## kernel 库

`kernels/` 内含 48 个 DFT/NLDFT/2D-NLDFT/GCMC kernel（源自 Micromeritics 官方公开 DFT 模型库，
Jagiello & Olivier 系列；`.df2/.df3` 二进制经逆向转换，转换器见
[kernels-package 仓库](https://github.com/owenxyzhang-seseTJ/dsh-adsorption) 文档）。

- N2 @ 77K 首选 `NLDFT-mod200.csv`（carbon slit）；另有有限 slit As=4/6/12、异质表面 HS-2D-NLDFT、SWNT/MWNT 圆柱、ZTC、oxide 圆柱、柱撑黏土圆柱
- Ar @ 87K 首选 `NLDFT-mod203.csv`；另有有限 slit、异质表面、SWNT/MWNT 圆柱、oxide 圆柱、zeolite H/Me 型
- CO2 @ 273K 首选 `NLDFT-mod400.csv`（P/P0 ≤ 0.3）；另有异质表面、10 atm、GCMC 微孔、原始 DFT 超微孔（mod011，P/P0 ≤ 0.039）

## 致谢与许可

- MIT License（见 LICENSE）。kernel 数据版权归 Micromeritics 所有，发表/商用请自行核对使用条款。
- 参考文献：pyIAST（*Comput. Phys. Commun.* 200, 364–380, 2016）；pyGAPS（*Adsorption* 25, 1533–1542, 2019）；
  RUPTURA（*Mol. Simul.* 49, 893–953, 2023）；RASPA3（*J. Chem. Phys.* 161, 062501, 2024）。

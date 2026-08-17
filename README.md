# dsh-adsorption

气体吸附数据计算工作台 —— DSH 持久宿主插件（注册 `adsorption` 工具，10 个动作）。

[![Release](https://img.shields.io/github/v/release/owenxyzhang-seseTJ/dsh-adsorption)](https://github.com/owenxyzhang-seseTJ/dsh-adsorption/releases)
[![License](https://img.shields.io/github/license/owenxyzhang-seseTJ/dsh-adsorption)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/owenxyzhang-seseTJ/dsh-adsorption/ci.yml?branch=main)](https://github.com/owenxyzhang-seseTJ/dsh-adsorption/actions)
[![Last commit](https://img.shields.io/github/last-commit/owenxyzhang-seseTJ/dsh-adsorption)](https://github.com/owenxyzhang-seseTJ/dsh-adsorption/commits/main)
[![Repo size](https://img.shields.io/github/repo-size/owenxyzhang-seseTJ/dsh-adsorption)](https://github.com/owenxyzhang-seseTJ/dsh-adsorption)

基于 pyIAST / pyGAPS / RUPTURA / RASPA3 的完整吸附计算管线：
**等温线拟合 → IAST 混合吸附与选择性 → BET → Qst → NLDFT 孔径分布 → 穿透曲线模拟/实测产率**。

## 一键安装

```bash
git clone https://github.com/owenxyzhang-seseTJ/dsh-adsorption.git
cd dsh-adsorption
bash install.sh
```

`install.sh` 自动完成：创建 conda 环境 `pyiast-env`（Python 3.12）→ 安装计算栈
（pyiast / pygaps / ruptura / numpy / scipy / pandas / matplotlib / openpyxl / CoolProp）
→ 安装插件到 `$DSH_HOME/profiles/node_modules/` → （macOS）源码重编译修补 RUPTURA wheel 的
use-after-free。常用选项：`--no-ruptura-patch` 跳过修补、`--env <name>` 指定环境名。

## 手动安装

1. 准备 Python 3.12 环境并安装依赖：
   `pip install pyiast pygaps ruptura numpy scipy pandas matplotlib openpyxl CoolProp`
2. 安装插件：`cp -R dsh-adsorption $DSH_HOME/profiles/node_modules/`
3. 在 agent 预设（`$DSH_HOME/.agent-presets/<id>/agent.cordis.yml`）中加入：
   ```yaml
   - id: adsorption-plugin
     name: 'dsh-adsorption'
   ```
4. 按需设置环境变量（见下）。

## 环境变量

| 变量 | 说明 |
|---|---|
| `DSH_ADSORPTION_PYTHON` | pyiast-env 的 python 解释器路径；缺省自动探测 `$HOME` 下 `miniforge3` / `anaconda3` / `miniconda3` 的 `envs/pyiast-env/bin/python` |
| `DSH_ADSORPTION_RASPA3` | `raspa3` 二进制路径；缺省自动探测 `$HOME/.tclaw/runtimes/raspa3-macos/bin`、`$HOME/raspa3/bin`、`/usr/local/bin` 与 `PATH` |

## RASPA3

- 官方仓库与编译安装指引：https://github.com/iRASPA/RASPA3 （RASPA2：https://github.com/iRASPA/RASPA2）
- 本插件**不打包** RASPA3 二进制（编译体系相关）。设置 `DSH_ADSORPTION_RASPA3` 后启用 GCMC 动作；
  未设置时其余 9 个动作不受影响。
- 参考实现：RASPA3: Dubbeldam, D., Calero, S., Vlugt, T. J. H. *J. Chem. Phys.* **161**, 062501 (2024).

## 动作一览

| action | 说明 |
|---|---|
| `env` | 检查计算环境（Python 包 + RASPA3）并给出安装指引 |
| `guide` | 获取工作流判据（stage: data/fit/iast/bet/qst/psd/breakthrough/productivity/raspa3/guardrails） |
| `standardize` | 任意仪器格式 → 标准 CSV（`P_bar,n_mmol_g`；支持 torr/pa/kpa/mpa/bar/atm/mbar/psi × mmol_g/mol_g/mol_kg/cm3stp_g/cc_g/mg_g） |
| `fit` | 等温线拟合（DSLF / Langmuir / Quadratic，scipy least_squares 带界，bar 制） |
| `iast` | 二元 IAST 选择性（解析铺展压力 Ψ=−ΣM·spence(1+K·P) + brentq，扫压输出 CSV） |
| `bet` | BET 比表面积（pyGAPS，Rouquerol 判据必报） |
| `qst` | 等量吸附热（Clausius–Clapeyron，多温度等温线） |
| `psd` | NLDFT/2D-NLDFT 孔径分布（48 个 kernel；N2 77K / Ar 87K / CO2 273K 全覆盖；可选 HK/BJH/t-plot） |
| `breakthrough` | RUPTURA 穿透曲线模拟（双曲双位点 Langmuir 拟合 → IAST 混合模拟） |
| `productivity` | 实测穿透曲线后处理（穿透时间/动态容量/工作容量/产率/纯度/回收率） |

## 标准格式

- 等温线：UTF-8 CSV，`P_bar,n_mmol_g[,T_K]`
- 穿透曲线：UTF-8 CSV，`time_min,<组分>_C_C0,...`

## 交付规范

每个计算任务交付三件套：**可直接画图的 CSV + PNG 图（仅 PNG）+ md/txt 分析报告**
（输入清单、方法、参数与不确定度、判据、结论、软件引用）。

## kernel 库

`kernels/` 内含 48 个 DFT/NLDFT/2D-NLDFT/GCMC kernel（源自 Micromeritics 官方公开 DFT 模型库，
Jagiello & Olivier 系列；`.df2/.df3` 二进制经逆向转换，转换器与逆向笔记见
[kernels-package](https://github.com/owenxyzhang-seseTJ/dsh-adsorption/tree/main/kernels) 说明）。

- N2 @ 77K 首选 `N2-77K-carbon-slit-NLDFT-mod200.csv`（carbon slit）；另有有限 slit As=4/6/12、异质表面 HS-2D-NLDFT、SWNT/MWNT 圆柱、ZTC、oxide 圆柱、柱撑黏土圆柱
- Ar @ 87K 首选 `Ar-87K-carbon-slit-NLDFT-mod203.csv`；另有有限 slit、异质表面、SWNT/MWNT 圆柱、oxide 圆柱、zeolite H/Me 型
- CO2 @ 273K 首选 `CO2-273K-carbon-slit-NLDFT-mod400.csv`（P/P0 ≤ 0.3）；另有异质表面、10 atm、GCMC 微孔、原始 DFT 超微孔（mod011，P/P0 ≤ 0.039）

## 已知修复（本机环境）

- **RUPTURA 1.0.4 wheel 的 use-after-free**：`Breakthrough::compute()` 把返回数组包装到局部
  `std::vector` 的悬垂指针上（`py::array_t(shape, buffer.data())`），多帧结果不可靠。
  已用包内 C++ 源码重编译修复（先分配再拷贝）；`install.sh` 在 macOS 上自动完成该修补。
- **数值稳定性**：`TimeStep` 需满足 `dt ≤ min(dx/v, dx²/2D_ax)`；实测 dx=0.005 m、D_ax=1e-6 m²/s
  时 dt 需 ≤0.001 s，否则内部网格点输出 NaN（脚本默认已按此设置）。

## 致谢与许可

- MIT License（见 LICENSE）。kernel 数据版权归 Micromeritics 所有，发表/商用请自行核对使用条款。
- 参考文献：pyIAST（*Comput. Phys. Commun.* 200, 364–380, 2016）；pyGAPS（*Adsorption* 25, 1533–1542, 2019）；
  RUPTURA（*Mol. Simul.* 49, 893–953, 2023）；RASPA3（*J. Chem. Phys.* 161, 062501, 2024）。

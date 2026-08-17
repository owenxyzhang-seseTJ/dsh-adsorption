---
name: raspa3-gcmc
description: RASPA3 分子模拟：GCMC 吸附等温线、吸附焓与 Henry 系数计算。本机已编译 RASPA3 3.1.0（macOS arm64），以 simulation.json 为输入。涉及 RASPA 模拟、GCMC、蒙特卡洛吸附、力场模拟时使用。
---

# RASPA3 GCMC 模拟

## 本机安装（固定路径，直接使用）

- 主程序：`"$DSH_ADSORPTION_RASPA3"（缺省探测 $HOME/.tclaw/runtimes/raspa3-macos、$HOME/raspa3、/usr/local/bin、PATH）`（3.1.0，Mach-O arm64）
- 辅助工具：`"$DSH_ADSORPTION_RASPA3"（缺省探测 $HOME/.tclaw/runtimes/raspa3-macos、$HOME/raspa3、/usr/local/bin、PATH）-cli`（读 CIF，输出框架信息/网格参数）
- 运行方式：在某工作目录放好 `simulation.json`，**在该目录下**执行 `raspa3`。
- 直接运行报 `[Input reader]: File 'simulation.json' not found` 是预期行为（说明需要 simulation.json，不是安装坏了）。
- 文档与示例：https://github.com/iRASPA/RASPA3（examples/ 目录有完整 simulation.json 样例）

## 目录约定

每个模拟一个独立子目录，例如 `sims/gcmc_co2_298k/`：
- `simulation.json`：任务描述（唯一的输入文件）
- 结构文件：CIF（框架原子与晶胞信息）
- 输出：`output_*.json` 等（能量/吸附量统计）
模拟目录与实验数据分开存放；力场、截断、循环数等参数必须记入报告。

## 典型任务：GCMC 吸附等温线

1. 准备结构：CIF 需要晶胞+框架原子；带电框架（含开放金属位点）必须给原子电荷，否则力场失真。
2. 每个压力点（如 0.01–1 bar 对数分布 20 点）一个 GCMC 任务：
   - ForceField：`UFF` / `Dreiding` / `TraPPE` / `OPLS-AA` 按材料选；MOF 常用 UFF（框架）+ Dreiding（吸附质）组合，或文献报道力场。
   - `ExternalTemperature` / `ExternalPressure` 设定；循环数：初始化 ≥1e4、平衡 ≥1e5、采样 ≥1e5。
   - 超胞：晶胞太小则 MakeSuperCell 到 2×2×2 以上，保证截断半径 < 最短晶胞边的一半。
   - LJ 截断 12 Å；带电体系开 Ewald。
3. 后处理：从输出 JSON 取平均吸附量（mol/uc），按晶胞质量换算 mmol/g：
   `n_mmol_g = n_mol_uc × 1000 / M_uc`（M_uc 为晶胞摩尔质量 g/mol）。
4. 汇总成标准两列 CSV（`P_bar, n_mmol_g`，带误差棒列）→ 交给 `gas-adsorption` skill 的工作流 A/B（拟合 + IAST）。
5. 与实验对比：同温度同单位画图；偏差来源（力场/电荷/骨架柔性）写进报告。

## 关键参数与常见错误

- CIF 无成键信息：框架原子类型自动识别失败时手动指定 atom types / 伪原子。
- 统计涨落 >5%：增加采样循环数，或检查平衡是否充分。
- GCMC 吸附量波动大：增加循环、加大超胞、检查截断与 Ewald 设置。
- 长任务：用 run_in_background 后台执行；正式跑之前先 1000 循环小试算验证输入文件无误，再与用户确认参数后放大。
- 每轮模拟结束汇报：体系、力场、循环数、平均吸附量 ± 标准差。

## 输出与报告

交付同 `gas-adsorption` skill 三件套：
1. processed CSV（P, n, 标准差，单位声明）；
2. PNG 图（scientific-figure-team 规范，仅 PNG）；
3. md 报告（力场、截断、循环数、超胞、单位换算公式、与实验/文献对比、不确定度）。

## 引用

- RASPA3: Dubbeldam, D., Calero, S., Vlugt, T. J. H. *J. Chem. Phys.* **161**, 062501 (2024). https://github.com/iRASPA/RASPA3

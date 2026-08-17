# kernel 库命名映射

命名规则：`<气体>-<温度>K-<材料>-<孔型>[-细节]-<方法>-mod<编号>.csv`（保留 Micromeritics 模型编号以便溯源）。

| 文件 | 来源模型 | 说明 |
|---|---|---|
| `Ar-77K-carbon-slit-NLDFT-mod023.csv` | `NLDFT-mod023.csv` | Ar@77 Carbon Slit NLDFT |
| `Ar-77K-zeolite-H-NLDFT-mod229.csv` | `NLDFT-mod229.csv` | Ar@77 Zeolites H-form |
| `Ar-77K-zeolite-Me-NLDFT-mod230.csv` | `NLDFT-mod230.csv` | Ar@77 Zeolites Me-form |
| `Ar-77K-zeolite-cylinder-NLDFT-mod102.csv` | `NLDFT-mod102.csv` | Ar@77 Zeolite Cyl |
| `Ar-87K-carbon-HS-2D-NLDFT-mod420.csv` | `2D-NLDFT-mod420.csv` | Ar@87 Carbon Heterogeneous Surface, HS-2D-NLDFT |
| `Ar-87K-carbon-MWNT-NLDFT-mod228.csv` | `NLDFT-mod228.csv` | Ar@87 Carbon Cyl MWNT |
| `Ar-87K-carbon-SWNT-NLDFT-mod227.csv` | `NLDFT-mod227.csv` | Ar@87 Carbon Cyl SWNT |
| `Ar-87K-carbon-finite-slit-As12-2D-NLDFT-mod207.csv` | `2D-NLDFT-mod207.csv` | Ar@87 Carbon Finite Pores As=12 |
| `Ar-87K-carbon-finite-slit-As4-2D-NLDFT-mod204.csv` | `2D-NLDFT-mod204.csv` | Ar@87 Carbon Finite Pores As=4 |
| `Ar-87K-carbon-finite-slit-As6-2D-NLDFT-mod205.csv` | `2D-NLDFT-mod205.csv` | Ar@87 Carbon Finite Pores As=6 |
| `Ar-87K-carbon-slit-DFT-mod001.csv` | `Original-Density-Functional-Theory-mod001.csv` | Ar@87 Carbon Slit 原始 DFT |
| `Ar-87K-carbon-slit-NLDFT-mod203.csv` | `NLDFT-mod203.csv` | Ar@87 Carbon Slit Pores by NLDFT（首选） |
| `Ar-87K-oxide-cylinder-HS-2D-NLDFT-mod610.csv` | `2D-NLDFT-mod610.csv` | Ar@87 Oxide Cyl HS-2D-NLDFT |
| `Ar-87K-oxide-cylinder-NLDFT-mod015.csv` | `Hybrid-NL-Density-Functional-Theory-mod015.csv` | Ar@87 Oxide Cyl NLDFT |
| `Ar-87K-zeolite-H-NLDFT-mod251.csv` | `NLDFT-mod251.csv` | Ar@87 Zeolites H-form |
| `Ar-87K-zeolite-Me-NLDFT-mod252.csv` | `NLDFT-mod252.csv` | Ar@87 Zeolites Me-form |
| `Ar-MOF1-cylinder-meso-2D-NLDFT-mod600.csv` | `2D-NLDFT-mod600.csv` | Ar MOF1 Cyl Mesopores 2D-NLDFT |
| `Ar-carbon-MDFT-mod012.csv` | `Density-Functional-Theory-mod012.csv` | Ar Modified Density Functional |
| `CO2-273K-carbon-HS-2D-NLDFT-mod425.csv` | `2D-NLDFT-mod425.csv` | CO2@273 Carbon Heterogeneous Surface, HS-2D-NLDFT |
| `CO2-273K-carbon-slit-10atm-NLDFT-mod250.csv` | `NLDFT-mod250.csv` | CO2@273 Carbon Slit, 10 atm |
| `CO2-273K-carbon-slit-DFT-mod011.csv` | `NLDFT-mod011.csv` | CO2@273 Carbon Slit 原始 DFT（P/P0 ≤ 0.039，超微孔段） |
| `CO2-273K-carbon-slit-GCMC-mod241.csv` | `GCMC-mod241.csv` | CO2 Carbon slit GCMC（仅微孔 0.32–1.5 nm，噪声大） |
| `CO2-273K-carbon-slit-NLDFT-mod400.csv` | `NLDFT-mod400.csv` | CO2@273 Carbon, NLDFT（首选；P/P0 ≤ 0.3） |
| `H2-77K-carbon-HS-2D-NLDFT-mod430.csv` | `2D-NLDFT-mod430.csv` | H2@77 Carbon HS-2D-NLDFT |
| `H2-77K-zeolite-NLDFT-mod310.csv` | `NLDFT-mod310.csv` | H2@77 Ultramicroporous Zeolites |
| `N2-77K-carbon-HS-2D-NLDFT-mod255.csv` | `2D-NLDFT-mod255.csv` | N2@77 Carbon Heterogeneous Surface, HS-2D-NLDFT |
| `N2-77K-carbon-MWNT-NLDFT-mod226.csv` | `NLDFT-mod226.csv` | N2@77 Carbon Cyl MWNT |
| `N2-77K-carbon-SWNT-NLDFT-mod225.csv` | `NLDFT-mod225.csv` | N2@77 Carbon Cyl SWNT |
| `N2-77K-carbon-ZTC-cylinder-2D-NLDFT-mod440.csv` | `2D-NLDFT-mod440.csv` | N2@77 Carbon Cyl (ZTC) |
| `N2-77K-carbon-cylinder-BdB-Kelvin-mod009.csv` | `Classical-Kelvin-Equation-mod009.csv` | N2@77 Cyl + Broekhoff-de Boer |
| `N2-77K-carbon-cylinder-HJ-Kelvin-mod007.csv` | `Classical-Kelvin-Equation-mod007.csv` | N2@77 Cyl + Harkins-Jura 厚度 |
| `N2-77K-carbon-cylinder-Halsey-Kelvin-mod005.csv` | `Classical-Kelvin-Equation-mod005.csv` | N2@77 Cyl + Halsey 厚度 |
| `N2-77K-carbon-cylinder-meso-2D-NLDFT-mod450.csv` | `2D-NLDFT-mod450.csv` | N2@77 Carbon Cyl Mesopores |
| `N2-77K-carbon-finite-slit-As12-2D-NLDFT-mod206.csv` | `2D-NLDFT-mod206.csv` | N2@77 Carbon Finite Pores As=12 |
| `N2-77K-carbon-finite-slit-As4-2D-NLDFT-mod201.csv` | `2D-NLDFT-mod201.csv` | N2@77 Carbon Finite Pores As=4 |
| `N2-77K-carbon-finite-slit-As6-2D-NLDFT-mod202.csv` | `2D-NLDFT-mod202.csv` | N2@77 Carbon Finite Pores As=6 |
| `N2-77K-carbon-slit-BdB-Kelvin-mod008.csv` | `Classical-Kelvin-Equation-mod008.csv` | N2@77 Slit + Broekhoff-de Boer |
| `N2-77K-carbon-slit-DFT-mod000.csv` | `Original-Density-Functional-Theory-mod000.csv` | N2@77 Carbon Slit 原始 DFT |
| `N2-77K-carbon-slit-HJ-Kelvin-mod006.csv` | `Classical-Kelvin-Equation-mod006.csv` | N2@77 Slit + Harkins-Jura 厚度 |
| `N2-77K-carbon-slit-Halsey-Kelvin-mod004.csv` | `Classical-Kelvin-Equation-mod004.csv` | N2@77 Slit + Halsey 厚度（经典 Kelvin） |
| `N2-77K-carbon-slit-NLDFT-mod200.csv` | `NLDFT-mod200.csv` | N2@77 Carbon Slit Pores by NLDFT（首选） |
| `N2-77K-clay-cylinder-NLDFT-mod014.csv` | `Hybrid-Density-Functional-Theory-mod014.csv` | N2@77 Pillared Clay Cyl |
| `N2-77K-oxide-cylinder-NLDFT-strong-mod010.csv` | `NLDFT-mod010.csv` | N2@77 Oxide Cyl Strong Potential |
| `N2-77K-oxide-cylinder-Tarazona-mod013.csv` | `NLDFT-mod013.csv` | N2@77 Oxide Cyl Tarazona |
| `N2-87K-carbon-slit-NLDFT-mod024.csv` | `NLDFT-mod024.csv` | N2@87 Carbon Slit NLDFT |
| `N2-carbon-MDFT-mod003.csv` | `Modified-Density-Functional-Theory-mod003.csv` | N2 Modified Density Functional |
| `O2-77K-carbon-HS-2D-NLDFT-mod410.csv` | `2D-NLDFT-mod410.csv` | O2@77 Carbon HS-2D-NLDFT |
| `O2-77K-zeolite-NLDFT-mod300.csv` | `NLDFT-mod300.csv` | O2@77 Ultramicroporous Zeolites |

来源：Micromeritics 官方 DFT 模型库（https://micromeritics.com.cn/dft-models/，Jagiello & Olivier 系列），
`.df2/.df3` 逆向转换（转换器与 manifest 见 kernels-package 仓库）。发表/商用请核对 Micromeritics 使用条款。
'use strict'

const path = require('path')
const fs = require('fs')
const os = require('os')
const { defineTool } = require('@deepseek-ai/dsh-tools')

const name = 'adsorption'
const inject = ['tools', 'shell']

// ── 计算栈路径解析（无硬编码本机路径）────────────────────────────────────
// 优先级: 环境变量 DSH_ADSORPTION_PYTHON / DSH_ADSORPTION_RASPA3
//         → $HOME 下常见安装位置探测 → PATH 探测（RASPA）
function resolvePython() {
    const fromEnv = process.env.DSH_ADSORPTION_PYTHON
    if (fromEnv) return fromEnv
    const home = os.homedir()
    const candidates = [
        home + '/miniforge3/envs/pyiast-env/bin/python',
        home + '/anaconda3/envs/pyiast-env/bin/python',
        home + '/miniconda3/envs/pyiast-env/bin/python',
    ]
    for (const c of candidates) if (fs.existsSync(c)) return c
    return candidates[0]  // 回退首个候选；env action 会给出安装指引
}

function resolveRaspa() {
    const fromEnv = process.env.DSH_ADSORPTION_RASPA3
    if (fromEnv) return fromEnv
    const home = os.homedir()
    const candidates = [
        home + '/.tclaw/runtimes/raspa3-macos/bin/raspa3',
        home + '/raspa3/bin/raspa3',
        '/usr/local/bin/raspa3',
    ]
    for (const c of candidates) if (fs.existsSync(c)) return c
    return 'raspa3'  // 回退 PATH 命令
}

const PY = resolvePython()
const RASPA_BIN = resolveRaspa()

const apply = (ctx) => {
    // 包内资源（scripts/ python 助手 + kernels/ NLDFT kernel 库）
    const PACKAGE_DIR = __dirname
    const SCRIPTS = path.join(PACKAGE_DIR, 'scripts')
    const KERNELS_DIR = path.join(PACKAGE_DIR, 'kernels')

    const ACTIONS = [
        'env', 'guide', 'standardize', 'fit', 'iast', 'bet', 'qst',
        'psd', 'breakthrough', 'productivity',
    ]

    // ---------- 工作流判据（浓缩中文版，与 gas-adsorption skill 一致） ----------
    const GUIDANCE = {
        data: [
            '【输入数据铁律 —— 先转标准格式】',
            '1. 任何计算前，先把输入转换为标准 CSV（UTF-8）：',
            '   等温线: P_bar,n_mmol_g[,T_K]；穿透曲线: time_min,<组分>_C_C0,...',
            '2. 用 standardize 动作或 standardize_isotherm.py 转换（支持 Torr/Pa/kPa/atm/psi、',
            '   cm3(STP)/g、mg/g、cc/g 等常见单位）。',
            '3. 单位/温度/吸附质有歧义时先与用户确认，不得猜测。',
        ].join('\n'),
        fit: [
            '【等温线拟合（pyIAST / scipy）】',
            '1. 全流程统一 bar 单位制（标准 CSV 的 P_bar 直接喂入）；K 参数 O(1) 数值更稳。',
            '2. pyIAST 1.4.3 的 Langmuir 是对数式 q=M·ln(1+K·P)，不是物理双曲式；',
            '   4 参数 DSLF 用其内置 Nelder-Mead 常收敛失败 → 用 scipy least_squares + 界约束。',
            '3. 拟合后必须检查参数合理性（K>0、M>0）与 RMSE/R²，坏极小（负 K）时换初值重拟。',
        ].join('\n'),
        iast: [
            '【IAST 混合吸附与选择性】',
            '1. 解析铺展压力: Ψ(P) = −Σ M_i·spence(1+K_i·P)（scipy.special.spence = Li₂(1−z)，注意负号）。',
            '2. 二元: 二分求根 Ψ1(p1/x1)=Ψ2(p2/(1−x1))，x1∈(1e-9, 1−1e-9)。',
            '3. 选择性 S = (x1/y1)/(x2/y2)；扫总压得 S–P 曲线。',
            '4. IAST 是理想假设，强吸附/高负载可能偏离，必要时与 GCMC 对比。',
        ].join('\n'),
        bet: [
            '【BET 比表面积（Rouquerol 判据必报）】',
            '1. 选点区间内 n(1−P/P0) 随 P/P0 单调递增；相关系数 ≥0.999；C>0。',
            '2. N₂ 77K 常规区间 (0.05, 0.30)；微孔材料收窄到 (0.005, 0.05) 并注明理由。',
            '3. 微孔材料直接套 0.05–0.30 会失真；必须报判据而不是只报数字。',
        ].join('\n'),
        qst: [
            '【等量吸附热 Qst（Clausius–Clapeyron）】',
            '1. 至少 3 条温度等温线；对每个固定吸附量，lnP 对 1/T 线性拟合，Qst = −R·斜率。',
            '2. 同吸附量点可用拟合模型插值；报告斜率不确定度传播。',
        ].join('\n'),
        psd: [
            '【孔径分布（NLDFT/QSDFT kernel）】',
            '1. kernel 轴是相对压力 P/P0：标准 CSV 的 P_bar 先按 P0 换算（N2 77K=1.0、Ar 87K=1.0、',
            '   CO2 273K=34.85 bar，不确定必须问用户）。',
            '2. kernel 选择四要素：吸附质+温度+孔型(slit/cyl/有限孔)+表面化学(carbon/oxide/zeolite)必须匹配。',
            '3. 库内 48 个 kernel（Micromeritics 逆向转换，manifest 见包内 kernels/README）：',
            '   N2 77K 首选 NLDFT-mod200.csv；Ar 87K 首选 NLDFT-mod203.csv；CO2 273K 首选 NLDFT-mod400.csv。',
            '4. CO2 273K 的 kernel 压力轴 ≤0.3（mod011 仅 ≤0.039，只用于超微孔段）。',
            '5. CIF 不能直接生成 kernel；无匹配 kernel 时联网搜已发表 kernel 表或 RASPA3 GCMC 自算。',
        ].join('\n'),
        breakthrough: [
            '【穿透曲线模拟（RUPTURA，SI 单位）】',
            '1. RUPTURA 用 Pa、mol/kg；Langmuir 是物理双曲式 q=q_sat·b·P/(1+b·P)，',
            '   与 pyIAST 对数式不同，参数要按 RUPTURA 形式单独拟合。',
            '2. 数值稳定：TimeStep 默认 0.001 s（约束 dt ≤ min(dx/v, dx²/2D_ax)），',
            '   出口出现 NaN 时减小 dt 或增大网格；NumberOfTimeSteps="auto"。',
            '3. 出口 C/C0 = data[:, -1, 8 + 6*i]（Pnorm 通道）；时间 = data[:, -1, 1] (min)。',
            '4. 本机已重编译修复官方 wheel 的 use-after-free（compute 返回悬垂指针）。',
        ].join('\n'),
        productivity: [
            '【实测穿透曲线后处理】',
            '1. 穿透时间 t_b: C/C0 首次达 0.05（线性插值）。',
            '2. 动态容量 q_dyn = (Q·y_i/m)·∫(1−C/C0)dt（mmol/g）；未饱和注明下界。',
            '3. 工作容量 = q_dyn − 解吸段残余；产率 = q_work/t_cycle（mmol/(g·h)）。',
            '4. 负工作容量 → 解吸窗内 C/C0 未下降，检查时间窗。',
        ].join('\n'),
        raspa3: [
            '【RASPA3 GCMC】',
            '1. 官方仓库与文档: https://github.com/iRASPA/RASPA3（编译安装方法见其 README）。',
            '2. 二进制由环境变量 DSH_ADSORPTION_RASPA3 或自动探测指定；工作目录放 simulation.json 后运行（无此文件报错是预期）。',
            '3. 每压力点一任务；循环: 初始化≥1e4/平衡≥1e5/采样≥1e5；超胞使截断<最短边一半。',
            '4. 输出 mol/uc → mmol/g: ×1000/M_uc。',
        ].join('\n'),
        guardrails: [
            '【科学底线】',
            '- 绝不虚构数据：每个数字必须来自输入文件或程序输出；',
            '- 单位必须显式声明，换算过程写入报告；',
            '- 图仅 PNG（scientific-figure-team 规范）；交付 = 可画图 CSV + PNG + md/txt 报告；',
            '- 报告必须给出参数、不确定度、拟合优度/判据与软件引用。',
        ].join('\n'),
    }

    // ---------- 工具函数 ----------
    function quotePath(value) {
        return "'" + String(value).replace(/'/g, "'\\''") + "'"
    }

    function sanitizeSimple(value, label) {
        const text = String(value == null ? '' : value).trim()
        if (text === '') return ''
        if (!/^[A-Za-z0-9._\-+/ ()]+$/.test(text)) throw new Error(label + ' 含不允许的字符: ' + text)
        return text
    }

    async function runCommand(command, workdir, opts) {
        const request = {
            command: command,
            workdir: workdir,
            timeoutMs: (opts && opts.timeoutMs) || 600000,
            stdoutMaxBytes: (opts && opts.stdoutMaxBytes) || 500000,
        }
        if (opts && opts.signal !== undefined && opts.signal !== null) request.signal = opts.signal
        let spec
        try {
            spec = ctx.shell.resolve(request)
        } catch (err) {
            return {
                exitCode: -1, timedOut: false, aborted: false, timeoutMs: 0,
                stdout: '', stdoutTruncated: false,
                stderr: 'shell.resolve 失败: ' + String(err && err.message ? err.message : err),
                stderrTruncated: false,
            }
        }
        const result = await ctx.shell.run(spec)
        return {
            exitCode: result.exitCode,
            signal: result.signal,
            timedOut: !!result.timedOut,
            aborted: !!result.aborted,
            timeoutMs: result.timeoutMs,
            stdout: result.stdout ? result.stdout.text : '',
            stdoutTruncated: !!(result.stdout && result.stdout.truncated),
            stderr: result.stderr ? result.stderr.text : '',
            stderrTruncated: !!(result.stderr && result.stderr.truncated),
        }
    }

    function trimText(text, max) {
        const s = String(text == null ? '' : text)
        return s.length > max ? s.slice(0, max) + '\n…[截断]' : s
    }

    function reportOk(action, summary, data, tail, guidance) {
        return { ok: true, action: action, gate: null, summary: summary, data: data || {}, tail: tail || '', guidance: guidance || null }
    }

    function reportFail(action, message) {
        return { ok: false, action: action, gate: null, summary: message, data: {}, tail: '', guidance: null }
    }

    function pyRun(script, args, workdir, signal, timeoutMs) {
        const cmd = [quotePath(PY), quotePath(path.join(SCRIPTS, script))].concat(
            args.map((a) => quotePath(a))
        ).join(' ')
        return runCommand(cmd, workdir, { signal: signal, timeoutMs: timeoutMs || 900000 })
    }

    // ---------- 动作分发 ----------
    async function performAction(args, signal, cwd) {
        const action = String((args && args.action) || '').trim()
        if (ACTIONS.indexOf(action) < 0) {
            return reportFail(action || '(空)', '未知 action: "' + action + '"。可用: ' + ACTIONS.join(', '))
        }
        const workdir = String((args && args.workdir) || '').trim() || cwd || process.cwd()
        const input = String((args && args.input_path) || '').trim() || workdir
        try {
            switch (action) {
                case 'env': {
                    const r = await runCommand(
                        quotePath(PY) + " -c \"import pyiast,pygaps,ruptura,numpy,scipy,pandas,matplotlib; print('pyiast', pyiast.__name__); print('pygaps', pygaps.__version__); print('ruptura', ruptura.__version__ if hasattr(ruptura,'__version__') else '1.0.4')\" && test -x " + quotePath(RASPA_BIN) + " && echo RASPA3-OK",
                        '/', { signal: signal, timeoutMs: 120000 })
                    const ok = r.exitCode === 0
                    return reportOk(action, ok ? '计算栈就绪' : '计算栈异常', {
                        python: PY, raspa3: RASPA_BIN, exit_code: r.exitCode,
                    }, trimText((r.stdout + '\n' + r.stderr).trim(), 2000))
                }
                case 'guide': {
                    const stage = sanitizeSimple(args.stage, 'stage') || 'data'
                    if (!GUIDANCE[stage]) return reportFail(action, '未知 stage: ' + stage + '。可用: ' + Object.keys(GUIDANCE).join(', '))
                    return reportOk(action, '工作流判据: ' + stage, { stage: stage }, '', GUIDANCE[stage])
                }
                case 'standardize': {
                    const r = await pyRun('standardize_isotherm.py', [
                        input,
                        '--pressure-col', args.pressure_col,
                        '--pressure-unit', args.pressure_unit,
                        '--loading-col', args.loading_col,
                        '--loading-unit', args.loading_unit,
                        '--temp-k', args.temp_k,
                        '--out', args.output_path || (workdir + '/standard.csv'),
                    ].filter((x) => x !== undefined && x !== null && x !== ''), workdir, signal)
                    if (r.exitCode !== 0) return reportFail(action, '转换失败:\n' + trimText(r.stderr || r.stdout, 2500))
                    return reportOk(action, '已转标准 CSV', { output: args.output_path || (workdir + '/standard.csv'), exit_code: 0 }, trimText(r.stdout, 2500))
                }
                case 'fit': {
                    const r = await pyRun('fit_isotherm.py', [
                        input, '--model', args.model || 'DSLF',
                        '--out-dir', args.out_dir || workdir,
                    ], workdir, signal)
                    if (r.exitCode !== 0) return reportFail(action, '拟合失败:\n' + trimText(r.stderr || r.stdout, 2500))
                    return reportOk(action, '拟合完成', { exit_code: 0 }, trimText(r.stdout, 4000), GUIDANCE.fit)
                }
                case 'iast': {
                    const r = await pyRun('iast_selectivity.py', [
                        input, args.second_isotherm,
                        '--y1', args.y1 || '0.15',
                        '--p-max-bar', args.p_max_bar || '1.0',
                        '--n-points', args.n_points || '30',
                        '--out-dir', args.out_dir || workdir,
                    ].filter((x) => x !== undefined && x !== null && x !== ''), workdir, signal)
                    if (r.exitCode !== 0) return reportFail(action, 'IAST 失败:\n' + trimText(r.stderr || r.stdout, 2500))
                    return reportOk(action, 'IAST 完成', { exit_code: 0 }, trimText(r.stdout, 4000), GUIDANCE.iast)
                }
                case 'bet': {
                    const r = await pyRun('bet_area.py', [
                        input, '--temp-k', args.temp_k || '77', '--adsorbate', args.adsorbate || 'N2',
                        '--p-limits', args.p_limits || '0.01,0.30',
                        '--out-dir', args.out_dir || workdir,
                    ], workdir, signal)
                    if (r.exitCode !== 0) return reportFail(action, 'BET 失败:\n' + trimText(r.stderr || r.stdout, 2500))
                    return reportOk(action, 'BET 完成', { exit_code: 0 }, trimText(r.stdout, 4000), GUIDANCE.bet)
                }
                case 'qst': {
                    const r = await pyRun('qst_heat.py', [
                        input, '--loading-points', args.loading_points || '0.5,1,2,3,5',
                        '--out-dir', args.out_dir || workdir,
                    ], workdir, signal)
                    if (r.exitCode !== 0) return reportFail(action, 'Qst 失败:\n' + trimText(r.stderr || r.stdout, 2500))
                    return reportOk(action, 'Qst 完成', { exit_code: 0 }, trimText(r.stdout, 4000), GUIDANCE.qst)
                }
                case 'psd': {
                    const r = await pyRun('psd_from_isotherm.py', [
                        input, '--temp-k', args.temp_k || '77', '--adsorbate', args.adsorbate || 'N2',
                        '--kernel', args.kernel || 'NLDFT-mod200.csv',
                        '--p0-bar', args.p0_bar,
                        '--hk', args.hk, '--bjh', args.bjh, '--t-plot', args.t_plot,
                        '--out-dir', args.out_dir || workdir,
                    ].filter((x) => x !== undefined && x !== null && x !== ''), workdir, signal)
                    if (r.exitCode !== 0) return reportFail(action, 'PSD 失败:\n' + trimText(r.stderr || r.stdout, 2500))
                    return reportOk(action, 'PSD 完成', { exit_code: 0, kernels_dir: KERNELS_DIR }, trimText(r.stdout, 4000), GUIDANCE.psd)
                }
                case 'breakthrough': {
                    const r = await pyRun('breakthrough_sim.py', [
                        input, args.second_isotherm,
                        '--y1', args.y1 || '0.15',
                        '--temp-k', args.temp_k || '298',
                        '--pressure-bar', args.pressure_bar || '1.0',
                        '--col-length-m', args.col_length_m || '0.5',
                        '--void-frac', args.void_frac || '0.4',
                        '--density-kg-m3', args.density_kg_m3 || '1000',
                        '--time-step-s', args.time_step_s || '0.05',
                        '--n-steps', args.n_steps || '2000',
                        '--out-dir', args.out_dir || workdir,
                    ].filter((x) => x !== undefined && x !== null && x !== ''), workdir, signal)
                    if (r.exitCode !== 0) return reportFail(action, '穿透模拟失败:\n' + trimText(r.stderr || r.stdout, 2500))
                    return reportOk(action, '穿透模拟完成', { exit_code: 0 }, trimText(r.stdout, 4000), GUIDANCE.breakthrough)
                }
                case 'productivity': {
                    const r = await pyRun('breakthrough_productivity.py', [
                        input,
                        '--time-col', args.time_col || 'time_min',
                        '--cols', args.cols,
                        '--feed-fracs', args.feed_fracs,
                        '--flow-ml-min', args.flow_ml_min,
                        '--mass-g', args.mass_g,
                        '--desorb-from', args.desorb_from,
                        '--desorb-to', args.desorb_to,
                        '--bt-frac', args.bt_frac || '0.05',
                        '--plot', args.plot || '',
                        '--out', args.output_path || (workdir + '/穿透_processed.csv'),
                    ].filter((x) => x !== undefined && x !== null && x !== ''), workdir, signal)
                    if (r.exitCode !== 0) return reportFail(action, '后处理失败:\n' + trimText(r.stderr || r.stdout, 2500))
                    return reportOk(action, '穿透后处理完成', { exit_code: 0 }, trimText(r.stdout, 4000), GUIDANCE.productivity)
                }
                default:
                    return reportFail(action, 'action 未实现: ' + action)
            }
        } catch (err) {
            return reportFail(action, '执行出错: ' + String(err && err.message ? err.message : err))
        }
    }

    // ---------- 工具注册 ----------
    const tool = defineTool({
        name: 'adsorption',
        description: '本机气体吸附计算工作台（pyiast-env: pyIAST/pyGAPS/RUPTURA + RASPA3 3.1.0 + 48 个 NLDFT kernel）。' +
            'action 取值：' +
            'env=检查计算环境；guide=获取工作流判据（stage: data/fit/iast/bet/qst/psd/breakthrough/productivity/raspa3/guardrails）；' +
            'standardize=任意格式→标准 CSV（P_bar,n_mmol_g；pressure_unit: torr/pa/kpa/mpa/bar/atm/mbar/psi；loading_unit: mmol_g/mol_g/mol_kg/cm3stp_g/cc_g/mg_g）；' +
            'fit=DSLF/Langmuir 等温线拟合（input_path=标准 CSV；model: DSLF/Langmuir/Quadratic）；' +
            'iast=二元 IAST 选择性（input_path=组分1 标准 CSV，second_isotherm=组分2；y1=进料摩尔分数；解析铺展压力求解）；' +
            'bet=BET 比表面积（temp_k/adsorbate/p_limits；Rouquerol 判据必报）；' +
            'qst=等量吸附热（input_path=多温度标准 CSV 目录或逗号分隔文件列表；loading_points）；' +
            'psd=NLDFT 孔径分布（temp_k/adsorbate/kernel；kernel 取 kernels/ 内文件名，N2 77K 默认 NLDFT-mod200.csv，Ar 87K 用 NLDFT-mod203.csv，CO2 273K 用 NLDFT-mod400.csv；p0_bar 压力换算；--hk/--bjh/--t-plot 附加方法）；' +
            'breakthrough=RUPTURA 穿透曲线模拟（input_path/second_isotherm=等温线 CSV；y1/temp_k/pressure_bar/col_length_m/void_frac/density_kg_m3/time_step_s/n_steps）；' +
            'productivity=实测穿透曲线产率计算（input_path=time_min+各组分_C_C0 列 CSV；cols/feed_fracs/flow_ml_min/mass_g/desorb-from/desorb-to/bt-frac）。' +
            '交付规范：可画图 CSV + PNG + md/txt 报告；图仅 PNG（scientific-figure-team）。' +
            '科学底线：数据先转标准格式、单位显式、不虚构数字、判据与参数必须写入报告。',
        parameters: {
            action: { type: 'string', required: true, enum: ACTIONS.slice(), description: '要执行的工作流动作' },
            workdir: { type: 'string', description: '项目工作目录（绝对路径；缺省尝试会话工作目录）' },
            input_path: { type: 'string', description: '输入文件（standardize=原始数据；fit/bet/psd=标准等温线 CSV；iast/breakthrough=组分1 CSV；qst=多温度 CSV 目录或逗号分隔列表；productivity=穿透 CSV）' },
            second_isotherm: { type: 'string', description: 'iast/breakthrough: 组分 2 的标准等温线 CSV' },
            pressure_col: { type: 'string', description: 'standardize: 压力列名' },
            pressure_unit: { type: 'string', enum: ['bar', 'pa', 'kpa', 'mpa', 'torr', 'mmhg', 'atm', 'mbar', 'psi'], description: 'standardize: 压力单位' },
            loading_col: { type: 'string', description: 'standardize: 吸附量列名' },
            loading_unit: { type: 'string', enum: ['mmol_g', 'mol_g', 'mol_kg', 'cm3stp_g', 'cc_g', 'cm3_g', 'ml_g', 'mg_g'], description: 'standardize: 吸附量单位（mg_g 需 molar_mass_g_mol）' },
            molar_mass_g_mol: { type: 'string', description: 'standardize: loading_unit=mg_g 时的摩尔质量 g/mol' },
            temp_k: { type: 'string', description: '温度 K（standardize 固定温度 / bet / psd）' },
            model: { type: 'string', enum: ['DSLF', 'Langmuir', 'Quadratic'], description: 'fit: 拟合模型' },
            y1: { type: 'string', description: 'iast/breakthrough: 组分 1 进料摩尔分数（默认 0.15）' },
            p_max_bar: { type: 'string', description: 'iast: 最大总压 bar（默认 1.0）' },
            n_points: { type: 'string', description: 'iast: 扫压点数（默认 30）' },
            p_limits: { type: 'string', description: 'bet: P/P0 区间 "0.01,0.30"' },
            loading_points: { type: 'string', description: 'qst: 吸附量点列表 "0.5,1,2,3,5"' },
            kernel: { type: 'string', description: 'psd: kernels/ 内 kernel 文件名（默认 NLDFT-mod200.csv）' },
            p0_bar: { type: 'string', description: 'psd: 饱和蒸气压 bar（默认 N2 77K=1.0 / Ar 87K=1.0 / CO2 273K=34.85）' },
            hk: { type: 'string', description: 'psd: 附加 HK 微孔（传 "1"）' },
            bjh: { type: 'string', description: 'psd: 附加 BJH 介孔（传 "1"）' },
            t_plot: { type: 'string', description: 'psd: 附加 t-plot（传 "1"）' },
            pressure_bar: { type: 'string', description: 'breakthrough: 总压 bar（默认 1.0）' },
            col_length_m: { type: 'string', description: 'breakthrough: 柱长 m（默认 0.5）' },
            void_frac: { type: 'string', description: 'breakthrough: 床层空隙率（默认 0.4）' },
            density_kg_m3: { type: 'string', description: 'breakthrough: 颗粒密度 kg/m3（默认 1000）' },
            time_step_s: { type: 'string', description: 'breakthrough: 时间步 s（默认 0.05）' },
            n_steps: { type: 'string', description: 'breakthrough: 时间步数（默认 2000）' },
            time_col: { type: 'string', description: 'productivity: 时间列名（默认 time_min）' },
            cols: { type: 'string', description: 'productivity: C/C0 列名，逗号分隔（必填）' },
            feed_fracs: { type: 'string', description: 'productivity: 进料摩尔分数，逗号分隔' },
            flow_ml_min: { type: 'string', description: 'productivity: 进料流量 STP mL/min' },
            mass_g: { type: 'string', description: 'productivity: 吸附剂质量 g' },
            desorb_from: { type: 'string', description: 'productivity: 解吸开始 min' },
            desorb_to: { type: 'string', description: 'productivity: 解吸结束 min' },
            bt_frac: { type: 'string', description: 'productivity: 穿透判定分数（默认 0.05）' },
            output_path: { type: 'string', description: 'standardize/productivity: 输出文件路径' },
            out_dir: { type: 'string', description: '输出目录（缺省 workdir）' },
            stage: { type: 'string', description: 'guide: 判据阶段名' },
        },
        output: {
            schema: {
                type: 'object',
                additionalProperties: false,
                properties: {
                    ok: { type: 'boolean', required: true },
                    action: { type: 'string', required: true },
                    gate: { oneOf: [{ type: 'string' }, { type: 'null' }], required: true },
                    summary: { type: 'string', required: true },
                    data: { type: 'object', additionalProperties: true, required: true },
                    tail: { type: 'string', required: true },
                    guidance: { oneOf: [{ type: 'string' }, { type: 'null' }], required: true },
                },
            },
            render(args, value) {
                const v = value || {}
                const parts = ['[adsorption:' + v.action + '] ' + (v.ok ? '成功' : '失败'), v.summary || '']
                if (v.gate) parts.push('证据门: ' + v.gate)
                if (v.guidance) parts.push('【工作流判据】\n' + v.guidance)
                if (v.tail) parts.push('【输出摘录】\n' + v.tail)
                return [{ type: 'text', text: parts.join('\n\n').slice(0, 16000) }]
            },
        },
        timeoutMs: 900000,
        async execute(args, exec) {
            const signal = exec && exec.signal ? exec.signal : undefined
            const cwd = exec && exec.agent && typeof exec.agent.cwd === 'string' ? exec.agent.cwd : undefined
            return performAction(args, signal, cwd)
        },
    })
    ctx.tools.register(tool)
}

module.exports = { name, inject, apply }

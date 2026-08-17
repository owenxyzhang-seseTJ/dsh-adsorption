#!/usr/bin/env bash
# =============================================================================
# dsh-adsorption 一键安装脚本
#
# 安装内容:
#   1. 检查/创建 conda 环境（默认 pyiast-env，Python 3.12）并安装计算栈
#      (pyiast, pygaps, ruptura, numpy, scipy, pandas, matplotlib, openpyxl, CoolProp)
#   2. 安装插件本体到 $DSH_HOME/profiles/node_modules/dsh-adsorption
#   3. （可选，macOS 默认开）修补 RUPTURA wheel 的 use-after-free（源码重编译）
#   4. 输出环境变量配置说明（DSH_ADSORPTION_PYTHON / DSH_ADSORPTION_RASPA3）
#
# 用法:
#   bash install.sh                    # 全自动
#   bash install.sh --no-ruptura-patch # 跳过 RUPTURA 重编译
#   bash install.sh --env myenv        # 使用/创建指定 conda 环境名
#   DSH_ADSORPTION_RASPA3=/path/to/raspa3 bash install.sh
#
# RASPA3 说明:
#   本脚本不负责 RASPA3 的编译/下载（体系相关且体积大）。
#   官方仓库与编译安装指引: https://github.com/iRASPA/RASPA3
#   装好后把二进制路径写入环境变量 DSH_ADSORPTION_RASPA3，或放入 PATH（自动探测）。
# =============================================================================
set -euo pipefail

NO_PATCH=0
ENV_NAME="pyiast-env"
while [ $# -gt 0 ]; do
  case "$1" in
    --no-ruptura-patch) NO_PATCH=1; shift ;;
    --env) ENV_NAME="${2:?用法: --env <name>}"; shift 2 ;;
    *) echo "未知参数: $1"; exit 2 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
PLUGIN_DST="$DSH_HOME/profiles/node_modules/dsh-adsorption"

echo "==> dsh-adsorption 一键安装"
echo "    插件目录 : $HERE"
echo "    安装目标 : $PLUGIN_DST"
echo "    conda 环境: $ENV_NAME"

# ── 1. conda 环境与计算栈 ───────────────────────────────────────────────
CONDA_BIN="$(command -v conda || true)"
if [ -z "$CONDA_BIN" ]; then
  cat <<'EOF'
!! 未找到 conda。请先安装 Miniforge: https://github.com/conda-forge/miniforge/releases
   或使用已有 Python 3.12 环境，设置 DSH_ADSORPTION_PYTHON 后重跑本脚本。
EOF
  exit 1
fi

if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  echo "==> 环境 $ENV_NAME 已存在，复用。"
else
  echo "==> 创建 conda 环境 $ENV_NAME（Python 3.12）..."
  conda create -y -n "$ENV_NAME" python=3.12
fi

PY_BIN="$(conda run -n "$ENV_NAME" which python)"
echo "==> 安装计算栈到 $ENV_NAME ..."
"$PY_BIN" -m pip install --quiet --upgrade pip
"$PY_BIN" -m pip install --quiet pyiast pygaps ruptura numpy scipy pandas matplotlib openpyxl CoolProp

"$PY_BIN" - <<'PYEOF'
import importlib.util
missing = [m for m in ("pyiast", "pygaps", "ruptura", "numpy", "scipy", "pandas", "matplotlib")
           if importlib.util.find_spec(m) is None]
if missing:
    raise SystemExit("缺失包: " + ", ".join(missing))
print("    计算栈 OK: pyiast / pygaps / ruptura / numpy / scipy / pandas / matplotlib")
PYEOF

# ── 2. 安装插件本体 ─────────────────────────────────────────────────────
mkdir -p "$DSH_HOME/profiles/node_modules"
rm -rf "$PLUGIN_DST"
cp -R "$HERE" "$PLUGIN_DST"
rm -rf "$PLUGIN_DST/.git" "$PLUGIN_DST/.github"
echo "==> 插件已安装: $PLUGIN_DST"
echo "    在 agent 预设（\$DSH_HOME/.agent-presets/<id>/agent.cordis.yml）中加一行:"
echo "      - id: adsorption-plugin"
echo "        name: 'dsh-adsorption'"

# ── 3.（可选）macOS 修补 RUPTURA wheel 的 use-after-free ───────────────
if [ "$NO_PATCH" -eq 0 ] && [ "$(uname -s)" = "Darwin" ]; then
  RUPTURA_DIR="$("$PY_BIN" -c "import pathlib, ruptura; print(pathlib.Path(ruptura.__file__).parent)")"
  SO="$("$PY_BIN" -c "import ruptura, pathlib, importlib.machinery as m; print(str(pathlib.Path(ruptura.__file__).parent.parent / ('_ruptura' + m.EXTENSION_SUFFIXES[0])))")"
  if grep -q "py_breakthrough.resize" "$RUPTURA_DIR/breakthrough.cpp" 2>/dev/null; then
    if ! command -v clang++ >/dev/null 2>&1; then
      echo "!! 需要 clang++（安装 Xcode Command Line Tools: xcode-select --install），跳过 RUPTURA 修补"
    else
      echo "==> 检测到 RUPTURA use-after-free，开始重编译修补..."
      "$PY_BIN" -m pip install --quiet pybind11
      PYBIND_INC="$("$PY_BIN" -m pybind11 --includes)"
      PY_INC="$("$PY_BIN" -c "import sysconfig; print(sysconfig.get_path('include'))")"
      [ -f "$SO" ] && cp "$SO" "$SO.bak"
      ( cd "$RUPTURA_DIR" && \
        clang++ -O2 -std=c++17 -fPIC -shared -DPYBUILD -undefined dynamic_lookup \
          -I"$PY_INC" $PYBIND_INC \
          breakthrough.cpp bindings.cpp component.cpp inputreader.cpp multi_site_isotherm.cpp \
          isotherm.cpp fitting.cpp special_functions.cpp random_numbers.cpp mixture_prediction.cpp \
          -o "$SO" )
      echo "==> RUPTURA 已重编译修复（原 .so 备份为 .so.bak）"
    fi
  else
    echo "==> RUPTURA 源码已含修复（跳过重编译）"
  fi
fi

# ── 4. 环境变量说明 ─────────────────────────────────────────────────────
cat <<EOF

==> 安装完成 ✅
    建议在 shell 配置（~/.zshrc / ~/.bashrc）中追加:
      export DSH_ADSORPTION_PYTHON="$PY_BIN"
      export DSH_ADSORPTION_RASPA3="<raspa3 二进制路径，可省略>"

    RASPA3 官方仓库与编译安装指引: https://github.com/iRASPA/RASPA3
    能力: 等温线拟合 / IAST / BET / Qst / NLDFT 孔径分布（48 kernel）/ 穿透模拟 / 产率计算
EOF

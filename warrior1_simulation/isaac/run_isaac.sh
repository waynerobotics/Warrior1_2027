#!/usr/bin/env bash
# Start the Warrior in Isaac Sim.
#
# Isaac Sim ships its own Python and its own copy of the ROS 2 Jazzy
# libraries, so it must NOT run inside the pixi environment (mixing the two
# sets of ROS libraries crashes). This wrapper starts Isaac's Python with a
# clean environment and the bundled ROS 2 libraries. It talks to the pixi ROS
# graph over DDS, exactly like a separate robot on the network would.
#
# Where Isaac Sim is, first match wins:
#   ISAAC_SIM_PATH=~/isaacsim                 (workstation zip / container: has python.sh)
#   ISAAC_PYTHON=~/isaacsim-venv/bin/python   (your own pip install of isaacsim)
#   <repo>/.pixi/envs/isaac                   (pixi install -e isaac; the default)
#
# Examples:
#   run_isaac.sh                       # GUI, URDF read from /robot_description
#   run_isaac.sh --headless --livestream
#   run_isaac.sh --urdf /tmp/warrior.urdf --world my_scene.usd
#
# Must use the same ROS_DOMAIN_ID as the machine running
#   ros2 launch warrior1_bringup sim.launch.py simulator:=isaac
set -euo pipefail

HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
SCRIPT="$HERE/run_isaac.py"

# The pixi `isaac` environment of this checkout (HERE resolves to the source
# tree even when called through install/, because colcon symlinks it).
REPO_ROOT="${PIXI_PROJECT_ROOT:-$(cd "$HERE/../.." && pwd)}"
PIXI_ISAAC="$REPO_ROOT/.pixi/envs/isaac"
PIXI_ISAAC_PYTHON="$PIXI_ISAAC/bin/python"
# Check for the isaacsim package, not just python: `pixi lock` alone creates
# the environment with a bare python in it.
if [[ -z "${ISAAC_SIM_PATH:-}" && -z "${ISAAC_PYTHON:-}" \
      && -d "$PIXI_ISAAC/lib/python3.12/site-packages/isaacsim" ]]; then
    ISAAC_PYTHON="$PIXI_ISAAC_PYTHON"
fi

ros_env=()
lib_path=()
if [[ -n "${ISAAC_SIM_PATH:-}"&& -x "${ISAAC_SIM_PATH}/python.sh" ]]; then
    PYTHON=("${ISAAC_SIM_PATH}/python.sh")
    # Isaac's launcher picks the bundled ROS 2 libraries itself when no ROS
    # environment is sourced, which is what the clean env below guarantees.
elif [[ -n "${ISAAC_PYTHON:-}" && -x "${ISAAC_PYTHON}" ]]; then
    PYTHON=("${ISAAC_PYTHON}")
    # pip installs have no launcher, so point at the bundled Jazzy libraries.
    site=$(env -i HOME="$HOME" "$ISAAC_PYTHON" -c \
        'import isaacsim, os; print(os.path.dirname(isaacsim.__file__))')
    ros_lib=$(find "$site" -maxdepth 6 -type d -path '*isaacsim.ros2.core/jazzy/lib' 2>/dev/null | head -1)
    if [[ -z "$ros_lib" ]]; then
        echo "run_isaac.sh: bundled ROS 2 Jazzy libraries not found under $site" >&2
        exit 1
    fi
    ros_env=(ROS_DISTRO=jazzy RMW_IMPLEMENTATION=rmw_fastrtps_cpp)
    lib_path=("$ros_lib")
else
    cat >&2 <<'EOF'
run_isaac.sh: Isaac Sim not found. Either
  pixi install -e isaac                     (recommended, version pinned by pixi.lock)
or set one of
  ISAAC_SIM_PATH=/path/to/isaacsim          (directory containing python.sh)
  ISAAC_PYTHON=/path/to/venv/bin/python     (your own pip install of isaacsim)
See warrior1_simulation/isaac/README.md
EOF
    exit 1
fi

# Clean environment: drop everything pixi/conda/ROS put in this shell, keep
# only what a GUI app and DDS need.
keep=(HOME USER LOGNAME LANG TERM DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR XAUTHORITY
      ROS_DOMAIN_ID ROS_LOCALHOST_ONLY ROS_AUTOMATIC_DISCOVERY_RANGE ROS_STATIC_PEERS
      FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE
      ACCEPT_EULA OMNI_KIT_ACCEPT_EULA PRIVACY_CONSENT
      NVIDIA_VISIBLE_DEVICES CUDA_VISIBLE_DEVICES)
clean_env=(PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin)
for var in "${keep[@]}"; do
    if [[ -n "${!var:-}" ]]; then
        clean_env+=("$var=${!var}")
    fi
done

# Isaac's FBX importer links libxml2.so.2, which distros on libxml2 >= 2.14
# (Arch, Fedora 42+, Ubuntu 25.10+) no longer ship. Expose ONLY that
# library from the pixi isaac env (adding its whole lib/ could shadow libraries
# Isaac bundles); its own deps resolve next to the symlink target.
if ! /sbin/ldconfig -p 2>/dev/null | grep -q 'libxml2\.so\.2 '; then
    if [[ -e "$PIXI_ISAAC/lib/libxml2.so.2" ]]; then
        compat="$PIXI_ISAAC/lib/warrior1-compat"
        mkdir -p "$compat"
        ln -sfn ../libxml2.so.2 "$compat/libxml2.so.2"
        lib_path+=("$compat")
    else
        echo "run_isaac.sh: host has no libxml2.so.2; Isaac's FBX importer will fail to load" \
             "(harmless for URDF import). Fix: pixi install -e isaac" >&2
    fi
fi
# Isaac's renderer aborts with ERROR_OUT_OF_DEVICE_MEMORY when other programs
# hold most of the VRAM; say so up front instead of after a crash.
if command -v nvidia-smi >/dev/null 2>&1; then
    free_mib=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null \
               | sort -n | tail -1 || true)
    if [[ "$free_mib" =~ ^[0-9]+$ ]] && (( free_mib < 8000 )); then
        echo "run_isaac.sh: WARNING: only ${free_mib} MiB of GPU memory free; Isaac Sim" \
             "needs about 8 GB and may crash. See what is using it: nvidia-smi" >&2
    fi
fi

if (( ${#lib_path[@]} )); then
    ros_env+=("LD_LIBRARY_PATH=$(IFS=:; echo "${lib_path[*]}")")
fi

exec env -i "${clean_env[@]}" "${ros_env[@]}" "${PYTHON[@]}" "$SCRIPT" "$@"

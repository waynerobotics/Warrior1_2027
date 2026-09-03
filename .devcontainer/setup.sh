#!/bin/bash
# Detects this machine's platform + GPU capability and writes:
#   .devcontainer/.env
#   .devcontainer/docker-compose.override.yml
# so the shared devcontainer.json / docker-compose.yml never need editing.
#
# Run manually: ./setup.sh
# Or let it run automatically via devcontainer.json's initializeCommand.
#
# Flags (all optional — auto-detected if omitted):
#   --gui=true|false        Enable any GUI at all (default: true)
#   --accel=auto|software   Force software rendering even if a GPU is found
set -e
cd "$(dirname "$0")"

ENABLE_GUI="true"
FORCE_SOFTWARE="false"
for arg in "$@"; do
    case "$arg" in
        --gui=false) ENABLE_GUI="false" ;;
        --gui=true) ENABLE_GUI="true" ;;
        --accel=software) FORCE_SOFTWARE="true" ;;
    esac
done

OS="$(uname -s)"
IS_WSL2="false"
if [ "$OS" = "Linux" ] && grep -qi microsoft /proc/version 2>/dev/null; then
    IS_WSL2="true"
fi

DISPLAY_MODE="novnc"
PROFILE="software-novnc"

if [ "$FORCE_SOFTWARE" = "true" ]; then
    PROFILE="software-novnc"

elif [ "$OS" = "Linux" ] && [ "$IS_WSL2" = "false" ]; then
    # Native Linux
    if [ -e /dev/dri/renderD128 ] && [ -d /tmp/.X11-unix ]; then
        PROFILE="linux-gpu-native-x11"
        DISPLAY_MODE="native"
    elif [ -e /dev/dri/renderD128 ]; then
        PROFILE="linux-gpu-novnc"
    fi

elif [ "$IS_WSL2" = "true" ]; then
    # Windows via WSL2
    if [ -e /dev/dxg ] && [ -d /mnt/wslg ]; then
        PROFILE="wsl2-gpu-wslg-native"
        DISPLAY_MODE="native"
    elif [ -e /dev/dxg ]; then
        PROFILE="wsl2-gpu-novnc"
    fi
fi
# macOS (Darwin) always falls through to software-novnc — Docker Desktop
# for Mac has no GPU passthrough mechanism.

echo "Detected: OS=$OS  WSL2=$IS_WSL2  ->  profile=$PROFILE  display_mode=$DISPLAY_MODE"

# --- X11 permission grant (native Linux profile only) ----------------------
if [ "$PROFILE" = "linux-gpu-native-x11" ]; then
    if command -v xhost >/dev/null 2>&1; then
        if xhost +local:docker >/dev/null 2>&1; then
            echo "xhost: granted local Docker containers access to your X server"
        else
            echo "WARNING: 'xhost +local:docker' failed to run. GUI apps will" >&2
            echo "         likely fail with 'could not connect to display'." >&2
            echo "         Try running it manually: xhost +local:docker" >&2
        fi
    else
        echo "WARNING: 'xhost' command not found on this host." >&2
        echo "         Install it: sudo apt install x11-xserver-utils" >&2
        echo "         Then run:   xhost +local:docker" >&2
        echo "         Without this, GUI apps will fail to connect to your display." >&2
    fi
fi

cat > .env <<EOF
ENABLE_GUI=$ENABLE_GUI
DISPLAY_MODE=$DISPLAY_MODE
EOF

case "$PROFILE" in

linux-gpu-native-x11)
    cat > docker-compose.override.yml <<'EOF'
services:
  ros2:
    devices:
      - /dev/dri:/dev/dri
    group_add:
      - video
      - render
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
    environment:
      DISPLAY: ${DISPLAY}
      LIBGL_ALWAYS_SOFTWARE: ""
EOF
    ;;

linux-gpu-novnc)
    cat > docker-compose.override.yml <<'EOF'
services:
  ros2:
    devices:
      - /dev/dri:/dev/dri
    group_add:
      - video
      - render
    environment:
      LIBGL_ALWAYS_SOFTWARE: ""
EOF
    ;;

wsl2-gpu-wslg-native)
    cat > docker-compose.override.yml <<'EOF'
services:
  ros2:
    devices:
      - /dev/dxg:/dev/dxg
    volumes:
      - /usr/lib/wsl:/usr/lib/wsl:ro
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
      - /mnt/wslg:/mnt/wslg:rw
    environment:
      DISPLAY: ${DISPLAY}
      WAYLAND_DISPLAY: ${WAYLAND_DISPLAY}
      XDG_RUNTIME_DIR: ${XDG_RUNTIME_DIR}
      LD_LIBRARY_PATH: /usr/lib/wsl/lib
      LIBGL_ALWAYS_SOFTWARE: ""
EOF
    ;;

wsl2-gpu-novnc)
    cat > docker-compose.override.yml <<'EOF'
services:
  ros2:
    devices:
      - /dev/dxg:/dev/dxg
    volumes:
      - /usr/lib/wsl:/usr/lib/wsl:ro
    environment:
      LD_LIBRARY_PATH: /usr/lib/wsl/lib
      LIBGL_ALWAYS_SOFTWARE: ""
EOF
    ;;

*)
    cat > docker-compose.override.yml <<'EOF'
# No GPU passthrough available/selected — software rendering + noVNC.
services:
  ros2: {}
EOF
    ;;
esac

echo "Wrote .devcontainer/.env and .devcontainer/docker-compose.override.yml"
echo ""
echo "Next steps:"
echo "  docker compose build"
echo "  docker compose up -d --force-recreate"

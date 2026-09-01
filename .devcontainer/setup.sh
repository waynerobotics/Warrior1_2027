#!/bin/bash
# Detects this machine's platform + GPU capability and writes:
#   .devcontainer/docker-compose.override.yml
#   .devcontainer/.env
# so the shared devcontainer.json / docker-compose.yml never need editing.
#
# Run manually once: ./setup.sh
# Or let it run automatically via devcontainer.json's initializeCommand
# every time the container is (re)built.
#
# Flags (all optional — auto-detected if omitted):
#   --gui=true|false      Enable any GUI at all (default: true)
#   --accel=auto|software Force software rendering even if a GPU is found
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
    if [ -e /dev/dri/renderD128 ] && [ -e /tmp/.X11-unix ]; then
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
# macOS (Darwin) always falls through to software-novnc — no GPU
# passthrough path exists in Docker Desktop for Mac.

echo "Detected: OS=$OS  WSL2=$IS_WSL2  ->  profile=$PROFILE  display_mode=$DISPLAY_MODE"

cat > .env <<EOF
ENABLE_GUI=$ENABLE_GUI
DISPLAY_MODE=$DISPLAY_MODE
EOF

case "$PROFILE" in

linux-gpu-native-x11)
    xhost +local:docker >/dev/null 2>&1 || true
    cat > docker-compose.override.yml <<EOF
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
      DISPLAY: \${DISPLAY}
      LIBGL_ALWAYS_SOFTWARE: ""
EOF
    ;;

linux-gpu-novnc)
    cat > docker-compose.override.yml <<EOF
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
    cat > docker-compose.override.yml <<EOF
services:
  ros2:
    devices:
      - /dev/dxg:/dev/dxg
    volumes:
      - /usr/lib/wsl:/usr/lib/wsl:ro
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
      - /mnt/wslg:/mnt/wslg:rw
    environment:
      DISPLAY: \${DISPLAY}
      WAYLAND_DISPLAY: \${WAYLAND_DISPLAY}
      XDG_RUNTIME_DIR: \${XDG_RUNTIME_DIR}
      LD_LIBRARY_PATH: /usr/lib/wsl/lib
      LIBGL_ALWAYS_SOFTWARE: ""
EOF
    ;;

wsl2-gpu-novnc)
    cat > docker-compose.override.yml <<EOF
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
    cat > docker-compose.override.yml <<EOF
# No GPU passthrough available/selected — software rendering + noVNC.
services:
  ros2: {}
EOF
    ;;
esac

echo "Wrote .devcontainer/.env and .devcontainer/docker-compose.override.yml"

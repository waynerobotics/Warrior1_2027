#!/bin/bash
# Detects this machine's display server and writes:
#   .devcontainer/.env
#   .devcontainer/docker-compose.override.yml
# so the shared devcontainer.json / docker-compose.yml never need editing.
#
# Run manually: ./setup.sh
# Or let it run automatically via devcontainer.json's initializeCommand.
#
# Flags (all optional — auto-detected if omitted):
#   --gui=true|false        Enable any GUI at all (default: true)
#   --accel=software|hardware
#                          Select the renderer (default: software).
set -e
cd "$(dirname "$0")"

ENABLE_GUI="true"
ACCEL="software"
if [ -z "${ACCEL_MODE:-}" ] && [ -f .env ]; then
  SAVED_ACCEL="$(sed -n 's/^ACCEL_MODE=//p' .env | head -n 1)"
  case "$SAVED_ACCEL" in
    software|hardware) ACCEL="$SAVED_ACCEL" ;;
  esac
fi
for arg in "$@"; do
    case "$arg" in
        --gui=false) ENABLE_GUI="false" ;;
        --gui=true) ENABLE_GUI="true" ;;
    --accel=software) ACCEL="software" ;;
    --accel=hardware) ACCEL="hardware" ;;
    *) echo "ERROR: unknown option: $arg" >&2; exit 2 ;;
    esac
done

OS="$(uname -s)"
IS_WSL2="false"
if [ "$OS" = "Linux" ] && grep -qi microsoft /proc/version 2>/dev/null; then
    IS_WSL2="true"
fi

DISPLAY_MODE="none"
PROFILE="headless"
DISPLAY_VALUE="${DISPLAY:-}"
WAYLAND_DISPLAY_VALUE="${WAYLAND_DISPLAY:-}"
XDG_RUNTIME_DIR_VALUE="${XDG_RUNTIME_DIR:-}"

if [ "$ENABLE_GUI" = "true" ] && [ "$IS_WSL2" = "true" ] && [ -d /mnt/wslg ] && [ -d /tmp/.X11-unix ]; then
  if [ "$ACCEL" = "hardware" ] && [ -e /dev/dxg ]; then
    PROFILE="hardware-native-wslg"
  else
    PROFILE="software-native-wslg"
  fi
  DISPLAY_MODE="native"
  DISPLAY_VALUE="${DISPLAY_VALUE:-:0}"
  WAYLAND_DISPLAY_VALUE="${WAYLAND_DISPLAY_VALUE:-wayland-0}"
  XDG_RUNTIME_DIR_VALUE="/mnt/wslg/runtime-dir"

elif [ "$ENABLE_GUI" = "true" ] && [ "$OS" = "Linux" ] && [ -d /tmp/.X11-unix ]; then
  if [ "$ACCEL" = "hardware" ] && [ -e /dev/dri/renderD128 ]; then
    PROFILE="hardware-native-x11"
  else
    PROFILE="software-native-x11"
  fi
  DISPLAY_MODE="native"
  DISPLAY_VALUE="${DISPLAY_VALUE:-:0}"
fi

if [ "$ACCEL" = "hardware" ] && [[ "$PROFILE" != hardware-* ]]; then
  echo "WARNING: hardware acceleration was requested but no supported GPU device was found; using software rendering." >&2
fi

echo "Detected: OS=$OS  WSL2=$IS_WSL2  ->  profile=$PROFILE  display_mode=$DISPLAY_MODE  accel=$ACCEL"

# --- X11 permission grant (native Linux profile only) ----------------------
if [ "$PROFILE" = "software-native-x11" ]; then
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
ACCEL_MODE=$ACCEL
DISPLAY=$DISPLAY_VALUE
WAYLAND_DISPLAY=$WAYLAND_DISPLAY_VALUE
XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR_VALUE
EOF

case "$PROFILE" in

software-native-x11)
  cat > docker-compose.override.yml <<EOF
services:
  ros2:
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
    environment:
      DISPLAY: $DISPLAY_VALUE
      LIBGL_ALWAYS_SOFTWARE: "1"
      GALLIUM_DRIVER: llvmpipe
      MESA_LOADER_DRIVER_OVERRIDE: llvmpipe
EOF
    ;;

hardware-native-x11)
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
      DISPLAY: $DISPLAY_VALUE
      LIBGL_ALWAYS_SOFTWARE: ""
EOF
    ;;

software-native-wslg)
  cat > docker-compose.override.yml <<EOF
services:
  ros2:
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
      - /mnt/wslg:/mnt/wslg:rw
    environment:
      DISPLAY: $DISPLAY_VALUE
      WAYLAND_DISPLAY: $WAYLAND_DISPLAY_VALUE
      XDG_RUNTIME_DIR: $XDG_RUNTIME_DIR_VALUE
      LIBGL_ALWAYS_SOFTWARE: "1"
      GALLIUM_DRIVER: llvmpipe
      MESA_LOADER_DRIVER_OVERRIDE: llvmpipe
EOF
    ;;

hardware-native-wslg)
  cat > docker-compose.override.yml <<EOF
services:
  ros2:
    devices:
      - /dev/dxg:/dev/dxg
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
      - /mnt/wslg:/mnt/wslg:rw
      - /usr/lib/wsl:/usr/lib/wsl:ro
    environment:
      DISPLAY: $DISPLAY_VALUE
      WAYLAND_DISPLAY: $WAYLAND_DISPLAY_VALUE
      XDG_RUNTIME_DIR: $XDG_RUNTIME_DIR_VALUE
      LD_LIBRARY_PATH: /usr/lib/wsl/lib
      LIBGL_ALWAYS_SOFTWARE: ""
EOF
    ;;

*)
    cat > docker-compose.override.yml <<'EOF'
# No host display socket was detected. GUI applications require a local
# X11/WSLg session; no virtual display or browser relay is started.
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

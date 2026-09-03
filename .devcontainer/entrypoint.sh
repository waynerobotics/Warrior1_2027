#!/bin/bash
set -e

# ENABLE_GUI: true/false — whether any GUI stack should run at all.
# DISPLAY_MODE: novnc | native
#   novnc  -> run our own Xvfb + x11vnc + noVNC (works everywhere, some overhead)
#   native -> DISPLAY/WAYLAND_DISPLAY point at a host-forwarded socket
#             (Linux X11, or WSLg on Windows 11) mounted in by
#             docker-compose.override.yml. We do NOT start Xvfb/x11vnc/
#             novnc in this mode — apps talk to the host compositor directly.

if [ "${ENABLE_GUI:-true}" = "true" ] && [ "${DISPLAY_MODE:-novnc}" = "novnc" ]; then
    if ! pgrep -f "supervisord -c /etc/supervisor/supervisord.conf" > /dev/null; then
        sudo supervisord -c /etc/supervisor/supervisord.conf
    fi
fi
# In "native" mode or with GUI disabled, nothing extra needs to start —
# DISPLAY is already set correctly by the environment (either unset for
# headless, or pointed at the mounted host socket for native mode).

exec "$@"

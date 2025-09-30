#!/bin/bash
# Omarchy Ambient Lighting Setup Script
# Sets up automatic ambient lighting with power management

set -e

echo "=================================="
echo "Omarchy Ambient Lighting Setup"
echo "=================================="
echo

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please run as normal user (not root)${NC}"
   exit 1
fi

echo -e "${YELLOW}Step 1: Installing dependencies...${NC}"
# Install required packages
sudo pacman -S --needed python python-numpy python-pyserial python-pillow grim

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo

echo -e "${YELLOW}Step 2: Setting up Python script...${NC}"
# Copy the Python script to /usr/local/bin
sudo cp hyprlight2 /usr/local/bin/hypr-ambilight
sudo chmod +x /usr/local/bin/hypr-ambilight

echo -e "${GREEN}✓ Script installed to /usr/local/bin/hypr-ambilight${NC}"
echo

echo -e "${YELLOW}Step 3: Setting up serial port permissions...${NC}"
# Add user to dialout group for serial port access
sudo usermod -a -G dialout $USER

# Create udev rule for RP2040
sudo tee /etc/udev/rules.d/99-rp2040.rules > /dev/null <<EOF
# RP2040 for ambient lighting
SUBSYSTEM=="tty", ATTRS{idVendor}=="2e8a", ATTRS{idProduct}=="000a", MODE="0666", GROUP="dialout", SYMLINK+="ambilight"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger

echo -e "${GREEN}✓ Serial permissions configured${NC}"
echo -e "${YELLOW}Note: You'll need to log out and back in for group changes to take effect${NC}"
echo

echo -e "${YELLOW}Step 4: Creating systemd user service...${NC}"
# Create systemd user service directory
mkdir -p ~/.config/systemd/user/

# Create the service file
cat > ~/.config/systemd/user/ambilight.service <<EOF
[Unit]
Description=Ambient Lighting for Omarchy
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/local/bin/hypr-ambilight --brightness 1.0 --saturation 1.0 --fps 60
Restart=on-failure
RestartSec=5

# Wait for display to be ready
ExecStartPre=/bin/sleep 3

[Install]
WantedBy=default.target
EOF

echo -e "${GREEN}✓ Systemd service created${NC}"
echo

echo -e "${YELLOW}Step 5: Setting up power management...${NC}"
# Create script to handle sleep/wake
mkdir -p ~/.config/omarchy/scripts/
cat > ~/.config/omarchy/scripts/ambilight-suspend.sh <<'EOF'
#!/bin/bash
# Suspend/resume handler for ambient lighting

case "$1" in
    pre)
        # Before sleep - stop the service
        systemctl --user stop ambilight.service
        ;;
    post)
        # After wake - restart the service
        systemctl --user start ambilight.service
        ;;
esac
EOF

chmod +x ~/.config/omarchy/scripts/ambilight-suspend.sh

# Create systemd sleep hook
sudo tee /usr/lib/systemd/system-sleep/ambilight-sleep > /dev/null <<EOF
#!/bin/bash
# Ambient lighting sleep handler

USER_NAME="$USER"

case "\$1" in
    pre)
        # Before sleep
        sudo -u \$USER_NAME DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/\$(id -u \$USER_NAME)/bus systemctl --user stop ambilight.service
        ;;
    post)
        # After wake
        sleep 2
        sudo -u \$USER_NAME DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/\$(id -u \$USER_NAME)/bus systemctl --user start ambilight.service
        ;;
esac
EOF

sudo chmod +x /usr/lib/systemd/system-sleep/ambilight-sleep

echo -e "${GREEN}✓ Power management configured${NC}"
echo

echo -e "${YELLOW}Step 6: Setting up screensaver detection...${NC}"
# Create idle detection script for Hyprland
cat > ~/.config/omarchy/scripts/idle-handler.sh <<'EOF'
#!/bin/bash
# Idle handler for ambient lighting using Hyprland's hyprctl

swayidle -w \
    timeout 300 'systemctl --user stop ambilight.service' \
    resume 'systemctl --user start ambilight.service' \
    before-sleep 'systemctl --user stop ambilight.service' \
    after-resume 'systemctl --user start ambilight.service'
EOF

chmod +x ~/.config/omarchy/scripts/idle-handler.sh

# Check if swayidle is installed
if ! command -v swayidle &> /dev/null; then
    echo -e "${YELLOW}Installing swayidle for idle detection...${NC}"
    sudo pacman -S --needed swayidle
fi

# Create systemd service for idle detection
cat > ~/.config/systemd/user/ambilight-idle.service <<EOF
[Unit]
Description=Ambient Lighting Idle Detection
After=graphical-session.target

[Service]
Type=simple
ExecStart=/home/$USER/.config/omarchy/scripts/idle-handler.sh
Restart=on-failure

[Install]
WantedBy=default.target
EOF

echo -e "${GREEN}✓ Screensaver detection configured${NC}"
echo

echo "=================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=================================="
echo
echo "Next steps:"
echo "1. Log out and log back in (for group permissions)"
echo "2. Plug in your RP2040"
echo "3. Enable and start the service:"
echo "   systemctl --user enable ambilight.service"
echo "   systemctl --user start ambilight.service"
echo "4. Enable idle detection:"
echo "   systemctl --user enable ambilight-idle.service"
echo "   systemctl --user start ambilight-idle.service"
echo
echo "Check status with:"
echo "   systemctl --user status ambilight.service"
echo
echo "View logs with:"
echo "   journalctl --user -u ambilight.service -f"
echo
echo "Test the toggle with:"
echo "   pkill -USR1 hypr-ambilight"
echo

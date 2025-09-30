#!/usr/bin/env python3
"""
Ambient Lighting Configuration Manager
Manages settings and provides CLI/GUI interface for ambilight control
"""

import json
import os
import subprocess
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "ambilight"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "brightness": 1.0,
    "saturation": 1.0,
    "fps": 60,
    "smoothing": 0.15,
    "border": 30,
    "auto_crop": True,
    "crop_threshold": 15,
    "manual_crop_top": 0,
    "manual_crop_bottom": 0,
    "min_content_ratio": 0.6,
    "enabled": True
}

class AmbilightConfig:
    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    
    def save_config(self, config=None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()
    
    def build_command_args(self):
        """Build command line arguments from config"""
        args = [
            "--brightness", str(self.config["brightness"]),
            "--saturation", str(self.config["saturation"]),
            "--fps", str(self.config["fps"]),
            "--smoothing", str(self.config["smoothing"]),
            "--border", str(self.config["border"]),
            "--crop-threshold", str(self.config["crop_threshold"]),
            "--min-content-ratio", str(self.config["min_content_ratio"])
        ]
        
        if not self.config["auto_crop"]:
            args.append("--no-auto-crop")
        
        if self.config["manual_crop_top"] > 0:
            args.extend(["--crop-top", str(self.config["manual_crop_top"])])
        
        if self.config["manual_crop_bottom"] > 0:
            args.extend(["--crop-bottom", str(self.config["manual_crop_bottom"])])
        
        return args

class AmbilightControl:
    def __init__(self):
        self.config_manager = AmbilightConfig()
    
    def is_running(self):
        """Check if ambilight service is running"""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "ambilight.service"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def start(self):
        """Start the ambilight service"""
        subprocess.run(["systemctl", "--user", "start", "ambilight.service"])
        self.config_manager.set("enabled", True)
    
    def stop(self):
        """Stop the ambilight service"""
        subprocess.run(["systemctl", "--user", "stop", "ambilight.service"])
        self.config_manager.set("enabled", False)
    
    def restart(self):
        """Restart the ambilight service with new settings"""
        subprocess.run(["systemctl", "--user", "restart", "ambilight.service"])
    
    def toggle(self):
        """Toggle the ambilight on/off"""
        if self.is_running():
            self.stop()
            return False
        else:
            self.start()
            return True
    
    def update_service_file(self):
        """Update systemd service file with current config"""
        service_file = Path.home() / ".config/systemd/user/ambilight.service"
        args = self.config_manager.build_command_args()
        args_str = " ".join(args)
        
        service_content = f"""[Unit]
Description=Ambient Lighting for Omarchy
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/local/bin/hypr-ambilight {args_str}
Restart=on-failure
RestartSec=5
ExecStartPre=/bin/sleep 3

[Install]
WantedBy=default.target
"""
        
        service_file.write_text(service_content)
        subprocess.run(["systemctl", "--user", "daemon-reload"])
    
    def get_status(self):
        """Get detailed status"""
        status = {
            "running": self.is_running(),
            "enabled": self.config_manager.get("enabled", True),
            "config": self.config_manager.config
        }
        return status

def print_status(control):
    """Print current status"""
    status = control.get_status()
    print("Ambient Lighting Status")
    print("=" * 40)
    print(f"Service Running: {'Yes' if status['running'] else 'No'}")
    print(f"Enabled: {'Yes' if status['enabled'] else 'No'}")
    print("\nCurrent Settings:")
    for key, value in status['config'].items():
        print(f"  {key}: {value}")

def main():
    control = AmbilightControl()
    
    if len(sys.argv) < 2:
        print_status(control)
        print("\nUsage: ambilight-config [command] [options]")
        print("\nCommands:")
        print("  status                Show current status")
        print("  start                 Start ambient lighting")
        print("  stop                  Stop ambient lighting")
        print("  restart               Restart with current settings")
        print("  toggle                Toggle on/off")
        print("  set [key] [value]     Set configuration value")
        print("  get [key]             Get configuration value")
        print("  cinema-on             Enable cinematic mode")
        print("  cinema-off            Disable cinematic mode")
        print("  cinema-toggle         Toggle cinematic mode")
        print("\nConfiguration keys:")
        print("  brightness (0.0-1.0)")
        print("  saturation (0.0-2.0)")
        print("  fps (30-144)")
        print("  smoothing (0.0-1.0)")
        print("  border (10-100)")
        print("  auto_crop (true/false)")
        print("  crop_threshold (0-255)")
        print("  manual_crop_top (pixels)")
        print("  manual_crop_bottom (pixels)")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        print_status(control)
    
    elif command == "start":
        control.start()
        print("Ambient lighting started")
    
    elif command == "stop":
        control.stop()
        print("Ambient lighting stopped")
    
    elif command == "restart":
        control.update_service_file()
        control.restart()
        print("Ambient lighting restarted with new settings")
    
    elif command == "toggle":
        is_on = control.toggle()
        print(f"Ambient lighting {'started' if is_on else 'stopped'}")
    
    elif command == "set":
        if len(sys.argv) < 4:
            print("Usage: ambilight-config set [key] [value]")
            return
        key = sys.argv[2]
        value_str = sys.argv[3]
        
        # Convert value to appropriate type
        if value_str.lower() in ["true", "false"]:
            value = value_str.lower() == "true"
        elif "." in value_str:
            value = float(value_str)
        else:
            try:
                value = int(value_str)
            except ValueError:
                value = value_str
        
        control.config_manager.set(key, value)
        print(f"Set {key} = {value}")
        print("Run 'ambilight-config restart' to apply changes")
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: ambilight-config get [key]")
            return
        key = sys.argv[2]
        value = control.config_manager.get(key)
        print(f"{key}: {value}")
    
    elif command == "cinema-on":
        control.config_manager.set("auto_crop", True)
        control.update_service_file()
        control.restart()
        print("Cinematic mode enabled (auto black bar detection)")
    
    elif command == "cinema-off":
        control.config_manager.set("auto_crop", False)
        control.config_manager.set("manual_crop_top", 0)
        control.config_manager.set("manual_crop_bottom", 0)
        control.update_service_file()
        control.restart()
        print("Cinematic mode disabled")
    
    elif command == "cinema-toggle":
        auto_crop = not control.config_manager.get("auto_crop", True)
        control.config_manager.set("auto_crop", auto_crop)
        control.update_service_file()
        control.restart()
        print(f"Cinematic mode {'enabled' if auto_crop else 'disabled'}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()

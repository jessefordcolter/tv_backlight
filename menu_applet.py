#!/usr/bin/env python3
"""
Ambient Lighting System Tray / Menu Bar Applet
Provides quick access to ambilight controls with visual feedback

Requires: python-gobject gtk3
Install: sudo pacman -S python-gobject gtk3
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib
import subprocess
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "ambilight"
CONFIG_FILE = CONFIG_DIR / "config.json"

class AmbilightIndicator:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "ambilight-indicator",
            "video-display-symbolic",
            AppIndicator3.IndicatorCategory.HARDWARE
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())
        
        # Start status update loop
        GLib.timeout_add_seconds(2, self.update_status)
        self.update_status()
    
    def load_config(self):
        """Load current configuration"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def is_running(self):
        """Check if service is running"""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "ambilight.service"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def update_status(self):
        """Update indicator based on current state"""
        running = self.is_running()
        if running:
            self.indicator.set_icon("video-display-symbolic")
        else:
            self.indicator.set_icon("video-display-dimmed-symbolic")
        return True  # Continue timeout
    
    def build_menu(self):
        """Build the popup menu"""
        menu = Gtk.Menu()
        
        # Status item
        self.status_item = Gtk.MenuItem(label="Status: Checking...")
        self.status_item.set_sensitive(False)
        menu.append(self.status_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        # Toggle on/off
        toggle_item = Gtk.MenuItem(label="Toggle On/Off")
        toggle_item.connect("activate", self.toggle_service)
        menu.append(toggle_item)
        
        # Restart
        restart_item = Gtk.MenuItem(label="Restart")
        restart_item.connect("activate", self.restart_service)
        menu.append(restart_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        # Cinematic mode submenu
        cinema_menu = Gtk.Menu()
        
        cinema_on = Gtk.MenuItem(label="Enable Auto-Crop")
        cinema_on.connect("activate", lambda _: self.run_command("cinema-on"))
        cinema_menu.append(cinema_on)
        
        cinema_off = Gtk.MenuItem(label="Disable Auto-Crop")
        cinema_off.connect("activate", lambda _: self.run_command("cinema-off"))
        cinema_menu.append(cinema_off)
        
        cinema_toggle = Gtk.MenuItem(label="Toggle Cinematic Mode")
        cinema_toggle.connect("activate", lambda _: self.run_command("cinema-toggle"))
        cinema_menu.append(cinema_toggle)
        
        cinema_item = Gtk.MenuItem(label="Cinematic Mode")
        cinema_item.set_submenu(cinema_menu)
        menu.append(cinema_item)
        
        # Settings submenu
        settings_menu = Gtk.Menu()
        
        # Brightness
        brightness_item = Gtk.MenuItem(label="Brightness")
        brightness_submenu = self.create_slider_submenu("brightness", 0.0, 1.0, 0.1)
        brightness_item.set_submenu(brightness_submenu)
        settings_menu.append(brightness_item)
        
        # Saturation
        saturation_item = Gtk.MenuItem(label="Saturation")
        saturation_submenu = self.create_slider_submenu("saturation", 0.5, 2.0, 0.1)
        saturation_item.set_submenu(saturation_submenu)
        settings_menu.append(saturation_item)
        
        # FPS
        fps_item = Gtk.MenuItem(label="FPS")
        fps_submenu = self.create_fps_submenu()
        fps_item.set_submenu(fps_submenu)
        settings_menu.append(fps_item)
        
        settings_menu.append(Gtk.SeparatorMenuItem())
        
        # Open full settings
        open_config = Gtk.MenuItem(label="Open Configuration...")
        open_config.connect("activate", self.open_settings_dialog)
        settings_menu.append(open_config)
        
        settings_item = Gtk.MenuItem(label="Settings")
        settings_item.set_submenu(settings_menu)
        menu.append(settings_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        # Quit
        quit_item = Gtk.MenuItem(label="Quit Applet")
        quit_item.connect("activate", self.quit)
        menu.append(quit_item)
        
        menu.show_all()
        return menu
    
    def create_slider_submenu(self, setting, min_val, max_val, step):
        """Create a submenu with preset values"""
        submenu = Gtk.Menu()
        
        values = []
        val = min_val
        while val <= max_val:
            values.append(val)
            val += step
        
        for value in values:
            item = Gtk.MenuItem(label=f"{value:.1f}")
            item.connect("activate", lambda _, v=value, s=setting: self.set_value(s, v))
            submenu.append(item)
        
        submenu.show_all()
        return submenu
    
    def create_fps_submenu(self):
        """Create FPS selection submenu"""
        submenu = Gtk.Menu()
        fps_values = [30, 45, 60, 75, 90, 120, 144]
        
        for fps in fps_values:
            item = Gtk.MenuItem(label=f"{fps} FPS")
            item.connect("activate", lambda _, f=fps: self.set_value("fps", f))
            submenu.append(item)
        
        submenu.show_all()
        return submenu
    
    def set_value(self, key, value):
        """Set a configuration value"""
        subprocess.run(["ambilight-config", "set", key, str(value)])
        self.show_notification(f"Set {key} to {value}", "Restart to apply")
    
    def run_command(self, command):
        """Run an ambilight-config command"""
        result = subprocess.run(
            ["ambilight-config", command],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            self.show_notification("Success", result.stdout.strip())
        self.update_status()
    
    def toggle_service(self, widget):
        """Toggle the service on/off"""
        self.run_command("toggle")
    
    def restart_service(self, widget):
        """Restart the service"""
        self.run_command("restart")
    
    def open_settings_dialog(self, widget):
        """Open full settings dialog"""
        dialog = SettingsDialog()
        dialog.run()
        dialog.destroy()
        self.update_status()
    
    def show_notification(self, title, message):
        """Show a desktop notification"""
        try:
            subprocess.run([
                "notify-send",
                "-a", "Ambient Lighting",
                title,
                message
            ])
        except:
            pass
    
    def quit(self, widget):
        """Quit the applet"""
        Gtk.main_quit()

class SettingsDialog(Gtk.Dialog):
    """Full settings dialog"""
    def __init__(self):
        super().__init__(title="Ambient Lighting Settings")
        self.set_default_size(500, 600)
        
        # Load current config
        self.config = self.load_config()
        
        # Build UI
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        
        # Brightness
        self.add_slider(box, "Brightness", "brightness", 0.0, 1.0, 0.01)
        
        # Saturation
        self.add_slider(box, "Saturation", "saturation", 0.0, 2.0, 0.01)
        
        # Smoothing
        self.add_slider(box, "Smoothing", "smoothing", 0.0, 1.0, 0.01)
        
        # FPS
        self.add_spin(box, "FPS", "fps", 30, 144, 1)
        
        # Border size
        self.add_spin(box, "Border Size (px)", "border", 10, 100, 5)
        
        box.pack_start(Gtk.Separator(), False, False, 10)
        
        # Cinematic mode
        self.auto_crop = Gtk.CheckButton(label="Auto-detect black bars")
        self.auto_crop.set_active(self.config.get("auto_crop", True))
        box.pack_start(self.auto_crop, False, False, 0)
        
        # Crop threshold
        self.add_spin(box, "Black Bar Threshold", "crop_threshold", 0, 255, 1)
        
        # Manual crop
        self.add_spin(box, "Manual Crop Top (px)", "manual_crop_top", 0, 500, 10)
        self.add_spin(box, "Manual Crop Bottom (px)", "manual_crop_bottom", 0, 500, 10)
        
        box.pack_start(Gtk.Separator(), False, False, 10)
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        apply_button = Gtk.Button(label="Apply & Restart")
        apply_button.connect("clicked", self.apply_and_restart)
        button_box.pack_start(apply_button, True, True, 0)
        
        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda _: self.destroy())
        button_box.pack_start(close_button, True, True, 0)
        
        box.pack_start(button_box, False, False, 0)
        
        self.show_all()
    
    def load_config(self):
        """Load configuration"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def add_slider(self, box, label, key, min_val, max_val, step):
        """Add a slider control"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        label_widget = Gtk.Label(label=label)
        label_widget.set_width_chars(20)
        label_widget.set_xalign(0)
        hbox.pack_start(label_widget, False, False, 0)
        
        adjustment = Gtk.Adjustment(
            value=self.config.get(key, min_val),
            lower=min_val,
            upper=max_val,
            step_increment=step,
            page_increment=step*10
        )
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
        scale.set_digits(2)
        scale.set_hexpand(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        setattr(self, key, scale)
        
        hbox.pack_start(scale, True, True, 0)
        box.pack_start(hbox, False, False, 0)
    
    def add_spin(self, box, label, key, min_val, max_val, step):
        """Add a spin button control"""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        label_widget = Gtk.Label(label=label)
        label_widget.set_width_chars(20)
        label_widget.set_xalign(0)
        hbox.pack_start(label_widget, False, False, 0)
        
        adjustment = Gtk.Adjustment(
            value=self.config.get(key, min_val),
            lower=min_val,
            upper=max_val,
            step_increment=step,
            page_increment=step*10
        )
        spin = Gtk.SpinButton(adjustment=adjustment)
        spin.set_digits(0)
        setattr(self, key, spin)
        
        hbox.pack_start(spin, False, False, 0)
        box.pack_start(hbox, False, False, 0)
    
    def apply_and_restart(self, widget):
        """Apply settings and restart service"""
        # Collect all values
        settings = {
            "brightness": self.brightness.get_value(),
            "saturation": self.saturation.get_value(),
            "smoothing": self.smoothing.get_value(),
            "fps": int(self.fps.get_value()),
            "border": int(self.border.get_value()),
            "auto_crop": self.auto_crop.get_active(),
            "crop_threshold": int(self.crop_threshold.get_value()),
            "manual_crop_top": int(self.manual_crop_top.get_value()),
            "manual_crop_bottom": int(self.manual_crop_bottom.get_value())
        }
        
        # Save each setting
        for key, value in settings.items():
            subprocess.run(["ambilight-config", "set", key, str(value)])
        
        # Restart service
        subprocess.run(["ambilight-config", "restart"])
        
        # Show notification
        subprocess.run([
            "notify-send",
            "-a", "Ambient Lighting",
            "Settings Applied",
            "Service restarted with new settings"
        ])
        
        self.destroy()

def main():
    indicator = AmbilightIndicator()
    Gtk.main()

if __name__ == "__main__":
    main()
        

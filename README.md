Code Snippet

def _precompute_led_mapping(self):
    """Precompute which LEDs correspond to screen positions"""
    c = self.config
    
    # Bottom edge - CONTINUOUS mapping with LED 266 at screen center
    # Physical order: 40->39->...->1->0/269->268->267->266->265->...->223
    # Note: LEDs 0 and 269 are the same physical LED (overlap)
    bottom_left_to_start = list(range(40, 0, -1))     # 40,39,38...2,1
    bottom_overlap_led = [0]                          # LED 0 (same as 269)
    bottom_center_section = list(range(268, 265, -1)) # 268,267,266
    bottom_center_to_right = list(range(265, 222, -1)) # 265,264,263...224,223
    
    self.bottom_leds = bottom_left_to_start + bottom_overlap_led + bottom_center_section + bottom_center_to_right
    
    # Left edge (49 LEDs) - bottom to top
    self.left_leds = list(range(c.led_bottom_left, c.led_top_left + 1))  # 40 to 89
    
    # Top edge (85 LEDs) - left to right
    self.top_leds = list(range(c.led_top_left, c.led_top_right + 1))  # 89 to 174
    
    # Right edge (49 LEDs) - top to bottom  
    self.right_leds = list(range(c.led_top_right, c.led_bottom_right + 1))  # 174 to 223
    
    # Corner LEDs for brightness boost
    self.corner_leds = set()
    for corner in [c.led_bottom_left, c.led_top_left, c.led_top_right, c.led_bottom_right]:
        self.corner_leds.update(range(max(0, corner-1), min(c.num_leds, corner+2)))

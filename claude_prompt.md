Claude prompt:

Hardware info:
-  RP2040 microcontroller connected to PC via usb C
- Serial port = /dev/ttyACM0
- 270 WS2812B LEDs

LED Positioning (clockwise)
- LED 0 starts at approximetly bottom center (6 o'clock position)
- Bottom Left Corner = 40
- Top Left Corner = 89
- Top Right Corner = 174
- Bottom Right Corner = 223
- LED 267 is dead center bottom
- LED 269 overlaps with LED 0 (completing the circle)

Screen Capture:
- Running on Arch linux pc running Hyprland
- Want maximal performant, custom Python script
- Automatically turns LED’s on when hyprland starts up (always on)
- {name of program…. hyperland} shortcut to turn on or off from keyboard
- Uses mss for fast screen capture and numpy for processing
- Features:
    - 60 FPS
    - Brightness control 
    - Saturation control
    - Border size
    - LED smoothing
    - Reads perimeter of monitor regardless of resolution
    - Monitors perimeter of screen and address LED’s accordingly
    - Smoothing
    - Corners and adjacent LED’s (two on either side, 3 total per corner) can be set brighter to allow for smoother backlighting
    - Very high performance code that is non blocking and won’t slow computer down.

Ascii art to include in python header comments:

# LED Strip Layout (270 LEDs total)
# 
#     						TOP (85 LEDs): 
#				89 ───────────────174
#                 		 │                      				        │
#    LEFT (49):        │                 						│	RIGHT (49)
#                 	 	 │                          					│
#                 		40 ───────0				│
# 							     269───────223
#						
#               	       BOTTOM (85 LEDs long, 86 LEDs total)
#                 		         (LED 0 overlaps LED 269)


Code Flashed to rp2040:

/*
 * Adalight for WS2812B LED Strip
 * 
 * This code receives LED color data from a computer via USB serial
 * and displays it on a WS2812B LED strip for ambient lighting.
 * 
 * Hardware: RP2040 Microcontroller + WS2812B LED strip (270 LEDs)
 * Connection: Data pin 0, Power, Ground
 * 
 * Compatible with Adalight software
 */

#include "FastLED.h"

/*****************************************************
 * HARDWARE CONFIGURATION
 *****************************************************/

// LED Strip Settings
#define NUM_LEDS 270              // Total number of LEDs in your strip
#define DATA_PIN 0                // Microcontroller pin connected to LED data line
#define LED_TYPE WS2812B          // Type of LED strip
#define COLOR_ORDER GRB           // Color order for WS2812B (Green-Red-Blue)

// Performance and Safety Settings
#define BRIGHTNESS 255            // Maximum brightness (0-255)
#define SERIAL_RATE 115200        // USB serial communication speed
#define TIMEOUT_MS 15000          // Turn off LEDs after 15 seconds of no data

// Startup Test Configuration
#define STARTUP_TEST_ENABLED true // Flash LEDs white on startup to verify connection
#define TEST_BRIGHTNESS 32        // Brightness level for startup test (0-255)
#define TEST_DURATION_MS 1000     // How long to show the startup test

/*****************************************************
 * ADALIGHT PROTOCOL VARIABLES
 *****************************************************/

// Adalight protocol uses a "magic word" to start each transmission
const uint8_t MAGIC_WORD[] = {'A', 'd', 'a'};
const uint8_t MAGIC_WORD_SIZE = sizeof(MAGIC_WORD);

// Communication variables
uint8_t header_hi, header_lo, checksum;    // Packet header bytes
uint8_t magic_index = 0;                   // Current position in magic word
unsigned long last_data_time;             // Timestamp of last received data

// LED array
CRGB leds[NUM_LEDS];

/*****************************************************
 * UTILITY FUNCTIONS
 *****************************************************/

/**
 * Sets all LEDs to the specified color and displays them
 * @param color The color to set all LEDs to
 */
void setAllLEDs(CRGB color) {
  fill_solid(leds, NUM_LEDS, color);
  FastLED.show();
}

/**
 * Turns off all LEDs (sets them to black)
 */
void turnOffAllLEDs() {
  setAllLEDs(CRGB::Black);
}

/**
 * Checks if serial data is available and handles timeout
 * @return true if data is available, false if timeout occurred
 */
bool waitForSerialData() {
  // Wait for data to become available
  while (!Serial.available()) {
    // Check if we've exceeded the timeout period
    if (millis() - last_data_time > TIMEOUT_MS) {
      turnOffAllLEDs();
      last_data_time = millis(); // Reset timer
      return false;
    }
  }
  return true;
}

/**
 * Performs startup LED test - flashes white to verify all LEDs work
 */
void performStartupTest() {
  if (!STARTUP_TEST_ENABLED) return;
  
  // Fade up to test brightness
  for (int brightness = 0; brightness <= TEST_BRIGHTNESS; brightness++) {
    setAllLEDs(CRGB(brightness, brightness, brightness));
    delay(TEST_DURATION_MS / (2 * TEST_BRIGHTNESS));
  }
  
  // Fade down to off
  for (int brightness = TEST_BRIGHTNESS; brightness >= 0; brightness--) {
    setAllLEDs(CRGB(brightness, brightness, brightness));
    delay(TEST_DURATION_MS / (2 * TEST_BRIGHTNESS));
  }
  
  turnOffAllLEDs();
}

/*****************************************************
 * ADALIGHT PROTOCOL FUNCTIONS
 *****************************************************/

/**
 * Reads the magic word from serial stream
 * @return true if complete magic word was received
 */
bool readMagicWord() {
  if (!waitForSerialData()) return false;
  
  uint8_t received_byte = Serial.read();
  
  // Check if this byte matches the expected position in magic word
  if (received_byte == MAGIC_WORD[magic_index]) {
    magic_index++;
    // If we've received the complete magic word
    if (magic_index >= MAGIC_WORD_SIZE) {
      magic_index = 0;
      return true;
    }
  } else {
    // Wrong byte received, start over
    magic_index = 0;
    // Check if this byte could be the start of a new magic word
    if (received_byte == MAGIC_WORD[0]) {
      magic_index = 1;
    }
  }
  
  return false;
}

/**
 * Reads the packet header (LED count and checksum)
 * @return true if valid header was received
 */
bool readPacketHeader() {
  // Read high byte of LED count
  if (!waitForSerialData()) return false;
  header_hi = Serial.read();
  
  // Read low byte of LED count  
  if (!waitForSerialData()) return false;
  header_lo = Serial.read();
  
  // Read checksum
  if (!waitForSerialData()) return false;
  checksum = Serial.read();
  
  // Verify checksum (XOR of hi and lo bytes with 0x55)
  uint8_t expected_checksum = header_hi ^ header_lo ^ 0x55;
  
  return (checksum == expected_checksum);
}

/**
 * Reads LED color data from serial stream
 * @return true if all LED data was successfully received
 */
bool readLEDData() {
  // Calculate number of LEDs to receive (never exceed our array size)
  uint16_t incoming_led_count = (header_hi << 8) | header_lo;
  uint16_t leds_to_read = min((uint16_t)NUM_LEDS, incoming_led_count);
  
  // Clear LED array to black
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  
  // Read RGB data for each LED
  for (uint16_t led_index = 0; led_index < leds_to_read; led_index++) {
    // Read Red value
    if (!waitForSerialData()) return false;
    uint8_t red = Serial.read();
    
    // Read Green value
    if (!waitForSerialData()) return false;
    uint8_t green = Serial.read();
    
    // Read Blue value
    if (!waitForSerialData()) return false;
    uint8_t blue = Serial.read();
    
    // Set LED color
    leds[led_index] = CRGB(red, green, blue);
  }
  
  return true;
}

/*****************************************************
 * MAIN PROGRAM
 *****************************************************/

void setup() {
  // Initialize serial communication
  Serial.begin(SERIAL_RATE);
  
  // Initialize FastLED
  FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  FastLED.setCorrection(TypicalLEDStrip);
  FastLED.setDither(BINARY_DITHER);
  
  // Perform startup test
  performStartupTest();
  
  // Send ready signal to computer
  Serial.println("Ada");
  Serial.print("Ready: ");
  Serial.print(NUM_LEDS);
  Serial.println(" LEDs");
  
  // Initialize timing
  last_data_time = millis();
  
  /*
   * MAIN ADALIGHT PROTOCOL LOOP
   * 
   * This runs continuously to receive and process LED data.
   * The loop is placed in setup() rather than loop() to eliminate
   * the small performance overhead of function calls.
   */
  while (true) {
    // Step 1: Wait for magic word
    if (!readMagicWord()) {
      continue; // Timeout occurred, start over
    }
    
    // Step 2: Read packet header
    if (!readPacketHeader()) {
      continue; // Invalid header, start over
    }
    
    // Step 3: Read LED color data
    if (!readLEDData()) {
      continue; // Data transmission failed, start over
    }
    
    // Step 4: Update LEDs and reset timeout
    FastLED.show();
    last_data_time = millis();
  }
}

void loop() {
  // Main program runs in setup() for performance reasons
  // This function intentionally left empty
}




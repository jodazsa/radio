#!/usr/bin/env python3
"""
Hardware Test Script for I2C Internet Radio
Tests I2C devices, encoders, buttons, NeoPixels, and OLED display
"""

import sys
import time

print("=" * 60)
print("I2C Internet Radio - Hardware Test")
print("=" * 60)
print()

# Test 1: Check Python dependencies
print("Test 1: Checking Python dependencies...")
dependencies = {
    'board': 'adafruit-blinka',
    'busio': 'adafruit-blinka',
    'adafruit_seesaw.seesaw': 'adafruit-circuitpython-seesaw',
    'adafruit_ssd1306': 'adafruit-circuitpython-ssd1306',
    'PIL': 'Pillow',
    'yaml': 'PyYAML'
}

missing = []
for module, package in dependencies.items():
    try:
        __import__(module)
        print(f"  ✓ {module} found")
    except ImportError:
        print(f"  ✗ {module} not found (install: pip3 install {package} --break-system-packages)")
        missing.append(package)

if missing:
    print()
    print("Install missing packages:")
    print(f"  pip3 install {' '.join(missing)} --break-system-packages")
    sys.exit(1)

print()

# Test 2: Check I2C bus
print("Test 2: Checking I2C bus...")
try:
    import board
    import busio
    
    i2c = busio.I2C(board.SCL, board.SDA)
    print("  ✓ I2C bus initialized")
except Exception as e:
    print(f"  ✗ Failed to initialize I2C: {e}")
    print("  Make sure I2C is enabled in raspi-config")
    sys.exit(1)

print()

# Test 3: Scan I2C devices
print("Test 3: Scanning for I2C devices...")
try:
    while not i2c.try_lock():
        pass
    
    devices = i2c.scan()
    i2c.unlock()
    
    if devices:
        print(f"  Found {len(devices)} device(s):")
        for device in devices:
            print(f"    0x{device:02X}", end="")
            if device == 0x49:
                print(" - Quad Encoder Breakout (Seesaw)")
            elif device == 0x3C:
                print(" - SSD1306 OLED Display")
            else:
                print(" - Unknown device")
    else:
        print("  ✗ No I2C devices found!")
        print("  Check physical connections")
        sys.exit(1)
    
    # Check for expected devices
    expected = [0x49, 0x3C]
    for addr in expected:
        if addr not in devices:
            name = "Encoder" if addr == 0x49 else "OLED"
            print(f"  ⚠ Warning: {name} not found at 0x{addr:02X}")
    
except Exception as e:
    print(f"  ✗ Failed to scan I2C: {e}")
    sys.exit(1)

print()

# Test 4: Test Quad Encoder Breakout
print("Test 4: Testing Quad Encoder Breakout...")
if 0x49 in devices:
    try:
        from adafruit_seesaw.seesaw import Seesaw
        from adafruit_seesaw.rotaryio import IncrementalEncoder
        from adafruit_seesaw.digitalio import DigitalIO
        
        seesaw = Seesaw(i2c, addr=0x49)
        print("  ✓ Seesaw initialized")
        
        # Test version
        version = seesaw.get_version()
        print(f"  ✓ Seesaw version: {version}")
        
        # Initialize one encoder as test
        encoder = IncrementalEncoder(seesaw, 9, 10)
        print("  ✓ Encoder 0 initialized")
        
        # Initialize one button as test
        button = DigitalIO(seesaw, 1)
        button.direction = False
        button.pull = True
        print("  ✓ Button 0 initialized")
        
        print()
        print("  Interactive Test:")
        print("  - Turn Encoder 1 (leftmost) - position will be shown")
        print("  - Press Encoder 1 button to continue")
        print()
        
        last_position = encoder.position
        button_was_pressed = False
        
        while True:
            # Check encoder
            new_position = encoder.position
            if new_position != last_position:
                delta = new_position - last_position
                direction = "CW" if delta > 0 else "CCW"
                print(f"    Encoder moved {direction}: position = {new_position}")
                last_position = new_position
            
            # Check button
            button_pressed = not button.value  # Inverted due to pull-up
            if button_pressed and not button_was_pressed:
                print(f"    Button pressed!")
                button_was_pressed = True
                time.sleep(1)
                break
            elif not button_pressed:
                button_was_pressed = False
            
            time.sleep(0.01)
        
        print("  ✓ Encoder and button working!")
        
    except Exception as e:
        print(f"  ✗ Failed to test encoder: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  ⊗ Skipped (device not found)")

print()

# Test 5: Test NeoPixels
print("Test 5: Testing NeoPixels...")
if 0x49 in devices:
    try:
        # Set up NeoPixels
        try:
            seesaw.pin_mode(17, seesaw.OUTPUT)
        except:
            pass
        
        print("  Testing colors on all 4 encoders...")
        
        colors = [
            ([255, 0, 0], "Red"),
            ([0, 255, 0], "Green"),
            ([0, 0, 255], "Blue"),
            ([255, 255, 0], "Yellow"),
            ([0, 255, 255], "Cyan"),
            ([255, 0, 255], "Magenta"),
            ([255, 255, 255], "White"),
            ([0, 0, 0], "Off")
        ]
        
        for color, name in colors:
            print(f"    {name}...", end=" ", flush=True)
            for i in range(4):
                seesaw.neopixel[i] = tuple(color)
            time.sleep(0.5)
            print("✓")
        
        print("  ✓ NeoPixels working!")
        
    except Exception as e:
        print(f"  ✗ Failed to test NeoPixels: {e}")
else:
    print("  ⊗ Skipped (device not found)")

print()

# Test 6: Test OLED Display
print("Test 6: Testing OLED Display...")
if 0x3C in devices:
    try:
        import adafruit_ssd1306
        from PIL import Image, ImageDraw, ImageFont
        
        display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3C)
        print("  ✓ Display initialized (128x32)")
        
        # Clear display
        display.fill(0)
        display.show()
        print("  ✓ Display cleared")
        
        # Create test pattern
        image = Image.new('1', (128, 32))
        draw = ImageDraw.Draw(image)
        
        # Draw border
        draw.rectangle((0, 0, 127, 31), outline=255, fill=0)
        
        # Draw text
        font = ImageFont.load_default()
        draw.text((10, 2), "I2C Radio Test", font=font, fill=255)
        draw.text((10, 12), "OLED Working!", font=font, fill=255)
        draw.text((10, 22), "Hello World", font=font, fill=255)
        
        # Display image
        display.image(image)
        display.show()
        print("  ✓ Test pattern displayed")
        
        time.sleep(3)
        
        # Clear display
        display.fill(0)
        display.show()
        
        print("  ✓ OLED working!")
        
    except Exception as e:
        print(f"  ✗ Failed to test OLED: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  ⊗ Skipped (device not found)")

print()

# Test 7: Check configuration file
print("Test 7: Checking configuration file...")
try:
    import yaml
    
    config_file = "/home/radio/hardware-config.yaml"
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"  ✓ Configuration file found: {config_file}")
        
        # Check key settings
        i2c_addr = config.get('i2c', {}).get('encoder_i2c_address')
        oled_addr = config.get('i2c', {}).get('oled_i2c_address')
        
        if i2c_addr == 0x49:
            print(f"  ✓ Encoder address: 0x{i2c_addr:02X}")
        else:
            print(f"  ⚠ Encoder address: 0x{i2c_addr:02X} (expected 0x49)")
        
        if oled_addr == 0x3C:
            print(f"  ✓ OLED address: 0x{oled_addr:02X}")
        else:
            print(f"  ⚠ OLED address: 0x{oled_addr:02X} (expected 0x3C)")
        
    except FileNotFoundError:
        print(f"  ⚠ Configuration file not found: {config_file}")
        print("  Run install.sh to create default configuration")
    
except Exception as e:
    print(f"  ✗ Failed to check configuration: {e}")

print()

# Test 8: Check systemd services
print("Test 8: Checking systemd services...")
import subprocess

services = [
    'encoder-controller.service',
    'oled-display.service',
    'shuffle-mode.service',
    'mpd.service'
]

for service in services:
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        status = result.stdout.strip()
        
        if status == 'active':
            print(f"  ✓ {service}: running")
        elif status == 'inactive':
            print(f"  ⊗ {service}: stopped")
        else:
            print(f"  ⚠ {service}: {status}")
    
    except Exception as e:
        print(f"  ? {service}: could not check")

print()

# Summary
print("=" * 60)
print("Test Summary")
print("=" * 60)
print()

if 0x49 in devices and 0x3C in devices:
    print("✓ All I2C devices detected!")
    print("✓ Your hardware appears to be working correctly.")
    print()
    print("Next steps:")
    print("  1. Make sure services are running:")
    print("     sudo systemctl start encoder-controller oled-display")
    print("  2. Test the radio:")
    print("     radio-play 0 0")
    print("  3. Monitor logs:")
    print("     sudo journalctl -u encoder-controller -f")
elif 0x49 in devices:
    print("⚠ Encoder found but OLED missing")
    print("  Check OLED connections and address")
elif 0x3C in devices:
    print("⚠ OLED found but encoder missing")
    print("  Check encoder connections and address")
else:
    print("✗ No I2C devices detected!")
    print("  1. Check physical connections")
    print("  2. Verify I2C is enabled: sudo raspi-config")
    print("  3. Try: i2cdetect -y 1")

print()
print("=" * 60)

import machine
import time
import math

class HX711:
    def __init__(self, dout, pd_sck, gain=128):
        print("Initializing HX711")
        self.PD_SCK = machine.Pin(pd_sck, machine.Pin.OUT)
        self.DOUT = machine.Pin(dout, machine.Pin.IN)
        
        self.GAIN = 0
        self.REFERENCE_UNIT = 1
        self.OFFSET = 0
        
        self.set_gain(gain)
        time.sleep_ms(1)
        print("HX711 Initialized")

    def convert_from_twos_complement(self, input_value):
        """Convert a 24-bit value in two's complement format to a signed integer."""
        if input_value & 0x800000:  # check if sign bit is set
            input_value -= 0x1000000  # convert to negative number
        return input_value

    def is_ready(self):
        """Check if the HX711 is ready to read data."""
        return self.DOUT.value() == 0

    def set_gain(self, gain):
        """Set the gain for the HX711."""
        print(f"Setting gain to {gain}")
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        elif gain == 32:
            self.GAIN = 2
        
        self.PD_SCK.off()
        self.read_raw_bytes()

    def read_next_bit(self):
        """Read the next bit from the HX711."""
        self.PD_SCK.on()
        self.PD_SCK.off()
        return int(self.DOUT.value())

    def read_next_byte(self):
        """Read a byte of data (8 bits) from the HX711."""
        byte_value = 0
        for _ in range(8):
            byte_value <<= 1
            byte_value |= self.read_next_bit()
        return byte_value 

    def read_raw_bytes(self):
        """Read 3 raw bytes from the HX711."""
        print("Reading raw bytes")
        print(f"DOUT value: {self.DOUT.value()}")
        while not self.is_ready():

            pass
        
        first_byte = self.read_next_byte()
        second_byte = self.read_next_byte()
        third_byte = self.read_next_byte()
        
        for _ in range(self.GAIN):
            self.read_next_bit()
        
        return [first_byte, second_byte, third_byte]

    def read_long(self):
        """Read a 24-bit signed integer from the HX711."""
        print("Reading long value")
        data_bytes = self.read_raw_bytes()
        
        # Combine the 3 bytes into one 24-bit value
        combined_value = (data_bytes[0] << 16) | (data_bytes[1] << 8) | data_bytes[2]
        
        # Convert from two's complement
        signed_value = self.convert_from_twos_complement(combined_value)
        
        # Calibration: Convert raw reading to kg
        weight_kg = (signed_value - self.OFFSET) / self.REFERENCE_UNIT
        
        return weight_kg

    def set_offset(self, offset):
        """Set the offset for calibration."""
        print(f"Setting offset to {offset}")
        self.OFFSET = offset

    def set_reference_unit(self, reference_unit):
        """Set the reference unit for calibration."""
        print(f"Setting reference unit to {reference_unit}")
        self.REFERENCE_UNIT = reference_unit


# 7-Segment Display Pins (common cathode)
SEGMENT_PINS = [27, 26, 22, 21, 20, 19, 18]
# Digit Select Pins
DIGIT_PINS = [2, 3, 4]

# Segments for numbers 0-9
SEGMENT_PATTERNS = [
    0b1111110,  # 0
    0b0110000,  # 1
    0b1101101,  # 2
    0b1111001,  # 3
    0b0110011,  # 4
    0b1011011,  # 5
    0b1011111,  # 6
    0b1110000,  # 7
    0b1111111,  # 8
    0b1111011,  # 9
    0b0000000,  # 10
]

class Display:
    def __init__(self, segment_pins, digit_pins):
        print("Initializing Display")
        # Setup segment pins as outputs
        self.segments = [machine.Pin(pin, machine.Pin.OUT) for pin in segment_pins]
        # Setup digit select pins as outputs
        self.digits = [machine.Pin(pin, machine.Pin.OUT) for pin in digit_pins]
        print("Display Initialized")
        
    def display_digit(self, digit, position):
        """Display a single digit on the 7-segment display."""

        # Turn off all digits
        for d in self.digits:
            d.value(1)

        

        
        # Turn on correct segments for the digit
        pattern = SEGMENT_PATTERNS[digit]
        for i, seg in enumerate(self.segments):
            seg.value((pattern >> i) & 1)
        
        # Turn on the correct digit
        self.digits[position].value(0)

    def show_number(self, number):
        """Display a 2-digit number on the 7-segment display."""

        # Ensure number is two digits
        round_number = max(0, min(99, int(number)))

        # Display tens digit
        if (round_number // 10):
            self.display_digit(round_number // 10, 0)
            time.sleep_ms(3)
        else:
            self.display_digit(10, 0)
            time.sleep_ms(3)

        
        # Display ones digit
        self.display_digit(round_number % 10, 1)
        time.sleep_ms(3)

        # Display decimal digit
        self.display_digit(int(round((number - math.floor(number)) * 10)), 2)
        time.sleep_ms(3)



def main():
    print("Starting main function")
    
    # Initialize HX711
    hx = HX711(dout=16, pd_sck=17)
    
    # Calibration: 
    # 1. First, get the offset with no weight
    hx.set_offset(0)  # You'll need to measure this precisely
    
    # 2. Then calibrate the reference unit with a known weight
    hx.set_reference_unit(420)  # This value depends on your specific load cell
    
    # Initialize display
    display = Display(SEGMENT_PINS, DIGIT_PINS)
    point = machine.Pin(5, machine.Pin.OUT)
    point.value(1)
    
    # Initialize alarm components
    buzzer = machine.Pin(14, machine.Pin.OUT)
    alarm_led = machine.Pin(15, machine.Pin.OUT)
    
    timer1 = machine.Timer()

    print("Entering main loop")
    while True:
        try:
            # Read weight
            weight = abs(hx.read_long())
            weight = 14.2
            # Display weight (limited to 99 for 2-digit display)
            display_weight = min(weight, 99)
            timer1.init(freq=2, mode=machine.Timer.PERIODIC, callback=display.show_number(display_weight))
            
            # Alarm if weight exceeds 200kg
            print(f"Current weight: {weight}")
            if weight > 20:
                # Sound buzzer and light LED
                buzzer.on()
                alarm_led.on()
                print("ALARM: Weight exceeds 20kg!")
            else:
                # Turn off alarm
                buzzer.off()
                alarm_led.off()
            
            # Small delay to prevent overwhelming the system
            time.sleep_ms(8)
        
        except Exception as e:
            # Basic error handling
            print("Error reading weight:", e)
            time.sleep_ms(500)

# Run the main program
print("Script loaded. Ready to run.")
if __name__ == '__main__':
    main()

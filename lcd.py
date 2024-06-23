import time
import machine

# Define LCD pin configuration
LCD_RS = machine.Pin(3,machine.Pin.OUT)
LCD_EN = machine.Pin(1,machine.Pin.OUT)
LCD_D4 = machine.Pin(4,machine.Pin.OUT)
LCD_D5 = machine.Pin(5,machine.Pin.OUT)
LCD_D6 = machine.Pin(6,machine.Pin.OUT)
LCD_D7 = machine.Pin(7,machine.Pin.OUT)

# LCD constants
LCD_WIDTH = 16  # Maximum characters per line
LCD_LINE_1 = 0x80  # LCD RAM address for the first line
LCD_LINE_2 = 0xC0  # LCD RAM address for the second line

# LCD commands
LCD_CLEAR = 0x01  # Clear the display
LCD_HOME = 0x02   # Return to home position

# Function to initialize the LCD
def lcd_init():
    lcd_command(0x33)  # Initialize
    lcd_command(0x32)  # Set to 4-bit mode
    lcd_command(0x06)  # Cursor move direction
    lcd_command(0x0C)  # Display on, cursor off, blink off
    lcd_command(0x28)  # 2 lines, 5x8 character matrix
    lcd_command(LCD_CLEAR)  # Clear the screen
    time.sleep_ms(2)  # Delay to allow for LCD initialization

# Function to send a command to the LCD
def lcd_command(cmd):
    LCD_RS.value(0)  # Set RS to command mode
    get_nibble(cmd)

# Function to send data to the LCD
def lcd_data(data):
    LCD_RS.value(1)  # Set RS to data mode
    get_nibble(data)

def get_nibble(data):

    LCD_EN.value(0)
    LCD_D4.value(0)
    LCD_D5.value(0)
    LCD_D6.value(0)
    LCD_D7.value(0)

      # High nibble
    if data & 0x10:
        LCD_D4.value(1)
    if data & 0x20:
        LCD_D5.value(1)
    if data & 0x40:
        LCD_D6.value(1)
    if data & 0x80:
        LCD_D7.value(1)

    # Toggle Enable
    LCD_EN.value(1)
    time.sleep_us(1)
    LCD_EN.value(0)
    time.sleep_us(100)

    # Low nibble
    LCD_D4.value(0)
    LCD_D5.value(0)
    LCD_D6.value(0)
    LCD_D7.value(0)

    # High nibble
    if data & 0x01:
        LCD_D4.value(1)
    if data & 0x02:
        LCD_D5.value(1)
    if data & 0x04:
        LCD_D6.value(1)
    if data & 0x08:
        LCD_D7.value(1)

    # Toggle Enable
    LCD_EN.value(1)
    time.sleep_us(1)
    LCD_EN.value(0)
    time.sleep_us(100)    

# Function to clear the LCD screen
def lcd_clear():
    lcd_command(LCD_CLEAR)

# Function to set the cursor to the home position
def lcd_home():
    lcd_command(LCD_HOME)

# Function to display text on the LCD
def lcd_text(line, text):
    if line == 1:
        lcd_command(LCD_LINE_1)
    elif line == 2:
        lcd_command(LCD_LINE_2)

    for char in text:
        lcd_data(ord(char))


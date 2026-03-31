import serial
import time

# Connect to the Jetson's hardware UART
try:
    esp32 = serial.Serial('/dev/ttyTHS1', 115200, timeout=1)
    time.sleep(1) # Give it a second to connect
    print("UART Connection Established.")
except Exception as e:
    print(f"Error opening UART: {e}")
    exit()

def send_command(cmd):
    esp32.write((cmd + '\n').encode('utf-8'))
    time.sleep(0.05)
    return esp32.readline().decode('utf-8').strip()

# 1. Check if ESP32 is alive
print("Ping Test:", send_command("PING"))

# 2. Set target temperature to 37.5°C
print("Updating Target:", send_command("SET_TEMP:37.5"))

# 3. Monitor live temperatures
print("--- Live Monitoring ---")
try:
    while True:
        temp_data = send_command("GET_TEMP")
        print(f"Reading: {temp_data}")
        time.sleep(1) # Read once every second
except KeyboardInterrupt:
    print("\nStopping monitor.")
    esp32.close()

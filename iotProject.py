import I2C_LCD_driver
import time
import RPi.GPIO as GPIO
import requests
import spidev
import datetime

# GPIO pin numbers
temSwPin = 17
humSwPin = 18
ledWhite = 24
servoPin = 13
buzzer = 19

# LCD
mylcd = I2C_LCD_driver.lcd()

# Weather API
api_key = 'ZyKzu7E+La1QDR3Y/+FcFEwwhO6cMb+g5vO/ez2129AM+/RSBEp1qcVmFPWU51AeQwI3nGVKOuw6fxOsJDnGYw=='
api_url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'

# Weather location
longitude = 63
latitude = 120

# Get current date and time
now = datetime.datetime.now()
current_date = now.strftime("%Y%m%d")
current_time = now.strftime("%H%M")

# Set GPIO pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(temSwPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(humSwPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(ledWhite, GPIO.OUT)
GPIO.setup(servoPin, GPIO.OUT)
GPIO.setup(buzzer, GPIO.OUT)
GPIO.setwarnings(False)

# Cds
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 100000


def get_weather(category, lon, lat):
    params = {
        "serviceKey": api_key,
        "numOfRows": 1000,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": current_date,
        #"base_time": current_time,
        "base_time": "1250",
        "nx": lon,
        "ny": lat,
    }
    response = requests.get(api_url, params)
    if response.status_code == 200:
        data = response.json()
        items = data["response"]["body"]["items"]["item"]
        for item in items:
            if item["category"] == category:
                return item["obsrValue"]
    return None


# CDS
def analogRead(ch):
    buf = [(1 << 2) | (1 << 1) | (ch & 4) >> 2, (ch & 3) << 6, 0]
    buf = spi.xfer(buf)
    adcValue = ((buf[1] & 0xF) << 8) | buf[2]
    return adcValue


# Servo, Buzzer
pwm_s = GPIO.PWM(servoPin, 50)
pwm_s.start(3.0)
time.sleep(2.0)
pwm_s.ChangeDutyCycle(0.0)
pwm_b = GPIO.PWM(buzzer, 262)


# Switch event callback
def switch_callback(channel):
    if channel == temSwPin:
        temperature = get_weather("T1H", longitude, latitude)
        if temperature is not None:
            mylcd.lcd_clear()
            mylcd.lcd_display_string("Temp: {}'C".format(temperature), 1)
            time.sleep(3)
        else:
            print("Failed to retrieve temperature.")
    elif channel == humSwPin:
        humidity = get_weather("REH", longitude, latitude)
        if humidity is not None:
            mylcd.lcd_clear()
            mylcd.lcd_display_string("Hum: {}%".format(humidity), 1)
            time.sleep(3)
        else:
            print("Failed to retrieve humidity.")


# Register switch event detection
GPIO.add_event_detect(temSwPin, GPIO.RISING, callback=switch_callback, bouncetime=200)
GPIO.add_event_detect(humSwPin, GPIO.RISING, callback=switch_callback, bouncetime=200)

# Main loop
try:
    while True:
        mylcd.lcd_clear()
        mylcd.lcd_display_string("Welcome!!!", 1)
        time.sleep(1)

        # CDS
        cdsValue = analogRead(0)
        print(cdsValue)
        if cdsValue > 1000:
            GPIO.output(ledWhite, GPIO.HIGH)
        else:
            GPIO.output(ledWhite, GPIO.LOW)
            time.sleep(0.2)

        # Check rain API and display appropriate messages
        rain = get_weather("PTY", longitude, latitude)
        rainfall = get_weather("RN1", longitude, latitude)
        ##rain = 1
        ##rainfall = 6.5

        if rain is not None and int(rain) != 0:
            # Close servo, activate buzzer, display "Take umbrella!"
            pwm_b.start(50.0)
            time.sleep(1.0)
            pwm_b.stop()
            pwm_s.ChangeDutyCycle(0.0)

            mylcd.lcd_clear()
            mylcd.lcd_display_string("Take umbrella!", 1)
            time.sleep(1)

            # Check rainfall and display "Take rainshoes!"
            if rainfall is not None and float(rainfall) >= 6.5:
                mylcd.lcd_display_string("& rainshoes too!", 1)
                time.sleep(0.5)
        else:
            # Open servo, stop buzzer, display "Today is sunny"
            time.sleep(1.0)
            pwm_s.ChangeDutyCycle(7.5)
            pwm_b.stop()

            mylcd.lcd_display_string("Today is sunny", 1)
            time.sleep(0.5)

except KeyboardInterrupt:
    pass

mylcd.lcd_clear()
GPIO.cleanup()
spi.close()
pwm_s.stop()
pwm_b.stop()

import time
import threading
from utils.logger import log

try:
    import RPi.GPIO as GPIO
    IS_RPI = True
except ImportError:
    IS_RPI = False


class HardwareInterface:
    def __init__(self, relay_pin=17, pir_pin=27):
        self.relay_pin = relay_pin
        self.pir_pin = pir_pin
        self.pir_callback = None

        if IS_RPI:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.relay_pin, GPIO.OUT)
            GPIO.output(self.relay_pin, GPIO.LOW)
            GPIO.setup(self.pir_pin, GPIO.IN)
            GPIO.add_event_detect(self.pir_pin, GPIO.RISING,
                                  callback=self._pir_triggered, bouncetime=2000)
            log("Initialized Real GPIO (Raspberry Pi mode)")
        else:
            log("Initialized Mock GPIO (PC testing mode)")

    def _pir_triggered(self, channel=None):
        log("Hardware PIR Motion Detected!")
        if self.pir_callback:
            self.pir_callback()

    def set_pir_callback(self, callback):
        self.pir_callback = callback

    def unlock_door(self, duration=3):
        if IS_RPI:
            log("Real GPIO: Opening Door Relay")
            GPIO.output(self.relay_pin, GPIO.HIGH)
            def lock_again():
                time.sleep(duration)
                GPIO.output(self.relay_pin, GPIO.LOW)
                log("Real GPIO: Closing Door Relay")
            threading.Thread(target=lock_again, daemon=True).start()
        else:
            log(f"Mock GPIO: DOOR UNLOCKED for {duration} seconds")

    def lock_door(self):
        if IS_RPI:
            log("Real GPIO: Closing Door Relay immediately")
            GPIO.output(self.relay_pin, GPIO.LOW)
        else:
            log("Mock GPIO: DOOR LOCKED immediately")

    def mock_pir_trigger(self):
        if not IS_RPI:
            self._pir_triggered()

    def cleanup(self):
        if IS_RPI:
            GPIO.cleanup()

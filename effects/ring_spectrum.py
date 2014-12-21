# Hyperion audio visualization effect by RanzQ
# ranzq87 [(at)] gmail.com

from devkit import hyperion
import sys
import time
import colorsys
import math

from effects.spectrum_dump import GstSpectrumDump


BLACK = (0, 0, 0)

class Effect(object):

    def __init__(self):


        # Get the parameters
        # rotationTime = float(hyperion.args.get('rotation-time', 3.0))
        # brightness = float(hyperion.args.get('brightness', 1.0))
        # saturation = float(hyperion.args.get('saturation', 1.0))
        # reverse = bool(hyperion.args.get('reverse', False))
        rotationTime = 1.0
        brightness = 1.0
        saturation = 1.0
        reverse = False

        # Check parameters
        rotationTime = max(0.1, rotationTime)
        brightness = max(0.0, min(brightness, 1.0))
        saturation = max(0.0, min(saturation, 1.0))

        # Initialize the led data
        self.ledsData = bytearray()
        for i in range(hyperion.ledCount/2):
            hue = float(i)/(hyperion.ledCount/2+30)
            rgb = colorsys.hsv_to_rgb(hue, saturation, brightness)
            self.ledsData += bytearray((int(255*rgb[0]), int(255*rgb[1]), int(255*rgb[2])))

        for i in range(hyperion.ledCount/2, 0, -1):
            hue = float(i)/(hyperion.ledCount/2+30)
            rgb = colorsys.hsv_to_rgb(hue, saturation, brightness)
            self.ledsData += bytearray((int(255*rgb[0]), int(255*rgb[1]), int(255*rgb[2])))

        # Temp buffer
        self.ledsDataTemp = bytearray(self.ledsData)

        # Calculate the sleep time and rotation increment
        self.increment = 3
        self.sleepTime = rotationTime / hyperion.ledCount

        if reverse:
            self.increment = -self.increment


        self.processing = False

        # Minimum magnitude level
        self.mag_min = 0.0

        # Maximum magnitude level
        self.mag_max = 70.0

        self.bands = hyperion.ledCount / 2


    def receive_magnitudes(self, magnitudes):

        # Don't update when processing
        if self.processing:
            return
        else:
            self.magnitudes = magnitudes
            self.update_leds()


    def normalize_mag(self, magnitude):
        # Normalize magnitude to 0-255

        if magnitude < self.mag_min:
            return 0
        if magnitude > self.mag_max:
            return 255

        return int(((magnitude-self.mag_min) / (self.mag_max - self.mag_min)) * 255)


    def update_leds(self):

        self.processing = True

        # bass = self.normalize_mag(self.magnitudes[0])

        # sys.stdout.write("\033[K")
        # sys.stdout.write('\r' + int(self.magnitudes[0])*'|' )

        # Copy all values
        self.ledsDataTemp[:] = self.ledsData[:]

        self.current_mag = 0.0

        # Scale them
        for i in range(0, self.bands):

            self.current_mag = self.normalize_mag(self.magnitudes[i])

            for j in range(0,3):

                self.ledsDataTemp[i*3+j] = (self.ledsDataTemp[i*3+j] * self.current_mag) >> 8

                self.ledsDataTemp[-1-i*3-j] = (self.ledsDataTemp[-1-i*3-j] * self.current_mag) >> 8

        self.processing = False



effect = Effect()

# You can play with the parameters here (quiet=False to print the magnitudes for example)
spectrum = GstSpectrumDump(source='autoaudiosrc', vumeter=False, quiet=True, bands=effect.bands+30, interval=20,callback=effect.receive_magnitudes)
spectrum.start()

while not hyperion.abort():

    hyperion.setColor(effect.ledsDataTemp)
    # effect.ledsData = effect.ledsData[-effect.increment:] + effect.ledsData[:-effect.increment]
    time.sleep(0.01)


spectrum.stop()
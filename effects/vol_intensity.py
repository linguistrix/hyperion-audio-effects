"""VU meter effect."""

import time
import webcolors

from app import hyperion
from effects.spectrum_dump import GstSpectrumDump

BLACK = (0, 0, 0)

class Effect(object):
    def __init__(self):
        self.processing = False
        self._leds_data = bytearray(hyperion.ledCount * (0, 0, 0))

        args = hyperion.args

        self.interval = int(100)
        
        self.level_min = int(args.get('level-min', 80))
        self.level_max = int(args.get('level-max', 100))

        self.color = args.get('color', 'green')

        if self.color.startswith('#'):
            self.color = webcolors.hex_to_rgb(self.color)
        else:
            self.color = webcolors.name_to_rgb(self.color)

        self.ledCount = hyperion.ledCount
        
        self._magnitudes = None


        print 'Effect: Volumetric Intensity '
        print '----------------'
        print 'Led Count:'
        print self.ledCount
        
        self._spectrum = GstSpectrumDump(
            source=hyperion.args.get('audiosrc', 'autoaudiosrc'),
            vumeter=True,
            interval=self.interval,
            quiet=True,
            bands=4,
            callback=self.receive_magnitudes
            )
        self._spectrum.start()

        print 'Effect started, waiting for gstreamer messages...'

    def __del__(self):
        self.stop()

    def stop(self):
        self._spectrum.stop()

    def receive_magnitudes(self, magnitudes):

        if hyperion.abort():
            self.stop()

        # Don't update when processing
        if self.processing:
            return
        else:
            self._magnitudes = magnitudes
            self.update_leds()
            hyperion.setColor(self._leds_data)


    def mag_to_gain(self, magnitude):
        # Magnitude is 0-100, get index according to min and max
        gain = ((magnitude-self.level_min) / (self.level_max - self.level_min)) * 1.0)
        return gain


    def update_led(self, i, color):
        self._leds_data[3*i:3*i+3] = color


    def get_led_color(self, gain):
        start_factor = (1 - gain)
        end_factor = gain

        r_s, g_s, b_s = 0, 0, 0
        r_e, g_e, b_e = self.color

        return (int(r_s*start_factor + r_e*end_factor % 256),
                int(g_s*start_factor + g_e*end_factor % 256),
                int(b_s*start_factor + b_e*end_factor % 256))


    def update_leds(self):

        self.processing = True

        # We get 4 magnitudes from gst (not sure about R/L order)
        # [0] Left, [1] left peak, [2] right, [3] right peak

        # If vumeter=False, magnitudes hold the spectrum data,
        # do something else with them...

        # Length of magnitudes array equals number of bands

        left = self.mag_to_gain(self._magnitudes[0])
        right = self.mag_to_gain(self._magnitudes[2])

        gain = 0.5 * (left + right)

        cur_color = self.get_led_color(gain)
        
        for i in range(0, self.ledCount):
            self.update_led(i, cur_color)

        self.processing = False

def run():
    """ Run this effect until hyperion aborts. """
    effect = Effect()

    # Keep this thread alive
    while not hyperion.abort():
        time.sleep(1)

    effect.stop()

run()

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

        self.level_min = int(args.get('level-min', 80))
        self.level_max = int(args.get('level-max', 100))
        self.interval = int(args.get('interval', 100))

        self.left_start = args.get('left-start')
        self.left_end = args.get('left-end')
        self.right_start = args.get('right-start')
        self.right_end = args.get('right-end')

        self.color_start = args.get('color-start', 'green')
        self.color_end = args.get('color-end', 'red')

        if self.color_start.startswith('#'):
            self.color_start = webcolors.hex_to_rgb(self.color_start)
        else:
            self.color_start = webcolors.name_to_rgb(self.color_start)

        if self.color_end.startswith('#'):
            self.color_end = webcolors.hex_to_rgb(self.color_end)
        else:
            self.color_end = webcolors.name_to_rgb(self.color_end)

        self.leds_left = hyperion.leds_left
        self.leds_right = hyperion.leds_right
        self.leds_top = hyperion.leds_top
        self.leds_right.reverse()

        self._magnitudes = None

        if self.left_start is not None:
            if None in (self.left_start, self.left_end, self.right_start, self.right_end):
                raise Exception('Only left start provided, set all or none')
            else:
                self.leds_left = []
                self.leds_right = []
                step_left = 1
                if self.left_end < self.left_start:
                    step_left = -1
                step_right = 1
                if self.right_end < self.right_start:
                    step_right = -1
                for i in range(self.left_start, self.left_end + step_left, step_left):
                    self.leds_left.append(i)
                for i in range(self.right_start, self.right_end + step_right, step_right):
                    self.leds_right.append(i)

        print 'Effect: VU meter'
        print '----------------'
        print 'Left leds:'
        print self.leds_left
        print 'Right leds:'
        print self.leds_right
        print 'Top leds:'
        print self.leds_top

        self.height = len(self.leds_left)
        self.width = len(self.leds_top)

        self.update_led(self.width/2, BLACK)

        # Helper for color function
        self.height_float = float(self.height)

        self.color_map = []

        self.top_color_map = []

        for i in range(0, self.height):
            self.color_map.append(self.get_led_color(i, float(self.height)))

        for i in range(0, self.width/2+1):
            self.top_color_map.append(self.get_led_color(i, float(self.width/2)))

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


    def mag_to_idx(self, magnitude, maximum):
        # Magnitude is 0-100, get index according to min and max
        idx = int(((magnitude-self.level_min) / (self.level_max - self.level_min)) * maximum)
        return idx


    def update_led(self, i, color):
        self._leds_data[3*i:3*i+3] = color


    def get_led_color(self, i, maximum):
        # Gradient from start to end

        start_factor = (maximum - i) / maximum
        end_factor = i / maximum

        r_s, g_s, b_s = self.color_start
        r_e, g_e, b_e = self.color_end

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

        left = self.mag_to_idx(self._magnitudes[0], self.height)
        left_peak = self.mag_to_idx(self._magnitudes[1], self.height)
        right = self.mag_to_idx(self._magnitudes[2], self.height)
        right_peak = self.mag_to_idx(self._magnitudes[3], self.height)

        top_left = self.width/2 - self.mag_to_idx(self._magnitudes[0], self.width/2)
        top_left_peak = self.width/2 - self.mag_to_idx(self._magnitudes[1], self.width/2)
        top_right = self.width/2 + self.mag_to_idx(self._magnitudes[2], self.width/2)
        top_right_peak = self.width/2 + self.mag_to_idx(self._magnitudes[3], self.width/2)

        for i in range(0, self.height):

            left_i = self.leds_left[i]
            right_i = self.leds_right[i]
            color_i = self.color_map[i]

            if i <= left or i == left_peak:
                self.update_led(left_i, color_i)
            else:
                self.update_led(left_i, BLACK)

            if i <= right or i == right_peak:
                self.update_led(right_i, color_i)
            else:
                self.update_led(right_i, BLACK)
        
        for i in range(0, self.width):
            top_i = self.leds_top[i]
            color_i = self.top_color_map[abs(i-self.width/2)]

            if i < self.width/2:
                if i >= top_left or i == top_left_peak:
                    self.update_led(top_i, color_i)
                else:
                    self.update_led(top_i, BLACK)
            elif i > self.width/2:
                if i <= top_right or i == top_right_peak:
                    self.update_led(top_i, color_i)
                else:
                    self.update_led(top_i, BLACK)

        self.processing = False


def run():
    """ Run this effect until hyperion aborts. """
    effect = Effect()

    # Keep this thread alive
    while not hyperion.abort():
        time.sleep(1)

    effect.stop()

run()

"""Change intensity of ambilight based on volume"""

import time
import webcolors

from app import hyperion
from effects.spectrum_dump import GstSpectrumDump

class Effect(object):
    def __init__(self):
        self.processing = False

        args = hyperion.args

        self.interval = int(100)
        
        self.level_min = int(args.get('level-min', 80))
        self.level_max = int(args.get('level-max', 100))

        self._magnitudes = None


        print 'Effect: Volumetric Ambilight Gain  '
        
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
            gain = max(0, self.mag_to_gain(0.5 * (self._magnitudes[0] + self._magnitudes[2])))
            hyperion.setGain(gain)


    def mag_to_gain(self, magnitude):
        # Magnitude is 0-100, get index according to min and max
        gain = ((magnitude-self.level_min) / (self.level_max - self.level_min)) * 2.0
        return gain

def run():
    """ Run this effect until hyperion aborts. """
    effect = Effect()

    # Keep this thread alive
    while not hyperion.abort():
        time.sleep(1)

    effect.stop()

run()

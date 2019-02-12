import numpy as np
from bokeh.io import push_notebook, output_notebook, export_png
import matplotlib.pyplot as plt
from bokeh.plotting import *
from bokeh.models import LogColorMapper
import os
import pickle
import imageio
import PIL
from PIL import Image
from threading import Thread, Lock, Event
#import colorcet
import avmu

CABLE_DELAYS = 0.65 * 2
SWEEP_COUNT = 2
AVMU_IP_ADDRESS = "192.168.1.219"

class AvmuCapture:
    def __init__(self, hop_rate='HOP_15K', points=1024, start_f=250, stop_f=2100, avmu_ip='192.168.1.219'):
        self.device = avmu.AvmuInterface()
        self.hop_rate = hop_rate
        self.points = points
        self.start_f = start_f
        self.stop_f = stop_f
        self.avmu_ip = avmu_ip
        self.prev_sweep_data = []
        self.prev_sweep_data_lock = Lock()
        self.sweep_data_generated_event = Event()

    def initialize(self):
        self.device.setIPAddress(self.avmu_ip)
        self.device.setIPPort(1027)
        self.device.setTimeout(500)
        self.device.setMeasurementType('PROG_ASYNC')

        self.device.initialize()

        self.device.setHopRate(self.hop_rate)
        self.device.addPathToMeasure('AVMU_TX_PATH_0', 'AVMU_RX_PATH_1')

        self.device.utilGenerateLinearSweep(startF_mhz=self.start_f, stopF_mhz=self.stop_f, points=self.points)

    def capture(self):
        while True:
            frequencies = self.device.getFrequencies()
            self.device.start()
            self.device.beginAsync()
            self.device.measure()
            sweeps = [self.device.extractAllPaths()]
            self.device.haltAsync()
            self.device.stop()
            sweeps = [np.multiply(tmp[0][1]['data'], np.hanning(len(sweeps[0]))) for tmp in sweeps]
            step = abs(frequencies[0] - frequencies[-1]) / len(frequencies)
            front_padding_count = max(int(frequencies[0] / step), 0)
            for i in range(len(sweeps)):
                data_pt = sweeps[i]

                padded_data = []

                while len(padded_data) < front_padding_count:
                    padded_data.append(0)
                padded_data.extend(data_pt)

                powers_of_two = [2 ** x for x in range(16)]

                for size in powers_of_two:
                    if size > len(padded_data):
                        final_size = size
                        break

                while len(padded_data) < final_size:
                    padded_data.append(0)

                padded_data = np.array(padded_data)
                self.prev_sweep_data_lock.acquire()
                if len(self.prev_sweep_data) < 2:
                    print("HERE")
                    self.prev_sweep_data.append(np.fft.ifft(padded_data))
                else:
                    self.prev_sweep_data_lock.release()
                    self.sweep_data_generated_event.wait()
                    self.sweep_data_generated_event.clear()
                self.prev_sweep_data_lock.release()

    def generate_image(self):
        while True:
            self.prev_sweep_data_lock.acquire()
            if len(self.prev_sweep_data) == 2:
                time_domain_data = np.array(self.prev_sweep_data)
                self.prev_sweep_data.pop(0)
                self.sweep_data_generated_event.set()
                axis = np.array(range(time_domain_data.shape[1]))
            #
            # step = step * 1e6  # Hertz
            # axis = axis * (1 / (len(axis) * step * 2))  # Hertz to seconds
            # axis = axis * 1e9  # Nanoseconds
            # axis = axis - CABLE_DELAYS
            # axis = axis * 0.983571  # Nanoseconds to feet
            # axis = axis * .5

                diff_ccd = np.zeros(time_domain_data.shape)

                for s in range(time_domain_data.shape[0]):
                    diff_ccd[s] = np.abs(time_domain_data[s] - time_domain_data[s - 1])

                diff_ccd = np.power(diff_ccd, (1 / 3))
                im = Image.fromarray(diff_ccd)
                im.save()
                #p = figure(x_range=(0, diff_ccd.shape[0]), y_range=(0, diff_ccd.shape[1]), plot_width=1000, plot_height=600)
                #p.image(image=[diff_ccd], x=0, y=0, dw=diff_ccd.shape[0], dh=diff_ccd.shape[1])
                #show(p)
            self.prev_sweep_data_lock.release()
cap = AvmuCapture()
cap.initialize()
producerThread = Thread(target=cap.capture)
print("Initializing")
consumerThread = Thread(target=cap.generate_image)
producerThread.start()
consumerThread.start()
producerThread.join()
consumerThread.join()

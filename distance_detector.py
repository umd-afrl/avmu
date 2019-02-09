import numpy as np
from bokeh.io import push_notebook, output_notebook
from bokeh.plotting import *
from bokeh.models import LogColorMapper
import os
import pickle
import imageio
import colorcet
import avmu
import demo_simple

CABLE_DELAYS = 0.65 * 2
SWEEP_COUNT = 2
AVMU_IP_ADDRESS = "192.168.1.219"
# DATA_DIRS = [dI for dI in os.listdir() if (os.path.isdir(dI) and not dI[0] == '.')]
# DATA_DIRS.sort(reverse=True)
# FOLDER_NAME = DATA_DIRS[4]
# print(FOLDER_NAME)

class AvmuCapture:
    def __init__(self, hop_rate='HOP_15K', points=1024, start_f=250, stop_f=2100, avmu_ip='192.168.1.219'):
        self.device = avmu.AvmuInterface()
        self.hop_rate = hop_rate
        self.points = points
        self.start_f = start_f
        self.stop_f = stop_f
        self.avmu_ip = avmu_ip

        self.prev_padded_data = None

    def initialize(self):
        self.device.setIPAddress(self.avmu_ip)
        self.device.setIPPort(1027)
        self.device.setTimeout(500)
        self.device.setMeasurementType('PROG_ASYNC')

        self.device.initialize()

        self.device.setHopRate(self.hop_rate)
        self.device.addPathToMeasure('AVMU_TX_PATH_0', 'AVMU_RX_PATH_1')

        self.device.utilGenerateLinearSweep(startF_mhz=self.start_f, stopF_mhz=self.stop_f, points=self.points)

#await
    def create_frame(self):
        global prev_sweep
        frequencies = self.device.getFrequencies()
        self.device.start()
        self.device.beginAsync()

        #await
        self.device.measure()
        sweeps = [self.device.extractAllPaths()]
        self.device.haltAsync()
        time_per_frame = self.device.getPreciseTimePerFrame()

        sweeps = [np.multiply(tmp[0][1]['data'], np.hanning(len(sweeps[0]))) for tmp in sweeps]

        step = abs(frequencies[0] - frequencies[-1]) / len(frequencies)
        front_padding_count = max(int(frequencies[0] / step), 0)

        time_domain_data = []

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

        if self.prev_sweep is not None:

            time_domain_data.append(np.fft.ifft(padded_data))
            time_domain_data = np.array(time_domain_data)
            axis = np.array(range(time_domain_data.shape[1]))

            step = step * 1e6  # Hertz
            axis = axis * (1 / (len(axis) * step * 2))  # Hertz to seconds
            axis = axis * 1e9  # Nanoseconds
            axis = axis - CABLE_DELAYS
            axis = axis * 0.983571  # Nanoseconds to feet
            axis = axis * .5

            diff_ccd = np.zeros(time_domain_data.shape)

            for s in range(time_domain_data.shape[0]):
                diff_ccd[s] = np.abs(time_domain_data[s] - time_domain_data[s - 1])

            diff_ccd = np.power(diff_ccd, (1 / 3))

            p = figure(x_range=(0, diff_ccd.shape[0]), y_range=(0, diff_ccd.shape[1]), plot_width=1000, plot_height=600)
            p.image(image=[diff_ccd], x=0, y=0, dw=diff_ccd.shape[0], dh=diff_ccd.shape[1], palette=colorcet.fire)
            show(p)


        else:
            self.prev_padded_data = padded_data

        self.device.stop()

cap = AvmuCapture()
cap.initialize()
cap.create_frame()
cap.create_frame()
import numpy as np
from PIL import Image
from threading import Thread, Lock
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
        self.image_file_lock = Lock()
        self.device.setIPAddress(self.avmu_ip)
        self.device.setIPPort(1027)
        self.device.setTimeout(500)
        self.device.setMeasurementType('PROG_ASYNC')

        self.device.initialize()

        self.device.setHopRate(self.hop_rate)
        self.device.addPathToMeasure('AVMU_TX_PATH_0', 'AVMU_RX_PATH_1')

        self.device.utilGenerateLinearSweep(startF_mhz=self.start_f, stopF_mhz=self.stop_f, points=self.points)

    def capture(self):
        self.device.start()
        self.device.beginAsync()
        while True:
            try:
                frequencies = self.device.getFrequencies()
                self.device.measure()
                sweeps = [self.device.extractAllPaths()]
                
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
                    self.prev_sweep_data_lock.acquire();
                    while len(self.prev_sweep_data) >= 2:
                        self.prev_sweep_data.pop(0);
                    self.prev_sweep_data.append(np.fft.ifft(padded_data))
                    self.prev_sweep_data_lock.release()
            except KeyboardInterrupt:
                self.device.haltAsync()
                self.device.stop()

    def generate_image(self):
        while True:
            self.prev_sweep_data_lock.acquire()
            if len(self.prev_sweep_data) == 2:
                time_domain_data = np.array(self.prev_sweep_data)
                self.prev_sweep_data.pop(0)
                self.prev_sweep_data_lock.release()

                diff_ccd = np.zeros(time_domain_data.shape)

                for s in range(time_domain_data.shape[0]):
                    diff_ccd[s] = np.abs(time_domain_data[s] - time_domain_data[s - 1])

                diff_ccd = np.power(diff_ccd, (2))
                im = Image.fromarray(diff_ccd)
                im = im.convert('RGB')
                self.image_file_lock.acquire()
                im.save("akela.jpg")
                self.image_file_lock.release()
            else:
                self.prev_sweep_data_lock.release()

    def get_image_lock(self):
        self.image_file_lock.acquire()

    def release_image_lock(self):
        self.image_file_lock.release()

    def start_threads(self):
        capture_thread = Thread(target=self.capture)
        image_generation_thread = Thread(target=self.generate_image)
        capture_thread.start()
        image_generation_thread.start()

# core/audio_detector.py — from Repo 2

import pyaudio
import numpy as np
import threading
import time
from scipy.fft import fft


class AudioDetector:
    def __init__(self, rate=16000, chunk=2048,
                 loud_threshold=0.6, voice_energy_threshold=0.3):
        self.rate = rate
        self.chunk = chunk
        self.loud_threshold = loud_threshold
        self.voice_energy_threshold = voice_energy_threshold

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16, channels=1, rate=self.rate,
            input=True, frames_per_buffer=self.chunk
        )
        self.current_status = "NORMAL"
        self.running = True
        self.thread = threading.Thread(target=self._process_audio, daemon=True)
        self.thread.start()

    def _process_audio(self):
        while self.running:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16) / 32768.0
                rms  = np.sqrt(np.mean(audio_data ** 2))
                peak = np.max(np.abs(audio_data))
                spectrum = np.abs(fft(audio_data))[: self.chunk // 2]
                freqs = np.fft.fftfreq(len(audio_data), 1 / self.rate)[: self.chunk // 2]
                voice_band   = spectrum[(freqs > 300) & (freqs < 3000)]
                voice_energy = np.mean(voice_band) if len(voice_band) > 0 else 0

                if peak > self.loud_threshold:
                    self.current_status = "LOUD_BANGING"
                elif rms > self.voice_energy_threshold and voice_energy > 0.01:
                    self.current_status = "AGGRESSIVE_SHOUTING"
                else:
                    self.current_status = "NORMAL"
                time.sleep(0.1)
            except Exception:
                self.current_status = "NORMAL"

    def get_audio_status(self):
        return self.current_status

    def stop(self):
        self.running = False
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

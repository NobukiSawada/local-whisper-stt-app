"""
Windows loopback audio capture module.
Provides one-shot recording (Step 1) and continuous chunk capture (Step 3+).
"""

import soundcard as sc
import soundfile as sf
import numpy as np

SAMPLE_RATE = 16000  # 16kHz — matches Whisper's expected input
DURATION = 5         # seconds (one-shot recording)
CHUNK_DURATION = 5   # seconds per chunk (continuous capture)
OUTPUT_FILE = "test_output.wav"


def find_loopback_device():
    """Return the first available loopback (speaker output) device."""
    all_mics = sc.all_microphones(include_loopback=True)
    loopback_devices = [m for m in all_mics if m.isloopback]

    if not loopback_devices:
        raise RuntimeError(
            "ループバックデバイスが見つかりません。\n"
            "Windowsサウンド設定で「ステレオミキサー」が有効になっているか確認してください。"
        )

    # Prefer the default speaker's loopback
    default_speaker_name = sc.default_speaker().name
    for device in loopback_devices:
        if default_speaker_name in device.name:
            return device

    return loopback_devices[0]


def record_loopback(duration=DURATION, sample_rate=SAMPLE_RATE, output_file=OUTPUT_FILE):
    device = find_loopback_device()
    print(f"録音デバイス: {device.name}")
    print(f"録音開始 ({duration}秒間)...")

    with device.recorder(samplerate=sample_rate) as recorder:
        frames = recorder.record(numframes=int(duration * sample_rate))

    # Stereo → Mono (Whisper は mono を想定)
    if frames.ndim > 1 and frames.shape[1] > 1:
        frames = frames.mean(axis=1)

    sf.write(output_file, frames, sample_rate)
    print(f"保存完了: {output_file}  (サンプルレート: {sample_rate} Hz, {duration}秒)")


def record_to_buffer(stop_event, sample_rate=SAMPLE_RATE):
    """Record loopback audio until stop_event is set. Returns a float32 numpy array."""
    device = find_loopback_device()
    chunks = []
    BLOCK = 4096
    with device.recorder(samplerate=sample_rate) as recorder:
        while not stop_event.is_set():
            block = recorder.record(numframes=BLOCK)
            if block.ndim > 1 and block.shape[1] > 1:
                block = block.mean(axis=1)
            chunks.append(block.astype("float32"))
    return np.concatenate(chunks) if chunks else np.zeros(0, dtype="float32")


def capture_loop(audio_queue, chunk_duration=CHUNK_DURATION, sample_rate=SAMPLE_RATE,
                 stop_event=None, on_chunk_recorded=None):
    """Continuously capture loopback audio and put float32 numpy arrays into audio_queue."""
    device = find_loopback_device()
    print(f"録音デバイス: {device.name}")

    with device.recorder(samplerate=sample_rate) as recorder:
        while not stop_event.is_set():
            frames = recorder.record(numframes=int(chunk_duration * sample_rate))
            if frames.ndim > 1 and frames.shape[1] > 1:
                frames = frames.mean(axis=1)
            audio_queue.put(frames.astype("float32"))
            if on_chunk_recorded:
                on_chunk_recorded()
    audio_queue.put(None)  # 番兵: 文字起こしスレッドに録音終了を通知


if __name__ == "__main__":
    record_loopback()

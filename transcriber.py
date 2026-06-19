"""
Step 2: Transcription module using faster-whisper.
Reads test_output.wav and prints transcription to console.
"""

from faster_whisper import WhisperModel
import ctranslate2

MODEL_SIZE = "large-v3-turbo"  # 日本語精度と速度のベストバランス
INPUT_FILE = "test_output.wav"


def get_device():
    """CUDA が使えれば GPU、なければ CPU を自動選択する。"""
    try:
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def load_model(model_size=MODEL_SIZE):
    device, compute_type = get_device()
    print(f"デバイス: {device}  /  量子化: {compute_type}")
    print(f"モデル読み込み中: {model_size}  (初回は自動ダウンロード・数分かかります)")
    return WhisperModel(model_size, device=device, compute_type=compute_type), device


def transcribe(audio_file=INPUT_FILE, model=None):
    if model is None:
        model, _ = load_model()

    print(f"\n文字起こし開始: {audio_file}")
    segments, info = model.transcribe(
        audio_file,
        language="ja",
        beam_size=5,
        vad_filter=True,                              # 無音区間をスキップして高速化
        vad_parameters={"min_silence_duration_ms": 500},
    )

    print(f"検出言語: {info.language}  (確率: {info.language_probability:.1%})")
    print("--- 文字起こし結果 ---")

    lines = []
    for seg in segments:
        text = seg.text.strip()
        print(f"[{seg.start:.1f}s -> {seg.end:.1f}s]  {text}")
        lines.append(text)

    print("--- 終了 ---")
    return "\n".join(lines)


def transcribe_array(audio_array, model, on_segment=None, time_offset=0.0,
                     initial_prompt=None):
    """Transcribe a float32 numpy array.
    Calls on_segment(text, timestamp_str) per segment.
    time_offset: seconds before this chunk start (for absolute timestamps).
    """
    segments, _ = model.transcribe(
        audio_array,
        language="ja",
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        initial_prompt=initial_prompt,
    )
    lines = []
    for seg in segments:
        text = seg.text.strip()
        lines.append(text)
        if on_segment:
            abs_sec = int(time_offset + seg.start)
            m, s = divmod(abs_sec, 60)
            on_segment(text, f"{m:02d}:{s:02d}")
    return "\n".join(lines)


if __name__ == "__main__":
    transcribe()

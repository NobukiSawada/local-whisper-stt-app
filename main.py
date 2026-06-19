"""
Step 5: Concurrent recording + transcription GUI.
Records in chunks and transcribes in parallel; continues transcribing after recording stops.
"""

import queue
import threading
from tkinter import filedialog

import customtkinter as ctk

from audio_capture import capture_loop
from transcriber import load_model, transcribe_array

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

CHUNK_DURATION = 5  # seconds per audio chunk


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ループバック文字起こし")
        self.geometry("720x520")
        self.resizable(True, True)

        self._model = None
        self._recording_stop_event = threading.Event()
        self._transcribe_stop_event = threading.Event()
        self._audio_queue = None
        self._is_recording = False

        self._build_ui()
        self._load_model_async()

    def _build_ui(self):
        self._status = ctk.CTkLabel(self, text="モデル読み込み中...", anchor="w")
        self._status.pack(fill="x", padx=20, pady=(14, 0))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        self._start_btn = ctk.CTkButton(btn_frame, text="開始", width=100,
                                        command=self._start, state="disabled")
        self._start_btn.pack(side="left", padx=6)

        self._stop_btn = ctk.CTkButton(btn_frame, text="停止", width=100,
                                       command=self._stop, state="disabled")
        self._stop_btn.pack(side="left", padx=6)

        self._save_btn = ctk.CTkButton(btn_frame, text="保存", width=100,
                                       command=self._save, state="disabled")
        self._save_btn.pack(side="left", padx=6)

        self._textbox = ctk.CTkTextbox(self, wrap="word")
        self._textbox.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    # --- model loading ---

    def _load_model_async(self):
        def _load():
            model, _ = load_model()
            self._model = model
            self.after(0, self._on_model_ready)
        threading.Thread(target=_load, daemon=True).start()

    def _on_model_ready(self):
        self._set_status("準備完了")
        self._start_btn.configure(state="normal")

    # --- start ---

    def _start(self):
        self._recording_stop_event.clear()
        self._transcribe_stop_event.clear()
        self._is_recording = True
        self._audio_queue = queue.Queue()  # 無制限キュー: 録音スレッドをブロックしない
        self._textbox.delete("1.0", "end")
        self._set_status("録音中...")
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._save_btn.configure(state="disabled")

        def _capture_worker():
            capture_loop(
                audio_queue=self._audio_queue,
                chunk_duration=CHUNK_DURATION,
                stop_event=self._recording_stop_event,
            )
            self.after(0, self._on_recording_stopped)

        threading.Thread(target=_capture_worker, daemon=True).start()
        threading.Thread(target=self._transcribe_loop, daemon=True).start()

    # --- stop (録音中 or 文字起こし中で挙動が変わる) ---

    def _stop(self):
        if self._is_recording:
            self._recording_stop_event.set()
            self._set_status("録音停止中...")
            self._stop_btn.configure(state="disabled")
        else:
            # 文字起こし中断
            self._transcribe_stop_event.set()
            self._audio_queue.put(None)  # get() でブロック中のスレッドを解放
            self._stop_btn.configure(state="disabled")

    def _on_recording_stopped(self):
        self._is_recording = False
        self._set_status("録音停止・文字起こし中...")
        self._stop_btn.configure(state="normal")  # 文字起こし中断ボタンとして再有効化

    # --- transcription loop (None または中断イベントで終了) ---

    def _transcribe_loop(self):
        while True:
            chunk = self._audio_queue.get()
            if chunk is None or self._transcribe_stop_event.is_set():
                break

            def on_segment(text):
                self.after(0, lambda t=text: self._append_text(t))

            transcribe_array(chunk, self._model, on_segment=on_segment)

        self.after(0, self._on_done)

    def _on_done(self):
        self._set_status("完了")
        self._start_btn.configure(state="normal")
        self._save_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

    # --- helpers ---

    def _append_text(self, text):
        self._textbox.insert("end", text + "\n")
        self._textbox.see("end")

    def _set_status(self, text):
        self._status.configure(text=text)

    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
        )
        if not path:
            return
        text = self._textbox.get("1.0", "end").strip()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        self._set_status(f"保存完了: {path}")


if __name__ == "__main__":
    app = App()
    app.mainloop()

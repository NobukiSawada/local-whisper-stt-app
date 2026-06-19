"""
Step 4: CustomTkinter GUI for loopback transcription.
Records all audio first, then transcribes after stopping.
"""

import threading
from tkinter import filedialog

import customtkinter as ctk

from audio_capture import record_to_buffer
from transcriber import load_model, transcribe_array

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ループバック文字起こし")
        self.geometry("720x520")
        self.resizable(True, True)

        self._model = None
        self._audio_buffer = None
        self._stop_event = threading.Event()

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

    # --- recording ---

    def _start(self):
        self._stop_event.clear()
        self._audio_buffer = None
        self._textbox.delete("1.0", "end")
        self._set_status("録音中...")
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._save_btn.configure(state="disabled")

        def _record():
            self._audio_buffer = record_to_buffer(self._stop_event)
            self.after(0, self._on_recording_done)

        threading.Thread(target=_record, daemon=True).start()

    def _stop(self):
        self._stop_event.set()
        self._set_status("録音停止中...")
        self._stop_btn.configure(state="disabled")

    def _on_recording_done(self):
        if self._audio_buffer is None or len(self._audio_buffer) == 0:
            self._set_status("録音データがありません")
            self._start_btn.configure(state="normal")
            return

        self._set_status("文字起こし中...")

        def _transcribe():
            def on_segment(text):
                self.after(0, lambda t=text: self._append_text(t))
            transcribe_array(self._audio_buffer, self._model, on_segment=on_segment)
            self.after(0, self._on_transcription_done)

        threading.Thread(target=_transcribe, daemon=True).start()

    # --- transcription done ---

    def _on_transcription_done(self):
        self._set_status("完了")
        self._start_btn.configure(state="normal")
        self._save_btn.configure(state="normal")

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

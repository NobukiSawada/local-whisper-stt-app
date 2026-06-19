"""
Step 7: Added error handling, safe close, timestamps, copy button,
        chunk-duration selector, model selector, and global hotkeys.
"""

import queue
import time
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from audio_capture import capture_loop
from transcriber import load_model, transcribe_array

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

MODEL_OPTIONS = ["large-v3-turbo", "medium", "small"]
CHUNK_OPTIONS = {"3秒": 3, "5秒": 5, "10秒": 10, "15秒": 15}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ループバック文字起こし")
        self.geometry("720x660")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._model = None
        self._recording_stop_event = threading.Event()
        self._transcribe_stop_event = threading.Event()
        self._audio_queue = None
        self._is_recording = False

        self._record_start_time = None
        self._total_chunks = 0
        self._done_chunks = 0
        self._chunk_times: list[float] = []

        self._build_ui()
        self._setup_hotkeys()
        self._load_model_async()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        # ステータス
        self._status = ctk.CTkLabel(self, text="モデル読み込み中...", anchor="w")
        self._status.pack(fill="x", padx=20, pady=(14, 0))

        # 設定行（モデル・チャンク長）
        settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        settings_frame.pack(fill="x", padx=20, pady=(6, 0))

        ctk.CTkLabel(settings_frame, text="モデル:").pack(side="left", padx=(0, 4))
        self._model_var = ctk.StringVar(value=MODEL_OPTIONS[0])
        self._model_menu = ctk.CTkOptionMenu(
            settings_frame, values=MODEL_OPTIONS,
            variable=self._model_var, width=160,
            command=self._on_model_changed,
        )
        self._model_menu.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(settings_frame, text="チャンク長:").pack(side="left", padx=(0, 4))
        self._chunk_var = ctk.StringVar(value="5秒")
        self._chunk_menu = ctk.CTkOptionMenu(
            settings_frame, values=list(CHUNK_OPTIONS.keys()),
            variable=self._chunk_var, width=100,
        )
        self._chunk_menu.pack(side="left")

        # 事前知識入力行
        prompt_frame = ctk.CTkFrame(self, fg_color="transparent")
        prompt_frame.pack(fill="x", padx=20, pady=(4, 0))

        ctk.CTkLabel(prompt_frame, text="事前知識 / 専門用語（カンマ区切り）:").pack(
            side="left", padx=(0, 8)
        )
        self._prompt_entry = ctk.CTkEntry(
            prompt_frame,
            placeholder_text="例: 統計的因果探索, LiNGAM, 因果推論",
            width=380,
        )
        self._prompt_entry.pack(side="left", fill="x", expand=True)

        # ボタン行
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=8)

        self._start_btn = ctk.CTkButton(btn_frame, text="開始 (Alt+R)", width=120,
                                        command=self._start, state="disabled")
        self._start_btn.pack(side="left", padx=4)

        self._stop_btn = ctk.CTkButton(btn_frame, text="停止 (Alt+S)", width=120,
                                       command=self._stop, state="disabled")
        self._stop_btn.pack(side="left", padx=4)

        self._copy_btn = ctk.CTkButton(btn_frame, text="コピー", width=90,
                                       command=self._copy, state="disabled")
        self._copy_btn.pack(side="left", padx=4)

        self._save_btn = ctk.CTkButton(btn_frame, text="保存", width=90,
                                       command=self._save, state="disabled")
        self._save_btn.pack(side="left", padx=4)

        # 進捗パネル
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=20, pady=(0, 8))

        row1 = ctk.CTkFrame(info_frame, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(8, 2))

        self._rec_time_label = ctk.CTkLabel(row1, text="録音時間:  --:--", anchor="w")
        self._rec_time_label.pack(side="left")

        self._chunk_label = ctk.CTkLabel(row1, text="チャンク:  0録音 / 0完了", anchor="e")
        self._chunk_label.pack(side="right")

        row2 = ctk.CTkFrame(info_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(2, 8))

        self._progress_bar = ctk.CTkProgressBar(row2)
        self._progress_bar.set(0)
        self._progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self._eta_label = ctk.CTkLabel(row2, text="0%完了", anchor="e", width=280)
        self._eta_label.pack(side="right")

        # テキストエリア
        self._textbox = ctk.CTkTextbox(self, wrap="word")
        self._textbox.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    # --------------------------------------------------------- hotkeys --

    def _setup_hotkeys(self):
        try:
            import keyboard
            keyboard.add_hotkey("alt+r", lambda: self.after(0, self._hotkey_start))
            keyboard.add_hotkey("alt+s", lambda: self.after(0, self._hotkey_stop))
        except Exception:
            # keyboard ライブラリ未インストール or 権限不足の場合は無効化
            pass

    def _hotkey_start(self):
        if str(self._start_btn.cget("state")) == "normal":
            self._start()

    def _hotkey_stop(self):
        if str(self._stop_btn.cget("state")) == "normal":
            self._stop()

    # ------------------------------------------------------- safe close --

    def _on_close(self):
        self._recording_stop_event.set()
        self._transcribe_stop_event.set()
        if self._audio_queue:
            self._audio_queue.put(None)
        self.destroy()

    # ------------------------------------------------------- model loading --

    def _load_model_async(self, model_size=None):
        if model_size is None:
            model_size = self._model_var.get()

        def _load():
            try:
                model, _ = load_model(model_size=model_size)
                self._model = model
                self.after(0, self._on_model_ready)
            except Exception as e:
                self.after(0, lambda: self._set_status(f"モデル読み込み失敗: {e}"))

        threading.Thread(target=_load, daemon=True).start()

    def _on_model_ready(self):
        self._set_status("準備完了")
        self._start_btn.configure(state="normal")
        self._model_menu.configure(state="normal")
        self._chunk_menu.configure(state="normal")

    def _on_model_changed(self, model_name: str):
        self._start_btn.configure(state="disabled")
        self._model_menu.configure(state="disabled")
        self._chunk_menu.configure(state="disabled")
        self._set_status(f"モデル変更中: {model_name} ...")
        self._load_model_async(model_size=model_name)

    # --------------------------------------------------------------- start --

    def _start(self):
        self._recording_stop_event.clear()
        self._transcribe_stop_event.clear()
        self._is_recording = True
        self._audio_queue = queue.Queue()
        self._record_start_time = time.time()
        self._total_chunks = 0
        self._done_chunks = 0
        self._chunk_times = []

        self._textbox.delete("1.0", "end")
        self._progress_bar.set(0)
        self._rec_time_label.configure(text="録音時間:  00:00")
        self._chunk_label.configure(text="チャンク:  0録音 / 0完了")
        self._eta_label.configure(text="0%完了")

        self._set_status("録音中...")
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._copy_btn.configure(state="disabled")
        self._save_btn.configure(state="disabled")
        self._model_menu.configure(state="disabled")
        self._chunk_menu.configure(state="disabled")

        chunk_duration = CHUNK_OPTIONS[self._chunk_var.get()]
        prompt_text = self._prompt_entry.get().strip()
        self._initial_prompt = prompt_text if prompt_text else None

        def _capture_worker():
            try:
                capture_loop(
                    audio_queue=self._audio_queue,
                    chunk_duration=chunk_duration,
                    stop_event=self._recording_stop_event,
                    on_chunk_recorded=lambda: self.after(0, self._on_chunk_recorded),
                )
            except Exception as e:
                self.after(0, lambda: self._set_status(f"録音エラー: {e}"))
                self._audio_queue.put(None)
            self.after(0, self._on_recording_stopped)

        threading.Thread(target=_capture_worker, daemon=True).start()
        threading.Thread(target=self._transcribe_loop, daemon=True).start()
        self.after(1000, self._tick)

    # ---------------------------------------------------------------- stop --

    def _stop(self):
        if self._is_recording:
            self._recording_stop_event.set()
            self._set_status("録音停止中...")
            self._stop_btn.configure(state="disabled")
        else:
            self._transcribe_stop_event.set()
            self._audio_queue.put(None)
            self._stop_btn.configure(state="disabled")

    def _on_recording_stopped(self):
        self._is_recording = False
        elapsed = time.time() - self._record_start_time
        m, s = divmod(int(elapsed), 60)
        self._rec_time_label.configure(text=f"録音時間:  {m:02d}:{s:02d}  (確定)")
        self._set_status("録音停止・文字起こし中...")
        self._stop_btn.configure(state="normal")

    # ---------------------------------------------------- recording timer --

    def _tick(self):
        if not self._is_recording:
            return
        elapsed = time.time() - self._record_start_time
        m, s = divmod(int(elapsed), 60)
        self._rec_time_label.configure(text=f"録音時間:  {m:02d}:{s:02d}")
        self.after(1000, self._tick)

    # ------------------------------------------------- chunk event handlers --

    def _on_chunk_recorded(self):
        self._total_chunks += 1
        self._update_progress()

    def _on_chunk_done(self, elapsed_sec: float):
        self._done_chunks += 1
        self._chunk_times.append(elapsed_sec)
        self._update_progress()

    def _update_progress(self):
        total = self._total_chunks
        done = self._done_chunks
        ratio = done / total if total > 0 else 0

        self._chunk_label.configure(text=f"チャンク:  {total}録音 / {done}完了")
        self._progress_bar.set(ratio)

        if self._chunk_times:
            avg = sum(self._chunk_times) / len(self._chunk_times)
            remaining = (total - done) * avg
            rm, rs = divmod(int(remaining), 60)
            self._eta_label.configure(
                text=f"{ratio*100:.0f}%完了  残り約{rm}分{rs:02d}秒  ({avg:.0f}秒/チャンク)"
            )
        else:
            self._eta_label.configure(text=f"{ratio*100:.0f}%完了")

    # ----------------------------------------------- transcription loop --

    def _transcribe_loop(self):
        chunk_index = 0
        chunk_duration = CHUNK_OPTIONS[self._chunk_var.get()]
        initial_prompt = self._initial_prompt

        while True:
            chunk = self._audio_queue.get()
            if chunk is None or self._transcribe_stop_event.is_set():
                break

            time_offset = chunk_index * chunk_duration
            t0 = time.time()

            def on_segment(text, ts):
                self.after(0, lambda t=text, s=ts: self._append_text(t, s))

            try:
                transcribe_array(chunk, self._model, on_segment=on_segment,
                                 time_offset=time_offset,
                                 initial_prompt=initial_prompt)
            except Exception as e:
                self.after(0, lambda: self._set_status(f"文字起こしエラー: {e}"))

            elapsed = time.time() - t0
            self.after(0, lambda e=elapsed: self._on_chunk_done(e))
            chunk_index += 1

        self.after(0, self._on_done)

    def _on_done(self):
        self._set_status("完了")
        self._start_btn.configure(state="normal")
        self._copy_btn.configure(state="normal")
        self._save_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._model_menu.configure(state="normal")
        self._chunk_menu.configure(state="normal")
        self._update_progress()

    # ---------------------------------------------------------------- helpers --

    def _append_text(self, text, timestamp: str = ""):
        line = f"[{timestamp}] {text}\n" if timestamp else f"{text}\n"
        self._textbox.insert("end", line)
        self._textbox.see("end")

    def _set_status(self, text):
        self._status.configure(text=text)

    def _copy(self):
        text = self._textbox.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("クリップボードにコピーしました")

    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
        )
        if not path:
            return
        text = self._textbox.get("1.0", "end").strip()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self._set_status(f"保存完了: {path}")
        except Exception as e:
            messagebox.showerror("保存エラー", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()

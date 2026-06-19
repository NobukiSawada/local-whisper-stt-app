# local-whisper-stt-app

Windowsのループバック音声（PC内部音声）をローカル環境でリアルタイム文字起こしするアプリケーション。  
外部APIを使用せず、完全にオフラインで動作します。

---

## 概要

Zoom等のオンライン会議・動画など、PC内部で鳴っている音声を録音し、  
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) を使ってローカルで文字起こしを行います。

- 機密情報を外部に送信しない（完全ローカル実行）
- 外部APIコスト不要
- 日本語認識に最適化されたモデルを使用

---

## システム構成

```
PC内部音声（ループバック）
        ↓
  audio_capture.py
  （soundcard でキャプチャ・バッファに蓄積）
        ↓
  transcriber.py
  （faster-whisper で文字起こし）
        ↓
  main.py（GUI）
  （CustomTkinter でテキストエリアに表示・保存）
```

### スレッド設計

```
メインスレッド（GUI）
├── 起動時: モデル読み込みスレッド（1回のみ）
├── 開始ボタン: 録音スレッド起動
│     └── record_to_buffer() → 音声をメモリに蓄積
└── 停止ボタン: 録音停止 → 文字起こしスレッド起動
      └── transcribe_array() → セグメントごとにGUIへ追記
```

録音と文字起こしを**分離**することで、CPU環境でも音声を逃さず確実に記録できます。

---

## ディレクトリ構成

```
local-whisper-stt-app/
├── main.py            # GUIエントリポイント（CustomTkinter）
├── audio_capture.py   # 音声取得モジュール（soundcard）
├── transcriber.py     # 文字起こしモジュール（faster-whisper）
├── requirements.txt   # 依存パッケージ
└── README.md
```

### 各ファイルの役割

| ファイル | 役割 | 主な関数 |
|---|---|---|
| `audio_capture.py` | ループバック音声の取得 | `find_loopback_device()` `record_to_buffer()` |
| `transcriber.py` | 音声のテキスト化 | `load_model()` `transcribe_array()` |
| `main.py` | GUI・スレッド管理 | `App` クラス |

---

## 技術スタック

| 用途 | ライブラリ |
|---|---|
| 音声取得（ループバック） | soundcard |
| 音声ファイル入出力 | soundfile |
| 数値処理 | numpy |
| 音声認識モデル | faster-whisper（`large-v3-turbo`） |
| GUI | CustomTkinter |

**モデル**: `large-v3-turbo`（初回起動時に自動ダウンロード・約800MB）  
**デバイス**: CUDA GPU があれば自動使用、なければ CPU（int8量子化）

---

## セットアップ

### 1. 依存パッケージのインストール

```powershell
pip install -r requirements.txt
```

### 2. Windowsのループバック設定

PCのサウンド設定で「ステレオミキサー」を有効にしてください。

1. タスクバーのスピーカーアイコンを右クリック →「サウンドの設定」
2. 「サウンドコントロールパネル」→「録音」タブ
3. 空白部分を右クリック →「無効なデバイスの表示」
4. 「ステレオミキサー」を右クリック →「有効化」

---

## 使い方

```powershell
python main.py
```

| ボタン | 動作 |
|---|---|
| 開始 | ループバック音声の録音を開始 |
| 停止 | 録音を停止し、文字起こしを開始 |
| 保存 | テキストエリアの内容を `.txt` として保存 |

**ボタンの状態遷移:**

```
起動（モデル読み込み中）→ 準備完了 → 録音中 → 文字起こし中 → 完了
```

文字起こしはセグメントが確定するたびにテキストエリアへ随時追記されます。

---

## 注意事項

- Windows 専用（soundcard の WASAPI ループバックを使用）
- CPU環境では録音時間が長いほど文字起こしに時間がかかります
- 録音データはメモリ上に保持されるため、長時間録音はRAM使用量が増加します  
  （目安: 1時間 ≒ 230MB）

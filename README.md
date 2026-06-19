# LoopbackTranscriber

Windows のループバック音声（PC から出る音）をリアルタイムでローカル文字起こしする Python アプリです。  
インターネット接続不要・無料で動作します。

## 機能

- **ループバック録音** — スピーカー出力を WASAPI 経由でキャプチャ
- **ローカル文字起こし** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) による GPU/CPU 自動選択推論
- **非同期キュー処理** — 録音しながら順次文字起こしするパイプライン
- **モデル選択** — `large-v3-turbo` / `medium` / `small` を UI から切り替え可能
- **チャンク長選択** — 3 / 5 / 10 / 15 秒から選択
- **進捗パネル** — 録音時間・チャンク数・推定残り時間をリアルタイム表示
- **事前知識 / 専門用語入力** — カンマ区切りで専門用語を入力すると `initial_prompt` として推論に反映し、認識精度を向上
- **グローバルホットキー** — `Alt+R` で開始、`Alt+S` で停止
- **テキスト出力** — コピーボタンとファイル保存に対応

## 動作環境

- Windows 10 / 11
- Python 3.10 以上
- CUDA 対応 GPU（任意）— なければ CPU 推論にフォールバック

## セットアップ

```bash
pip install -r requirements.txt
python main.py
```

初回起動時にモデルが自動ダウンロードされます（`large-v3-turbo` は約 1.5 GB）。

## 使い方

1. モデルとチャンク長を選択する
2. 必要に応じて「事前知識 / 専門用語」欄にカンマ区切りで用語を入力する  
   （例: `統計的因果探索, LiNGAM, 因果推論`）
3. **開始** ボタン（または `Alt+R`）を押して録音・文字起こしを開始する
4. **停止** ボタン（または `Alt+S`）を押すと、残りチャンクを文字起こしして完了する
5. 結果を **コピー** または **保存** する

## ビルド（exe 化）

### ローカルでビルドする

```bash
pip install pyinstaller
python build.py
```

実行後、`LoopbackTranscriber_Release.zip` が生成されます。  
中身は `LoopbackTranscriber/` フォルダ（exe 本体 + 依存ファイル + README.md）です。

### GitHub Actions で自動リリースする

バージョンタグをプッシュすると、Windows ランナーでビルドが走り ZIP が GitHub Releases に自動公開されます。

```bash
git tag v1.0.0
git push origin v1.0.0
```

ワークフロー定義: `.github/workflows/release.yml`

## ファイル構成

```
local-whisper-stt-app/
├── main.py           # GUI・録音・スレッド制御
├── transcriber.py    # faster-whisper ラッパー
├── audio_capture.py  # WASAPI ループバック録音
├── build.py          # ローカルビルドスクリプト
├── requirements.txt
└── .github/
    └── workflows/
        └── release.yml   # GitHub Actions 自動リリース
```

## ライセンス

MIT

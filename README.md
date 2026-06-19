# local-whisper-stt-app

A lightweight local Windows app to transcribe internal PC audio using Hugging Face models.

## 開発用Gitコマンド集

### 1. 新しい機能の開発を始めるとき

必ず `main` ブランチから最新の状態を取得し、新しい機能ブランチを作成して作業します。

```bash
# mainブランチに移動して最新にする
git checkout main
git pull origin main

# 新しい機能ブランチを作成して切り替え
git checkout -b feature/機能名
```

# AI Markdown to PowerPoint Generator

MarkdownからAIを活用して、スライド設計・画像生成・PPTX作成を一貫して行うツールです。

## 主な機能
1. **Markdown解析**: 基本的な構造（タイトル、スライド）を抽出
2. **AIプランニング (Gemini)**: 内容に基づいて、スライドごとのレイアウトと画像プロンプト（英語）を自動設計
3. **画像生成 (Google Nano Banana)**: GoogleのAIモデルを使用してスライド用画像を生成（失敗時はプレースホルダー）
4. **PPTXビルド**: 固定レイアウトで崩れないスライドを生成

## 必要要件
- `.env` ファイルによるAPIキー設定 (Google API Key)

## セットアップ手順

1. **APIキーの取得**: Google AI Studio等で API Key を取得してください。

2. **.env ファイルの作成**:
   プロジェクトルートに `.env` という名前のファイルを作成し、以下を記述してください。

   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   IMAGE_MODEL_NAME=nano-banana
   IMAGE_PROVIDER=google
   ```
   ※ `IMAGE_MODEL_NAME` は、実際に使用可能なモデルID（例: `imagen-3.0-generate-001` 等）に変更が必要な場合があります。デフォルトはユーザー指定の `nano-banana` です。

3. **ライブラリのインストール**:
   ```bash
   pip install -r requirements.txt
   ```

4. **起動**:
   ```bash
   streamlit run app.py
   ```

## 注意事項
- 画像生成に失敗した場合（モデルが非対応、制限等）、自動的にテキストのみのプレースホルダー画像が生成されます。
- `.env` ファイルは git にコミットしないでください（`.gitignore` 設定済み）。

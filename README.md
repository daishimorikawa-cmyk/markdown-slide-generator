# AI Markdown to PowerPoint Generator

Markdown原稿から、AIを活用してスライド設計・画像生成・PPTX作成を一貫して行うツールです。

## ツール一覧

### 1. CLI版（Node.js / OpenAI）

Markdown → OpenAI Chat Completions でスライド構成JSON → DALL·E 3 で画像生成 → pptxgenjs で PPTX 出力。

#### 必要要件
- Node.js v20+
- OpenAI API Key

#### セットアップ

```bash
# 依存パッケージのインストール
npm install

# .env ファイルの作成
cp .env.example .env
# エディタで .env を開き、OPENAI_API_KEY を設定
```

#### 使い方

```bash
# 基本的な使い方
node cli.js input.md out/presentation.pptx

# Markdown見出しでスライド分割するモード
node cli.js input.md out/presentation.pptx --headings

# 画像サイズを横長に変更
node cli.js input.md out/presentation.pptx --size 1792x1024

# 画像生成をスキップ（高速プレビュー）
node cli.js input.md out/presentation.pptx --no-images

# ヘルプ
node cli.js --help
```

#### 環境変数（.env）

| 変数名 | 必須 | デフォルト | 説明 |
|--------|------|-----------|------|
| `OPENAI_API_KEY` | ○ | - | OpenAI API キー |
| `OPENAI_MODEL` | - | `gpt-4.1-mini` | スライド構成生成に使うChatモデル |
| `DALLE_MODEL` | - | `dall-e-3` | 画像生成に使うDALL·Eモデル |

#### CLIオプション

| オプション | 説明 |
|-----------|------|
| `--headings` | Markdownの見出し（# / ##）でスライドを分割 |
| `--size <size>` | 画像サイズ: `1024x1024`（デフォルト）, `1792x1024`, `1024x1792` |
| `--no-images` | 画像生成をスキップしてPPTXのみ作成 |

#### 処理フロー

```
input.md
  ↓
1. OpenAI Chat Completions でスライド構成JSON生成
   - title, bullets(3-5), image_prompt（英語）を自動設計
   - Zodスキーマでバリデーション
  ↓
2. DALL·E 3 で各スライドの画像を生成
   - out/images/slide_01.png, slide_02.png, ...
   - 失敗時はリトライ（最大2回）、それでも失敗なら画像なしで続行
  ↓
3. pptxgenjs で PPTX を生成
   - 16:9レイアウト、タイトル＋箇条書き＋画像
  ↓
out/presentation.pptx
```

#### ファイル構成

```
cli.js            # CLIエントリポイント
src/plan.js       # Markdown → スライド構成JSON（OpenAI Chat）
src/images.js     # DALL·E 3 画像生成
src/pptx.js       # PPTX組み立て（pptxgenjs）
input.md          # サンプルMarkdown
.env.example      # 環境変数テンプレート
package.json      # Node.js依存関係
```

---

### 2. Streamlit版（Python / Google AI）

Streamlit UIを使ったWeb版。Google Generative AI（Gemini）でスライド設計・画像生成を行います。

#### 必要要件
- Python 3.10+
- Google API Key

#### セットアップ

```bash
pip install -r requirements.txt
```

`.env` ファイルを作成:
```env
GOOGLE_API_KEY=your_google_api_key_here
IMAGE_MODEL_NAME=nano-banana
IMAGE_PROVIDER=google
```

#### 起動

```bash
streamlit run app.py
```

#### Streamlit Cloud デプロイ（Vertex AI / サービスアカウント認証）

Streamlit Cloud で動かす場合、サービスアカウント JSON をリポジトリに含めず、
**Secrets** に貼り付けて使います。

1. Streamlit Cloud の **Settings → Secrets** を開く
2. 以下の TOML を貼り付ける（値は自分の環境に合わせて変更）

```toml
GCP_PROJECT_ID = "your-gcp-project-id"
GCP_LOCATION = "us-central1"
TEXT_MODEL_NAME = "gemini-1.5-flash-002"
IMAGE_PROVIDER = "google"
IMAGE_MODEL_NAME = "imagen-3.0-generate-001"

GCP_SA_JSON = """
{
  "type": "service_account",
  "project_id": "your-gcp-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...@your-gcp-project-id.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
"""
```

> **注意:** `GCP_SA_JSON` の値は三重引用符 `"""` で囲みます（TOML の複数行文字列）。
> サービスアカウント JSON の中身をそのまま貼り付けてください。

アプリ起動時に `GCP_SA_JSON` が検出されると、一時ファイルに書き出して
`GOOGLE_APPLICATION_CREDENTIALS` を自動設定します。ログに以下が出力されます:

```
[AUTH] using sa_json from secrets
[AUTH] wrote temp credentials: /tmp/gcp_sa_XXXX.json
```

#### ローカル開発

ローカルでは従来通り `.env` + JSON ファイル方式が使えます:

```env
GOOGLE_API_KEY=your_google_api_key_here
IMAGE_MODEL_NAME=imagen-3.0-generate-001
IMAGE_PROVIDER=google
```

または Vertex AI を使う場合:

```env
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1
TEXT_MODEL_NAME=gemini-1.5-flash-002
IMAGE_MODEL_NAME=imagen-3.0-generate-001
IMAGE_PROVIDER=google
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

#### 認証の優先順位

| 優先度 | モード | 条件 |
|--------|--------|------|
| 1 | Vertex AI (SA) | `GCP_PROJECT_ID` + `GOOGLE_APPLICATION_CREDENTIALS` が存在 |
| 2 | API Key | `GOOGLE_API_KEY` が存在 |
| 3 | Fallback | 認証なし → プレースホルダー画像 + フォールバックプラン |

設定値の取得は全て **Streamlit Secrets → 環境変数 → デフォルト** の順で解決されます。

## 注意事項
- 画像生成に失敗した場合、自動的にプレースホルダー画像のスライドが生成されます。
- `.env` ファイルは git にコミットしないでください（`.gitignore` 設定済み）。
- サービスアカウント JSON ファイルもリポジトリに含めないでください。

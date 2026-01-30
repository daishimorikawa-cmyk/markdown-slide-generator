"""
Phase B: Generate deck_json from extracted text using Gemini.

Output schema (deck_json):
{
  "deck_title": "...",
  "slides": [
    {
      "title": "...",
      "message": "このスライドで最も言いたい1文（20-40字）",
      "body": "説明文（80-180字）",
      "bullets": ["...", "...", "..."],
      "image_prompt": "English prompt for Imagen",
      "layout": "TITLE | TITLE_LEFT_IMAGE_RIGHT | IMAGE_FULL_TEXT_BOTTOM"
    }
  ]
}
"""

import json
import os

from config import get_setting


# ── Public API ──────────────────────────────────────────────────────

def generate_deck_json(extracted_text: str, api_key=None, project_id=None,
                       location=None, model_name=None) -> dict:
    """
    Phase B entry point.

    Takes raw extracted text and returns a deck_json dict conforming to the
    slide structure schema.  Markdown is NOT used as an intermediate
    representation.
    """
    project_id = project_id or get_setting("GCP_PROJECT_ID")
    location = location or get_setting("GCP_LOCATION", "us-central1")
    model_name = model_name or get_setting("TEXT_MODEL_NAME", "gemini-1.5-flash-002")
    api_key = api_key or get_setting("GOOGLE_API_KEY")

    use_vertex = bool(
        project_id and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )

    prompt = _build_deck_prompt(extracted_text)

    # ── Vertex AI path ──
    if use_vertex:
        print(f"[GEN][JSON] Using Vertex AI (project={project_id}, "
              f"location={location}, model={model_name})")
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=project_id, location=location)
            model = GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            deck = json.loads(response.text)
            deck = _validate_and_fix(deck, extracted_text)
            print(f"[GEN][JSON] slides={len(deck.get('slides', []))}")
            return deck
        except Exception as e:
            print(f"[GEN][JSON][ERROR] Vertex AI failed: {e}")
            if not api_key:
                print("[GEN][JSON] No API key fallback, using local fallback")
                return _create_fallback_deck(extracted_text)

    # ── API-key path ──
    if api_key:
        print(f"[GEN][JSON] Using API key mode (model={model_name})")
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            deck = json.loads(response.text)
            deck = _validate_and_fix(deck, extracted_text)
            print(f"[GEN][JSON] slides={len(deck.get('slides', []))}")
            return deck
        except Exception as e:
            print(f"[GEN][JSON][ERROR] API-key Gemini failed: {e}")
            return _create_fallback_deck(extracted_text)

    print("[GEN][JSON][ERROR] No authentication configured")
    return _create_fallback_deck(extracted_text)


# ── Prompt builder ──────────────────────────────────────────────────

def _build_deck_prompt(extracted_text: str) -> str:
    return f"""あなたは一流の経営コンサルタント兼プレゼン資料デザイナーです。
以下の入力テキスト（箇条書き・PDF抜粋・メモ等）をもとに、
**提案資料として十分に成立する** PowerPoint スライド構成を JSON で生成してください。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
入力テキスト:
{extracted_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 生成ルール（厳守）

### 1. 出力形式
- 出力は **JSON のみ**（Markdown記法・コードフェンス禁止）。
- 下記スキーマに完全準拠すること。

### 2. スライド本文 (`body`) の書き方
- 入力の箇条書きをそのままコピーしない。
- 各スライドの `body` は **80〜180字** の説明文を書く。
- 提案資料として自然な流れで書くこと:
  - 背景（現場の状況・業界動向）
  - 課題の影響（コスト増・ミス・属人化・引き継ぎ困難・品質低下など）
  - 施策の狙い（標準化・効率化・可視化・品質向上など）
- **税務業務らしい具体例**を最低1つ入れる
  （例: 転記、証憑確認、申告前チェック、進捗管理、顧客からの資料回収、
   勘定科目マッピング、消費税区分判定、電子帳簿保存法対応 など）

### 3. `message` フィールド
- そのスライドで最も伝えたい**1文**を 20〜40字 で書く。

### 4. `bullets` フィールド
- 3〜5個の箇条書き。入力のコピペではなく補完・具体化すること。

### 5. スライド構成
- 最低4枚（タイトル / 課題 / 解決策 / 期待効果）。
- 入力が薄くても「期待効果」スライド（工数削減・品質向上・属人化解消など）を**必ず自動追加**する。
- 各スライドの `layout` は内容に応じて以下から選ぶ:
  - `"TITLE"` — 表紙。タイトル＋サブタイトルのみ。
  - `"TITLE_LEFT_IMAGE_RIGHT"` — 左にテキスト、右に画像。汎用レイアウト。
  - `"IMAGE_FULL_TEXT_BOTTOM"` — 全面画像＋下部テキスト帯。インパクト重視。

### 6. `image_prompt` の書き方
- **必ず英語**で書く。
- ビジネス向け・不適切表現なし。
- 被写体・状況・スタイル・禁止事項まで具体化する。
- 例: "A clean flat illustration of a modern office with accountants reviewing digital tax documents on large screens, minimal style, white background, no text, no watermark, business professional"

### 7. テーマ
- `primary_color` / `secondary_color` はビジネスに適した色（例: 紺/青系 + アクセント色）。

## 出力 JSON スキーマ

{{
  "deck_title": "プレゼンテーション全体のタイトル",
  "theme": {{
    "primary_color": "#2B579A",
    "secondary_color": "#4472C4",
    "font": "Arial"
  }},
  "slides": [
    {{
      "title": "スライドタイトル",
      "message": "このスライドで最も言いたい1文（20〜40字）",
      "body": "説明文。80〜180字で、背景→課題→狙いの流れで書く。",
      "bullets": ["具体化された箇条書き1", "具体化された箇条書き2", "具体化された箇条書き3"],
      "image_prompt": "English image prompt, detailed, flat illustration, business, no text, no watermark",
      "layout": "TITLE_LEFT_IMAGE_RIGHT"
    }}
  ]
}}

上記ルールを**すべて**満たす JSON を出力してください。"""


# ── Validation & fixup ──────────────────────────────────────────────

_REQUIRED_SLIDE_KEYS = {"title", "message", "body", "bullets", "image_prompt", "layout"}
_VALID_LAYOUTS = {"TITLE", "TITLE_LEFT_IMAGE_RIGHT", "IMAGE_FULL_TEXT_BOTTOM"}


def _validate_and_fix(deck: dict, source_text: str) -> dict:
    """Ensure deck_json conforms to the schema, fixing minor issues."""

    if "deck_title" not in deck:
        deck["deck_title"] = "Presentation"

    if "theme" not in deck:
        deck["theme"] = {
            "primary_color": "#2B579A",
            "secondary_color": "#4472C4",
            "font": "Arial",
        }

    if "slides" not in deck or not deck["slides"]:
        return _create_fallback_deck(source_text)

    for slide in deck["slides"]:
        # Fill missing keys
        slide.setdefault("title", "")
        slide.setdefault("message", "")
        slide.setdefault("body", "")
        slide.setdefault("bullets", [])
        slide.setdefault("image_prompt",
                         "A clean flat illustration of a modern business office, "
                         "minimal style, white background, no text, no watermark")
        if slide.get("layout") not in _VALID_LAYOUTS:
            slide["layout"] = "TITLE_LEFT_IMAGE_RIGHT"

    # Ensure at least one "期待効果" style slide exists
    has_effect_slide = any(
        "効果" in s.get("title", "") or "effect" in s.get("title", "").lower()
        for s in deck["slides"]
    )
    if not has_effect_slide:
        deck["slides"].append(_make_effect_slide())

    return deck


def _make_effect_slide() -> dict:
    return {
        "title": "期待効果",
        "message": "DX推進により業務品質と効率を同時に高める",
        "body": (
            "本施策の導入により、税務申告前チェックの自動化で転記ミスを大幅に削減し、"
            "進捗管理のデジタル化によって属人的な業務フローを標準化します。"
            "結果として顧客対応スピードが向上し、繁忙期の残業削減にも寄与します。"
        ),
        "bullets": [
            "申告前チェック自動化によるミス削減",
            "進捗管理のリアルタイム可視化",
            "属人化解消と業務標準化の実現",
            "繁忙期の工数20〜30%削減を目標",
        ],
        "image_prompt": (
            "A clean flat illustration showing a rising bar chart and efficiency "
            "icons such as a clock, checkmark, and gears, representing business "
            "productivity improvement, minimal style, white background, "
            "no text, no watermark, professional business illustration"
        ),
        "layout": "TITLE_LEFT_IMAGE_RIGHT",
    }


# ── Fallback (no AI) ───────────────────────────────────────────────

def _create_fallback_deck(source_text: str) -> dict:
    """Create a minimal deck_json when AI generation fails entirely."""
    print("[GEN][JSON] Creating fallback deck (no AI)")
    return {
        "deck_title": "提案資料",
        "theme": {
            "primary_color": "#2B579A",
            "secondary_color": "#4472C4",
            "font": "Arial",
        },
        "slides": [
            {
                "title": "提案資料",
                "message": "業務改善に向けた提案をご紹介します",
                "body": "",
                "bullets": [],
                "image_prompt": (
                    "A clean flat illustration of a professional business "
                    "presentation setting, minimal, white background, no text"
                ),
                "layout": "TITLE",
            },
            {
                "title": "現状の課題",
                "message": "手作業中心の業務フローが品質リスクを高めている",
                "body": (
                    "現在の税務業務では、仕訳の転記や証憑確認などの多くの工程が手作業で行われており、"
                    "担当者ごとにやり方が異なる属人的なフローが定着しています。"
                    "この結果、繁忙期にはミスが増加し、引き継ぎも困難な状況が続いています。"
                ),
                "bullets": [
                    "手作業による転記・照合が多い",
                    "業務フローが担当者に依存",
                    "ミスの検出が事後的になりがち",
                ],
                "image_prompt": (
                    "A flat illustration of an overwhelmed office worker surrounded "
                    "by stacks of paper documents and spreadsheets, minimal style, "
                    "white background, no text, no watermark"
                ),
                "layout": "TITLE_LEFT_IMAGE_RIGHT",
            },
            {
                "title": "解決策",
                "message": "AI・自動化・クラウドの三本柱で業務を変革する",
                "body": (
                    "AI-OCRによる証憑の自動読取や、クラウド会計ソフトとの連携による仕訳自動化を導入し、"
                    "申告前チェックをルールベース＋AIで二重に実施します。"
                    "これにより転記ミスを未然に防ぎ、業務の標準化と効率化を同時に実現します。"
                ),
                "bullets": [
                    "AI-OCRで証憑を自動読取・データ化",
                    "クラウド連携による仕訳の自動生成",
                    "ルールベース＋AIの申告前ダブルチェック",
                ],
                "image_prompt": (
                    "A flat illustration of a digital transformation concept with "
                    "cloud computing icons, AI brain symbol, and automated workflow "
                    "arrows, minimal style, white background, no text, no watermark"
                ),
                "layout": "TITLE_LEFT_IMAGE_RIGHT",
            },
            _make_effect_slide(),
        ],
    }


# ── Legacy compatibility (kept as alias, not the default path) ─────

def generate_slide_plan(parsed_data, api_key=None, project_id=None,
                        location=None, model_name=None):
    """
    Legacy wrapper: converts old parsed_data format to extracted text,
    then delegates to generate_deck_json.
    """
    # Reconstruct text from old format
    title = parsed_data.get("title", "")
    parts = [title]
    for slide in parsed_data.get("slides", []):
        parts.append(slide.get("title", ""))
        for b in slide.get("bullets", []):
            parts.append(f"- {b}")
    text = "\n".join(parts)
    return generate_deck_json(text, api_key=api_key, project_id=project_id,
                              location=location, model_name=model_name)

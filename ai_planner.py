import json
import os
import streamlit as st
from openai import OpenAI

def _get_api_key(api_key=None):
    """
    Retrieves OpenAI API Key from args, secrets, or env.
    """
    if api_key:
        return api_key
    
    # Try Streamlit Secrets
    try:
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    
    # Try Environment Variable
    return os.getenv("OPENAI_API_KEY")

def generate_slide_plan(parsed_data, api_key=None, model="gpt-4o"):
    """
    Generates a JSON plan for the presentation using OpenAI API.
    """
    final_api_key = _get_api_key(api_key)
    
    if not final_api_key:
        raise ValueError("OPENAI_API_KEY is not set. Please set it in Streamlit Secrets or environment variables.")

    client = OpenAI(api_key=final_api_key)

    system_prompt = """You are an expert presentation designer creating slides for a **VIDEO presentation**.
Since there is no live speaker, **all key explanations must be visible ON THE SLIDE**.

## ⚠️ Video Presentation Rules
1. **One-Claim per Slide**: Each slide must have exactly ONE main message. Split slides if necessary.
2. **Self-Explanatory**: The slide body must contain sentences (not just bullets) that explain the "Why" and "How".
3. **Concrete & Specific**: Avoid abstract jargon. Instead of "Optimization", say "Reduces processing time by 50%".
4. **Structure**: Create 6-8 slides following this flow: Conclusion -> Problem -> Cause -> Solution -> Effect -> Steps -> Next Action.

## Slide Structure (JSON Fields)
For each slide, generate:
- **title**: Short headline (Max 20 chars, Japanese). 1 line.
- **takeaway**: A single concluding sentence (15-30 chars).
    - Format: "結論：〜により、〜を実現します。"
- **bullets**: Key points (Max 3 items, <40 chars each). 1 line per item.
- **body**: **CRITICAL**. Explanatory text displayed on the slide.
    - 90-140 characters (Japanese).
    - 2-3 sentences.
    - MUST include "What/How", "Specific Example", and "Effect".
    - Do NOT copy the input Markdown. Rewrite it to be conversational yet professional.
    - Long text is PROHIBITED.
- **image**:
    - Prompt for a flat vector illustration (No text).
    - Aspect ratio "1:1" (Square) or "4:3".

## Output Format (JSON Only)
{
  "theme": { "style": "flat", "font": "Meiryo" },
  "slides": [
    {
      "title": "入力業務の工数増大",
      "takeaway": "結論：自動化により月20時間の創出を実現します。",
      "bullets": [
        "転記作業に毎日1時間を費やしている",
        "入力ミスが週平均3件発生"
      ],
      "body": "現在は紙の届出書を手動でシステムに入力しており、月間で約20時間の工数ロスが発生しています。例えば、申請書1枚の転記に5分かかり、ダブルチェックも含めると負担は甚大です。この単純作業を自動化することで、本来の分析業務に時間を割けるようになります。",
      "image": {
        "type": "illustration",
        "prompt": "Flat vector illustration of a tired office worker with piles of paper, minimal, white background, no text",
        "aspect_ratio": "1:1"
      }
    }
  ]
}
"""

    user_content = json.dumps(parsed_data, ensure_ascii=False)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        print(f"AI Planning failed: {e}")
        return _create_fallback_plan(parsed_data)

def _create_fallback_plan(parsed_data):
    """Creates a basic plan without AI intelligence if API fails."""
    slides = []
    for s in parsed_data.get('slides', []):
        slides.append({
            "title": s['title'],
            "bullets": s.get('bullets', []),
            "body": "（APIエラーのため自動生成できませんでした。詳細を追加してください。）",
            "takeaway": "結論：詳細を確認してください。",
            "image": {
                "type": "placeholder",
                "prompt": "Placeholder image",
                "aspect_ratio": "1:1"
            }
        })
    
    return {
        "theme": {"style": "simple"},
        "slides": slides
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

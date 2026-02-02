"""
Streamlit UI — AI PowerPoint Generator (deck_json pipeline)

Pipeline:
  Phase A: Input (PDF / text) → extracted text
  Phase B: Extracted text → deck_json (via Gemini)
  Phase C: deck_json → slide images (via Imagen + retry + fallback)
  Phase D: deck_json + images → PPTX
"""

import streamlit as st
import os
import shutil

from markdown_parser import parse_markdown
from ai_planner import generate_slide_plan
from image_generator import generate_images, STYLE_PROMPTS
from slide_builder import generate_pptx

# Optional: load .env locally (app.py might run before other modules)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _get_secret(key, default=None):
    """st.secrets を優先し、なければ os.getenv にフォールバック。"""
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.getenv(key, default)

# --- Config ---
ASSETS_DIR = "assets"
OUTPUT_FILENAME = "presentation.pptx"


def main():
    st.set_page_config(page_title="AI Slide Generator", layout="wide")
    
    st.title("✨ AI PowerPoint Generator (OpenAI Edition)")
    
    # Check API Key
    openai_api_key = _get_secret("OPENAI_API_KEY")
    
    st.markdown("Markdown → AI Plan (GPT-4o) → AI Images ({Style} + DALL·E 3) → PPTX")

    # --- Sidebar ---
    with st.sidebar:
        st.header("Settings")
        
        if openai_api_key:
            st.success("OpenAI Key Loaded")
        else:
            st.error("OPENAI_API_KEY not found. Please set it in .env or Secrets.")

        # Config
        image_model = _get_secret("IMAGE_MODEL_NAME", "dall-e-3")
        st.text_input("Image Model", value=image_model, disabled=True)
        
        # Image Style Selection
        style_options = list(STYLE_PROMPTS.keys())
        selected_style = st.selectbox("Image Style", style_options, index=0)
        
        st.info(f"Style: {selected_style}\n(OpenAI API for Planning & Images)")

    # Input Area
    default_text = """# 税務DX提案

## 現状の課題
- 手作業が多い
- 属人化している
- ミスが起きやすい

## 解決策
- AI活用
- 自動化
- クラウド連携
"""
    user_input = st.text_area("Markdown Input", value=default_text, height=300)

    if st.button("🚀 Generate Presentation", type="primary"):
        if not user_input.strip():
            st.error("Markdownを入力してください。")
            return

        if not openai_api_key:
            st.error("OPENAI_API_KEY is missing. Cannot proceed.")
            return

        # --- Pipeline ---
        status = st.status("Generating Presentation...", expanded=True)

        try:
            # 1. Parse
            status.write("📝 Parsing Markdown...")
            parsed_data = parse_markdown(user_input)
            st.json(parsed_data, expanded=False)
            
            # 2. Plan (AI - OpenAI)
            status.write("🧠 AI Planning (GPT-4o) - One-Claim Policy...")
            plan = generate_slide_plan(parsed_data, api_key=openai_api_key)
            st.write("--- Design Plan ---")
            st.json(plan, expanded=False)
            
            # 3. Images (AI - DALL-E 3)
            status.write(f"🎨 Generating Images ({selected_style} - {image_model})...")
            # Cleanup old assets
            if os.path.exists(ASSETS_DIR):
                shutil.rmtree(ASSETS_DIR)

            image_results = generate_slide_images(
                deck_json,
                output_dir=ASSETS_DIR,
                api_key=openai_api_key,
                model_name=image_model,
                image_style=selected_style,
            )
            
            # Show previews
            if image_paths:
                cols = st.columns(4)
                for i, path in image_paths.items():
                    with cols[i % 4]:
                        st.image(path, caption=f"Slide {i+1}", use_container_width=True)
            else:
                st.warning("No images generated (failed or skipped). Proceeding with text only.")
            
            # 4. Build PPTX
            status.write("🔨 Building PowerPoint...")
            output_path = generate_pptx(plan, image_paths, OUTPUT_FILENAME, title=parsed_data['title'])
            
            status.update(label="✅ Complete!", state="complete", expanded=False)
            
            # 5. Download
            with open(output_path, "rb") as f:
                st.download_button(
                    label="Download .pptx",
                    data=f,
                    file_name="ai_presentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )

        except Exception as e:
            status.update(label="Error", state="error")
            st.error(f"An error occurred: {e}")
            st.exception(e)


if __name__ == "__main__":
    main()

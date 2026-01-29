import streamlit as st
import io
import os
import json
import shutil
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

from markdown_parser import parse_markdown
from ai_planner import generate_slide_plan
from image_generator import generate_images
from slide_builder import generate_pptx

# --- Config ---
ASSETS_DIR = "assets"
OUTPUT_FILENAME = "presentation.pptx"

def main():
    st.set_page_config(page_title="AI Slide Generator", layout="wide")
    
    st.title("✨ AI PowerPoint Generator (Google Nano Banana Edition)")
    
    # Check API Key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        st.error("⛔ `GOOGLE_API_KEY` が設定されていません。 `.env` ファイルを作成してください。")
        st.markdown("""
        **Set up .env file:**
        1. Create `.env` in the project root.
        2. Add: `GOOGLE_API_KEY=your_key_here`
        3. Restart the app.
        """)
        st.stop()

    st.markdown("Markdown → AI Plan → AI Images (Nano Banana) → PPTX")

    # Sidebar
    with st.sidebar:
        st.header("Settings")
        st.success("API Key Loaded from .env")
        
        # Optional Overrides (readonly mostly)
        st.text_input("Image Model", value=os.getenv("IMAGE_MODEL_NAME", "nano-banana"), disabled=True)
        st.text_input("Provider", value=os.getenv("IMAGE_PROVIDER", "google"), disabled=True)

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

        # --- Pipeline ---
        status = st.status("Generating Presentation...", expanded=True)
        
        try:
            # 1. Parse
            status.write("📝 Parsing Markdown...")
            parsed_data = parse_markdown(user_input)
            st.json(parsed_data, expanded=False)
            
            # 2. Plan (AI - Gemini)
            status.write("🧠 AI Planning (Gemini)...")
            # Using the same key for planning
            plan = generate_slide_plan(parsed_data, api_key=google_api_key)
            st.write("--- Design Plan ---")
            st.json(plan, expanded=False)
            
            # 3. Images (AI - Nano Banana / Google)
            status.write(f"🎨 Generating Images (Model: {os.getenv('IMAGE_MODEL_NAME', 'nano-banana')})...")
            # Cleanup old assets
            if os.path.exists(ASSETS_DIR):
                shutil.rmtree(ASSETS_DIR)
            
            # Key is handled via env inside generate_images (or we could pass it)
            # generate_images internally reads env if not passed, but we ensured env is loaded.
            image_paths = generate_images(plan, output_dir=ASSETS_DIR)
            
            # Show previews
            if image_paths:
                cols = st.columns(4)
                for i, path in image_paths.items():
                    with cols[i % 4]:
                        st.image(path, caption=f"Slide {i+1}", use_container_width=True)
            else:
                st.warning("No images generated (failed or skipped).")
            
            # 4. Build PPTX
            status.write("🔨 Building PowerPoint...")
            output_path = generate_pptx(plan, image_paths, OUTPUT_FILENAME, title=parsed_data['title'])
            
            status.update(label="✅ Complete!", state="complete", expanded=False)
            
            # 5. Download
            with open(output_path, "rb") as f:
                st.download_button(
                    label="📥 Download .pptx",
                    data=f,
                    file_name="ai_presentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )

        except Exception as e:
            status.update(label="❌ Error", state="error")
            st.error(f"An error occurred: {e}")
            st.exception(e)

if __name__ == "__main__":
    main()

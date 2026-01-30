import streamlit as st
import io
import os
import json
import shutil

from config import get_setting, bootstrap_gcp_auth, is_vertex_mode, auth_label
from markdown_parser import parse_markdown
from ai_planner import generate_slide_plan
from image_generator import generate_images
from slide_builder import generate_pptx

# --- Bootstrap GCP auth (must run before any Google client is created) ---
bootstrap_gcp_auth()

# --- Config ---
ASSETS_DIR = "assets"
OUTPUT_FILENAME = "presentation.pptx"


def main():
    st.set_page_config(page_title="AI Slide Generator", layout="wide")

    st.title("✨ AI PowerPoint Generator (Vertex AI Edition)")

    # --- Read settings via unified helper ---
    gcp_project = get_setting("GCP_PROJECT_ID")
    gcp_location = get_setting("GCP_LOCATION", "us-central1")
    text_model = get_setting("TEXT_MODEL_NAME", "gemini-1.5-flash-002")
    image_model = get_setting("IMAGE_MODEL_NAME", "imagen-3.0-generate-001")
    image_provider = get_setting("IMAGE_PROVIDER", "google")
    google_api_key = get_setting("GOOGLE_API_KEY")

    # Validate: need either Vertex SA or API key
    vertex = is_vertex_mode()
    if not vertex and not google_api_key:
        st.error(
            "⛔ 認証情報が見つかりません。\n\n"
            "Streamlit Cloud: Secrets に `GCP_SA_JSON` と `GCP_PROJECT_ID` を設定してください。\n\n"
            "ローカル: `.env` に `GOOGLE_API_KEY` を設定してください。"
        )
        st.stop()

    st.markdown("Markdown → AI Plan → AI Images → PPTX")

    # Sidebar
    with st.sidebar:
        st.header("Settings")
        st.info(f"Auth: {auth_label()}")
        if vertex:
            st.text_input("GCP Project", value=gcp_project or "", disabled=True)
            st.text_input("Location", value=gcp_location, disabled=True)
        st.text_input("Text Model", value=text_model, disabled=True)
        st.text_input("Image Model", value=image_model, disabled=True)
        st.text_input("Provider", value=image_provider, disabled=True)
        st.caption("Last updated: 2025-01-30")

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

            # 2. Plan (AI - Gemini via Vertex or API key)
            status.write(f"🧠 AI Planning ({text_model})...")
            plan = generate_slide_plan(
                parsed_data,
                api_key=google_api_key,
                project_id=gcp_project,
                location=gcp_location,
                model_name=text_model,
            )
            st.write("--- Design Plan ---")
            st.json(plan, expanded=False)

            # 3. Images (Imagen via Vertex or API key)
            status.write(f"🎨 Generating Images ({image_model})...")
            if os.path.exists(ASSETS_DIR):
                shutil.rmtree(ASSETS_DIR)

            image_paths = generate_images(
                plan,
                output_dir=ASSETS_DIR,
                api_key=google_api_key,
                provider=image_provider,
                model_name=image_model,
                project_id=gcp_project,
                location=gcp_location,
            )

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

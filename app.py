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

from config import get_setting, bootstrap_gcp_auth, is_vertex_mode, auth_label
from text_extractor import extract_text
from ai_planner import generate_deck_json
from image_generator import generate_slide_images
from slide_builder import build_pptx

# --- Bootstrap GCP auth (must run before any Google client is created) ---
bootstrap_gcp_auth()

# --- Config ---
ASSETS_DIR = "assets"
OUTPUT_FILENAME = "presentation.pptx"


def main():
    st.set_page_config(page_title="AI Slide Generator", layout="wide")

    st.title("AI PowerPoint Generator (Vertex AI Edition)")

    # --- Read settings ---
    gcp_project = get_setting("GCP_PROJECT_ID")
    gcp_location = get_setting("GCP_LOCATION", "us-central1")
    text_model = get_setting("TEXT_MODEL_NAME", "gemini-1.5-flash-002")
    image_model = get_setting("IMAGE_MODEL_NAME", "imagen-3.0-generate-001")
    image_provider = get_setting("IMAGE_PROVIDER", "google")
    google_api_key = get_setting("GOOGLE_API_KEY")

    # Validate auth
    vertex = is_vertex_mode()
    if not vertex and not google_api_key:
        st.error(
            "認証情報が見つかりません。\n\n"
            "Streamlit Cloud: Secrets に `GCP_SA_JSON` と `GCP_PROJECT_ID` を設定してください。\n\n"
            "ローカル: `GOOGLE_APPLICATION_CREDENTIALS`（サービスアカウント）または "
            "`GOOGLE_API_KEY` を設定してください。"
        )
        st.stop()

    st.markdown(
        "テキストまたはPDFを入力 → AI が提案資料として成立する "
        "PowerPoint を自動生成します（deck_json 方式）"
    )

    # --- Sidebar ---
    with st.sidebar:
        st.header("Settings")
        st.info(f"Auth: {auth_label()}")
        if vertex:
            st.text_input("GCP Project", value=gcp_project or "", disabled=True)
            st.text_input("Location", value=gcp_location, disabled=True)
        st.text_input("Text Model", value=text_model, disabled=True)
        st.text_input("Image Model", value=image_model, disabled=True)
        st.text_input("Provider", value=image_provider, disabled=True)
        st.caption("Last updated: 2026-01-30")

    # --- Input Area ---
    input_tab_text, input_tab_pdf = st.tabs(["Text Input", "PDF Upload"])

    with input_tab_text:
        default_text = (
            "税務DX提案\n\n"
            "現状の課題\n"
            "- 手作業が多い\n"
            "- 属人化している\n"
            "- ミスが起きやすい\n\n"
            "解決策\n"
            "- AI活用\n"
            "- 自動化\n"
            "- クラウド連携"
        )
        user_text = st.text_area(
            "テキスト入力（箇条書き・メモ等なんでもOK）",
            value=default_text, height=300,
        )

    with input_tab_pdf:
        uploaded_pdf = st.file_uploader(
            "PDFファイルをアップロード", type=["pdf"],
        )

    if st.button("Generate Presentation", type="primary"):
        # Determine input source
        source = None
        source_type = "text"
        if uploaded_pdf is not None:
            source = uploaded_pdf
            source_type = "pdf"
        elif user_text and user_text.strip():
            source = user_text
            source_type = "text"
        else:
            st.error("テキストを入力するか、PDFをアップロードしてください。")
            return

        # --- Pipeline ---
        status = st.status("Generating Presentation...", expanded=True)

        try:
            # ── Phase A: Extract text ──
            status.write("Phase A: テキスト抽出中...")
            extracted = extract_text(source, source_type)
            if not extracted.strip():
                st.error("入力からテキストを抽出できませんでした。")
                return
            st.text_area("Extracted Text", value=extracted, height=150, disabled=True)

            # ── Phase B: Generate deck_json via Gemini ──
            status.write(f"Phase B: スライド構成を生成中 ({text_model})...")
            deck_json = generate_deck_json(
                extracted,
                api_key=google_api_key,
                project_id=gcp_project,
                location=gcp_location,
                model_name=text_model,
            )
            n_slides = len(deck_json.get("slides", []))
            status.write(f"  deck_json: {n_slides} slides")
            st.json(deck_json, expanded=False)

            # ── Phase C: Generate images ──
            status.write(f"Phase C: スライド画像を生成中 ({image_model})...")
            if os.path.exists(ASSETS_DIR):
                shutil.rmtree(ASSETS_DIR)

            image_results = generate_slide_images(
                deck_json,
                output_dir=ASSETS_DIR,
                api_key=google_api_key,
                provider=image_provider,
                model_name=image_model,
                project_id=gcp_project,
                location=gcp_location,
            )

            # Show image previews
            if image_results:
                cols = st.columns(min(4, len(image_results)))
                for idx, info in image_results.items():
                    path = info.get("path", "") if isinstance(info, dict) else info
                    img_type = info.get("type", "?") if isinstance(info, dict) else "?"
                    col = cols[idx % len(cols)]
                    with col:
                        if os.path.exists(path):
                            st.image(path, caption=f"Slide {idx + 1} ({img_type})",
                                     use_container_width=True)
                        else:
                            st.warning(f"Slide {idx + 1}: image not found")

            # ── Phase D: Build PPTX ──
            status.write("Phase D: PowerPoint を生成中...")
            output_path = build_pptx(deck_json, image_results, OUTPUT_FILENAME)

            status.update(label="Complete!", state="complete", expanded=False)

            # Download
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

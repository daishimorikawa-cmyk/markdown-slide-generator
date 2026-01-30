import json
import os

from config import get_setting, is_vertex_mode


def generate_slide_plan(parsed_data, api_key=None, project_id=None,
                        location=None, model_name=None):
    """
    Generates a JSON plan for the presentation using Gemini.

    Auth priority:
      1. Vertex AI (service account) – when GCP_PROJECT_ID +
         GOOGLE_APPLICATION_CREDENTIALS are present.
      2. Google Generative AI (API key) – legacy / local mode.
    """
    project_id = project_id or get_setting("GCP_PROJECT_ID")
    location = location or get_setting("GCP_LOCATION", "us-central1")
    model_name = model_name or get_setting("TEXT_MODEL_NAME", "gemini-1.5-flash-002")
    api_key = api_key or get_setting("GOOGLE_API_KEY")

    use_vertex = bool(
        project_id and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )

    prompt = _build_prompt(parsed_data)

    # ------------------------------------------------------------------
    # Vertex AI path
    # ------------------------------------------------------------------
    if use_vertex:
        print(f"[PLAN] Using Vertex AI (project={project_id}, location={location}, model={model_name})")
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=project_id, location=location)
            model = GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"[PLAN][ERROR] Vertex AI failed: {e}")
            # Fall through to API-key path if available, else fallback
            if not api_key:
                print("[PLAN] No API key fallback available, using fallback plan")
                return _create_fallback_plan(parsed_data)

    # ------------------------------------------------------------------
    # API-key path (local / legacy)
    # ------------------------------------------------------------------
    if api_key:
        print(f"[PLAN] Using API key mode (model={model_name})")
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"[PLAN][ERROR] API-key Gemini failed: {e}")
            return _create_fallback_plan(parsed_data)

    # No auth at all
    print("[PLAN][ERROR] No authentication configured")
    return _create_fallback_plan(parsed_data)


# ------------------------------------------------------------------
# Prompt builder
# ------------------------------------------------------------------

def _build_prompt(parsed_data):
    return f"""
    You are an expert presentation designer.
    Create a detailed design plan for a PowerPoint presentation based on the following content.

    Input Content:
    {json.dumps(parsed_data, ensure_ascii=False)}

    Requirements:
    1. Output MUST be a valid JSON object.
    2. Theme: Choose a professional "flat illustration" style.
    3. Colors: Pick a primary and secondary color suitable for business.
    4. For EACH slide:
       - 'layout': Choose one of ["title_only", "title_bullets", "title_bullets_image_right", "hero_image"].
       - 'image': Define an image prompt.
         - 'type': "illustration"
         - 'prompt': A detailed ENGLISH prompt for an AI image generator describing a flat illustration style image.
         - 'aspect_ratio': "16:9" or "1:1" (use 1:1 for side images, 16:9 for hero).
    5. 'bullets': Keep the original bullets. If a slide has too many bullets (more than 5), you don't need to split them here; the builder will handle it, but you should ensure the layout fits.
    6. Simplify the prompt to avoid text in images.

    Output Format (JSON Only):
    {{
      "theme": {{
        "style": "flat illustration",
        "primary_color": "#Hex",
        "secondary_color": "#Hex",
        "font": "Arial"
      }},
      "slides": [
        {{
          "title": "Slide Title",
          "bullets": ["Point 1", "Point 2"],
          "layout": "title_bullets_image_right",
          "image": {{
            "type": "illustration",
            "prompt": "flat illustration of ..., minimal, white background",
            "aspect_ratio": "1:1"
          }}
        }}
      ]
    }}
    """


# ------------------------------------------------------------------
# Fallback plan (no AI)
# ------------------------------------------------------------------

def _create_fallback_plan(parsed_data):
    """Creates a basic plan without AI intelligence if API fails."""
    slides = []
    for s in parsed_data['slides']:
        slides.append({
            "title": s['title'],
            "bullets": s['bullets'],
            "layout": "title_bullets_image_right",
            "image": {
                "type": "placeholder",
                "prompt": "Placeholder image",
                "aspect_ratio": "16:9"
            }
        })

    return {
        "theme": {
            "style": "simple",
            "primary_color": "#000000",
            "secondary_color": "#ffffff",
            "font": "Arial"
        },
        "slides": slides
    }

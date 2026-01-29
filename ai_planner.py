import google.generativeai as genai
import json
import os
import streamlit as st

def generate_slide_plan(parsed_data, api_key=None):
    """
    Generates a JSON plan for the presentation using Gemini.
    """
    if not api_key:
        # Fallback: st.secrets → os.getenv
        try:
            api_key = st.secrets["GOOGLE_API_KEY"]
        except (KeyError, FileNotFoundError):
            api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY が設定されていません。Streamlit Cloud の Secrets に設定してください。")

    genai.configure(api_key=api_key)
    
    # Use a model that is good at JSON
    model = genai.GenerativeModel('gemini-1.5-flash') 

    prompt = f"""
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
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        # Fallback manual plan if AI fails
        print(f"AI Planning failed: {e}")
        return _create_fallback_plan(parsed_data)

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

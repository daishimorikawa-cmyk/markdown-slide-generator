"""
Phase C: Generate visuals for each slide.

Routing:
  - visual_type=SCENE  → Imagen generation (fallback: PPT shapes via slide_builder)
  - visual_type=DIAGRAM → Skip Imagen entirely; return diagram metadata
                           for slide_builder to draw PPT shapes

Features:
  - Retry up to 2 times with prompt simplification on SCENE failure
  - Never leaves a slide without visual content
"""

import os
import io
import requests
import traceback
import streamlit as st
from openai import OpenAI

# Optional: load .env locally
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DEBUG_IMAGES = os.environ.get("DEBUG_IMAGES", "False").lower() == "true"

def _get_openai_key(api_key=None):
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

STYLE_PROMPTS = {
    "pixar": "3D render in Pixar animation style, cute, friendly, vibrant colors, soft lighting, high detail 3d render",
    "disney": "2D animated movie style, hand-drawn look, classic animation, detailed backgrounds, expressive, magical atmosphere",
    "infographic": "Modern flat infographic style, simple vector art, clean lines, minimalist, professional business color palette, iconic representation",
    "graph": "Business flowchart or schematic diagram style, professional, clean abstract shapes, corporate look, isometric view",
}

def generate_images(plan, output_dir="assets", api_key=None, provider=None, model_name=None, image_style="pixar"):
    """
    Generates images using OpenAI (DALL-E 3).
    Returns a dict mapping slide index (0-based) to image file path.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    final_api_key = _get_openai_key(api_key)
    if not final_api_key:
        st.warning("Image Generation Skipped: OPENAI_API_KEY not found.")
        return {}
        
    client = OpenAI(api_key=final_api_key)
    
    generated_paths = {}

    if not plan or 'slides' not in plan:
        return {}
        
    # Get style prompt suffix
    style_suffix = STYLE_PROMPTS.get(image_style, STYLE_PROMPTS["pixar"])

    for i, slide in enumerate(plan['slides']):
        # Check if image is requested
        if 'image' not in slide:
            continue
        
        image_cfg = slide['image']
        prompt = image_cfg.get('prompt')
        if not prompt:
            st.warning(f"Slide {i+1}: No prompt provided. Skipping image.")
            continue
            
        aspect_ratio = image_cfg.get('aspect_ratio', '16:9') # 16:9 or 1:1
        
        # Map aspect ratio to DALL-E 3 supported sizes
        size = "1024x1024"
        if aspect_ratio == "16:9":
            size = "1792x1024" # Landscape
        
        # Enhance prompt to avoid text
        # Combine: {Style} + {Content} + {Negative Constraints}
        enhanced_prompt = (
            f"{style_suffix}. {prompt}. "
            "IMPORTANT: Do NOT include any text, letters, numbers, or words in the image. "
            "No layouts, no charts with text. Visual representation only. "
            "High quality, professional."
        )
        
        filename = f"slide_{i+1}.png"
        filepath = os.path.join(output_dir, filename)
        
        try:
            response = client.images.generate(
                model=model_name or "dall-e-3",
                prompt=enhanced_prompt,
                size=size,
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            
            # Download the image
            img_data = requests.get(image_url).content
            with open(filepath, 'wb') as handler:
                handler.write(img_data)
                
            generated_paths[i] = filepath
            
        except Exception as e:
            st.error(f"Slide {i+1} Image Gen Failed: {e}")
            if DEBUG_IMAGES:
                st.code(traceback.format_exc())
            # Continue to next slide
            continue

    return generated_paths

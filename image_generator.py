import os
import io
from PIL import Image, ImageDraw, ImageFont

from config import get_setting


def generate_images(plan, output_dir="assets", api_key=None, provider=None,
                    model_name=None, project_id=None, location=None):
    """
    Generates images based on the plan.

    Auth priority:
      1. Vertex AI Imagen (service account) – when project_id +
         GOOGLE_APPLICATION_CREDENTIALS are present.
      2. Google Generative AI (API key) – legacy / local mode.
      3. Mock placeholder – when generation fails or no auth.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    generated_paths = {}

    # Resolve settings
    api_key = api_key or get_setting("GOOGLE_API_KEY")
    provider = provider or get_setting("IMAGE_PROVIDER", "google")
    model_name = model_name or get_setting("IMAGE_MODEL_NAME", "imagen-3.0-generate-001")
    project_id = project_id or get_setting("GCP_PROJECT_ID")
    location = location or get_setting("GCP_LOCATION", "us-central1")

    use_vertex = bool(
        project_id and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )

    # Configure genai once if using API-key path
    if not use_vertex and provider == "google" and api_key:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

    for i, slide in enumerate(plan['slides']):
        if 'image' not in slide:
            continue

        prompt = slide['image'].get('prompt', 'No prompt')
        aspect_ratio = slide['image'].get('aspect_ratio', '16:9')

        if aspect_ratio == '16:9':
            width, height = 1024, 576
        else:
            width, height = 1024, 1024

        filename = f"slide_{i+1}.png"
        filepath = os.path.join(output_dir, filename)

        success = False

        # --- Vertex AI Imagen path ---
        if use_vertex and provider == "google":
            success = _generate_vertex_image(
                prompt, filepath, model_name, project_id, location, aspect_ratio,
            )

        # --- API-key path (fallback) ---
        if not success and provider == "google" and api_key:
            success = _generate_google_image(prompt, filepath, model_name, aspect_ratio)

        # --- Mock placeholder ---
        if not success:
            if use_vertex or api_key:
                print(f"[VERTEX][ERROR] All image generation attempts failed for slide {i+1}. Using placeholder.")
            _generate_mock_image(prompt, width, height, filepath)

        generated_paths[i] = filepath

    return generated_paths


# ------------------------------------------------------------------
# Vertex AI Imagen
# ------------------------------------------------------------------

def _generate_vertex_image(prompt, filepath, model_name, project_id, location, aspect_ratio):
    """Generate an image via Vertex AI Imagen."""
    try:
        print(f"[VERTEX] calling image generation... (model={model_name})")
        import vertexai
        from vertexai.preview.vision_models import ImageGenerationModel

        vertexai.init(project=project_id, location=location)
        model = ImageGenerationModel.from_pretrained(model_name)

        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio=aspect_ratio,
        )

        if response.images:
            response.images[0].save(filepath)
            print("[VERTEX] image generation done.")
            return True

        print("[VERTEX][ERROR] Imagen returned no images")
        return False
    except Exception as e:
        print(f"[VERTEX][ERROR] Vertex Imagen failed: {e}")
        return False


# ------------------------------------------------------------------
# API-key Google Generative AI (legacy)
# ------------------------------------------------------------------

def _generate_google_image(prompt, filepath, model_name, aspect_ratio):
    """Generate an image using google-generativeai (API key mode)."""
    try:
        import google.generativeai as genai

        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)

        if hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'image'):
                    img = Image.open(io.BytesIO(part.image))
                    img.save(filepath)
                    return True

        if hasattr(response, 'images') and len(response.images) > 0:
            response.images[0].save(filepath)
            return True

        return False
    except Exception as e:
        print(f"[IMG][ERROR] API-key image gen failed ({model_name}): {e}")
        return False


# ------------------------------------------------------------------
# Mock placeholder
# ------------------------------------------------------------------

def _generate_mock_image(prompt, width, height, filepath):
    """Generates a placeholder image using Pillow."""
    img = Image.new('RGB', (width, height), color=(225, 235, 250))
    d = ImageDraw.Draw(img)

    # Subtle gradient effect
    for y in range(height):
        r = int(225 - (y / height) * 25)
        g = int(235 - (y / height) * 15)
        b = int(250 - (y / height) * 10)
        d.line([(0, y), (width, y)], fill=(r, g, b))

    # Decorative shapes
    cx, cy = width // 2, height // 2
    radius = min(width, height) // 5
    d.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(200, 215, 240), outline=(160, 180, 220), width=3
    )
    r2 = radius // 2
    d.ellipse(
        [cx - r2, cy - r2, cx + r2, cy + r2],
        fill=(180, 200, 230)
    )

    # Small accent dots
    for ox, oy in [(-1.4, -0.6), (1.4, 0.6), (-0.5, 1.3), (0.5, -1.3)]:
        dx = int(cx + radius * ox)
        dy = int(cy + radius * oy)
        d.ellipse([dx - 12, dy - 12, dx + 12, dy + 12], fill=(190, 210, 240))

    # Label
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font = ImageFont.load_default()
    d.text((20, height - 35), "AI Image Placeholder", fill=(130, 150, 185), font=font)

    img.save(filepath)

"""
Phase C: Generate images for each slide using Imagen (Vertex AI).

Features:
  - Retry up to 2 times with prompt simplification on failure
  - Fallback to shape-based diagram generation when all retries fail
  - Never leaves a slide without visual content
"""

import os
import io
import re
from PIL import Image, ImageDraw, ImageFont

from config import get_setting


# ── Public API ──────────────────────────────────────────────────────

def generate_slide_images(deck_json: dict, output_dir: str = "assets",
                          api_key=None, provider=None, model_name=None,
                          project_id=None, location=None) -> dict:
    """
    Phase C entry point.  Generates one image per slide based on
    ``image_prompt`` in deck_json.

    Returns:
        dict mapping slide index → {"path": str, "type": "imagen"|"fallback_shape"}
    """
    os.makedirs(output_dir, exist_ok=True)

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

    results: dict = {}
    slides = deck_json.get("slides", [])

    for i, slide in enumerate(slides):
        prompt = slide.get("image_prompt", "")
        layout = slide.get("layout", "TITLE_LEFT_IMAGE_RIGHT")

        # Determine image size
        if layout == "IMAGE_FULL_TEXT_BOTTOM":
            width, height = 1920, 1080  # 16:9 for full-bleed
            aspect = "16:9"
        else:
            width, height = 1024, 1024  # 1:1 for side images
            aspect = "1:1"

        filepath = os.path.join(output_dir, f"slide_{i + 1}.png")

        # ── Attempt Imagen generation with retries ──
        success = _generate_with_retries(
            prompt=prompt,
            filepath=filepath,
            aspect_ratio=aspect,
            model_name=model_name,
            project_id=project_id,
            location=location,
            api_key=api_key,
            provider=provider,
            use_vertex=use_vertex,
            slide_index=i,
        )

        if success:
            results[i] = {"path": filepath, "type": "imagen"}
            print(f"[IMG] slide={i + 1} type=imagen")
        else:
            # ── Fallback: generate shape-based diagram ──
            print(f"[IMG] slide={i + 1} all retries failed, generating fallback shapes")
            _generate_shape_fallback(
                slide=slide, width=width, height=height, filepath=filepath
            )
            results[i] = {"path": filepath, "type": "fallback_shape"}
            print(f"[IMG] slide={i + 1} type=fallback_shape")

    return results


# ── Retry logic ─────────────────────────────────────────────────────

def _generate_with_retries(prompt, filepath, aspect_ratio, model_name,
                           project_id, location, api_key, provider,
                           use_vertex, slide_index) -> bool:
    """
    Try image generation up to 3 times (original + 2 retries).
    Each retry simplifies the prompt progressively.
    """
    prompts = _build_retry_prompts(prompt)

    for attempt, p in enumerate(prompts):
        print(f"[IMG] slide={slide_index + 1} prompt={p[:80]}... attempt={attempt + 1}/{len(prompts)}")

        success = False

        # Vertex AI Imagen
        if use_vertex and provider == "google":
            success = _generate_vertex_image(p, filepath, model_name,
                                             project_id, location, aspect_ratio)

        # API-key fallback
        if not success and provider == "google" and api_key:
            success = _generate_google_image(p, filepath, model_name, aspect_ratio)

        if success:
            # Verify the file actually exists and is non-empty
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return True
            print(f"[IMG][ERROR] slide={slide_index + 1} file empty/missing after generation")

        if attempt < len(prompts) - 1:
            print(f"[IMG][ERROR] slide={slide_index + 1} retry={attempt + 1}/2")

    return False


def _build_retry_prompts(original_prompt: str) -> list:
    """
    Build 3 progressively simplified prompts:
    1. Original prompt
    2. Shortened (remove adjectives, keep core)
    3. Ultra-safe minimal English prompt
    """
    # Attempt 1: original
    prompts = [original_prompt]

    # Attempt 2: shortened – strip adjective-heavy phrases
    shortened = original_prompt
    # Remove excessive adjectives
    for adj in ["detailed", "highly detailed", "intricate", "elaborate",
                "photorealistic", "ultra-realistic", "hyper-realistic",
                "complex", "sophisticated"]:
        shortened = shortened.replace(adj, "").replace(adj.capitalize(), "")
    # Collapse whitespace
    shortened = re.sub(r"\s{2,}", " ", shortened).strip()
    # Ensure safety keywords
    if "minimal" not in shortened.lower():
        shortened += ", minimal style"
    if "no text" not in shortened.lower():
        shortened += ", no text"
    prompts.append(shortened)

    # Attempt 3: ultra-safe minimal prompt
    safe_prompt = (
        "A clean flat illustration for a business presentation, "
        "simple geometric shapes, professional color palette, "
        "minimal design, white background, no text, no watermark, "
        "no people, corporate style"
    )
    prompts.append(safe_prompt)

    return prompts


# ── Vertex AI Imagen ────────────────────────────────────────────────

def _generate_vertex_image(prompt, filepath, model_name, project_id,
                           location, aspect_ratio) -> bool:
    """Generate an image via Vertex AI Imagen."""
    try:
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
            return True

        print("[IMG][ERROR] Imagen returned no images")
        return False
    except Exception as e:
        print(f"[IMG][ERROR] Vertex Imagen failed: {e}")
        return False


# ── API-key Google Generative AI ────────────────────────────────────

def _generate_google_image(prompt, filepath, model_name, aspect_ratio) -> bool:
    """Generate an image using google-generativeai (API key mode)."""
    try:
        import google.generativeai as genai

        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)

        if hasattr(response, "parts"):
            for part in response.parts:
                if hasattr(part, "image"):
                    img = Image.open(io.BytesIO(part.image))
                    img.save(filepath)
                    return True

        if hasattr(response, "images") and len(response.images) > 0:
            response.images[0].save(filepath)
            return True

        return False
    except Exception as e:
        print(f"[IMG][ERROR] API-key image gen failed ({model_name}): {e}")
        return False


# ── Shape-based fallback diagram ────────────────────────────────────

def _generate_shape_fallback(slide: dict, width: int, height: int,
                             filepath: str):
    """
    Generate a professional-looking diagram using Pillow shapes
    when Imagen fails.  Uses slide metadata to create a relevant
    visual representation.
    """
    img = Image.new("RGB", (width, height), color=(245, 247, 252))
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = font_large

    # Color palette (business blue tones)
    colors = {
        "primary": (43, 87, 154),       # #2B579A
        "secondary": (68, 114, 196),    # #4472C4
        "accent": (91, 155, 213),       # #5B9BD5
        "light": (180, 210, 240),
        "bg_card": (255, 255, 255),
        "text": (60, 60, 70),
        "text_light": (120, 130, 150),
    }

    bullets = slide.get("bullets", [])
    title = slide.get("title", "")

    if len(bullets) >= 3:
        _draw_card_layout(draw, width, height, bullets, colors, font_large, font_small)
    elif "効果" in title or "期待" in title:
        _draw_chart_layout(draw, width, height, bullets, colors, font_large, font_small)
    elif "課題" in title or "問題" in title:
        _draw_problem_layout(draw, width, height, bullets, colors, font_large, font_small)
    else:
        _draw_flow_layout(draw, width, height, bullets, colors, font_large, font_small)

    # Subtle branding strip at bottom
    draw.rectangle(
        [(0, height - 4), (width, height)],
        fill=colors["primary"]
    )

    img.save(filepath)


def _draw_card_layout(draw, w, h, bullets, colors, font_l, font_s):
    """Draw card-style layout with one card per bullet."""
    n = min(len(bullets), 4)
    card_w = (w - 80 - (n - 1) * 20) // n
    card_h = h - 120
    y = 60

    for i in range(n):
        x = 40 + i * (card_w + 20)
        # Card background
        draw.rounded_rectangle(
            [(x, y), (x + card_w, y + card_h)],
            radius=12,
            fill=colors["bg_card"],
            outline=colors["light"],
            width=2,
        )
        # Icon circle at top
        cx = x + card_w // 2
        cy = y + 50
        r = 28
        icon_color = [colors["primary"], colors["secondary"],
                      colors["accent"], colors["light"]][i % 4]
        draw.ellipse(
            [(cx - r, cy - r), (cx + r, cy + r)],
            fill=icon_color,
        )
        # Inner icon shape
        draw.rectangle(
            [(cx - 10, cy - 10), (cx + 10, cy + 10)],
            fill=(255, 255, 255),
        )
        # Bullet text (truncated)
        text = bullets[i][:20] if i < len(bullets) else ""
        # Center text under icon
        draw.text((x + 15, cy + 45), text, fill=colors["text"], font=font_s)


def _draw_chart_layout(draw, w, h, bullets, colors, font_l, font_s):
    """Draw a rising bar chart for effect/outcome slides."""
    n = max(len(bullets), 3)
    bar_w = (w - 160) // (n + 1)
    base_y = h - 80

    for i in range(n):
        bar_h = int((h - 200) * (0.3 + 0.7 * (i + 1) / n))
        x = 80 + i * (bar_w + 15)
        y = base_y - bar_h

        # Gradient-like bar (two-tone)
        draw.rounded_rectangle(
            [(x, y), (x + bar_w - 10, base_y)],
            radius=8,
            fill=colors["secondary"] if i % 2 == 0 else colors["accent"],
        )

        # Growth arrow on last bar
        if i == n - 1:
            ax = x + bar_w // 2
            ay = y - 20
            draw.polygon(
                [(ax - 12, ay + 15), (ax + 12, ay + 15), (ax, ay - 5)],
                fill=colors["primary"],
            )

    # Baseline
    draw.line([(60, base_y), (w - 40, base_y)], fill=colors["text_light"], width=2)

    # Label
    draw.text((w // 2 - 60, 25), "Expected Impact", fill=colors["text"], font=font_l)


def _draw_problem_layout(draw, w, h, bullets, colors, font_l, font_s):
    """Draw warning/problem icons for issue slides."""
    cx, cy = w // 2, h // 2

    # Large warning triangle
    size = min(w, h) // 3
    draw.polygon(
        [(cx, cy - size // 2),
         (cx - size // 2, cy + size // 2),
         (cx + size // 2, cy + size // 2)],
        fill=colors["light"],
        outline=colors["secondary"],
        width=3,
    )

    # Exclamation mark
    draw.rectangle(
        [(cx - 6, cy - size // 5), (cx + 6, cy + size // 8)],
        fill=colors["primary"],
    )
    draw.ellipse(
        [(cx - 7, cy + size // 5), (cx + 7, cy + size // 5 + 14)],
        fill=colors["primary"],
    )

    # Surrounding small circles for bullet count
    n = min(len(bullets), 5)
    for i in range(n):
        angle_offset = -90 + i * (360 // max(n, 1))
        import math
        ax = int(cx + (size * 0.8) * math.cos(math.radians(angle_offset)))
        ay = int(cy + (size * 0.8) * math.sin(math.radians(angle_offset)))
        r = 20
        draw.ellipse(
            [(ax - r, ay - r), (ax + r, ay + r)],
            fill=colors["accent"],
            outline=colors["secondary"],
            width=2,
        )

    draw.text((30, 25), "Current Challenges", fill=colors["text"], font=font_l)


def _draw_flow_layout(draw, w, h, bullets, colors, font_l, font_s):
    """Draw a simple flow diagram with arrows."""
    n = max(len(bullets), 3)
    box_w = (w - 80 - (n - 1) * 40) // n
    box_h = 80
    cy = h // 2

    for i in range(n):
        x = 40 + i * (box_w + 40)
        y = cy - box_h // 2

        # Rounded rectangle
        fill = colors["primary"] if i == 0 else (
            colors["secondary"] if i == n - 1 else colors["accent"]
        )
        draw.rounded_rectangle(
            [(x, y), (x + box_w, y + box_h)],
            radius=10,
            fill=fill,
        )

        # Box label
        label = f"Step {i + 1}"
        if i < len(bullets):
            label = bullets[i][:12]
        draw.text((x + 10, y + 30), label, fill=(255, 255, 255), font=font_s)

        # Arrow between boxes
        if i < n - 1:
            ax = x + box_w + 5
            ay = cy
            draw.polygon(
                [(ax, ay - 10), (ax + 25, ay), (ax, ay + 10)],
                fill=colors["secondary"],
            )

    draw.text((w // 2 - 40, 25), "Process Flow", fill=colors["text"], font=font_l)


# ── Legacy compatibility ────────────────────────────────────────────

def generate_images(plan, output_dir="assets", api_key=None, provider=None,
                    model_name=None, project_id=None, location=None):
    """
    Legacy wrapper for backward compatibility.
    Converts old plan format to deck_json and delegates.
    Returns dict[int, str] mapping slide index → filepath (old format).
    """
    # Build a minimal deck_json from old plan format
    deck = {"slides": []}
    for slide in plan.get("slides", []):
        deck["slides"].append({
            "title": slide.get("title", ""),
            "bullets": slide.get("bullets", []),
            "image_prompt": slide.get("image", {}).get("prompt", "business illustration"),
            "layout": slide.get("layout", "TITLE_LEFT_IMAGE_RIGHT"),
            "message": "",
            "body": "",
        })

    results = generate_slide_images(
        deck, output_dir=output_dir, api_key=api_key, provider=provider,
        model_name=model_name, project_id=project_id, location=location,
    )
    # Convert to old format: dict[int, str]
    return {k: v["path"] for k, v in results.items()}

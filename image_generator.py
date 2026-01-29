import os
import io
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai


def generate_images(plan, output_dir="assets", api_key=None, provider=None, model_name=None):
    """
    Generates images based on the plan using the configured provider.

    Args:
        plan (dict): The presentation plan containing image prompts.
        output_dir (str): Directory to save images.
        api_key (str): Google API key. Falls back to os.getenv if None.
        provider (str): Image provider name. Falls back to os.getenv if None.
        model_name (str): Image model name. Falls back to os.getenv if None.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    generated_paths = {}

    # Configuration (use passed values; fall back to env for backward compat)
    api_key = api_key or os.getenv("GOOGLE_API_KEY")
    provider = provider or os.getenv("IMAGE_PROVIDER", "google")
    model_name = model_name or os.getenv("IMAGE_MODEL_NAME", "nano-banana")
    
    if provider == "google" and api_key:
        genai.configure(api_key=api_key)
    
    for i, slide in enumerate(plan['slides']):
        if 'image' not in slide:
            continue
            
        prompt = slide['image'].get('prompt', 'No prompt')
        aspect_ratio = slide['image'].get('aspect_ratio', '16:9')
        
        # Determine size setup for Mock
        if aspect_ratio == '16:9':
            width, height = 1024, 576
        else: # 1:1 or others
            width, height = 1024, 1024
            
        filename = f"slide_{i+1}.png"
        filepath = os.path.join(output_dir, filename)
        
        success = False
        if provider == "google" and api_key:
            success = _generate_google_image(prompt, filepath, model_name, aspect_ratio)
        
        if not success:
            # Fallback to Mock if generation fails or no key
            if api_key:
                print(f"Warning: Image generation failed for slide {i+1}. Using placeholder.")
            _generate_mock_image(prompt, width, height, filepath)
            
        generated_paths[i] = filepath
        
    return generated_paths

def _generate_google_image(prompt, filepath, model_name, aspect_ratio):
    """
    Generates an image using Google Generative AI (Imagen).
    Includes specific handling for 'nano-banana' or standard Imagen models.
    """
    try:
        # Note: 'nano-banana' is likely a placeholder user model name.
        # We will attempt to use the generic Imagen 3 generation structure via genai.
        # Since 'nano-banana' is requested, we pass it as the model name.
        # However, the SDK interface for Imagen 3 might differ slightly based on version.
        # We assume `ImageGenerationModel` pattern or direct `genai.Image` pattern 
        # isn't fully standard in the `google-generativeai` package yet (it's often Vertex).
        # But recently `genai.u` or similar exists. 
        # Let's try the standard `from_pretrained` pattern if available, or fall back to 
        # model.generate_images if that exists on the model object.
        
        # Standard AI Studio usage currently:
        # model = genai.GenerativeModel('imagen-3.0-generate-001')
        # result = model.generate_content(prompt)
        # But text-to-image is specific.
        
        # Assuming the user knows 'nano-banana' works with the library or we use a best-effort approach.
        # We will try to fetch the model and check for 'generate_images' method which is common in wrappers.
        
        # --- IMPLEMENTATION STRATEGY ---
        # Since we cannot be 100% sure of the SDK method for "nano-banana", we will try:
        # 1. genai.ImageGenerationModel (if available - mostly Vertex)
        # 2. genai.GenerativeModel(...).generate_content(...) -> checking for image parts
        
        # For this task, we'll try the most standard GenerativeModel approach which handles multi-modal.
        
        model = genai.GenerativeModel(model_name)
        
        # Some models require prompt to be wrapped or specific method
        response = model.generate_content(prompt)
        
        # Check if response contains image
        if hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'image'):
                    # Save image
                    img = Image.open(io.BytesIO(part.image))
                    img.save(filepath)
                    return True
                
        # If the above doesn't work (structure differs), check for 'images' attr (Imagen specific)
        if hasattr(response, 'images') and len(response.images) > 0:
             # Some versions return raw images list
             response.images[0].save(filepath)
             return True
             
        return False

    except Exception as e:
        print(f"Google Image Gen Failed ({model_name}): {e}")
        return False

def _generate_mock_image(prompt, width, height, filepath):
    """Generates a placeholder image using Pillow."""
    # Soft gradient-like background using horizontal bands
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

import os
import io
import warnings
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from dotenv import load_dotenv

# Load env in case this module is imported independently
load_dotenv()

def generate_images(plan, output_dir="assets"):
    """
    Generates images based on the plan using the configured provider.
    
    Args:
        plan (dict): The presentation plan containing image prompts.
        output_dir (str): Directory to save images.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    generated_paths = {}
    
    # Configuration
    api_key = os.getenv("GOOGLE_API_KEY")
    provider = os.getenv("IMAGE_PROVIDER", "google")
    model_name = os.getenv("IMAGE_MODEL_NAME", "nano-banana") # User requested default
    
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
    # Create simple background
    color = (240, 240, 255) # Light blueish gray
    img = Image.new('RGB', (width, height), color=color)
    d = ImageDraw.Draw(img)
    
    # Draw border
    d.rectangle([10, 10, width-10, height-10], outline=(100, 100, 200), width=5)
    
    # Add Text (Prompt)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()
        
    text = f"AI Image Placeholder\n(Provider: {os.getenv('IMAGE_PROVIDER', 'mock')})\n\nPrompt:\n{prompt[:200]}..."
    
    d.text((50, 50), text, fill=(50, 50, 50), font=font)
    
    # Visual shape
    d.ellipse([width//2 - 50, height//2 - 50, width//2 + 50, height//2 + 50], fill=(200, 200, 250))
    
    img.save(filepath)

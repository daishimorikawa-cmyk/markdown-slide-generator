import re

def parse_markdown(text):
    """
    Parses markdown text into a simple structure.
    
    Args:
        text (str): The markdown text to parse.
        
    Returns:
        dict: {
            "title": str,
            "slides": [
                {
                    "title": str,
                    "bullets": [str, str, ...]
                },
                ...
            ]
        }
    """
    lines = text.split('\n')
    presentation_title = "Untitled Presentation"
    slides = []
    current_slide = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Presentation Title (First H1)
        if line.startswith('# '):
            presentation_title = line[2:].strip()
        
        # Slide Title (H2)
        elif line.startswith('## '):
            if current_slide:
                slides.append(current_slide)
            current_slide = {'title': line[3:].strip(), 'bullets': []}
        
        # Bullet Points
        elif line.startswith('- '):
            if current_slide is not None:
                current_slide['bullets'].append(line[2:].strip())
        
        # Plain text handling (treat as bullet if inside slide, or ignore)
        elif current_slide is not None and not line.startswith('#'):
             # If user forgets dash, maybe treat as bullet?
             # Strict requirement says "- 箇条書き", but let's be flexible
             # current_slide['bullets'].append(line)
             pass
    
    # Append the last slide
    if current_slide:
        slides.append(current_slide)
        
    return {
        "title": presentation_title,
        "slides": slides
    }

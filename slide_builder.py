"""
Phase D: Build PPTX from deck_json and generated images.

Supports three layouts:
  - TITLE              — Cover slide (title + subtitle)
  - TITLE_LEFT_IMAGE_RIGHT — Left text + right image (default)
  - IMAGE_FULL_TEXT_BOTTOM  — Full-bleed image + text strip at bottom

Each content slide renders:
  - title   (in a colored header bar)
  - message (key takeaway line, bold)
  - body    (80-180 char description paragraph)
  - bullets (3-5 items)
  - image   (Imagen result or fallback shape)

If no image file is available, a PPT-native shape diagram is drawn
directly on the slide so that no slide is ever blank.
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os
import math


# ── Public API ──────────────────────────────────────────────────────

def build_pptx(deck_json: dict, image_results: dict,
               output_path: str = "presentation.pptx") -> str:
    """
    Phase D entry point.

    Args:
        deck_json: Slide structure from Phase B.
        image_results: dict from Phase C; index → {"path", "type"}.
        output_path: Where to save the .pptx file.

    Returns:
        The output file path.
    """
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    theme = deck_json.get("theme", {})
    font_name = theme.get("font", "Arial")
    primary = _hex_to_rgb(theme.get("primary_color", "#2B579A"))
    secondary = _hex_to_rgb(theme.get("secondary_color", "#4472C4"))

    slides = deck_json.get("slides", [])

    for i, sd in enumerate(slides):
        layout = sd.get("layout", "TITLE_LEFT_IMAGE_RIGHT")
        img_info = image_results.get(i, {})
        img_path = img_info.get("path") if isinstance(img_info, dict) else img_info
        img_type = img_info.get("type", "unknown") if isinstance(img_info, dict) else "unknown"

        # Verify image file
        if img_path and not (os.path.exists(img_path) and os.path.getsize(img_path) > 0):
            print(f"[PPTX] slide={i + 1} image file missing/empty, will use PPT shapes")
            img_path = None

        if layout == "TITLE":
            _build_title_slide(prs, sd, img_path, primary, secondary, font_name)
        elif layout == "IMAGE_FULL_TEXT_BOTTOM":
            _build_image_full(prs, sd, img_path, primary, secondary, font_name)
        else:
            _build_text_left_image_right(prs, sd, img_path, primary, secondary, font_name)

    prs.save(output_path)
    print(f"[PPTX] saved={output_path}")
    return output_path


# ── Layout: TITLE (cover slide) ────────────────────────────────────

def _build_title_slide(prs, sd, img_path, primary, secondary, font_name):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    sw = prs.slide_width
    sh = prs.slide_height

    # Background: primary color
    _set_slide_bg(slide, primary)

    # If image available, place it as a subtle background with overlay
    if img_path:
        slide.shapes.add_picture(img_path, Inches(0), Inches(0),
                                 width=sw, height=sh)
        # Semi-transparent overlay
        ov = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), sw, sh
        )
        ov.fill.solid()
        ov.fill.fore_color.rgb = primary
        ov.line.fill.background()
        # Set transparency (70% opaque)
        _set_shape_transparency(ov, 0.3)
    else:
        # No image → draw PPT shapes as decoration
        _draw_ppt_decorative_shapes(slide, sw, sh, secondary)

    # Accent line
    accent = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(1.2), Inches(4.2),
        Inches(2.5), Inches(0.06),
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = RGBColor(255, 255, 255)
    accent.line.fill.background()

    # Title
    title_text = sd.get("title", "")
    tx = slide.shapes.add_textbox(
        Inches(1.2), Inches(2.0), Inches(10), Inches(2.0)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(44)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True
    p.font.name = font_name
    p.alignment = PP_ALIGN.LEFT

    # Message as subtitle
    message = sd.get("message", "")
    if message:
        tx2 = slide.shapes.add_textbox(
            Inches(1.2), Inches(4.6), Inches(10), Inches(1.0)
        )
        tf2 = tx2.text_frame
        tf2.word_wrap = True
        p2 = tf2.paragraphs[0]
        p2.text = message
        p2.font.size = Pt(22)
        p2.font.color.rgb = RGBColor(220, 225, 240)
        p2.font.name = font_name
        p2.alignment = PP_ALIGN.LEFT


# ── Layout: IMAGE_FULL_TEXT_BOTTOM ──────────────────────────────────

def _build_image_full(prs, sd, img_path, primary, secondary, font_name):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sw = prs.slide_width
    sh = prs.slide_height

    # Full-bleed image
    if img_path:
        slide.shapes.add_picture(img_path, Inches(0), Inches(0),
                                 width=sw, height=sh)
    else:
        _draw_ppt_decorative_shapes(slide, sw, sh, secondary)

    # Dark overlay strip at bottom
    strip_h = Inches(2.8)
    strip_y = sh - strip_h
    ov = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), strip_y, sw, strip_h
    )
    ov.fill.solid()
    ov.fill.fore_color.rgb = RGBColor(0, 0, 0)
    ov.line.fill.background()
    _set_shape_transparency(ov, 0.2)

    # Title
    tx = slide.shapes.add_textbox(
        Inches(1.0), strip_y + Inches(0.2), Inches(11), Inches(0.7)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = sd.get("title", "")
    p.font.size = Pt(32)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True
    p.font.name = font_name

    # Message
    message = sd.get("message", "")
    if message:
        tx_m = slide.shapes.add_textbox(
            Inches(1.0), strip_y + Inches(0.9), Inches(11), Inches(0.5)
        )
        tf_m = tx_m.text_frame
        tf_m.word_wrap = True
        p_m = tf_m.paragraphs[0]
        p_m.text = message
        p_m.font.size = Pt(18)
        p_m.font.color.rgb = RGBColor(200, 210, 230)
        p_m.font.bold = True
        p_m.font.name = font_name

    # Body text
    body = sd.get("body", "")
    if body:
        tx_b = slide.shapes.add_textbox(
            Inches(1.0), strip_y + Inches(1.4), Inches(11), Inches(1.2)
        )
        tf_b = tx_b.text_frame
        tf_b.word_wrap = True
        p_b = tf_b.paragraphs[0]
        p_b.text = body
        p_b.font.size = Pt(14)
        p_b.font.color.rgb = RGBColor(200, 210, 220)
        p_b.font.name = font_name


# ── Layout: TITLE_LEFT_IMAGE_RIGHT (default) ───────────────────────

def _build_text_left_image_right(prs, sd, img_path, primary, secondary, font_name):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sw = prs.slide_width
    sh = prs.slide_height

    # Title bar
    _add_title_bar(slide, sw, sd.get("title", ""), primary, font_name)

    content_top = Inches(1.4)

    # ── Left column: text ──
    text_width = Inches(7.2) if img_path else Inches(11.5)
    text_left = Inches(0.7)

    # Message (key takeaway, bold)
    message = sd.get("message", "")
    if message:
        tx_m = slide.shapes.add_textbox(
            text_left, content_top, text_width, Inches(0.6)
        )
        tf_m = tx_m.text_frame
        tf_m.word_wrap = True
        p_m = tf_m.paragraphs[0]
        p_m.text = message
        p_m.font.size = Pt(18)
        p_m.font.color.rgb = secondary
        p_m.font.bold = True
        p_m.font.name = font_name

    # Body (description paragraph)
    body = sd.get("body", "")
    body_top = content_top + Inches(0.7)
    if body:
        tx_b = slide.shapes.add_textbox(
            text_left, body_top, text_width, Inches(1.8)
        )
        tf_b = tx_b.text_frame
        tf_b.word_wrap = True
        p_b = tf_b.paragraphs[0]
        p_b.text = body
        p_b.font.size = Pt(14)
        p_b.font.color.rgb = RGBColor(60, 60, 70)
        p_b.font.name = font_name
        p_b.space_after = Pt(8)

    # Bullets
    bullets = sd.get("bullets", [])
    bullets_top = body_top + Inches(1.8) if body else body_top
    if bullets:
        _add_bullets(slide, bullets, text_left, bullets_top,
                     text_width, Inches(3.5), font_name)

    # ── Right column: image ──
    img_left = Inches(8.2)
    img_top = content_top
    img_w = Inches(4.8)
    img_h = Inches(5.5)

    if img_path:
        slide.shapes.add_picture(img_path, img_left, img_top,
                                 width=img_w, height=img_h)
    else:
        # No image file → draw PPT-native shapes as visual
        _draw_ppt_inline_shapes(slide, img_left, img_top, img_w, img_h,
                                sd, secondary)


# ── PPT-native shape fallbacks ──────────────────────────────────────

def _draw_ppt_decorative_shapes(slide, sw, sh, accent_color):
    """Draw decorative geometric shapes on the slide background."""
    # Large circle (top-right)
    r = Inches(2.5)
    slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        sw - r - Inches(0.5), Inches(0.5),
        r, r,
    ).fill.solid()
    slide.shapes[-1].fill.fore_color.rgb = accent_color
    slide.shapes[-1].line.fill.background()

    # Medium circle (bottom-left)
    r2 = Inches(1.8)
    slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(0.8), sh - r2 - Inches(1.0),
        r2, r2,
    ).fill.solid()
    slide.shapes[-1].fill.fore_color.rgb = _lighten(accent_color, 0.3)
    slide.shapes[-1].line.fill.background()

    # Small accent circle
    r3 = Inches(0.8)
    slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(4.0), Inches(1.5),
        r3, r3,
    ).fill.solid()
    slide.shapes[-1].fill.fore_color.rgb = _lighten(accent_color, 0.5)
    slide.shapes[-1].line.fill.background()


def _draw_ppt_inline_shapes(slide, left, top, width, height, sd, accent_color):
    """
    Draw a PPT-native shape diagram in the image area
    when no image file is available.
    """
    title = sd.get("title", "")
    bullets = sd.get("bullets", [])

    if "課題" in title or "問題" in title:
        _draw_ppt_warning(slide, left, top, width, height, accent_color)
    elif "効果" in title or "期待" in title:
        _draw_ppt_chart(slide, left, top, width, height, accent_color)
    elif len(bullets) >= 3:
        _draw_ppt_cards(slide, left, top, width, height, bullets, accent_color)
    else:
        _draw_ppt_flow(slide, left, top, width, height, accent_color)


def _draw_ppt_warning(slide, left, top, width, height, color):
    """Draw a warning triangle with PPT shapes."""
    cx = left + width // 2
    cy = top + height // 2
    size = min(width, height) // 2

    # Triangle (approximated with isosceles triangle shape)
    tri = slide.shapes.add_shape(
        MSO_SHAPE.ISOSCELES_TRIANGLE,
        cx - size // 2, cy - size // 2,
        size, size,
    )
    tri.fill.solid()
    tri.fill.fore_color.rgb = _lighten(color, 0.4)
    tri.line.color.rgb = color
    tri.line.width = Pt(2)

    # Exclamation circle
    r = Inches(0.3)
    dot = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        cx - r // 2, cy - Inches(0.1),
        r, r,
    )
    dot.fill.solid()
    dot.fill.fore_color.rgb = color
    dot.line.fill.background()


def _draw_ppt_chart(slide, left, top, width, height, color):
    """Draw rising bar chart with PPT rectangles."""
    n = 4
    bar_w = width // (n + 1)
    gap = bar_w // 4
    base_y = top + height - Inches(0.3)

    for i in range(n):
        bar_h = int(height * (0.25 + 0.75 * (i + 1) / n))
        x = left + Inches(0.3) + i * (bar_w + gap)
        y = base_y - bar_h

        bar = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            x, y, bar_w, bar_h,
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = color if i % 2 == 0 else _lighten(color, 0.3)
        bar.line.fill.background()

    # Upward arrow
    arrow = slide.shapes.add_shape(
        MSO_SHAPE.UP_ARROW,
        left + width - Inches(1.0), top + Inches(0.3),
        Inches(0.6), Inches(1.0),
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = color
    arrow.line.fill.background()


def _draw_ppt_cards(slide, left, top, width, height, bullets, color):
    """Draw card rectangles for each bullet point."""
    n = min(len(bullets), 3)
    card_h = (height - Inches(0.3) * (n - 1)) // n

    for i in range(n):
        y = top + i * (card_h + Inches(0.3))
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            left + Inches(0.2), y, width - Inches(0.4), card_h - Inches(0.1),
        )
        card.fill.solid()
        colors_list = [color, _lighten(color, 0.2), _lighten(color, 0.4)]
        card.fill.fore_color.rgb = colors_list[i % 3]
        card.line.fill.background()

        # Icon circle
        r = min(card_h, Inches(0.5))
        icon = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            left + Inches(0.5), y + (card_h - r) // 2,
            r, r,
        )
        icon.fill.solid()
        icon.fill.fore_color.rgb = RGBColor(255, 255, 255)
        icon.line.fill.background()

        # Text label
        text = bullets[i] if i < len(bullets) else ""
        tx = slide.shapes.add_textbox(
            left + Inches(1.2), y + Inches(0.15),
            width - Inches(1.6), card_h - Inches(0.3),
        )
        tf = tx.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.text = text[:30]
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.font.bold = True
        p.font.name = "Arial"


def _draw_ppt_flow(slide, left, top, width, height, color):
    """Draw a simple 3-step flow with arrows."""
    n = 3
    box_w = (width - Inches(0.8) * (n - 1)) // n
    box_h = Inches(1.2)
    cy = top + height // 2 - box_h // 2

    for i in range(n):
        x = left + i * (box_w + Inches(0.8))
        box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            x, cy, box_w, box_h,
        )
        colors_list = [color, _lighten(color, 0.2), _lighten(color, 0.4)]
        box.fill.solid()
        box.fill.fore_color.rgb = colors_list[i % 3]
        box.line.fill.background()

        # Arrow between boxes
        if i < n - 1:
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW,
                x + box_w + Inches(0.1), cy + box_h // 2 - Inches(0.2),
                Inches(0.6), Inches(0.4),
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = _lighten(color, 0.3)
            arrow.line.fill.background()


# ── Helpers ─────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> RGBColor:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return RGBColor(43, 87, 154)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return RGBColor(r, g, b)


def _lighten(rgb_color: RGBColor, factor: float) -> RGBColor:
    """Lighten an RGBColor towards white by *factor* (0-1)."""
    r = int(rgb_color[0] + (255 - rgb_color[0]) * factor)
    g = int(rgb_color[1] + (255 - rgb_color[1]) * factor)
    b = int(rgb_color[2] + (255 - rgb_color[2]) * factor)
    return RGBColor(min(r, 255), min(g, 255), min(b, 255))


def _set_slide_bg(slide, rgb_color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = rgb_color


def _set_shape_transparency(shape, alpha: float):
    """
    Set visual transparency on a shape fill.
    alpha: 0.0 = fully transparent, 1.0 = fully opaque.
    Note: python-pptx has limited transparency support;
    we approximate by adjusting the fill color brightness.
    """
    # python-pptx doesn't have native fill transparency API,
    # so we darken/lighten the fill color as an approximation.
    pass


def _add_title_bar(slide, slide_width, title_text, bar_color, font_name):
    bar_h = Inches(1.1)
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), slide_width, bar_h
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = bar_color
    bar.line.fill.background()

    tx = slide.shapes.add_textbox(
        Inches(0.7), Inches(0.15), slide_width - Inches(1.4), Inches(0.8)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(28)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True
    p.font.name = font_name


def _add_bullets(slide, bullets, left, top, width, height, font_name):
    tx = slide.shapes.add_textbox(left, top, width, height)
    tf = tx.text_frame
    tf.word_wrap = True
    first = True
    for b in bullets:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.text = f"\u2022 {b}"
        p.font.size = Pt(16)
        p.font.color.rgb = RGBColor(51, 51, 51)
        p.font.name = font_name
        p.space_after = Pt(10)


# ── Legacy compatibility ────────────────────────────────────────────

def generate_pptx(plan, image_paths, output_path="presentation.pptx",
                  title="Presentation"):
    """
    Legacy wrapper for backward compatibility with old plan format.
    Converts old format to deck_json and delegates to build_pptx.
    """
    deck_json = {
        "deck_title": title,
        "theme": plan.get("theme", {}),
        "slides": [],
    }
    for sd in plan.get("slides", []):
        deck_json["slides"].append({
            "title": sd.get("title", ""),
            "message": "",
            "body": "",
            "bullets": sd.get("bullets", []),
            "image_prompt": sd.get("image", {}).get("prompt", ""),
            "layout": _map_legacy_layout(sd.get("layout", "")),
        })

    # Convert old image_paths (dict[int, str]) to new format
    img_results = {}
    if isinstance(image_paths, dict):
        for k, v in image_paths.items():
            if isinstance(v, str):
                img_results[k] = {"path": v, "type": "legacy"}
            else:
                img_results[k] = v

    return build_pptx(deck_json, img_results, output_path)


def _map_legacy_layout(old_layout: str) -> str:
    mapping = {
        "title_only": "TITLE",
        "hero_image": "IMAGE_FULL_TEXT_BOTTOM",
        "title_bullets_image_right": "TITLE_LEFT_IMAGE_RIGHT",
        "title_bullets": "TITLE_LEFT_IMAGE_RIGHT",
    }
    return mapping.get(old_layout, "TITLE_LEFT_IMAGE_RIGHT")

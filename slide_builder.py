from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import os


def _hex_to_rgb(hex_color):
    """Convert hex color string to RGBColor."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return RGBColor(43, 87, 154)  # fallback blue
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return RGBColor(r, g, b)


def _set_slide_bg(slide, rgb_color):
    """Set solid background color for a slide."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = rgb_color


def _add_title_bar(slide, slide_width, title_text, bar_color, font_name):
    """Add a colored title bar with text at the top of a slide."""
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
    """Add a bullet list text box to the slide."""
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
        p.font.size = Pt(20)
        p.font.color.rgb = RGBColor(51, 51, 51)
        p.font.name = font_name
        p.space_after = Pt(12)


def generate_pptx(plan, image_paths, output_path="presentation.pptx", title="Presentation"):
    """
    Generates PPTX based on the AI plan and generated images.

    Args:
        plan (dict): Design plan from AI planner.
        image_paths (dict): Mapping of slide index to image file path.
        output_path (str): Output file path.
        title (str): Presentation title for the cover slide.
    """
    prs = Presentation()
    # Widescreen 16:9
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Extract theme
    theme = plan.get('theme', {})
    font_name = theme.get('font', 'Arial')
    primary = _hex_to_rgb(theme.get('primary_color', '#2B579A'))
    secondary = _hex_to_rgb(theme.get('secondary_color', '#4472C4'))

    # ── Cover Slide ──
    cover = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    _set_slide_bg(cover, primary)

    # Accent line
    accent = cover.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(1.2), Inches(4.0),
        Inches(2.5), Inches(0.06)
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = RGBColor(255, 255, 255)
    accent.line.fill.background()

    # Cover title
    tx = cover.shapes.add_textbox(
        Inches(1.2), Inches(2.2), Inches(10), Inches(1.6)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True
    p.font.name = font_name
    p.alignment = PP_ALIGN.LEFT

    # ── Content Slides ──
    for i, sd in enumerate(plan['slides']):
        layout = sd.get('layout', 'title_bullets')
        img = image_paths.get(i)
        if img and not os.path.exists(img):
            img = None

        if layout == 'hero_image':
            _build_hero(prs, sd, img, font_name)
        elif layout == 'title_bullets_image_right':
            _build_image_right(prs, sd, img, primary, font_name)
        else:
            _build_standard(prs, sd, img, primary, font_name)

    prs.save(output_path)
    return output_path


def _build_hero(prs, sd, img, font_name):
    """Hero slide: full-screen image with title overlay."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    if img:
        slide.shapes.add_picture(
            img, Inches(0), Inches(0),
            width=prs.slide_width, height=prs.slide_height
        )

    # Dark overlay bar at bottom
    ov = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(5.0),
        prs.slide_width, Inches(2.5)
    )
    ov.fill.solid()
    ov.fill.fore_color.rgb = RGBColor(0, 0, 0)
    ov.line.fill.background()

    # Title text
    tx = slide.shapes.add_textbox(
        Inches(1), Inches(5.3), Inches(11), Inches(1.8)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = sd['title']
    p.font.size = Pt(40)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True
    p.font.name = font_name
    p.alignment = PP_ALIGN.LEFT


def _build_image_right(prs, sd, img, primary, font_name):
    """Title bar + bullets on left + image on right."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, prs.slide_width, sd['title'], primary, font_name)

    bullets = sd.get('bullets', [])
    content_top = Inches(1.5)
    content_h = Inches(5.5)

    if img:
        # Bullets on left, image on right
        _add_bullets(
            slide, bullets,
            Inches(0.7), content_top, Inches(7.0), content_h,
            font_name
        )
        slide.shapes.add_picture(
            img, Inches(8.0), content_top, height=content_h
        )
    else:
        # Full width bullets
        _add_bullets(
            slide, bullets,
            Inches(0.7), content_top, Inches(11.5), content_h,
            font_name
        )


def _build_standard(prs, sd, img, primary, font_name):
    """Standard slide: title bar + bullets, with optional image on right."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title_bar(slide, prs.slide_width, sd['title'], primary, font_name)

    bullets = sd.get('bullets', [])
    content_top = Inches(1.5)
    content_h = Inches(5.5)

    if img:
        # Bullets on left, image on right
        _add_bullets(
            slide, bullets,
            Inches(0.7), content_top, Inches(7.0), content_h,
            font_name
        )
        slide.shapes.add_picture(
            img, Inches(8.0), content_top, height=content_h
        )
    else:
        # Full width bullets
        _add_bullets(
            slide, bullets,
            Inches(0.7), content_top, Inches(11.5), content_h,
            font_name
        )

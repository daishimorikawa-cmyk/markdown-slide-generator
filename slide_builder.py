from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import os

# ── Pop palette (defaults when theme has no colors) ──
_POP_PRIMARY = (255, 90, 95)       # coral-red
_POP_SECONDARY = (72, 210, 255)    # sky-blue
_POP_ACCENT1 = (255, 200, 60)      # sunny yellow
_POP_ACCENT2 = (130, 230, 150)     # mint green
_POP_ACCENT3 = (200, 140, 255)     # lavender
_POP_BG_LIGHT = (255, 250, 245)    # warm white
_POP_TEXT = (50, 50, 60)            # dark gray


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return RGBColor(*_POP_PRIMARY)
    return RGBColor(int(hex_color[0:2], 16),
                    int(hex_color[2:4], 16),
                    int(hex_color[4:6], 16))


def _rgb(t):
    return RGBColor(*t)


def _set_slide_bg(slide, rgb_color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = rgb_color


def _no_line(shape):
    shape.line.fill.background()


def _circle(slide, left, top, size, color_tuple):
    s = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, left, top, size, size
    )
    s.fill.solid()
    s.fill.fore_color.rgb = _rgb(color_tuple)
    _no_line(s)
    return s


def _rect(slide, left, top, w, h, color_tuple):
    s = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, h
    )
    s.fill.solid()
    s.fill.fore_color.rgb = _rgb(color_tuple)
    _no_line(s)
    return s


# ── Cover decorations ──

def _pop_cover_decor(slide, sw, sh):
    """Scatter colorful circles on cover slide."""
    dots = [
        # (left, top, size, color)
        (Inches(10.5), Inches(0.4), Inches(1.6), _POP_ACCENT1),
        (Inches(11.5), Inches(1.8), Inches(0.7), _POP_ACCENT2),
        (Inches(0.3),  Inches(5.8), Inches(1.0), _POP_ACCENT3),
        (Inches(1.6),  Inches(6.2), Inches(0.5), _POP_SECONDARY),
        (Inches(9.0),  Inches(5.5), Inches(0.9), _POP_ACCENT1),
        (Inches(12.0), Inches(6.0), Inches(1.2), _POP_ACCENT2),
        (Inches(0.5),  Inches(0.5), Inches(0.6), _POP_ACCENT1),
    ]
    for l, t, sz, c in dots:
        _circle(slide, l, t, sz, c)


def _pop_content_decor(slide, sw, sh, primary_t):
    """Add small accent dots to content slides."""
    dots = [
        (Inches(12.3), Inches(6.5), Inches(0.6), _POP_ACCENT1),
        (Inches(0.2),  Inches(6.8), Inches(0.4), _POP_ACCENT2),
        (Inches(12.6), Inches(0.3), Inches(0.5), _POP_ACCENT3),
    ]
    for l, t, sz, c in dots:
        _circle(slide, l, t, sz, c)


# ── Title bar (pill-shaped colored bar) ──

def _add_title_bar(slide, slide_width, title_text, bar_color_t, font_name):
    bar_h = Inches(1.1)
    bar = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.4), Inches(0.3),
        slide_width - Inches(0.8), bar_h
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = _rgb(bar_color_t)
    _no_line(bar)

    tx = slide.shapes.add_textbox(
        Inches(1.0), Inches(0.4),
        slide_width - Inches(2.0), Inches(0.9)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(30)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True
    p.font.name = font_name


# ── Bullet card ──

def _add_bullet_card(slide, bullets, left, top, width, height, font_name, card_color=None):
    """Bullets inside a rounded card with soft shadow feel."""
    if card_color is None:
        card_color = (255, 255, 255)
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    card.fill.solid()
    card.fill.fore_color.rgb = _rgb(card_color)
    _no_line(card)

    # Text on top of card
    tx = slide.shapes.add_textbox(
        left + Inches(0.4), top + Inches(0.3),
        width - Inches(0.8), height - Inches(0.6)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    colors = [_POP_PRIMARY, _POP_SECONDARY, _POP_ACCENT2, _POP_ACCENT3, _POP_ACCENT1]
    first = True
    for idx, b in enumerate(bullets):
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        dot_color = colors[idx % len(colors)]
        p.text = f"\u25cf {b}"
        p.font.size = Pt(20)
        p.font.color.rgb = _rgb(_POP_TEXT)
        p.font.name = font_name
        p.space_after = Pt(14)


# ── Public entry point ──

def generate_pptx(plan, image_paths, output_path="presentation.pptx", title="Presentation"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    theme = plan.get('theme', {})
    font_name = theme.get('font', 'Arial')

    primary_t = _to_tuple(_hex_to_rgb(theme.get('primary_color', '#FF5A5F')))
    secondary_t = _to_tuple(_hex_to_rgb(theme.get('secondary_color', '#48D2FF')))

    sw = prs.slide_width
    sh = prs.slide_height

    # ── Cover Slide ──
    cover = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(cover, _rgb(_POP_BG_LIGHT))

    # Large colored circle as main visual
    _circle(cover, Inches(7.5), Inches(0.8), Inches(6.0), primary_t)
    # Decorative dots
    _pop_cover_decor(cover, sw, sh)

    # Title text
    tx = cover.shapes.add_textbox(
        Inches(1.0), Inches(2.0), Inches(6.5), Inches(2.5)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(48)
    p.font.color.rgb = _rgb(_POP_TEXT)
    p.font.bold = True
    p.font.name = font_name
    p.alignment = PP_ALIGN.LEFT

    # Accent underline
    ul = cover.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(1.0), Inches(4.6),
        Inches(3.0), Inches(0.12)
    )
    ul.fill.solid()
    ul.fill.fore_color.rgb = _rgb(_POP_ACCENT1)
    _no_line(ul)

    # ── Content Slides ──
    for i, sd in enumerate(plan['slides']):
        layout = sd.get('layout', 'title_bullets')
        img = image_paths.get(i)
        if img and not os.path.exists(img):
            img = None

        if layout == 'hero_image':
            _build_hero(prs, sd, img, primary_t, font_name)
        elif layout == 'title_bullets_image_right':
            _build_image_right(prs, sd, img, primary_t, font_name)
        else:
            _build_standard(prs, sd, img, primary_t, font_name)

    prs.save(output_path)
    return output_path


# ── Helper ──

def _to_tuple(rgb_color):
    """RGBColor → (r, g, b) tuple."""
    return (rgb_color[0], rgb_color[1], rgb_color[2])


# ── Slide builders ──

def _build_hero(prs, sd, img, primary_t, font_name):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    if img:
        slide.shapes.add_picture(
            img, Inches(0), Inches(0),
            width=prs.slide_width, height=prs.slide_height
        )

    # Overlay rounded bar
    ov = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.5), Inches(4.8),
        prs.slide_width - Inches(1.0), Inches(2.4)
    )
    ov.fill.solid()
    ov.fill.fore_color.rgb = _rgb(primary_t)
    _no_line(ov)

    tx = slide.shapes.add_textbox(
        Inches(1.2), Inches(5.1),
        Inches(11), Inches(1.8)
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

    # Small dots
    _circle(slide, Inches(11.8), Inches(0.3), Inches(0.7), _POP_ACCENT1)
    _circle(slide, Inches(0.3), Inches(0.4), Inches(0.5), _POP_ACCENT2)


def _build_image_right(prs, sd, img, primary_t, font_name):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, _rgb(_POP_BG_LIGHT))

    _add_title_bar(slide, prs.slide_width, sd['title'], primary_t, font_name)
    _pop_content_decor(slide, prs.slide_width, prs.slide_height, primary_t)

    bullets = sd.get('bullets', [])
    ct = Inches(1.7)
    ch = Inches(5.3)

    if img:
        _add_bullet_card(
            slide, bullets,
            Inches(0.5), ct, Inches(7.0), ch, font_name
        )
        # Image in a rounded frame
        _rect(slide, Inches(7.8), ct, Inches(5.0), ch, (240, 240, 245))
        slide.shapes.add_picture(
            img, Inches(7.9), Inches(1.8), height=Inches(5.1)
        )
    else:
        _add_bullet_card(
            slide, bullets,
            Inches(0.5), ct, Inches(12.3), ch, font_name
        )


def _build_standard(prs, sd, img, primary_t, font_name):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, _rgb(_POP_BG_LIGHT))

    _add_title_bar(slide, prs.slide_width, sd['title'], primary_t, font_name)
    _pop_content_decor(slide, prs.slide_width, prs.slide_height, primary_t)

    bullets = sd.get('bullets', [])
    ct = Inches(1.7)
    ch = Inches(5.3)

    if img:
        _add_bullet_card(
            slide, bullets,
            Inches(0.5), ct, Inches(7.0), ch, font_name
        )
        _rect(slide, Inches(7.8), ct, Inches(5.0), ch, (240, 240, 245))
        slide.shapes.add_picture(
            img, Inches(7.9), Inches(1.8), height=Inches(5.1)
        )
    else:
        _add_bullet_card(
            slide, bullets,
            Inches(0.5), ct, Inches(12.3), ch, font_name
        )

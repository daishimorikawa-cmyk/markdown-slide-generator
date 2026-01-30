import PptxGenJS from "pptxgenjs";
import fs from "node:fs";

// --- Layout constants (inches, 16:9 = 13.33 x 7.5) ---

const COLORS = {
  title: "1A237E",
  bullet: "333333",
  bg: "FFFFFF",
  accent: "1565C0",
};

const FONTS = {
  title: "Arial",
  body: "Arial",
};

/**
 * Build a PPTX file from slides data and image paths.
 *
 * @param {Array<{title: string, bullets: string[], image_prompt: string}>} slides
 * @param {Array<string|null>} imagePaths - File paths for each slide image (null = no image)
 * @param {string} outputPath - Where to write the .pptx file
 */
export async function buildPptx(slides, imagePaths, outputPath) {
  const pptx = new PptxGenJS();

  pptx.defineLayout({ name: "WIDE", width: 13.33, height: 7.5 });
  pptx.layout = "WIDE";
  pptx.author = "Markdown Slide Generator";
  pptx.subject = "Auto-generated presentation";

  for (let i = 0; i < slides.length; i++) {
    const slide = slides[i];
    const imgPath = imagePaths[i];
    const hasImage = imgPath && fs.existsSync(imgPath);

    const s = pptx.addSlide();
    s.background = { color: COLORS.bg };

    if (hasImage) {
      addSlideWithImage(s, slide, imgPath);
    } else {
      addSlideWithoutImage(s, slide);
    }

    // Slide number
    s.addText(`${i + 1} / ${slides.length}`, {
      x: 12.0,
      y: 7.0,
      w: 1.0,
      h: 0.4,
      fontSize: 10,
      color: "999999",
      fontFace: FONTS.body,
      align: "right",
    });
  }

  await pptx.writeFile({ fileName: outputPath });
  console.log(`[pptx] Saved: ${outputPath}`);
}

/**
 * Layout: title + bullets on left, image on right.
 */
function addSlideWithImage(s, slide, imgPath) {
  // Accent bar
  s.addShape("rect", {
    x: 0,
    y: 0,
    w: 0.15,
    h: 7.5,
    fill: { color: COLORS.accent },
  });

  // Title
  s.addText(slide.title, {
    x: 0.6,
    y: 0.3,
    w: 6.8,
    h: 1.0,
    fontSize: 28,
    fontFace: FONTS.title,
    color: COLORS.title,
    bold: true,
    valign: "top",
  });

  // Bullets
  const bulletObjs = slide.bullets.map((b) => ({
    text: b,
    options: {
      fontSize: 16,
      fontFace: FONTS.body,
      color: COLORS.bullet,
      bullet: { code: "2022" },
      paraSpaceAfter: 8,
      lineSpacingMultiple: 1.2,
    },
  }));

  s.addText(bulletObjs, {
    x: 0.8,
    y: 1.5,
    w: 6.4,
    h: 5.2,
    valign: "top",
  });

  // Image on right
  s.addImage({
    path: imgPath,
    x: 7.8,
    y: 0.5,
    w: 5.0,
    h: 5.0,
    rounding: true,
  });
}

/**
 * Layout: title + bullets centered (no image).
 */
function addSlideWithoutImage(s, slide) {
  // Accent bar
  s.addShape("rect", {
    x: 0,
    y: 0,
    w: 0.15,
    h: 7.5,
    fill: { color: COLORS.accent },
  });

  // Title
  s.addText(slide.title, {
    x: 0.6,
    y: 0.3,
    w: 12.0,
    h: 1.0,
    fontSize: 32,
    fontFace: FONTS.title,
    color: COLORS.title,
    bold: true,
    valign: "top",
  });

  // Bullets
  const bulletObjs = slide.bullets.map((b) => ({
    text: b,
    options: {
      fontSize: 18,
      fontFace: FONTS.body,
      color: COLORS.bullet,
      bullet: { code: "2022" },
      paraSpaceAfter: 10,
      lineSpacingMultiple: 1.3,
    },
  }));

  s.addText(bulletObjs, {
    x: 0.8,
    y: 1.5,
    w: 11.5,
    h: 5.2,
    valign: "top",
  });
}

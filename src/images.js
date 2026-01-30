import fs from "node:fs";
import path from "node:path";

/**
 * Generate images for all slides using DALL·E.
 *
 * @param {import("openai").default} openai - OpenAI client instance
 * @param {Array<{title: string, bullets: string[], image_prompt: string}>} slides
 * @param {object} options
 * @param {string} options.outDir - Directory to save images
 * @param {string} [options.model] - DALL·E model (default: dall-e-3)
 * @param {"1024x1024"|"1792x1024"|"1024x1792"} [options.size] - Image size
 * @param {number} [options.maxRetries] - Max retries per image (default 2)
 * @returns {Promise<Array<string|null>>} Array of file paths (null if failed)
 */
export async function generateImages(openai, slides, options = {}) {
  const {
    outDir,
    model = process.env.DALLE_MODEL || "dall-e-3",
    size = "1024x1024",
    maxRetries = 2,
  } = options;

  const imagesDir = path.join(outDir, "images");
  fs.mkdirSync(imagesDir, { recursive: true });

  const results = [];

  for (let i = 0; i < slides.length; i++) {
    const slide = slides[i];
    const filename = `slide_${String(i + 1).padStart(2, "0")}.png`;
    const filepath = path.join(imagesDir, filename);

    console.log(
      `[images] (${i + 1}/${slides.length}) Generating: "${slide.image_prompt.slice(0, 60)}..."`
    );

    const imagePath = await generateSingleImage(openai, {
      prompt: slide.image_prompt,
      filepath,
      model,
      size,
      maxRetries,
    });

    results.push(imagePath);
  }

  return results;
}

/**
 * Generate a single image with retry logic.
 * Returns the file path on success, null on failure.
 */
async function generateSingleImage(openai, options) {
  const { prompt, filepath, model, size, maxRetries } = options;

  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await openai.images.generate({
        model,
        prompt,
        n: 1,
        size,
        response_format: "b64_json",
      });

      const b64 = response.data[0].b64_json;
      const buffer = Buffer.from(b64, "base64");
      fs.writeFileSync(filepath, buffer);

      console.log(`[images] Saved: ${filepath}`);
      return filepath;
    } catch (err) {
      lastError = err;
      console.error(
        `[images] Attempt ${attempt + 1}/${maxRetries + 1} failed: ${err.message}`
      );
      if (attempt < maxRetries) {
        await sleep(2000 * (attempt + 1));
      }
    }
  }

  console.error(
    `[images] Giving up on image: ${lastError.message}. Slide will have no image.`
  );
  return null;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

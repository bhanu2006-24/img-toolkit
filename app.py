import io
import time
import zipfile
from typing import List, Tuple

import streamlit as st
from rembg import remove
from PIL import Image, ImageColor, ImageFilter, ImageOps, ImageDraw

# ---------------- Page config ----------------
st.set_page_config(page_title="🪄 Background Remover", page_icon="✨", layout="wide")

# ---------------- Sidebar: controls ----------------
with st.sidebar:
    st.title("⚙️ Controls")
    st.markdown("Set global options for processing")

    # Input & output
    keep_size = st.checkbox("Keep original size", value=True)
    max_edge = st.slider("Max long edge (px)", 512, 3000, 1600)
    out_format = st.selectbox("Output format", ["PNG (transparent)", "JPG", "WEBP"], index=0)
    out_quality = st.slider("JPEG/WEBP quality", 60, 100, 90)

    st.markdown("---")

    # Background mode
    bg_mode = st.radio("Background mode", ["Transparent", "Solid color", "Custom image", "Blurred"], index=0)
    bg_color_hex = st.color_picker("Solid background color", "#FFFFFF")
    preview_bg_hex = st.color_picker("Preview background color", "#000000")

    st.markdown("---")

    # Styling
    add_shadow = st.checkbox("Add soft shadow", value=False)
    add_outline = st.checkbox("Add subject outline", value=False)
    outline_width = st.slider("Outline width (px)", 0, 20, 6)
    outline_color_hex = st.color_picker("Outline color", "#FFFFFF")
    circle_crop = st.checkbox("Circle crop (profile mode)", value=False)
    rounded_corners = st.checkbox("Rounded corners", value=False)
    corner_radius = st.slider("Corner radius (px)", 0, 200, 40)

    st.caption("Tip: High‑res inputs produce cleaner edges. Transparent output requires PNG.")

st.title("🪄 Background Remover")
st.markdown("Upload one or more images, remove backgrounds, replace or style them, and download individually or as a ZIP.")

# ---------------- Upload ----------------
uploads = st.file_uploader(
    "Upload images (PNG, JPG, JPEG, WEBP)",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True
)

# ---------------- Helpers ----------------
def load_image(file) -> Image.Image:
    return Image.open(file).convert("RGBA")

def to_rgb_tuple(hex_color: str) -> Tuple[int, int, int]:
    return ImageColor.getrgb(hex_color)

def resize_long_edge(img: Image.Image, target_max: int) -> Image.Image:
    w, h = img.size
    long_edge = max(w, h)
    if long_edge <= target_max:
        return img
    scale = target_max / long_edge
    new_size = (int(w * scale), int(h * scale))
    return img.resize(new_size, Image.LANCZOS)

def remove_bg(img: Image.Image) -> Image.Image:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    out_bytes = remove(buf.getvalue())
    return Image.open(io.BytesIO(out_bytes)).convert("RGBA")

def composite_on_solid(img_rgba: Image.Image, hex_color: str) -> Image.Image:
    rgb = to_rgb_tuple(hex_color)
    bg = Image.new("RGBA", img_rgba.size, rgb + (255,))
    bg.paste(img_rgba, (0, 0), img_rgba)
    return bg.convert("RGB")

def composite_on_image(img_rgba: Image.Image, bg_img: Image.Image) -> Image.Image:
    bg = bg_img.convert("RGBA").resize(img_rgba.size, Image.LANCZOS)
    canvas = Image.new("RGBA", img_rgba.size)
    canvas.paste(bg, (0, 0))
    canvas.paste(img_rgba, (0, 0), img_rgba)
    return canvas.convert("RGB")

def composite_on_blurred(img_rgba: Image.Image, original: Image.Image, blur_radius: int = 25) -> Image.Image:
    base = original.convert("RGBA")
    base = base.resize(img_rgba.size, Image.LANCZOS)
    blurred = base.filter(ImageFilter.GaussianBlur(blur_radius))
    blurred.paste(img_rgba, (0, 0), img_rgba)
    return blurred.convert("RGB")

def add_soft_shadow(img_rgba: Image.Image, spread: int = 30, offset: Tuple[int, int] = (0, 12), opacity: int = 120) -> Image.Image:
    # Create shadow from alpha
    alpha = img_rgba.getchannel("A")
    shadow = alpha.filter(ImageFilter.GaussianBlur(spread))
    shadow_img = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    shadow_img.putalpha(shadow.point(lambda p: min(255, int(p * opacity / 255))))

    canvas = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    # Paste shadow with offset
    canvas.paste(shadow_img, offset, shadow_img)
    canvas.paste(img_rgba, (0, 0), img_rgba)
    return canvas

def add_subject_outline(img_rgba: Image.Image, width: int, hex_color: str) -> Image.Image:
    if width <= 0:
        return img_rgba
    rgb = to_rgb_tuple(hex_color)
    alpha = img_rgba.getchannel("A")
    # Dilate alpha via blur and threshold
    expand = alpha.filter(ImageFilter.GaussianBlur(width)).point(lambda p: 255 if p > 0 else 0)
    outline = Image.new("RGBA", img_rgba.size, rgb + (0,))
    outline.putalpha(expand)
    canvas = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    canvas.paste(outline, (0, 0), outline)
    canvas.paste(img_rgba, (0, 0), img_rgba)
    return canvas

def apply_shape_mask(img_rgba: Image.Image, circle: bool, rounded: bool, radius: int) -> Image.Image:
    if not circle and not rounded:
        return img_rgba
    w, h = img_rgba.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    if circle:
        d = min(w, h)
        x0 = (w - d) // 2
        y0 = (h - d) // 2
        draw.ellipse([x0, y0, x0 + d, y0 + d], fill=255)
    elif rounded and radius > 0:
        draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    shaped = Image.new("RGBA", (w, h))
    shaped.paste(img_rgba, (0, 0), mask)
    return shaped

def preview_on_color(img_rgba: Image.Image, hex_color: str) -> Image.Image:
    rgb = to_rgb_tuple(hex_color)
    bg = Image.new("RGBA", img_rgba.size, rgb + (255,))
    bg.paste(img_rgba, (0, 0), img_rgba)
    return bg.convert("RGB")

def save_image_buffer(img: Image.Image, fmt: str, quality: int) -> io.BytesIO:
    buf = io.BytesIO()
    params = {}
    if fmt in ["JPEG", "WEBP"]:
        params["quality"] = quality
    if fmt == "WEBP":
        params["method"] = 6
    img.save(buf, format=fmt, **params)
    buf.seek(0)
    return buf

# ---------------- Main ----------------
if uploads:
    # Optional background image for "Custom image" mode
    custom_bg_file = None
    if bg_mode == "Custom image":
        st.warning("Upload a background image to use for replacement.")
        custom_bg_file = st.file_uploader("Upload background image", type=["png", "jpg", "jpeg", "webp"], key="bg_upload")

    col_left, col_right = st.columns([1, 1])

    processed_items = []  # List[Tuple[str, Image.Image, Image.Image]] (filename, original, output)

    with col_left:
        st.subheader("Queue")
        for i, f in enumerate(uploads, start=1):
            st.write(f"{i}. {getattr(f, 'name', 'image')}")
        st.caption(f"{len(uploads)} file(s) ready")

    with col_right:
        st.subheader("Process all")
        start = st.button("Run background removal for all")
        if start:
            t0 = time.time()
            with st.spinner("Processing images..."):
                bg_img_loaded = None
                if bg_mode == "Custom image" and custom_bg_file:
                    bg_img_loaded = load_image(custom_bg_file)

                for f in uploads:
                    original = load_image(f)

                    # Remove background
                    cutout = remove_bg(original)

                    # Resize if needed
                    if not keep_size:
                        cutout = resize_long_edge(cutout, max_edge)

                    # Optional styling
                    if add_outline:
                        cutout = add_subject_outline(cutout, outline_width, outline_color_hex)
                    if add_shadow:
                        cutout = add_soft_shadow(cutout)

                    # Optional shape mask
                    cutout = apply_shape_mask(cutout, circle_crop, rounded_corners, corner_radius)

                    # Compose according to mode
                    if bg_mode == "Transparent":
                        output = cutout
                    elif bg_mode == "Solid color":
                        output = composite_on_solid(cutout, bg_color_hex)
                    elif bg_mode == "Custom image" and bg_img_loaded is not None:
                        output = composite_on_image(cutout, bg_img_loaded)
                    elif bg_mode == "Blurred":
                        # Use original resized to match cutout
                        base_for_blur = original.resize(cutout.size, Image.LANCZOS)
                        output = composite_on_blurred(cutout, base_for_blur)
                    else:
                        output = cutout  # fallback

                    processed_items.append((getattr(f, "name", "image.png"), original, output))

            st.success(f"Done in {time.time() - t0:.2f}s")

    # ---------------- Preview gallery ----------------
    if processed_items:
        st.markdown("### Results")
        for name, original, output in processed_items:
            tabs = st.tabs([f"🖼️ {name}", "Original", "Transparent preview"])
            with tabs[0]:
                st.image(output, caption="Final output", use_container_width=True)
                # Download individual
                if out_format.startswith("PNG"):
                    fmt = "PNG"
                elif out_format == "JPG":
                    fmt = "JPEG"
                else:
                    fmt = "WEBP"
                buf = save_image_buffer(output, fmt, out_quality)
                dl_name = f"{name.rsplit('.', 1)[0]}_processed.{fmt.lower() if fmt!='JPEG' else 'jpg'}"
                st.download_button("⬇️ Download this image", buf, file_name=dl_name, mime=f"image/{'jpeg' if fmt=='JPEG' else fmt.lower()}")

            with tabs[1]:
                st.image(original, caption="Original", use_container_width=True)

            with tabs[2]:
                st.image(preview_on_color(output.convert("RGBA"), preview_bg_hex), caption=f"Preview over {preview_bg_hex}", use_container_width=True)

        # ---------------- ZIP export ----------------
        st.markdown("### 📦 Download all as ZIP")
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, _, output in processed_items:
                if out_format.startswith("PNG"):
                    fmt = "PNG"
                    ext = "png"
                    mime = "image/png"
                elif out_format == "JPG":
                    fmt = "JPEG"
                    ext = "jpg"
                    mime = "image/jpeg"
                else:
                    fmt = "WEBP"
                    ext = "webp"
                    mime = "image/webp"

                img_bytes = save_image_buffer(output, fmt, out_quality).getvalue()
                base = name.rsplit(".", 1)[0]
                zf.writestr(f"{base}_processed.{ext}", img_bytes)

        zip_buf.seek(0)
        st.download_button("⬇️ Download ZIP", zip_buf, file_name="processed_images.zip", mime="application/zip")

else:
    st.info("📂 Upload one or more images to begin.")


# ---------------- Footer ----------------
st.caption("Built with Streamlit + rembg • Supports PNG/JPG/JPEG/WEBP • Batch processing • Transparent, solid, custom or blurred backgrounds • Shadows, outlines, and shape masks")

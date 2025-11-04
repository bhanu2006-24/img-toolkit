# 🪄 Premium Background Remover

A Streamlit web app that removes image backgrounds using [rembg](https://github.com/danielgatis/rembg) (U²‑Net under the hood).  
Upload one or more images, remove their backgrounds, replace them with solid colors, custom images, or blurred versions, and download the results individually or as a ZIP.

---

## ✨ Features

- **Batch processing**: Upload multiple images at once and process them in one click.
- **Background options**:
  - Transparent (PNG with alpha channel)
  - Solid color (choose any hex color)
  - Custom background image
  - Blurred background (like Zoom/Teams)
- **Styling tools**:
  - Soft shadow
  - Subject outline with adjustable width and color
  - Circle crop (profile picture mode)
  - Rounded corners
- **Output control**:
  - Resize by max long edge
  - Choose output format: PNG, JPG, or WEBP
  - Adjustable quality for JPG/WEBP
- **Downloads**:
  - Individual image downloads
  - Bulk ZIP download of all processed images
- **Modern UI**:
  - Tabs for Original / Transparent / Final preview
  - Color pickers and sliders for customization

---

## 📦 Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/bhanu2006-24/bgremover
cd bg-remover

# Create a virtual environment (recommended)
conda create -n bgremover python=3.11
conda activate bgremover

# Install requirements
pip install -r requirements.txt
# bgremover

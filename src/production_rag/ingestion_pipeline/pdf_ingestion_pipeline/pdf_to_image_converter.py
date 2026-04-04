"""Convert PDF pages to images."""

import os
from pathlib import Path

from pdf2image import convert_from_path, pdfinfo_from_path


def pdf_to_images(pdf_path, output_folder="pdf_images", page_number=None, dpi=300):
    """
    Convert PDF pages to images.

    Args:
        pdf_path: Path to the PDF file.
        output_folder: Folder to save the images.
        page_number: Specific page number to convert (1-indexed). If None, converts all.
        dpi: Resolution of output images.

    Returns:
        list: Paths of saved image files.
    """
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    pdf_name = Path(pdf_path).stem

    # Skip conversion if all pages already exist
    existing = sorted(Path(output_folder).glob(f"{pdf_name}_page_*.png"))
    if existing:
        total_pages = pdfinfo_from_path(pdf_path)["Pages"]
        if len(existing) >= total_pages:
            print(f"Found all {len(existing)} images for {pdf_name}, skipping conversion.")
            return [str(p) for p in existing]
        else:
            print(f"Found {len(existing)}/{total_pages} images for {pdf_name}, resuming conversion...")

    saved_files = []

    try:
        if page_number is not None:
            print(f"Converting page {page_number}...")
            images = convert_from_path(
                pdf_path, dpi=dpi, first_page=page_number, last_page=page_number
            )

            output_path = os.path.join(output_folder, f"{pdf_name}_page_{page_number}.png")
            images[0].save(output_path, "PNG")
            saved_files.append(output_path)
            print(f"Saved: {output_path}")
        else:
            print("Converting all pages...")
            images = convert_from_path(pdf_path, dpi=dpi)

            for i, image in enumerate(images, start=1):
                output_path = os.path.join(output_folder, f"{pdf_name}_page_{i}.png")
                if os.path.exists(output_path):
                    saved_files.append(output_path)
                    continue
                image.save(output_path, "PNG")
                saved_files.append(output_path)
                print(f"Saved: {output_path}")

        print(f"\nTotal images saved: {len(saved_files)}")
        return saved_files

    except Exception as e:
        print(f"Error converting PDF: {e}")
        return []

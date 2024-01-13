import os
import fitz

# Directory containing the images and PDFs
directory = "files/illustrations/"  # Replace with the actual path


def convert_pdf_to_png(pdf_path, png_path):
    # Open the PDF file
    doc = fitz.open(pdf_path)

    # Convert the first page of the PDF to PNG
    page = doc.load_page(0)  # first page
    pix = page.get_pixmap()
    pix.save(png_path)

    doc.close()


def check_and_convert_pdfs(directory):
    # Gather all file names in the directory
    file_names = os.listdir(directory)

    # Split them into base names and extensions
    base_names = [os.path.splitext(file)[0] for file in file_names]
    extensions = [os.path.splitext(file)[1] for file in file_names]

    # Check for PDFs without corresponding PNG
    for base, ext in zip(base_names, extensions):
        if ext.lower() == ".pdf" and base + ".png" not in file_names:
            pdf_path = os.path.join(directory, base + ext)
            png_path = os.path.join(directory, base + "_converted.png")
            convert_pdf_to_png(pdf_path, png_path)
            print(f"Converted {pdf_path} to {png_path}")


# Convert all PDFs in the directory to PNGs when one doesnt exist yet
check_and_convert_pdfs(directory)


# Markdown file to be written
readme_path = "_pages/illustrations.md"

# GitHub base URL for the files
base_url = "https://raw.githubusercontent.com/mhostert/mhostert.github.io/main/files/illustrations/"

# Fixed width for the images (in pixels)
fixed_width = 400

HEADER = """---
layout: archive
title: "Illustrations"
permalink: /illustrations/
author_profile: true
---

This is a collection of illustrations from talks and papers.

"""

LIST_OF_IMAGES = os.listdir(directory)
LIST_OF_IMAGES.sort()

# Start writing to the markdown file
with open(readme_path, "w") as readme_file:
    readme_file.write(HEADER)
    for filename in LIST_OF_IMAGES:
        file_root = os.path.splitext(filename)[0]
        file_url = base_url + filename
        # Check if the file is an image
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
            readme_file.write(f"| [{file_root}]({file_url}) | ")
            candidate_pdf = (os.path.splitext(filename)[0] + ".pdf").replace(
                "_converted", ""
            )
            if os.path.exists(os.path.join(directory, candidate_pdf)):
                readme_file.write(f"[{file_root} (PDF)]({base_url + candidate_pdf}) |")
            readme_file.write("\n")
            if "_dark." in filename.lower():
                bkg_color = "black"
            else:
                bkg_color = "white"
            readme_file.write(
                f'\n<div style="background-color:{bkg_color}; width: {fixed_width}px">\n'
            )
            readme_file.write(
                f'\t<img src="{file_url}" width="{fixed_width}" alt="{filename}" style="display:block; margin:auto;">\n'
            )
            readme_file.write(f"</div>\n\n")
print(
    f"'readme.md' file has been successfully created with images and PDF links from '{directory}'."
)

import fitz  # PyMuPDF
from PIL import Image

def crop_pdf_page(pdf_path: str, page_number: int, crop_rect: tuple, zoom: int = 2) -> Image.Image:
    """
    Crop a specific region from a PDF page.
    
    Args:
        pdf_path (str): Path to the PDF file
        page_number (int): Page number (0-based index)
        crop_rect (tuple): Rectangle coordinates (x0, y0, x1, y1) in points
        zoom (int): Zoom factor for higher resolution (default: 2)
    
    Returns:
        PIL.Image.Image: The cropped image
    """
    # Open PDF
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)

    # Render the full page as a pixmap (image)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Convert to PIL Image
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Adjust rectangle coordinates for zoom
    x0, y0, x1, y1 = [int(coord * zoom) for coord in crop_rect]
    cropped_image = image.crop((x0, y0, x1, y1))

    return cropped_image

def save_cropped_image(image: Image.Image, output_path: str) -> None:
    """
    Save a cropped image to a file.
    
    Args:
        image (PIL.Image.Image): The image to save
        output_path (str): Path where to save the image
    """
    image.save(output_path)

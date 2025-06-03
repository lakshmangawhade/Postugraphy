from flask import Flask, request, send_file, render_template_string
import tempfile
from pathlib import Path
import logging

from src.crop_utils import crop_pdf_page, save_cropped_image
from src.extract_tables import setup_clients, process_image_ocr, convert_markdown_to_json, save_json
from src.doc_utils import create_doc_from_json, save_doc

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base and output directories
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
IMAGE_DIR = BASE_DIR / "image"

# Create necessary directories
OUTPUT_DIR.mkdir(exist_ok=True)
IMAGE_DIR.mkdir(exist_ok=True)

# HTML template
UPLOAD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Postugraphy Document Processor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .upload-form {
            border: 2px dashed #ccc;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }
        .upload-form:hover {
            border-color: #666;
        }
        .submit-btn {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 10px;
        }
        .submit-btn:hover {
            background-color: #45a049;
        }
        .progress {
            margin-top: 20px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            display: none;
        }
        .progress.active {
            display: block;
        }
    </style>
</head>
<body>
    <h1>Postugraphy Document Processor</h1>
    <div class="upload-form">
        <form action="/process-document" method="post" enctype="multipart/form-data" id="uploadForm">
            <h2>Upload PDF Document</h2>
            <input type="file" name="file" accept=".pdf" required>
            <br>
            <input type="submit" value="Process Document" class="submit-btn">
        </form>
        <div id="progress" class="progress">
            <h3>Processing Steps:</h3>
            <div id="steps"></div>
        </div>
    </div>
    <script>
        document.getElementById('uploadForm').onsubmit = function() {
            document.getElementById('progress').classList.add('active');
            document.getElementById('steps').innerHTML = '<p>Starting processing...</p>';
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(UPLOAD_TEMPLATE)

@app.route('/process-document', methods=['POST'])
def process_document():
    try:
        logger.info("Starting document processing...")
        
        if 'file' not in request.files:
            logger.error("No file uploaded")
            return 'No file uploaded', 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("No file selected")
            return 'No file selected', 400
        
        if not file.filename.lower().endswith('.pdf'):
            logger.error("Invalid file type")
            return 'Only PDF files are allowed', 400

        # Get base filename without extension
        base_filename = Path(file.filename).stem
        logger.info(f"Processing file: {file.filename}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            file.save(temp_pdf.name)
            pdf_path = temp_pdf.name
            logger.info("PDF file saved temporarily")

        # Step 1: Extract image from page 5
        logger.info("Step 1: Extracting image from page 5")
        page_number = 5  # 0-based indexing
        crop_rect = (0, 127, 700, 470)
        image_output_path = IMAGE_DIR / f"{base_filename}.png"

        cropped_image = crop_pdf_page(pdf_path, page_number, crop_rect)
        save_cropped_image(cropped_image, str(image_output_path))
        logger.info(f"Image saved to {image_output_path}")

        # Step 2: Process image to extract tables
        logger.info("Step 2: Processing tables from the image")
        mistral_client, groq_client = setup_clients()
        logger.info("OCR clients initialized")

        markdown_table = process_image_ocr(str(image_output_path), mistral_client)
        logger.info("OCR processing completed")

        json_data = convert_markdown_to_json(markdown_table, groq_client)
        logger.info("JSON conversion completed")

        json_output_path = OUTPUT_DIR / f"{base_filename}.json"
        save_json(json_data, str(json_output_path))
        logger.info(f"JSON saved to {json_output_path}")

        # Step 3: Generate Word document
        logger.info("Step 3: Generating Word document")
        doc = create_doc_from_json(json_data)
        doc_output_path = OUTPUT_DIR / f"{base_filename}.docx"
        save_doc(doc, str(doc_output_path))
        logger.info(f"Document saved to {doc_output_path}")

        # Clean up
        Path(pdf_path).unlink(missing_ok=True)
        logger.info("Temporary PDF file deleted")

        return send_file(
            str(doc_output_path),
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=f'{base_filename}.docx'
        )

    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        return str(e), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

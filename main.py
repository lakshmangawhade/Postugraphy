clude from flask import Flask, request, send_file, render_template_string, jsonify
import tempfile
from flask_cors import CORS
from pathlib import Path
import logging
import os
import json
import fitz  # PyMuPDF

from src.crop_utils import crop_pdf_page, save_cropped_image
from src.extract_tables import setup_clients, process_image_ocr, convert_markdown_to_json_with_multiple_models, save_json
from src.doc_utils import create_doc_from_json, save_doc
from src.uploadToS3 import upload_to_s3

app = Flask(__name__)
CORS(app, origins="*", send_wildcard=True, supports_credentials=False)

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
        document.getElementById('uploadForm').onsubmit = function(e) {
            e.preventDefault();
            document.getElementById('progress').classList.add('active');
            document.getElementById('steps').innerHTML = '<p>Starting processing...</p>';
            
            const formData = new FormData(this);
            
            fetch('/process-document', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('steps').innerHTML = '<p>✅ Processing completed successfully!</p>';
                    // Automatically trigger download
                    const downloadLink = document.createElement('a');
                    downloadLink.href = data.download_url;
                    downloadLink.download = data.filename;
                    document.body.appendChild(downloadLink);
                    downloadLink.click();
                    document.body.removeChild(downloadLink);
                    
                    // Show success message
                    setTimeout(() => {
                        document.getElementById('steps').innerHTML += '<p>📥 Download started automatically</p>';
                    }, 1000);
                } else {
                    document.getElementById('steps').innerHTML = '<p>❌ Error: ' + data.message + '</p>';
                }
            })
            .catch(error => {
                document.getElementById('steps').innerHTML = '<p>❌ Error: ' + error.message + '</p>';
            });
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(UPLOAD_TEMPLATE)

@app.route('/download/<filename>')
def download_file(filename):
    """Download a generated document"""
    try:
        file_path = OUTPUT_DIR / filename
        if not file_path.exists():
            logger.error(f"File not found: {filename}")
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
        
        logger.info(f"Serving download for: {filename}")
        return send_file(str(file_path), as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Error serving download: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Download failed'}), 500

@app.route('/process-document', methods=['POST'])
def process_document():
    # Define file paths outside the try block so they're available in all except blocks
    pdf_path = None
    image_output_path = None
    json_output_path = None
    doc_output_path = None
    
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

        # Step 1: Extract image from the last page
        logger.info("Step 1: Extracting image from the last page")
        
        # Get the last page number from the PDF
        doc = fitz.open(pdf_path)
        page_number = len(doc) - 1  # Get the last page (0-based indexing)
        doc.close()            
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
        logger.info(f"Generated markdown table:\n{markdown_table}")

        json_data = convert_markdown_to_json_with_multiple_models(markdown_table, groq_client)
        logger.info("JSON conversion completed")

        json_output_path = OUTPUT_DIR / f"{base_filename}.json"
        save_json(json_data, str(json_output_path))
        logger.info(f"JSON saved to {json_output_path}")

        # json_s3_url, unique_json_filename = upload_to_s3(str(json_output_path))

        # Step 3: Generate Word document
        logger.info("Step 3: Generating Word document")
        doc = create_doc_from_json(json_data)
        doc_output_path = OUTPUT_DIR / f"{base_filename}.docx"
        save_doc(doc, str(doc_output_path))
        logger.info(f"Document saved to {doc_output_path}")

        # Upload the generated document to S3
        logger.info("Uploading generated document to S3")
        doc_s3_url, unique_doc_filename = upload_to_s3(str(doc_output_path))
        logger.info(f"Document uploaded to S3: {doc_s3_url}")
        
        # Check if the document is empty (file size near zero)
        all_paragraphs = doc.paragraphs
        if len(all_paragraphs) < 1:  # Checking if doc is too small (likely empty)
            # Clean up files before returning error
            cleanup_files(pdf_path, image_output_path, json_output_path, doc_output_path)
            logger.error("Generated document is empty")
            return jsonify({
                'status': 'error',
                'message': 'Generated document is empty'
            }), 400

        # Clean up temporary files but keep the doc for download
        cleanup_files(pdf_path, image_output_path, json_output_path)
        logger.info("Temporary files deleted")

        # Step 4: Return S3 URL for download
        logger.info("Step 4: Returning S3 URL for download")

        return jsonify({
            'status': 'success',
            'download_url': doc_s3_url,
            'filename': unique_doc_filename,
            'message': 'Document generated successfully and uploaded to S3. Click to download.'
        })

    except Exception as e:
        # Clean up all files in case of any error
        cleanup_files(pdf_path, image_output_path, json_output_path, doc_output_path)
        logger.error(f"Error during processing: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': "This PDF can't be processed"
        }), 400

# Helper function to safely delete files
def cleanup_files(pdf_path=None, image_output_path=None, json_output_path=None, doc_output_path=None):
    """Safely delete temporary files"""
    try:
        if pdf_path:
            Path(pdf_path).unlink(missing_ok=True)
        if image_output_path:
            Path(image_output_path).unlink(missing_ok=True)
        if json_output_path:
            Path(json_output_path).unlink(missing_ok=True)
        if doc_output_path:
            Path(doc_output_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Error during file cleanup: {str(e)}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.getenv("PORT"), debug=True)

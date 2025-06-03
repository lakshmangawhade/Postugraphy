# Postugraphy Document Processor

A Flask-based web application that processes PDF documents to extract and analyze data from specific pages, generating structured outputs in various formats.

## Features

- PDF document upload and processing
- Image extraction from specific PDF pages
- OCR processing using Mistral AI
- JSON data conversion using Groq
- Word document generation with formatted results

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   MISTRAL_API_KEY=your_mistral_api_key
   GROQ_API_KEY=your_groq_api_key
   ```
4. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. Open your browser and navigate to `http://localhost:5000`
2. Upload a PDF document
3. The system will process the document and generate:
   - An extracted image (PNG)
   - JSON data file
   - Word document with formatted results

## Project Structure

- `main.py`: Main Flask application
- `src/`: Source code directory
  - `crop_utils.py`: PDF page cropping utilities
  - `extract_tables.py`: OCR and data extraction
  - `doc_utils.py`: Word document generation

## Requirements

- Python 3.8+
- Flask
- PyMuPDF
- Pillow
- python-docx
- Mistral AI API
- Groq API

## License

MIT License 
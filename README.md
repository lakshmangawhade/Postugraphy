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

## Word Document Generation Details

`src/doc_utils.py` is responsible for turning the structured JSON output into a nicely-formatted Microsoft Word document (`.docx`).  Below is an overview of how it works and what the key design decisions are.

1. **Loading JSON**  
   The helper `load_json(path)` wraps `json.load` and returns a Python dictionary ready for processing.

2. **Creating the document**  
   `create_doc_from_json(json_data)` is the main work-horse.  It:
   - Creates a blank `python-docx` `Document` and sets the default font to *Calibri 11 pt* for consistency.
   - Determines which *tests* are present by first looking at `"Test Type"` and falling back to `"Test Name"` keys in the JSON.
   - Iterates through each test and adds a level-2 heading in the form `Test X: Test Name (Test Type)`.

3. **Field ordering**  
   Clinical staff requested that the results appear in a strict, human-friendly order (not alphabetical).  Therefore a static `fields` list defines the display label and the JSON key to pull from.  The function respects this order verbatim.

4. **Bullet list output**  
   Each result is rendered as a *List Bullet* paragraph.  Arrays are expanded as
   `value[0] & value[1]` (when length == 2) or `value1, value2, …` for longer lists.

5. **Automatic flagging of reduced stability**  
   If the *Stability Class* string contains the word **"Reduced"** (case-insensitive) the script automatically appends the marker `→ FLAG` so that the reviewer's eye is drawn to possible balance issues.  After the latest update, this marker is rendered **in bold** while the preceding text keeps the normal weight, e.g.:

   > Stability Class: Mildly Reduced **→ FLAG**

6. **Saving the document**  
   `save_doc(doc, path)` ensures a `.docx` extension and persists the file.

### Running the utility stand-alone

Although the function is primarily called by the Flask app, you can run it directly:

```bash
python - <<'PY'
from src.doc_utils import load_json, create_doc_from_json, save_doc
json_data = load_json('sample.json')
doc = create_doc_from_json(json_data)
save_doc(doc, 'sample_output.docx')
PY
```

Replace `sample.json` with your own exported JSON file. 
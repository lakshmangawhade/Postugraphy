import json
from docx import Document
from docx.shared import Pt
import os
from typing import Dict, Any

def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from a file.
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        Dict[str, Any]: The loaded JSON data
    """
    with open(file_path, 'r') as f:
        return json.load(f)

def create_doc_from_json(json_data: Dict[str, Any]) -> Document:
    """
    Create a Word document from JSON data.
    
    Args:
        json_data (Dict[str, Any]): The JSON data to convert
        
    Returns:
        Document: The created Word document
    """
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(12)

    # Add main heading
   # heading = doc.add_heading("Postural Stability Score -", level=1)
   # heading.style.font.name = 'Calibri'
   # heading.style.font.size = Pt(14)

    # Get test keys from Test Type or Test Name
    test_keys = list(json_data.get("Test Type", {}).keys())
    if not test_keys:
        test_keys = list(json_data.get("Test Name", {}).keys())
    
    # If still no keys found, return empty document
    if not test_keys:
        print("Warning: No test data found in JSON")
        return doc

    # Process each test
    for test_key in test_keys:
        # Get test name and type
        test_name = json_data.get("Test Name", {}).get(test_key, test_key)
        test_type = json_data.get("Test Type", {}).get(test_key, "")
        
        # Create title in the format "Test X: Test Name (Test Type)"
        title = f"{test_key}: {test_name}"
        if test_type:
            title += f" ({test_type})"
        
        # Add title with custom formatting
        title_paragraph = doc.add_paragraph(title, style='Heading2')
        title_paragraph.style.font.name = 'Calibri'
        title_paragraph.style.font.size = Pt(14)
        

        # Define fields in the exact order required
        fields = [
            ("Stability Score", "Stability Score"),
            ("Stability Class", "Stability Class"),
            ("Pred. Direction of Sway", "Pred. Direction of Sway"),
            ("Fatigue Ratio", "Fatigue Ratio"),
            ("Adaptation Ratio", "Adaptation Ratio"),
            ("Directionality", "Directionality"),
            ("Sway Center [Xo, Yo]", "Sway Center [Xo, Yo]"),
            ("ML Sway (Max & 95%)", "ML Sway: Max & 95% Conf."),
            ("AP Sway (Max & 95%)", "AP Sway: Max & 95% Conf."),
            ("Actual Sway (Max & Ave)", "Actual Sway: Max & Ave"),
            ("Sway Velocity (Max & Ave)", "Sway Velocity: Max & Ave"),
            ("Sway Acceleration (Max & Ave)", "Sway Acceler.: Max & Ave"),
            ("Sway Path Length", "Sway Path Length"),
            ("Area 95% Conf. Ellipse", "Area 95% Conf. Ellipse"),
            ("LoS", "Max Theoretical Sway (LoS)"),
            ("Parameter p", "Parameter p")
        ]

        # Add each field in the specified order
        for display_name, json_key in fields:
            value = json_data.get(json_key, {}).get(test_key)
            if value is not None:
                if isinstance(value, list):
                    if len(value) == 2:
                        doc.add_paragraph(f"{display_name}: {value[0]} & {value[1]}", style='List Bullet')
                    else:
                        doc.add_paragraph(f"{display_name}: {', '.join(value)}", style='List Bullet')
                else:
                    if display_name == "Stability Class":
                        # Flag whenever the stability class text contains the word "Reduced" (case-insensitive)
                        if isinstance(value, str) and "reduced" in value.lower():
                            # Create a paragraph where only the arrow and FLAG are bold
                            paragraph = doc.add_paragraph(style='List Bullet')
                            paragraph.add_run(f"{display_name}: {value}")
                            flag_run = paragraph.add_run(" → FLAG")
                            flag_run.bold = True
                        else:
                            doc.add_paragraph(f"{display_name}: {value}", style='List Bullet')
                    else:
                        doc.add_paragraph(f"{display_name}: {value}", style='List Bullet')

        doc.add_paragraph("")  # Space between tests

    return doc

def save_doc(doc: Document, output_path: str) -> None:
    """
    Save a Word document to a file.
    
    Args:
        doc (Document): The document to save
        output_path (str): Path where to save the document
    """
    if not output_path.lower().endswith(".docx"):
        output_path += ".docx"
    doc.save(output_path)
   

#if __name__ == "__main__":
    # Use forward slashes or raw string for Windows paths
 #   input_path = "C:/Users/Lakshman/Downloads/AJ19760617_Posturography.T2.json"
  #  output_path = "output/AJ19760617_Posturography.T2.docx"

   # if not output_path.lower().endswith(".docx"):
    #    output_path += ".docx"

    #if os.path.exists(input_path):
     #   try:
      #      json_data = load_json(input_path)
       #     print(f"Loaded JSON data with keys: {list(json_data.keys())}")
        #    doc = create_doc_from_json(json_data)
         #   save_doc(doc, output_path)
          #  print(f"✅ Document saved successfully to {output_path}")
       # except Exception as e:
        #    print(f"❌ Error processing file: {str(e)}")
   # else:
    #    print(f"❌ Error: JSON file not found at {input_path}")

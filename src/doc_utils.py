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
    font.size = Pt(11)

    test_keys = json_data.get("Test Type", {}).keys()

    for test_key in test_keys:
        test_type = json_data["Test Type"].get(test_key, "Unknown")
        title = f"{test_key}: Perturbed Stability Eyes Closed ({test_type}):"
        doc.add_paragraph(title, style='Heading2')

        # Extract and write values from JSON
        doc.add_paragraph(f"Stability Score: {json_data.get('Stability Score', {}).get(test_key, 'N/A')}", style='List Bullet')
        doc.add_paragraph(f"Stability Class: {json_data.get('Stability Class', {}).get(test_key, 'N/A')} → FLAG", style='List Bullet')
        doc.add_paragraph(f"Predicted Direction of Sway: {json_data.get('Pred. Direction of Sway', {}).get(test_key, 'N/A')}", style='List Bullet')
        doc.add_paragraph(f"Fatigue Ratio: {json_data.get('Fatigue Ratio', {}).get(test_key, 'N/A')}", style='List Bullet')
        doc.add_paragraph(f"Adaptation Ratio: {json_data.get('Adaptation Ratio', {}).get(test_key, 'N/A')}", style='List Bullet')
        doc.add_paragraph(f"Directionality: {json_data.get('Directionality', {}).get(test_key, 'N/A')}", style='List Bullet')

        sway_center = json_data.get("Sway Center", {}).get(test_key, ["N/A", "N/A"])
        ml_sway = json_data.get("ML Sway: Max & 95% Conf.", {}).get(test_key, ["N/A", "N/A"])
        ap_sway = json_data.get("AP Sway: Max & 95% Conf.", {}).get(test_key, ["N/A", "N/A"])
        los = json_data.get("Max Theoretical Sway (LoS)", {}).get(test_key, "N/A")

        doc.add_paragraph(f"Sway Center [Xo, Yo]: [{sway_center[0]}, {sway_center[1]}]", style='List Bullet')
        doc.add_paragraph(f"ML Sway (Max & 95%): {ml_sway[0]} & {ml_sway[1]}", style='List Bullet')
        doc.add_paragraph(f"AP Sway (Max & 95%): {ap_sway[0]} & {ap_sway[1]}", style='List Bullet')

        # Optional fields
        optional_fields = [
            ("Actual Sway (Max & Ave)", "Actual Sway (Max & Ave)"),
            ("Sway Velocity (Max & Ave)", "Sway Velocity (Max & Ave)"),
            ("Sway Acceleration (Max & Ave)", "Sway Acceleration (Max & Ave)"),
            ("Sway Path Length", "Sway Path Length"),
            ("Area 95% Conf. Ellipse", "Area 95% Conf. Ellipse"),
            ("Parameter p", "Parameter p"),
        ]

        for label, key in optional_fields:
            value = json_data.get(key, {}).get(test_key)
            if value:
                doc.add_paragraph(f"{label}: {value}", style='List Bullet')

        doc.add_paragraph(f"LoS: {los}", style='List Bullet')
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
   # input_path = "output/table_output.json"
    #output_path = "output/test_report.docx"

    #if not output_path.lower().endswith(".docx"):
    #    output_path += ".docx"

    #if os.path.exists(input_path):
    #    json_data = load_json(input_path)
    #    doc = create_doc_from_json(json_data)
    #    save_doc(doc, output_path)
    #else:
    #    print("❌ Error: JSON file not found.")

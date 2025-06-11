import base64
from pathlib import Path
from mistralai import DocumentURLChunk, ImageURLChunk, Mistral
from groq import Groq
import json
import os
import dotenv
from typing import Dict, Any
import re


def setup_clients() -> tuple[Mistral, Groq]:
    """
    Set up and return Mistral and Groq API clients.
    
    Returns:
        tuple[Mistral, Groq]: Tuple containing Mistral and Groq clients
    """
    dotenv.load_dotenv()
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    if not mistral_api_key or not groq_api_key:
        raise ValueError("MISTRAL_API_KEY and GROQ_API_KEY must be set in .env file")
    
    mistral_client = Mistral(api_key=mistral_api_key)
    groq_client = Groq(api_key=groq_api_key)
    
    return mistral_client, groq_client

def process_image_ocr(image_path: str, mistral_client: Mistral) -> str:
    """
    Process an image using Mistral OCR.

    Args:
        image_path (str): Path to the image file
        mistral_client (Mistral): Mistral API client

    Returns:
        str: Markdown table extracted from the image

    Raises:
        FileNotFoundError: If the image file doesn't exist
        ValueError: If the OCR processing fails
    """
    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    try:
        encoded = base64.b64encode(image_path.read_bytes()).decode()
        base64_data_url = f"data:image/jpeg;base64,{encoded}"

        image_response = mistral_client.ocr.process(
            document=ImageURLChunk(image_url=base64_data_url),
            model="mistral-ocr-latest"
        )

        response_dict = json.loads(image_response.model_dump_json())
        return response_dict["pages"][0]["markdown"]
    except Exception as e:
        raise ValueError(f"OCR processing failed: {str(e)}")


def parse_markdown_table_manually(markdown_table: str) -> Dict[str, Any]:
    """
    Manually parse markdown table to ensure all data is captured correctly.
    
    Args:
        markdown_table (str): Markdown table to parse
        
    Returns:
        Dict[str, Any]: Parsed data as JSON structure
    """
    lines = markdown_table.strip().split('\n')
    
    # Find table lines (ignore empty lines and separator lines with |---|)
    table_lines = []
    for line in lines:
        line = line.strip()
        if line and '|' in line and not re.match(r'^\|[\s\-\|]+\|$', line):
            table_lines.append(line)
    
    if len(table_lines) < 2:
        raise ValueError("Invalid table format: not enough rows")
    
    # Parse header row
    header_line = table_lines[0]
    headers = [cell.strip() for cell in header_line.split('|') if cell.strip()]
    
    print(f"Parsed headers: {headers}")
    
    # Initialize result
    result = {
        "Test Type": {},
        "Test Name": {}
    }
    
    # Extract test names from headers
    for i, header in enumerate(headers[1:], 1):  # Skip first header "Test Name"
        if i <= 4:  # Only process first 4 test columns
            test_key = f"Test {i}"
            # Extract test name by removing "Test X " prefix
            test_name = header.replace(f"Test {i} ", "").strip()
            result["Test Name"][test_key] = test_name
            print(f"Extracted test name for {test_key}: {test_name}")
    
    # Process the rest of the table for other parameters
    for line in table_lines[1:]:
        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
        if not cells:
            continue
            
        param_name = cells[0].strip()
        print(f"Processing row with parameter: {param_name}")
        
        if param_name == "Test Type":
            print("Found Test Type row")
            for j, value in enumerate(cells[1:], 1):
                if j <= 4:  # Only take first 4 test values
                    test_key = f"Test {j}"
                    result["Test Type"][test_key] = value.strip()
                    print(f"Added Test Type for {test_key}: {value.strip()}")
        else:
            # Create test data structure for other parameters
            test_data = {}
            for j, value in enumerate(cells[1:], 1):
                if j <= 4:  # Only take first 4 test values
                    test_data[f"Test {j}"] = value.strip()
            
            # Ensure all 4 tests are present
            for test_num in range(1, 5):
                test_key = f"Test {test_num}"
                if test_key not in test_data:
                    test_data[test_key] = "N/A"
            
            result[param_name] = test_data
    
    # Print final result for debugging
    print("\nFinal parsed result:")
    print(json.dumps(result, indent=2))
    
    return result


def convert_markdown_to_json_with_multiple_models(markdown_table: str, groq_client: Groq) -> Dict[str, Any]:
    """
    Try multiple models and approaches to convert markdown to JSON.
    
    Args:
        markdown_table (str): Markdown table to convert
        groq_client (Groq): Groq API client
        
    Returns:
        Dict[str, Any]: Converted JSON data
    """
    
    # First, try manual parsing
    print("=" * 80)
    print("TRYING MANUAL PARSING FIRST...")
    print("=" * 80)
    
    try:
        manual_result = parse_markdown_table_manually(markdown_table)
        print("MANUAL PARSING SUCCESSFUL!")
        print("Manual parsing result:")
        print(json.dumps(manual_result, indent=2))
        return manual_result
    except Exception as e:
        print(f"Manual parsing failed: {e}")
        print("Falling back to LLM parsing...")
    
    # Models to try in order of preference
    models = [
        "llama-3.1-8b-instant"            # Alternative model
    ]
    
    prompt = (
        "You are a specialized AI for converting markdown tables to JSON. Your task is to convert the following markdown table into a structured JSON object.\n\n"
        "Important rules:\n"
        "1. Extract ALL data from the table, including headers and values\n"
        "2. Maintain the hierarchical structure of the data\n"
        "3. For test results, create nested objects with test numbers as keys\n"
        "4. For numerical values, keep them as strings to preserve units\n"
        "5. For coordinates or multiple values, use arrays\n"
        "6. Include ALL fields from the table, even if they seem empty\n"
        "7. Preserve the exact formatting of values\n"
        "8. IMPORTANT: Your response must ONLY contain valid JSON, with no additional text\n"
        "9. Ensure all object keys are properly quoted\n"
        "10. Do not include trailing commas in objects or arrays\n"
        "11. CRITICAL: Ensure ALL tests (Test 1 through Test 4) are included for each measurement\n"
        "12. If a test value is missing, use 'N/A' as the value\n"
        "13. Include ALL measurements like Stability Score, Sway Center, etc.\n"
        "14. CRITICAL: Ensure proper JSON syntax with colons between keys and values, and commas between key-value pairs\n"
        "15. CRITICAL: Do not include extra commas before property names\n"
        "16. CRITICAL: Ensure proper nesting of objects and arrays\n"
        "17. CRITICAL: Each test must have a proper key format: 'Test 1', 'Test 2', etc.\n\n"
        "Example structure:\n"
        "{\n"
        '  "Test Type": {\n'
        '    "Test 1": "value",\n'
        '    "Test 2": "value",\n'
        '    "Test 3": "value",\n'
        '    "Test 4": "value"\n'
        "  },\n"
        '  "Stability Score": {\n'
        '    "Test 1": "value",\n'
        '    "Test 2": "value",\n'
        '    "Test 3": "value",\n'
        '    "Test 4": "value"\n'
        "  },\n"
        '  "Sway Center": {\n'
        '    "Test 1": ["x", "y"],\n'
        '    "Test 2": ["x", "y"],\n'
        '    "Test 3": ["x", "y"],\n'
        '    "Test 4": ["x", "y"]\n'
        "  }\n"
        "}\n\n"
        f"Here is the markdown table to convert:\n{markdown_table}\n\n"
        "Convert this table into a complete JSON object following the structure above. Your response must ONLY contain the JSON object, with no additional text or explanation. Ensure all JSON syntax is valid, including proper comma usage and quoted keys."
    )

    for model in models:
        print(f"\n{'='*80}")
        print(f"TRYING MODEL: {model}")
        print(f"{'='*80}")
        
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise data parser. Convert the markdown table to JSON format. Include ALL tests (1-4) for each parameter. Output ONLY valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                model=model,
                temperature=0.0,  # Use 0 for most deterministic output
                max_tokens=4000
            )
            
            response_text = chat_completion.choices[0].message.content.strip()
            
            print(f"RAW RESPONSE FROM {model}:")
            print("-" * 50)
            print(response_text)
            print("-" * 50)
            
            # Try to parse the JSON
            try:
                # Clean the response
                json_text = response_text
                if "```json" in json_text:
                    json_text = json_text.split("```json")[1].split("```")[0]
                elif "```" in json_text:
                    json_text = json_text.split("```")[1].split("```")[0]
                
                json_data = json.loads(json_text.strip())
                
                # Validate that we have all tests
                missing_tests = []
                for param, tests in json_data.items():
                    if isinstance(tests, dict):
                        for i in range(1, 5):
                            if f"Test {i}" not in tests:
                                missing_tests.append(f"{param} - Test {i}")
                
                if missing_tests:
                    print(f"WARNING: Missing tests detected: {missing_tests}")
                    # Try to fill missing tests
                    for param, tests in json_data.items():
                        if isinstance(tests, dict):
                            for i in range(1, 5):
                                if f"Test {i}" not in tests:
                                    tests[f"Test {i}"] = "N/A"
                
                print(f"SUCCESS WITH {model}!")
                print("Final parsed JSON:")
                print(json.dumps(json_data, indent=2))
                return json_data
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed for {model}: {e}")
                continue
                
        except Exception as e:
            print(f"Error with model {model}: {e}")
            continue
    
    raise ValueError("All models failed to produce valid JSON")


def save_json(data: Dict[str, Any], output_path: str) -> None:
    """
    Save JSON data to a file.

    Args:
        data (Dict[str, Any]): JSON data to save
        output_path (str): Path where to save the JSON file

    Raises:
        IOError: If the file cannot be written
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise IOError(f"Failed to save JSON file: {str(e)}")


# Main execution
#if __name__ == "__main__":
#    try:
#        # Setup clients
#        mistral_client, groq_client = setup_clients()
        
        # Process image with OCR
#        markdown_table = process_image_ocr("image\AJ19760617_Posturography.T1 (1).png", mistral_client)
        
        # Print the markdown table from OCR        print("MARKDOWN TABLE FROM OCR:")
#        print("-" * 50)
#        print(markdown_table)
#        print("-" * 50)
#        print()
        
        # Convert to JSON with multiple model fallback
#        json_data = convert_markdown_to_json_with_multiple_models(markdown_table, groq_client)

        # Save the result
#        json_output_path = "output\Posturography.T1.docx"
#        save_json(json_data, json_output_path)
        
#        print(f"\n{'='*80}")
#        print(f"FINAL RESULT SAVED TO: {json_output_path}")
#        print(f"{'='*80}")
        
#    except Exception as e:
#        print(f"Error: {str(e)}")
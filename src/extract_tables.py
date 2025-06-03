import base64
from pathlib import Path
from mistralai import DocumentURLChunk, ImageURLChunk, Mistral
from groq import Groq
import json
import os
import dotenv
from typing import Dict, Any

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

def convert_markdown_to_json(markdown_table: str, groq_client: Groq) -> Dict[str, Any]:
    """
    Convert markdown table to JSON using Groq.
    
    Args:
        markdown_table (str): Markdown table to convert
        groq_client (Groq): Groq API client
        
    Returns:
        Dict[str, Any]: Converted JSON data
        
    Raises:
        ValueError: If the JSON conversion fails
    """
    prompt = (
        "You are a specialized AI for converting markdown tables to JSON. Your task is to convert the following markdown table into a structured JSON object.\n\n"
        "Important rules:\n"
        "1. Extract ALL data from the table, including headers and values\n"
        "2. Maintain the hierarchical structure of the data\n"
        "3. For test results, create nested objects with test numbers as keys\n"
        "4. For numerical values, keep them as strings to preserve units\n"
        "5. For coordinates or multiple values, use arrays\n"
        "6. Include ALL fields from the table, even if they seem empty\n"
        "7. Preserve the exact formatting of values\n\n"
        "Example structure:\n"
        "{\n"
        '  "Test Type": {\n'
        '    "Test 1": "value",\n'
        '    "Test 2": "value"\n'
        "  },\n"
        '  "Stability Score": {\n'
        '    "Test 1": "value",\n'
        '    "Test 2": "value"\n'
        "  },\n"
        '  "Sway Center": {\n'
        '    "Test 1": ["x", "y"],\n'
        '    "Test 2": ["x", "y"]\n'
        "  }\n"
        "}\n\n"
        f"Here is the markdown table to convert:\n{markdown_table}\n\n"
        "Convert this table into a complete JSON object following the structure above. Include ALL data from the table."
    )

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise JSON converter that extracts ALL data from tables and maintains their structure exactly."
                },
                {"role": "user", "content": prompt}
            ],
            model="llama3-70b-8192",
            temperature=0.1,
            max_tokens=4000
        )
        
        response_text = chat_completion.choices[0].message.content.strip()
        
        # Clean the response text
        response_text = response_text.replace('\n', ' ').replace('\r', '')
        
        # Try to find and parse JSON
        try:
            # First try direct JSON parsing
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # If that fails, try to extract JSON from the response
            import re
            # Look for content between curly braces, including nested ones
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text)
            if json_match:
                json_str = json_match.group(0)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    raise ValueError(f"Invalid JSON format: {str(e)}")
            else:
                raise ValueError("No valid JSON object found in the response")
            
    except Exception as e:
        raise ValueError(f"JSON conversion failed: {str(e)}")

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


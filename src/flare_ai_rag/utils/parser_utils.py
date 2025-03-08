import json
import re
from typing import Any

from flare_ai_rag.ai.base import ModelResponse


def parse_chat_response(response: dict) -> str:
    """Parse response from chat completion endpoint"""
    return response.get("choices", [])[0].get("message", {}).get("content", "")


def extract_author(model_id: str) -> tuple[str, str]:
    """
    Extract the author and slug from a model_id.

    :param model_id: The model ID string.
    :return: A tuple (author, slug).
    """
    author, slug = model_id.split("/", 1)
    return author, slug


def parse_chat_response_as_json(response: dict) -> dict[str, Any]:
    """Parse response from OpenRouter's chat completion endpoint"""
    json_data = parse_chat_response(response)
    return json.loads(json_data)


def parse_gemini_response_as_json(raw_response: ModelResponse) -> dict[str, Any]:
    """
    Extracts JSON content from a Gemini response.

    Args:
        raw_response (ModelResponse): The raw response from Gemini.

    Returns:
        dict: The parsed JSON content.
    """
    try:
        if not raw_response or not hasattr(raw_response, 'text') or not raw_response.text:
            return {"classification": "ANSWER"}  # Default fallback for empty responses

        text = raw_response.text.strip()
        
        # Try to find JSON in code blocks
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        json_str = match.group(1) if match else text
        
        # Clean up the string before parsing
        json_str = json_str.strip()
        
        # Handle potential JSON formatting issues
        if not json_str:
            return {"classification": "ANSWER"}
            
        return json.loads(json_str)
    except (json.JSONDecodeError, AttributeError, Exception) as e:
        import structlog
        logger = structlog.get_logger(__name__)
        logger.error(f"Failed to parse Gemini response: {e}")
        logger.debug(f"Raw response text: {raw_response.text if hasattr(raw_response, 'text') else 'None'}")
        return {"classification": "ANSWER"}  # Default fallback

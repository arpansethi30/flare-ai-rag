"""
Gemini AI Provider Module

This module implements the Gemini AI provider for the AI Agent API, integrating
with Google's Generative AI service. It handles chat sessions, content generation,
and message management while maintaining a consistent AI personality.
"""

from typing import Any, override

from google import genai
from google.genai import types
from google.genai import errors as genai_errors
import structlog

from flare_ai_rag.ai.base import BaseAIProvider, ModelResponse
from flare_ai_rag.utils.text_utils import calculate_text_size

logger = structlog.get_logger(__name__)

# Maximum size for Gemini API requests in bytes
MAX_CONTENT_SIZE = 8000  # Reduced from 10kb to ensure we stay under the limit

SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in helping users navigate
the Flare blockchain documentation.

When helping users:
- Prioritize security best practices
- Verify user understanding of important steps
- Format technical information (addresses, hashes, etc.) in easily readable ways

You maintain professionalism while allowing your subtle wit to make interactions
more engaging - your goal is to be helpful first, entertaining second.
"""


class GeminiProvider(BaseAIProvider):
    """
    Provider class for Google's Gemini AI service.

    This class implements the BaseAIProvider interface to provide AI capabilities
    through Google's Gemini models. It manages chat sessions, generates content,
    and maintains conversation history.

    Attributes:
        client (genai.Client): The Google GenAI client
        chat (genai.ChatSession | None): Active chat session
    """

    def __init__(self, api_key: str, model: str, **kwargs: str) -> None:
        """Initialize the Gemini provider."""
        self.client = genai.Client(api_key=api_key)
        # Strip the "models/" prefix if present since GenerativeModel doesn't expect it
        self.model_name = model.replace("models/", "")
        self.chat = None
        self.system_instruction = kwargs.get("system_instruction", SYSTEM_INSTRUCTION)
        self.api_key = api_key  # Required by the base class
        self.model_id = model  # Keep track of the original model ID
        self.chat_history = []  # Required by the base class
        self.initialization_error = None  # Track initialization errors

    @override
    def reset(self) -> None:
        """Reset the chat session."""
        self.chat = None
        self.chat_history = []
        self.initialization_error = None

    @override
    def reset_model(self, model: str, **kwargs: str) -> None:
        """Reset the model configuration."""
        # Strip the "models/" prefix if present since GenerativeModel doesn't expect it
        self.model_name = model.replace("models/", "")
        self.chat = None
        self.model_id = model
        self.system_instruction = kwargs.get("system_instruction", SYSTEM_INSTRUCTION)
        self.chat_history = []
        self.initialization_error = None

    @override
    def generate(
        self,
        prompt: str,
        response_mime_type: str | None = None,
        response_schema: Any | None = None,
    ) -> ModelResponse:
        """
        Generate content using the Gemini model.

        Args:
            prompt (str): The input prompt
            response_mime_type (str | None): Expected response MIME type
            response_schema (Any | None): Expected response schema

        Returns:
            ModelResponse: The generated response
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                ),
            )
            return ModelResponse(
                text=response.text,
                raw_response=response,
                metadata={
                    "model": self.model_id,
                    "prompt": prompt,
                }
            )
        except Exception as e:
            logger.exception("Error generating content", error=str(e))
            raise

    @override
    def send_message(
        self,
        msg: str,
    ) -> ModelResponse:
        """
        Send a message in the chat session.

        Args:
            msg (str): The message to send

        Returns:
            ModelResponse: The model's response
        """
        # Add the user message to chat history
        self.chat_history.append({"role": "user", "content": msg})
        
        # If we had a previous initialization error, return it for follow-up messages
        if self.initialization_error:
            error_text = f"Error: Chat session could not be initialized. {self.initialization_error}"
            self.chat_history.append({"role": "assistant", "content": error_text})
            return ModelResponse(
                text=error_text,
                raw_response=None,
                metadata={
                    "model": self.model_id,
                    "error": self.initialization_error,
                }
            )
        
        try:
            # Initialize chat session if needed
            if self.chat is None:
                try:
                    # Create a new chat session
                    self.chat = self.client.chats.create(model=self.model_name)
                    
                    # Set system instruction if provided
                    if self.system_instruction:
                        self.chat.send_message(self.system_instruction)
                except genai_errors.APIError as e:
                    logger.error(f"Failed to initialize chat session: {str(e)}")
                    self.initialization_error = str(e)
                    error_text = f"Error: Failed to initialize chat session. Please check your API key and model name. Details: {str(e)}"
                    # Add error response to chat history
                    self.chat_history.append({"role": "assistant", "content": error_text})
                    # Return a fallback response
                    return ModelResponse(
                        text=error_text,
                        raw_response=None,
                        metadata={
                            "model": self.model_id,
                            "error": str(e),
                        }
                    )

            # At this point, chat is initialized
            response = self.chat.send_message(msg)
            response_text = response.text
            
            # Add the assistant response to chat history
            self.chat_history.append({"role": "assistant", "content": response_text})
            
            return ModelResponse(
                text=response_text,
                raw_response=response,
                metadata={
                    "model": self.model_id,
                    "chat_history": self.chat_history,
                }
            )
                
        except Exception as e:
            logger.exception("Error sending message", error=str(e))
            error_text = f"Error: {str(e)}"
            # Add error response to chat history
            self.chat_history.append({"role": "assistant", "content": error_text})
            
            # Return a fallback response
            return ModelResponse(
                text=error_text,
                raw_response=None,
                metadata={
                    "model": self.model_id,
                    "error": str(e),
                }
            )


class GeminiEmbedding:
    """Client for generating embeddings using Gemini models."""

    def __init__(self, api_key: str) -> None:
        """Initialize the embedding client."""
        self.client = genai.Client(api_key=api_key)

    def embed_content(
        self,
        embedding_model: str,
        contents: str,
        task_type: Any,
        title: str | None = None,
    ) -> list[float]:
        """
        Generate embeddings for the given content.

        Args:
            embedding_model (str): The embedding model to use
            contents (str): The content to embed
            task_type (Any): The type of embedding task
            title (str | None): Optional title for the content

        Returns:
            list[float]: The generated embedding vector
        """
        # Check content size
        content_size = calculate_text_size(contents)
        if content_size > MAX_CONTENT_SIZE:
            raise ValueError(f"Content size ({content_size} bytes) exceeds maximum allowed size ({MAX_CONTENT_SIZE} bytes)")
            
        try:
            # Use the model name as provided (with 'models/' prefix)
            # Gemini embed_content expects the full model path
            embedding_result = self.client.models.embed_content(
                model=embedding_model,
                contents=contents,
                config=types.EmbedContentConfig(
                    task_type=str(task_type.name) if hasattr(task_type, 'name') else str(task_type),
                    title=title,
                ),
            )
            
            # Get the embedding from the result
            # Extract the values from the embeddings object
            if hasattr(embedding_result, 'embeddings') and embedding_result.embeddings:
                # If embeddings is a list, get the first item's values
                if embedding_result.embeddings and hasattr(embedding_result.embeddings[0], 'values'):
                    return embedding_result.embeddings[0].values
                # If it has a values attribute directly
                elif hasattr(embedding_result.embeddings, 'values'):
                    return embedding_result.embeddings.values
            
            # Fallback
            raise ValueError("Could not extract embedding values from response")
        except Exception as e:
            logger.exception("Error generating embedding", error=str(e))
            raise

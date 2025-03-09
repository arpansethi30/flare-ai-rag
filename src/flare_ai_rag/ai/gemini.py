"""
Gemini AI Provider Module

This module implements the Gemini AI provider for the AI Agent API, integrating
with Google's Generative AI service. It handles chat sessions, content generation,
and message management while maintaining a consistent AI personality.
"""

from typing import Any, override
import random
import time
import logging

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
            # Update prompt to explicitly instruct against templates
            safe_prompt = prompt + "\n\nIMPORTANT: Do not use template placeholders like {response} or {query} in your answer. Write a direct, fully-formed response instead."
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=safe_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                ),
            )
            
            response_text = response.text
            
            # Post-process to handle template issues
            if "{response}" in response_text or "{query}" in response_text:
                logger.warning("Template placeholders found in response, replacing with error message")
                response_text = "I don't have enough information to provide a complete answer. Please try asking a more specific question about Flare."
            
            return ModelResponse(
                text=response_text,
                raw_response=response,
                metadata={
                    "model": self.model_id,
                    "prompt": safe_prompt,
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
        embedding_model: str = "models/text-embedding-004", 
        contents: str = "", 
        task_type = None,
        content: str = None,
        title: str = None,
        max_retries: int = 5, 
        initial_delay: float = 1.0
    ) -> list[float]:
        """
        Generate embeddings for content using Gemini API with rate limit handling.
        
        This method supports both the template's parameter style and the original style.
        
        Args:
            embedding_model (str): Model to use for embedding
            contents (str): Content to embed (from template style)
            task_type: Type of task (document or query embedding)
            content (str): Content to embed (from original style)
            title (str): Optional title for the content
            max_retries (int): Maximum number of retries for rate limit errors
            initial_delay (float): Initial delay in seconds before retrying
            
        Returns:
            list[float]: Embedding vector
        """
        # Handle different parameter styles
        final_content = contents
        if not final_content and content is not None:
            final_content = content
            
        # Add title if provided and we have content
        if title is not None and final_content:
            if not final_content.startswith(title):
                final_content = f"{title}\n\n{final_content}"
            
        # Make sure we have content to embed
        if not final_content:
            raise ValueError("No content provided for embedding")
            
        # Extract model name (handle both formats)
        model_name = embedding_model
        if model_name.startswith("models/"):
            model_name = model_name.split("/")[1]
            
        delay = initial_delay
        attempt = 0
        
        while attempt < max_retries:
            try:
                # The correct way to use the Gemini API for embeddings
                result = self.client.models.embed_content(
                    model=model_name,
                    contents=final_content,
                )
                return result.embeddings[0].values
                
            except genai_errors.ResourceExhaustedError as e:
                if attempt < max_retries - 1:
                    # Use exponential backoff with jitter
                    jitter = random.uniform(0, 0.1 * delay)
                    sleep_time = delay + jitter
                    logger.warning(f"Rate limit hit, retrying in {sleep_time:.1f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(sleep_time)
                    delay *= 2  # Exponential backoff
                    attempt += 1
                else:
                    # Re-raise after max retries
                    logger.error(f"Embedding generation failed after {max_retries} attempts: {str(e)}")
                    raise
            except Exception as e:
                # Log other errors and re-raise
                logger.error(f"Error generating embedding: {str(e)}")
                raise
                
        raise Exception(f"Failed to generate embedding after {max_retries} attempts due to rate limits")

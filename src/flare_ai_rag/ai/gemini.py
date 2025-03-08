"""
Gemini AI Provider Module

This module implements the Gemini AI provider for the AI Agent API, integrating
with Google's Generative AI service. It handles chat sessions, content generation,
and message management while maintaining a consistent AI personality.
"""

from typing import Any, override

import google.generativeai as genai
import structlog
from google.generativeai.embedding import (
    EmbeddingTaskType,
)
from google.generativeai.embedding import (
    embed_content as _embed_content,
)
from google.generativeai.generative_models import ChatSession, GenerativeModel
from google.generativeai.types import GenerationConfig

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
        chat (generativeai.ChatSession | None): Active chat session
    """

    def __init__(self, api_key: str, model: str, **kwargs: str) -> None:
        """Initialize the Gemini provider."""
        genai.configure(api_key=api_key)
        # Strip the "models/" prefix if present since GenerativeModel doesn't expect it
        model_name = model.replace("models/", "")
        self.model = genai.GenerativeModel(model_name)
        self.chat = None
        self.system_instruction = kwargs.get("system_instruction", SYSTEM_INSTRUCTION)
        self.api_key = api_key  # Required by the base class
        self.model_id = model  # Keep track of the original model ID
        self.chat_history = []  # Required by the base class

    @override
    def reset(self) -> None:
        """Reset the chat session."""
        self.chat = None
        self.chat_history = []

    @override
    def reset_model(self, model: str, **kwargs: str) -> None:
        """Reset the model configuration."""
        # Strip the "models/" prefix if present since GenerativeModel doesn't expect it
        model_name = model.replace("models/", "")
        self.model = genai.GenerativeModel(model_name)
        self.chat = None
        self.model_id = model
        self.system_instruction = kwargs.get("system_instruction", SYSTEM_INSTRUCTION)
        self.chat_history = []

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
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
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
        try:
            if self.chat is None:
                self.chat = self.model.start_chat(history=[])
                if self.system_instruction:
                    self.chat.send_message(self.system_instruction)

            response = self.chat.send_message(msg)
            
            # Update chat history
            self.chat_history.append({"role": "user", "content": msg})
            self.chat_history.append({"role": "assistant", "content": response.text})
            
            return ModelResponse(
                text=response.text,
                raw_response=response,
                metadata={
                    "model": self.model_id,
                    "chat_history": self.chat_history,
                }
            )
        except Exception as e:
            logger.exception("Error sending message", error=str(e))
            raise


class GeminiEmbedding:
    """Client for generating embeddings using Gemini models."""

    def __init__(self, api_key: str) -> None:
        """Initialize the embedding client."""
        genai.configure(api_key=api_key)

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
            response = genai.embed_content(
                model=embedding_model,
                content=contents,
                task_type=task_type,
                title=title,
            )
            
            # Verify that we have an embedding in the response
            if "embedding" not in response:
                raise ValueError("Response does not contain an embedding")
                
            return response["embedding"]
        except Exception as e:
            logger.exception("Error generating embedding", error=str(e))
            raise

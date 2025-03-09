"""
Responder module.

This module contains the responder implementation.
"""

import structlog
from typing import Any, override

from flare_ai_rag.ai import BaseAIProvider, ModelResponse
from flare_ai_rag.prompts import PromptService
from flare_ai_rag.responder.base import BaseResponder
from flare_ai_rag.responder.config import ResponderConfig
from flare_ai_rag.responder.prompts import (
    RESPONDER_SYSTEM_PROMPT,
    RESPONDER_NO_CONTEXT_PROMPT,
    RESPONDER_ATTESTATION_PROMPT,
)

logger = structlog.get_logger(__name__)


class GeminiResponder(BaseResponder):
    """
    Gemini-based responder.
    
    This class uses the Gemini API to generate responses.
    """
    
    def __init__(
        self,
        client: BaseAIProvider,
        responder_config: ResponderConfig,
    ) -> None:
        """
        Initialize the responder.
        
        Args:
            client: AI provider client
            responder_config: Responder configuration
        """
        self.client = client
        self.config = responder_config
        
    @override
    async def generate_response(
        self,
        query: str,
        context: list[dict[str, Any]],
        prompt_service: PromptService,
    ) -> str:
        """
        Generate a response to the query using the provided context.
        
        Args:
            query: User query
            context: Retrieved context documents
            prompt_service: Prompt service
            
        Returns:
            Generated response
        """
        # Try using a direct answer approach first
        try:
            return await self.generate_direct_answer(query)
        except Exception as e:
            logger.warning(f"Direct answer generation failed: {str(e)}")
            # Fall back to standard approach
        
        # If no context is provided, use the no-context prompt
        if not context:
            logger.warning("No context provided for query", query=query)
            # Generate response with no context
            prompt, _, _ = prompt_service.get_formatted_prompt(
                "RESPONDER_NO_CONTEXT_PROMPT",
                query=query,
            )
            
            # Add an extra instruction to prevent template issues
            prompt = prompt + "\n\nIMPORTANT: Give a direct answer about Flare. Do not return template placeholders or format strings like '{response}' or '{query}'."
            
            response = self.client.generate(prompt)
            response_text = response.text
            
            # Check for placeholder template issues
            if "{response}" in response_text or "{query}" in response_text:
                return f"I apologize, but I couldn't find specific information about '{query}' in my knowledge base. Please try asking a different question about Flare."
            
            return response_text
        
        # Add debug logging for context
        for i, doc in enumerate(context):
            logger.debug(f"Context document {i+1}:", content=doc.get("content", "")[:100], score=doc.get("score", 0))
        
        # Format context for the prompt
        formatted_context = self._format_context(context)
        logger.debug("Formatted context sample", context_sample=formatted_context[:500])
        
        # Generate response
        prompt, _, _ = prompt_service.get_formatted_prompt(
            "RESPONDER_SYSTEM_PROMPT",
            context=formatted_context,
            query=query,
        )
        
        # Add an extra instruction to prevent template issues
        prompt = prompt + "\n\nIMPORTANT: Give a direct answer about Flare. Do not return template placeholders like '{response}' or '{query}'. Provide a final, formatted answer."
        
        logger.debug("Generated prompt sample", prompt_sample=prompt[:500])
        
        response = self.client.generate(prompt)
        response_text = response.text
        logger.debug("Generated response", response=response_text)
        
        # Check for placeholder template issues
        if "{response}" in response_text or "{query}" in response_text:
            logger.warning("Placeholder template issue detected in response", query=query)
            return f"I apologize, but I couldn't find specific information about '{query}' in my knowledge base. Please try asking a different question about Flare."
        
        return response_text
    
    def _format_context(self, context: list[dict[str, Any]]) -> str:
        """
        Format context for the prompt.
        
        Args:
            context: Retrieved context documents
            
        Returns:
            Formatted context string
        """
        formatted_docs = []
        
        for i, doc in enumerate(context, start=1):
            # Extract document content - use 'content' key which is what RetrieverComponent.search returns
            content = doc.get("content", "")
            
            # Clean the content to remove import statements and other noise
            if content.startswith("import "):
                # Try to find the actual content after the imports
                parts = content.split(";.")
                if len(parts) > 1:
                    content = parts[1].strip()
                    
            # Remove any remaining import statements
            content = "\n".join([line for line in content.split("\n") if not line.strip().startswith("import ")])
            
            # Skip empty content
            if not content.strip():
                continue
                
            # Extract metadata
            metadata = {}
            for key, value in doc.items():
                if key != "content" and key != "score":
                    metadata[key] = value
            
            # Format document with metadata
            doc_header = f"[Doc{i}]"
            
            # Add source information if available
            if "file_name" in metadata:
                doc_header += f" Source: {metadata['file_name']}"
            
            # Add URL if available
            if "url" in metadata:
                doc_header += f" [Link: {metadata['url']}]"
            
            # Format the document
            formatted_doc = f"{doc_header}\n{content}\n"
            
            formatted_docs.append(formatted_doc)
        
        # Join all documents
        return "\n\n".join(formatted_docs)
    
    @override
    async def generate_attestation_response(
        self,
        query: str,
        prompt_service: PromptService,
    ) -> str:
        """
        Generate a response for a query that requires attestation.
        
        Args:
            query: User query
            prompt_service: Prompt service
            
        Returns:
            Generated response
        """
        prompt, _, _ = prompt_service.get_formatted_prompt(
            "RESPONDER_ATTESTATION_PROMPT",
            query=query,
        )
        
        # Add an extra instruction to prevent template issues
        prompt = prompt + "\n\nIMPORTANT: Give a direct answer. Do not return template placeholders like '{response}' or '{query}'."
        
        response = self.client.generate(prompt)
        response_text = response.text
        
        # Check for placeholder template issues
        if "{response}" in response_text or "{query}" in response_text:
            return "I apologize, but I couldn't generate a proper response for your attestation request. Please try again."
        
        return response_text

    async def generate_direct_answer(self, query: str) -> str:
        """
        Generate a direct answer to the query using a simplified approach.
        
        Args:
            query: User query
            
        Returns:
            Direct answer
        """
        from flare_ai_rag.prompts.templates import DIRECT_ANSWER_PROMPT
        
        # Format the prompt
        prompt = DIRECT_ANSWER_PROMPT.format(query=query)
        
        # Generate response
        response = self.client.generate(prompt)
        response_text = response.text
        
        # Check for placeholder template issues
        if "{response}" in response_text or "{query}" in response_text:
            return f"I apologize, but I couldn't find specific information about '{query}'. Please try asking a different question about Flare."
        
        return response_text

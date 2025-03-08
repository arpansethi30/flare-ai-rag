from typing import Any, override

from flare_ai_rag.ai import GeminiProvider, OpenRouterClient
from flare_ai_rag.responder import BaseResponder, ResponderConfig
from flare_ai_rag.utils import parse_chat_response


class GeminiResponder(BaseResponder):
    def __init__(
        self, client: GeminiProvider, responder_config: ResponderConfig
    ) -> None:
        """
        Initialize the responder with a GeminiProvider.

        :param client: An instance of OpenRouterClient.
        :param model: The model identifier to be used by the API.
        """
        self.client = client
        self.responder_config = responder_config

    @override
    def generate_response(self, query: str, retrieved_documents: list[dict]) -> str:
        """
        Generate a final answer using the query and the retrieved context.

        :param query: The input query.
        :param retrieved_documents: A list of dictionaries containing retrieved docs.
        :return: The generated answer as a string.
        """
        context = "List of retrieved documents:\n"

        # Build enhanced context from the retrieved documents with better source information
        for idx, doc in enumerate(retrieved_documents, start=1):
            # Extract all available metadata for better source attribution
            metadata = doc.get("metadata", {})
            identifier = metadata.get("filename", f"Doc{idx}")
            url = metadata.get("url", "")
            title = metadata.get("title", "")
            author = metadata.get("author", "")
            date = metadata.get("date", "")
            
            # Create a structured source reference
            source_info = f"Document {idx} [Source: {identifier}]"
            if title:
                source_info += f" - {title}"
            if author:
                source_info += f" by {author}"
            if date:
                source_info += f" ({date})"
            if url:
                source_info += f" URL: {url}"
                
            context += f"{source_info}:\n{doc.get('text', '')}\n\n"

        # Add citation instructions to the prompt
        citation_instructions = """
When answering, please cite your sources using the document numbers provided (e.g., [Doc1], [Doc2]).
Each claim or piece of information should be attributed to its specific source.
If information comes from multiple sources, cite all relevant documents.
If you're unsure about any information or it's not in the provided documents, clearly state this.
"""

        # Compose the enhanced prompt with citation instructions
        prompt = (
            context + 
            citation_instructions + 
            f"\nUser query: {query}\n" + 
            self.responder_config.query_prompt
        )

        # Use the generate method of GeminiProvider to obtain a response.
        response = self.client.generate(
            prompt,
            response_mime_type=None,
            response_schema=None,
        )

        return response.text


class OpenRouterResponder(BaseResponder):
    def __init__(
        self, client: OpenRouterClient, responder_config: ResponderConfig
    ) -> None:
        """
        Initialize the responder with an OpenRouter client and the model to use.

        :param client: An instance of OpenRouterClient.
        :param model: The model identifier to be used by the API.
        """
        self.client = client
        self.responder_config = responder_config

    @override
    def generate_response(self, query: str, retrieved_documents: list[dict]) -> str:
        """
        Generate a final answer using the query and the retrieved context,
        and include citations.

        :param query: The input query.
        :param retrieved_documents: A list of dictionaries containing retrieved docs.
        :return: The generated answer as a string.
        """
        context = "List of retrieved documents:\n"

        # Build enhanced context from the retrieved documents with better source information
        for idx, doc in enumerate(retrieved_documents, start=1):
            # Extract all available metadata for better source attribution
            metadata = doc.get("metadata", {})
            identifier = metadata.get("filename", f"Doc{idx}")
            url = metadata.get("url", "")
            title = metadata.get("title", "")
            author = metadata.get("author", "")
            date = metadata.get("date", "")
            
            # Create a structured source reference
            source_info = f"Document {idx} [Source: {identifier}]"
            if title:
                source_info += f" - {title}"
            if author:
                source_info += f" by {author}"
            if date:
                source_info += f" ({date})"
            if url:
                source_info += f" URL: {url}"
                
            context += f"{source_info}:\n{doc.get('text', '')}\n\n"

        # Add citation instructions to the prompt
        citation_instructions = """
When answering, please cite your sources using the document numbers provided (e.g., [Doc1], [Doc2]).
Each claim or piece of information should be attributed to its specific source.
If information comes from multiple sources, cite all relevant documents.
If you're unsure about any information or it's not in the provided documents, clearly state this.
"""

        # Compose the enhanced prompt with citation instructions
        prompt = (
            context + 
            citation_instructions + 
            f"\nUser query: {query}\n" + 
            self.responder_config.query_prompt
        )
        
        # Prepare the payload for the completion endpoint.
        payload: dict[str, Any] = {
            "model": self.responder_config.model.model_id,
            "messages": [
                {"role": "system", "content": self.responder_config.system_prompt},
                {"role": "user", "content": prompt},
            ],
        }

        if self.responder_config.model.max_tokens is not None:
            payload["max_tokens"] = self.responder_config.model.max_tokens
        if self.responder_config.model.temperature is not None:
            payload["temperature"] = self.responder_config.model.temperature

        # Send the prompt to the OpenRouter API.
        response = self.client.send_chat_completion(payload)

        return parse_chat_response(response)

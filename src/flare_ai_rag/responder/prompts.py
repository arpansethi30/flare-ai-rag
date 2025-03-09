"""
Prompts for the responder module.

This module contains prompts for the responder module.
"""

# Import directly from templates.py to avoid circular imports
from flare_ai_rag.prompts.templates import (
    PromptTemplate,
    RESPONDER_SYSTEM_PROMPT_TEMPLATE,
    RESPONDER_NO_CONTEXT_PROMPT_TEMPLATE,
    RESPONDER_ATTESTATION_PROMPT_TEMPLATE,
    RESPONDER_INSTRUCTION,
    RESPONDER_PROMPT
)

# System prompt for the responder
RESPONDER_SYSTEM_PROMPT = PromptTemplate(RESPONDER_SYSTEM_PROMPT_TEMPLATE)

# System prompt for the responder with no context
RESPONDER_NO_CONTEXT_PROMPT = PromptTemplate(RESPONDER_NO_CONTEXT_PROMPT_TEMPLATE)

# System prompt for the responder with attestation
RESPONDER_ATTESTATION_PROMPT = PromptTemplate(RESPONDER_ATTESTATION_PROMPT_TEMPLATE)

# Re-export the constants to avoid circular imports
INSTRUCTION = RESPONDER_INSTRUCTION
PROMPT = RESPONDER_PROMPT

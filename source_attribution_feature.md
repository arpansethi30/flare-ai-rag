# Source Attribution Feature

## Overview

The source attribution feature enhances the RAG system's responses by clearly citing the sources of information used to generate answers. This improves transparency, verifiability, and trustworthiness of the system's outputs.

## Implementation Details

We've enhanced the responder components to better handle source attribution:

1. **Enhanced Context Formatting**:
   - Added structured source references including document title, author, date, and URL
   - Formatted document references consistently as "Document X [Source: filename]"
   - Included all available metadata to provide comprehensive source information

2. **Explicit Citation Instructions**:
   - Added clear instructions to the LLM to cite sources using document numbers
   - Required attribution for each claim or piece of information
   - Instructed the LLM to acknowledge when information is not in the provided documents

3. **Improved System Prompts**:
   - Updated the RESPONDER_INSTRUCTION to emphasize the importance of citations
   - Modified the RESPONDER_PROMPT to explicitly request citations
   - Added formatting guidelines for distinguishing between different sources

## Code Changes

The feature was implemented by modifying:

1. `src/flare_ai_rag/responder/responder.py`:
   - Enhanced both `GeminiResponder` and `OpenRouterResponder` classes
   - Improved context building with better source information
   - Added citation instructions to the prompt

2. `src/flare_ai_rag/responder/prompts.py`:
   - Updated system instructions to emphasize citation requirements
   - Modified query prompt to explicitly request citations

## Example Output

The feature produces responses like:

```
Flare Network is a blockchain designed to provide data to smart contracts safely and securely [Doc1]. It features the Flare Time Series Oracle (FTSO), which provides decentralized price feeds for various cryptocurrencies [Doc2].

The FTSO is a key component of the Flare ecosystem, enabling reliable price data to be used by applications built on the network [Doc2].

Sources:
[Doc1] Introduction to Flare by Flare Team (2023-01-15)
[Doc2] Flare Time Series Oracle by Flare Labs (2023-02-20)
```

## Benefits

1. **Improved Verifiability**: Users can trace information back to its source
2. **Enhanced Transparency**: Clear attribution shows where information comes from
3. **Better Trust**: Users can verify the reliability of sources
4. **Reduced Hallucinations**: Explicit citation requirements discourage the LLM from making up information

## Testing

The feature can be tested using the `test_source_attribution_mock.py` script, which demonstrates:
- How source information is formatted
- What citation instructions are provided to the LLM
- What a properly cited response looks like

## Future Enhancements

Potential improvements to the source attribution feature:
1. Add hyperlinks to sources in web-based interfaces
2. Implement confidence scores for retrieved documents
3. Add the ability to filter sources by credibility or relevance
4. Enhance citation formatting with page numbers or section references when available 
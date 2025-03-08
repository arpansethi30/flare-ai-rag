#!/usr/bin/env python
"""
Test script to verify if the Gemini API can properly route queries
similar to how your application does it.
"""

import os
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai

def clean_json_response(text):
    """Clean and extract JSON from response text."""
    try:
        # Try to find JSON in code blocks
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        json_str = match.group(1) if match else text
        
        # Clean up the string before parsing
        json_str = json_str.strip()
        
        # Parse JSON
        return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw text: {text}")
        return {"classification": "FALLBACK_ANSWER"}

def test_router_query(query):
    """Test router functionality with a specific query."""
    # Construct the routing prompt
    routing_prompt = f"""
Analyze the query provided and classify it into EXACTLY ONE category from the following
options:

    1. ANSWER: Use this if the query is clear, specific, and can be answered with
    factual information. Relevant queries must have at least some vague link to
    the Flare Network blockchain.
    2. CLARIFY: Use this if the query is ambiguous, vague, or needs additional context.
    3. REJECT: Use this if the query is inappropriate, harmful, or completely
    out of scope. Reject the query if it is not related at all to the Flare Network
    or not related to blockchains.

Input: {query}

Response format:
{{
  "classification": "<UPPERCASE_CATEGORY>"
}}

Processing rules:
- The response should be exactly one of the three categories
- DO NOT infer missing values
- Normalize response to uppercase

Examples:
- "What is Flare's block time?" → {{"classification": "ANSWER"}}
- "How do you stake on Flare?" → {{"classification": "ANSWER"}}
- "How is the weather today?" → {{"classification": "REJECT"}}
- "What is the average block time?" - No specific chain is mentioned.
   → {{"classification": "CLARIFY"}}
- "How secure is it?" → {{"classification": "CLARIFY"}}
- "Tell me about Flare." → {{"classification": "CLARIFY"}}
"""

    try:
        # Generate content from Gemini
        print(f"\nSending query for classification: '{query}'")
        response = model.generate_content(routing_prompt)
        
        print("\nRaw response from Gemini:")
        print(response.text)
        
        # Process the response
        json_response = clean_json_response(response.text)
        classification = json_response.get("classification", "").upper()
        
        print(f"\nExtracted classification: {classification}")
        
        # Apply our additional logic for Flare-related queries
        if "flare" in query.lower() or "blockchain" in query.lower():
            print("Query contains 'flare' or 'blockchain', would default to ANSWER in application")
        
        return classification
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return None

# Load environment variables and configure Gemini
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
print(f"Using API key: {api_key[:5]}...{api_key[-4:]}")
genai.configure(api_key=api_key)

# Use Gemini 1.5 Flash model (faster and cheaper than Pro)
model = genai.GenerativeModel('gemini-1.5-flash')

# Test with some example queries
test_queries = [
    "What is Flare?",
    "How does the FTSO system work?",
    "What's the weather like today?",
    "Tell me about blockchain technology",
    "What is the average block time?"
]

print("==== TESTING ROUTER FUNCTIONALITY ====")
for query in test_queries:
    classification = test_router_query(query)
    print(f"\nQuery: '{query}' → Classification: {classification}")
    print("-" * 50)

print("\n✅ Router testing completed!") 
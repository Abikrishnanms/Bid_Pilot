import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from pydantic import BaseModel

class LLMProvider(ABC):
    @abstractmethod
    def extract_structured_data(self, text: str, schema: Type[BaseModel], prompt: str) -> BaseModel:
        pass

class MockLLMProvider(LLMProvider):
    def extract_structured_data(self, text: str, schema: Type[BaseModel], prompt: str) -> BaseModel:
        # Return a deterministic mock response based on the schema
        # In a real app, you might use a pre-canned JSON response
        mock_data = {
            "title": "Sample Tender",
            "organization": "Mock Org",
            "deadline": "2026-12-31",
            "estimated_value": "$100,000",
            "location": "Mock City",
            "eligibility_requirements": ["Must be registered"],
            "technical_requirements": ["Cloud experience", "Python expertise"],
            "experience_requirements": ["5 years in industry"],
            "certifications_required": ["ISO 9001"],
            "deliverables": ["Source code", "Documentation"],
            "evaluation_criteria": ["Cost (40%)", "Technical (60%)"]
        }
        return schema(**mock_data)

# You can add GeminiProvider and AnthropicProvider here as subclasses 
# using google.generativeai and anthropic SDKs later.

def get_llm_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider_name == "mock":
        return MockLLMProvider()
    # Add other providers logic here
    return MockLLMProvider()

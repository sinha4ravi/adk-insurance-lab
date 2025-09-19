"""
Insurance Claim Processing System using Google ADK.

This package implements a complete insurance claim processing system using Google's
Agent Development Kit (ADK). The system follows a microservices-like architecture
where each step in the claims process is handled by a dedicated agent.

Key Components:
- InsuranceClaimProcessor: Main coordinator that orchestrates the workflow
- Multiple specialized agents for different processing steps
- FastAPI application for HTTP interface

Basic Usage:
    ```python
    from insurance_agent import InsuranceClaimProcessor
    
    # Create an instance of the processor
    processor = InsuranceClaimProcessor()
    
    # Process a claim
    result = await processor.root_agent.tools[0]._run({
        "policy_number": "POL123456",
        "claim_amount": 5000,
        "incident_details": "Car accident on Main St",
        "supporting_documents": ["doc1.pdf", "photo1.jpg"]
    })
    print(result)
    ```

For web interface, use the ADK CLI:
    ```bash
    adk web
    ```
    Then access the web interface at http://localhost:8000

Note:
    This package requires the Google ADK to be properly configured with
    appropriate API keys and permissions.
"""

from fastapi import FastAPI
from .agent import InsuranceClaimProcessor

# Create a global instance of the processor for easy access
insurance_processor = InsuranceClaimProcessor()

# Ensure the agent has the correct instructions
root_agent = insurance_processor.root_agent

# Set the system instruction directly on the agent's model
if hasattr(root_agent, 'model') and hasattr(root_agent.model, 'system_instruction'):
    root_agent.model.system_instruction = (
        "You are an automated insurance claim processor. Your role is to process claims through the workflow.\n\n"
        "RULES:\n"
        "1. When you receive a claim, IMMEDIATELY call process_claim with the provided data\n"
        "2. NEVER ask for confirmation - process all claims automatically\n"
        "3. The system will handle validation and fraud detection\n"
        "4. ALWAYS respond with the final claim processing result\n\n"
        "Example usage:\n"
        "User: {claim data}\n"
        "You: [Call process_claim with the data]\n"
        "System: [Processing result]\n"
        "You: Here's the processing result: [summary]"
    )

# Create a FastAPI application instance
# This can be used to add additional API endpoints if needed
app = FastAPI(
    title="Insurance Claim Processing API",
    description="API for processing insurance claims using Google ADK",
    version="1.0.0"
)

# For backward compatibility and easier imports
__all__ = [
    'root_agent',
    'InsuranceClaimProcessor',
    'app',
    'insurance_processor'
]
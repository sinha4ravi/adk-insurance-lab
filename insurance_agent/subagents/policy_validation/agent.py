from typing import Dict, Any
from google.adk.agents import Agent
from ...subagents.base_agent import BaseAgent, ProcessingResult

class PolicyValidationAgent(BaseAgent):
    """Agent responsible for validating policy details and coverage."""
    
    def __init__(self):
        super().__init__(
            name="policy_validation_agent",
            description="Validates policy details and coverage for claims"
        )
        self.agent = Agent(
            name=self.name,
            model="gemini-2.0-flash",
            description=self.description,
            instruction=(
                "You are a policy validation agent. Your role is to verify "
                "that the claim is covered under the policy terms and that "
                "the policy is active and valid."
            ),
        )
    
    async def process(self, claim_data: Dict[str, Any]) -> ProcessingResult:
        """Validate the policy for the given claim."""
        try:
            # Get the ingested claim data
            ingested_data = claim_data.get('ingested_claim', {})
            if not ingested_data:
                return ProcessingResult(
                    success=False,
                    data={},
                    error="No ingested claim data found"
                )
            
            # Mock policy validation logic
            # In a real implementation, this would check against a policy database
            policy_number = ingested_data.get('policy_number', '')
            claim_type = ingested_data.get('claim_type', '')
            
            # Simple validation logic
            is_valid = bool(policy_number.startswith('POL-'))
            
            validation_result = {
                "policy_number": policy_number,
                "is_valid": is_valid,
                "claim_type_covered": claim_type in ['auto', 'home', 'health'],
                "validation_date": "2023-09-17"  # Should be current date in production
            }
            
            return ProcessingResult(
                success=is_valid,
                data={"policy_validation": validation_result}
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                data={},
                error=f"Error validating policy: {str(e)}"
            )

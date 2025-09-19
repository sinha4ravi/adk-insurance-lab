from typing import Dict, Any
from google.adk.agents import Agent
from ...subagents.base_agent import BaseAgent, ProcessingResult

class DataIngestionAgent(BaseAgent):
    """Agent responsible for ingesting and validating claim data."""
    
    def __init__(self):
        super().__init__(
            name="data_ingestion_agent",
            description="Validates and structures incoming claim data"
        )
        self.agent = Agent(
            name=self.name,
            model="gemini-2.0-flash",
            description=self.description,
            instruction=(
                "You are a data ingestion agent. Your role is to validate and structure "
                "incoming insurance claim data. Check for required fields and ensure "
                "data types are correct."
            ),
        )
    
    async def process(self, claim_data: Dict[str, Any]) -> ProcessingResult:
        """Process and validate the incoming claim data."""
        try:
            # Basic validation
            required_fields = ["claim_id", "policy_number", "claim_type", "incident_date"]
            missing_fields = [field for field in required_fields if field not in claim_data]
            
            if missing_fields:
                return ProcessingResult(
                    success=False,
                    data={},
                    error=f"Missing required fields: {', '.join(missing_fields)}"
                )
            
            # Structure the data
            structured_data = {
                "claim_id": str(claim_data["claim_id"]),
                "policy_number": str(claim_data["policy_number"]),
                "claim_type": str(claim_data["claim_type"]).lower(),
                "incident_date": str(claim_data["incident_date"]),
                "additional_data": {k: v for k, v in claim_data.items() 
                                  if k not in required_fields}
            }
            
            return ProcessingResult(
                success=True,
                data={"ingested_claim": structured_data}
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                data={},
                error=f"Error processing claim data: {str(e)}"
            )

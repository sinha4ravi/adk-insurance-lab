from typing import Dict, Any
from google.adk.agents import Agent
from ...subagents.base_agent import BaseAgent, ProcessingResult

class PayoutEstimatorAgent(BaseAgent):
    """Agent responsible for calculating claim payouts."""
    
    def __init__(self):
        super().__init__(
            name="payout_estimator_agent",
            description="Calculates estimated payouts for valid claims"
        )
        self.agent = Agent(
            name=self.name,
            model="gemini-2.0-flash",
            description=self.description,
            instruction=(
                "You are a payout estimation agent. Your role is to calculate "
                "the appropriate payout amount for valid insurance claims based on "
                "policy terms, claim details, and validation results."
            ),
        )
    
    async def process(self, claim_data: Dict[str, Any]) -> ProcessingResult:
        """Calculate the estimated payout for the claim."""
        try:
            # Get the necessary data from previous steps
            ingested_data = claim_data.get('ingested_claim', {})
            policy_validation = claim_data.get('policy_validation', {})
            fraud_analysis = claim_data.get('fraud_analysis', {})
            
            if not all([ingested_data, policy_validation, fraud_analysis]):
                return ProcessingResult(
                    success=False,
                    data={},
                    error="Incomplete claim data for payout estimation"
                )
            
            # Check if claim is valid and not fraudulent
            if not policy_validation.get('is_valid', False) or not policy_validation.get('claim_type_covered', False):
                return ProcessingResult(
                    success=False,
                    data={"claim_denied": "Policy validation failed"},
                    error="Claim not covered by policy"
                )
                
            # Only flag for review if fraud analysis explicitly says so
            if fraud_analysis.get('risk_assessment', {}).get('requires_manual_review', False):
                return ProcessingResult(
                    success=False,
                    data={
                        "needs_manual_review": True,
                        "fraud_indicators": fraud_analysis.get('fraud_indicators', []),
                        "risk_score": fraud_analysis.get('risk_score', 0)
                    },
                    error="Potential fraud detected, requires manual review"
                )
            
            # Extract claim details
            claim_data = ingested_data.get('additional_data', {}) or ingested_data.get('claim_data', {})
            claim_amount = float(claim_data.get('amount_claimed', 0) or claim_data.get('claim_amount', 0))
            claim_type = ingested_data.get('claim_type', '').lower()
            
            # Apply policy limits and deductibles (simplified)
            payout = claim_amount
            
            # Apply maximum limits based on claim type
            max_payouts = {
                'auto': 50000,
                'home': 500000,
                'health': 100000
            }
            
            max_payout = max_payouts.get(claim_type, 10000)
            payout = min(payout, max_payout)
            
            # Apply deductible (simplified)
            deductible = 500  # In a real system, this would come from the policy
            payout = max(0, payout - deductible)
            
            payout_result = {
                "claim_id": ingested_data.get('claim_id', ''),
                "original_claim_amount": claim_amount,
                "approved_amount": round(payout, 2),
                "deductible_applied": min(deductible, claim_amount),
                "currency": "USD",
                "calculation_notes": [
                    f"Applied standard {claim_type} policy limits",
                    f"Deductible of ${deductible} applied"
                ]
            }
            
            return ProcessingResult(
                success=True,
                data={"payout_estimation": payout_result}
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                data={},
                error=f"Error calculating payout: {str(e)}"
            )

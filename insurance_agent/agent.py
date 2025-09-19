"""
Insurance Claim Processing System using Google ADK.

This module implements the main coordinator for processing insurance claims
using multiple specialized agents with both sequential and parallel workflows. 
The system follows a microservices-like architecture where each step in the 
claims process is handled by dedicated agents that can run sequentially or 
in parallel as needed.

Key Components:
- InsuranceClaimProcessor: Main coordinator that orchestrates the workflow
- ProcessClaimTool: Tool that exposes the claim processing functionality
- ParallelAgent: For running independent validations concurrently
- Multiple specialized agents for different processing steps

Workflow:
1. Data Ingestion: Extract and validate claim data (sequential)
2. Parallel Execution:
   - Policy Validation: Verify claim against policy terms
   - Fraud Check: Analyze claim for potential fraud
3. Payout Estimation: Calculate estimated payout amount (sequential)

Implementation Patterns:
- Sequential Flow: Used for dependent steps that require the output of 
  previous steps (e.g., data ingestion before validation)
- Parallel Flow: Used for independent validations that can run concurrently
  (e.g., policy validation and fraud check)

Dependencies:
- google-adk: Google's Agent Development Kit
- pydantic: For data validation and modeling

Dependencies:
- google-adk: Google's Agent Development Kit
- pydantic: For data validation
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union, Callable, Awaitable
import logging
import asyncio
from typing import Dict, Any
from pydantic import BaseModel, Field
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.tools import FunctionTool

# Relative imports for subagents
from .subagents.data_ingestion import DataIngestionAgent
from .subagents.policy_validation import PolicyValidationAgent
from .subagents.fraud_check import FraudCheckAgent
from .subagents.payout_estimator import PayoutEstimatorAgent
from .subagents.base_agent import ProcessingResult

class InsuranceClaimProcessor:
    """
    Main coordinator for the insurance claim processing workflow.
    
    This class serves as the central coordinator that manages the entire
    claim processing pipeline. It initializes and coordinates multiple
    specialized agents, each responsible for a specific part of the process.
    
    The workflow consists of the following steps:
    1. Data Ingestion: Extract and validate claim data
    2. Policy Validation: Verify claim against policy terms
    3. Fraud Check: Analyze claim for potential fraud
    4. Payout Estimation: Calculate estimated payout amount
    
    The coordinator exposes a single endpoint 'process_claim' that can be
    used to submit new claims for processing.
    """
    
    def __init__(self):
        """
        Initialize the InsuranceClaimProcessor and all its sub-agents.
        
        This sets up the entire processing pipeline by:
        1. Initializing all specialized agents
        2. Creating the sequential workflow for claim processing
        3. Creating the root agent that coordinates the workflow
        4. Registering the process_claim tool
        """
        # Initialize all sub-agents with their specific responsibilities
        self.data_ingestion_agent = DataIngestionAgent()
        self.policy_validation_agent = PolicyValidationAgent()
        self.fraud_check_agent = FraudCheckAgent()
        self.payout_estimator_agent = PayoutEstimatorAgent()
        
        # Create the sequential workflow
        self.workflow = self._create_workflow()
        
        # Create the root agent that will coordinate the workflow
        self.root_agent = Agent(
            name="insurance_claim_processor",
            model="gemini-2.0-flash",
            description="Coordinates the insurance claim processing workflow",
            instruction=(
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
        )
        
        # Import the base tool class from ADK
        from google.adk.tools.base_tool import BaseTool
        
        # Define the process_claim function that will be exposed as a tool
        # This function serves as the entry point for claim processing
        async def process_claim(claim_data: dict) -> dict:
            """
            Process an insurance claim through the complete workflow.
            
            This is the main entry point for claim processing. It takes raw claim data,
            processes it through all the necessary steps, and returns the results.
            
            Args:
                claim_data: A dictionary containing the claim information with keys like:
                    - policy_number: The insurance policy number
                    - claim_amount: The amount being claimed
                    - incident_details: Description of the incident
                    - supporting_documents: List of document references
                    
            Returns:
                A dictionary containing:
                - status: Processing status (success/error)
                - steps: Results from each processing step
                - final_decision: The final decision on the claim
                - estimated_payout: The calculated payout amount if approved
                
            Raises:
                ValueError: If required claim data is missing or invalid
            """
            return await self._process_claim_impl(claim_data)
        
        # Create a function tool that integrates with the ADK framework
        # This makes our process_claim function available to the agent
        process_claim_tool = FunctionTool(process_claim)
        
        # Register the tool with the root agent
        # This makes it available for the agent to use
        if not hasattr(self.root_agent, 'tools') or self.root_agent.tools is None:
            self.root_agent.tools = []
        self.root_agent.tools.append(process_claim_tool)
    
    async def _create_parallel_agents(self, context: Dict[str, Any]) -> ParallelAgent:
        """Create and configure parallel agents for validation and fraud check.
        
        Args:
            context: The current processing context with claim data
            
        Returns:
            A configured ParallelAgent instance
        """
        # Create a parallel agent to run validation and fraud check concurrently
        parallel_agent = ParallelAgent(
            name="validation_and_fraud_check",
            description="Runs policy validation and fraud check in parallel"
        )
        
        # Add policy validation agent
        @parallel_agent.add_agent(name="policy_validation")
        async def policy_validation_agent() -> Dict[str, Any]:
            result = await self.policy_validation_agent.process(context)
            return {"success": result.success, "data": result.data}
            
        # Add fraud check agent
        @parallel_agent.add_agent(name="fraud_check")
        async def fraud_check_agent() -> Dict[str, Any]:
            result = await self.fraud_check_agent.process(context)
            return {"success": result.success, "data": result.data}
            
        return parallel_agent
        
    def _create_workflow(self) -> SequentialAgent:
        """Create the sequential workflow for claim processing.
        
        This method defines the sequence of steps for processing an insurance claim,
        including both sequential and parallel processing steps.
        
        Returns:
            A configured SequentialAgent instance that processes claims through
            multiple validation steps including parallel execution of policy
            validation and fraud check.
        """
        # Store a reference to self for use in agent methods
        processor = self
        
        # Create a custom agent for each step in the workflow
        class IngestAgent(Agent):
            processor: Any = Field(default=None, exclude=True)
            
            def __init__(self, **data):
                # Set the processor before calling parent's __init__
                super().__init__(**{k: v for k, v in data.items() if k != 'processor'})
                self.processor = processor
                
            async def _run_async_impl(self, context):
                result = await self.processor.data_ingestion_agent.process(context["claim_data"])
                if not result.success:
                    raise ValueError(f"Data ingestion failed: {result.error}")
                context["ingested_claim"] = result.data.get("ingested_claim", {})
                return context
        
        class ValidationAgent(Agent):
            processor: Any = Field(default=None, exclude=True)
            
            def __init__(self, **data):
                # Set the processor before calling parent's __init__
                super().__init__(**{k: v for k, v in data.items() if k != 'processor'})
                self.processor = processor
                
            async def _run_async_impl(self, context):
                # Create and run parallel validations
                parallel_agent = await self.processor._create_parallel_agents(context)
                results = await parallel_agent.run()
                
                # Process results with better error handling
                policy_result = results.get("policy_validation", {})
                fraud_result = results.get("fraud_check", {})
                
                # Log raw results for debugging
                logging.info(f"[DEBUG] Raw Policy Result: {policy_result}")
                logging.info(f"[DEBUG] Raw Fraud Result: {fraud_result}")
                
                # Check for errors with more detailed messages
                if not policy_result:
                    raise ValueError("Policy validation result is empty")
                if not fraud_result:
                    raise ValueError("Fraud check result is empty")
                
                # Extract validation data with defaults
                policy_data = policy_result.get("data", {})
                fraud_data = fraud_result.get("data", {})
                
                # Set default values if validation data is empty
                context["policy_validation"] = {
                    "is_valid": policy_data.get("is_valid", True),
                    "claim_type_covered": policy_data.get("claim_type_covered", True),
                    **policy_data.get("policy_validation", {})  # Preserve any additional data
                }
                
                context["fraud_analysis"] = {
                    "risk_score": fraud_data.get("risk_score", 0.0),
                    "needs_review": fraud_data.get("needs_review", False),
                    "fraud_indicators": fraud_data.get("fraud_indicators", []),
                    **fraud_data.get("fraud_analysis", {})  # Preserve any additional data
                }
                return context
        
        class PayoutAgent(Agent):
            processor: Any = Field(default=None, exclude=True)
            
            def __init__(self, **data):
                # Set the processor before calling parent's __init__
                super().__init__(**{k: v for k, v in data.items() if k != 'processor'})
                self.processor = processor
                
            async def _run_async_impl(self, context):
                result = await self.processor.payout_estimator_agent.process(context)
                if not result.success:
                    raise ValueError(f"Payout calculation failed: {result.error}")
                context["payout_estimation"] = result.data.get("payout_estimation", {})
                return context
        
        # Create the sequential agent with sub-agents
        workflow = SequentialAgent(
            name="claim_processing_workflow",
            description="Processes insurance claims through multiple validation steps"
        )
        
        # Create and configure sub-agents
        ingest_agent = IngestAgent(
            name="ingest_claim_data",
            description="Ingests and validates claim data"
        )
        
        validation_agent = ValidationAgent(
            name="run_validations",
            description="Runs policy validation and fraud check in parallel"
        )
        
        payout_agent = PayoutAgent(
            name="calculate_payout",
            description="Calculates the final payout amount"
        )
        
        # Set the sub_agents attribute using the proper method if available
        if hasattr(workflow, 'set_sub_agents'):
            workflow.set_sub_agents([ingest_agent, validation_agent, payout_agent])
        else:
            # Fallback to direct attribute access if set_sub_agents doesn't exist
            workflow.sub_agents = [ingest_agent, validation_agent, payout_agent]
        
        return workflow

    def _create_initial_context(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create the initial context for the workflow.
        
        Args:
            claim_data: The raw claim data
            
        Returns:
            A dictionary with the initial context structure
        """
        # Create a shallow copy of the claim data to avoid modifying the original
        claim_data_copy = claim_data.copy()
        
        # Create a simple context structure
        return {
            "claim_data": claim_data_copy,
            "ingested_claim": {},
            "policy_validation": {},
            "fraud_analysis": {},
            "payout_estimation": {}
        }
    
    async def _process_claim_impl(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal implementation of the claim processing workflow.
        
        This method implements the actual claim processing pipeline using a sequential
        workflow with parallel steps where appropriate. It's called by the process_claim
        tool and should not be called directly.
        
        The processing flow is:
        1. Data Ingestion: Extract and validate claim data (sequential)
        2. Parallel Execution:
           - Policy Validation: Verify claim against policy terms
           - Fraud Check: Analyze claim for potential fraud
        3. Payout Estimation: Calculate estimated payout amount (sequential)
        
        Args:
            claim_data: A dictionary containing the raw claim data with keys like:
                - policy_number: The insurance policy number
                - claim_amount: The amount being claimed
                - incident_details: Description of the incident
                - supporting_documents: List of document references
                
        Returns:
            A dictionary containing the processing results with the following structure:
            {
                "status": "processing"|"approved"|"rejected"|"requires_review"|"error",
                "steps": {
                    "data_ingestion": { ... },
                    "policy_validation": { ... },
                    "fraud_check": { ... },
                    "payout_estimation": { ... }
                },
                "approved_amount": float,  # Only present if status is "approved"
                "currency": str,          # Currency code (e.g., "USD")
                "error": str              # Only present if status is "error" or "rejected"
            }
        """
        # Create a copy of the claim data to avoid modifying the original
        processed_claim = claim_data.copy()
        
        # Generate a claim_id if not provided
        if 'claim_id' not in processed_claim:
            import uuid
            processed_claim['claim_id'] = f"CLAIM-{str(uuid.uuid4())[:8].upper()}"
        
        result = {
            "status": "processing",
            "claim_id": processed_claim['claim_id'],
            "steps": {}
        }
        
        try:
            # Create a simple context to track the workflow state
            context = self._create_initial_context(processed_claim)
            
            try:
                # Manually execute each step in the workflow
                # Step 1: Data Ingestion
                # Prepare data for ingestion
                ingestion_data = context["claim_data"].copy()
                
                # Ensure the claim amount is properly formatted
                if 'claim_amount' in ingestion_data and not isinstance(ingestion_data['claim_amount'], (int, float)):
                    try:
                        ingestion_data['claim_amount'] = float(ingestion_data['claim_amount'])
                    except (ValueError, TypeError) as e:
                        logging.warning(f"Invalid claim amount format: {ingestion_data['claim_amount']}. Setting to 0.0. Error: {str(e)}")
                        ingestion_data['claim_amount'] = 0.0
                
                # Get vehicle data once to avoid multiple lookups
                vehicle_data = context["claim_data"].get("vehicle", {})
                
                # Prepare data for ingestion - vehicle data is only stored in additional_data
                context["ingested_claim"] = {
                    "claim_id": context["claim_data"].get("claim_id") or f"CLAIM-{str(uuid.uuid4())[:8].upper()}",
                    "policy_number": context["claim_data"].get("policy_number", ""),
                    "claim_type": context["claim_data"].get("claim_type", "auto").lower(),
                    "incident_date": context["claim_data"].get("incident_date", ""),
                    "policy_start_date": context["claim_data"].get("policy_start_date", ""),
                    "additional_data": {
                        "amount_claimed": float(context["claim_data"].get("claim_amount", 0.0)),
                        "incident_details": context["claim_data"].get("incident_details", ""),
                        "supporting_documents": context["claim_data"].get("supporting_documents", []),
                        "vehicle": vehicle_data  # Single source of truth for vehicle data
                    }
                }
                
                logging.info(f"[DEBUG] Prepared ingested claim data for claim {context['ingested_claim']['claim_id']}")
                
                # Prepare fraud check data with all required fields
                fraud_check_data = {
                    "ingested_claim": context["ingested_claim"],
                    "claim_data": context["claim_data"],
                    "vehicle": vehicle_data
                }
                
                logging.info("[DEBUG] Starting parallel validations...")
                
                # Run validations in parallel
                validation_tasks = [
                    self.policy_validation_agent.process(context["ingested_claim"]),
                    self.fraud_check_agent.process(fraud_check_data)
                ]
                
                # Wait for all validations to complete
                try:
                    validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
                    
                    # Process policy validation results
                    if isinstance(validation_results[0], Exception):
                        logging.error(f"Policy validation failed: {str(validation_results[0])}")
                        raise validation_results[0]
                    
                    context["policy_validation"] = validation_results[0].data.get("policy_validation", {})
                    logging.info(f"[DEBUG] Policy validation completed: {context['policy_validation']}")
                    
                    # Process fraud check results
                    if isinstance(validation_results[1], Exception):
                        error_msg = f"Fraud check failed: {str(validation_results[1])}"
                        logging.error(error_msg, exc_info=True)
                        context["fraud_analysis"] = {
                            "error": error_msg,
                            "risk_score": 1.0,
                            "needs_review": True,
                            "fraud_indicators": ["error_processing_fraud_check"]
                        }
                    else:
                        # Ensure we have a valid fraud_analysis dictionary
                        fraud_analysis = validation_results[1].data.get("fraud_analysis", {})
                        if not fraud_analysis:
                            fraud_analysis = {
                                "risk_score": 0.0,
                                "fraud_indicators": [],
                                "needs_review": False,
                                "recommendation": "approve"
                            }
                        
                        context["fraud_analysis"] = fraud_analysis
                        logging.info(f"[DEBUG] Fraud check completed. Risk score: {fraud_analysis.get('risk_score', 0)}")
                        
                        # Log any fraud indicators
                        if fraud_analysis.get("fraud_indicators"):
                            logging.warning(f"[FRAUD INDICATORS] {', '.join(fraud_analysis['fraud_indicators'])}")
                            
                        # Log risk factors if available
                        if "risk_factors" in fraud_analysis:
                            logging.info(f"[RISK FACTORS] {fraud_analysis['risk_factors']}")
                            
                except Exception as e:
                    logging.error("Unexpected error during parallel validations", exc_info=True)
                    raise
                
                # Step 3: Prepare data for payout estimation
                # Log the current context for debugging
                logging.info(f"[DEBUG] Policy Validation: {context.get('policy_validation', {})}")
                logging.info(f"[DEBUG] Fraud Analysis: {context.get('fraud_analysis', {})}")
                logging.info(f"[DEBUG] Ingested Claim: {context.get('ingested_claim', {})}")
                
                # Get the ingested claim data
                ingested_claim = context.get("ingested_claim", {})
                if isinstance(ingested_claim, dict) and 'data' in ingested_claim:
                    ingested_claim = ingested_claim['data']
                
                # Ensure claim amount is properly set
                try:
                    claim_amount = float(context["claim_data"].get("claim_amount", 0.0))
                except (ValueError, TypeError):
                    claim_amount = 0.0
                
                # Prepare the ingested data structure
                claim_data = context["claim_data"]
                ingested_data = {
                    "claim_id": ingested_claim.get("claim_id") or f"CLAIM-{str(uuid.uuid4())[:8].upper()}",
                    "policy_number": claim_data.get("policy_number", ""),
                    "claim_type": claim_data.get("claim_type", "auto").lower(),
                    "incident_date": claim_data.get("incident_date", ""),
                    "policy_start_date": claim_data.get("policy_start_date", ""),
                    "vehicle": claim_data.get("vehicle", {}),
                    "additional_data": {
                        "amount_claimed": claim_amount,
                        "incident_details": claim_data.get("incident_details", ""),
                        "supporting_documents": claim_data.get("supporting_documents", []),
                        "vehicle": claim_data.get("vehicle", {})
                    }
                }
                
                # Ensure policy validation has all required fields with defaults
                policy_validation = context.get("policy_validation", {})
                if not isinstance(policy_validation, dict):
                    policy_validation = {}
                
                # Ensure fraud analysis has all required fields with defaults
                fraud_analysis = context.get("fraud_analysis", {})
                if not isinstance(fraud_analysis, dict):
                    fraud_analysis = {
                        "risk_score": 0.0,
                        "needs_review": False,
                        "fraud_indicators": []
                    }
                
                # Build the complete payout data structure with all required fields
                payout_data = {
                    "claim_data": context["claim_data"].copy(),
                    "ingested_claim": {
                        **ingested_data,
                        "claim_id": ingested_data["claim_id"],
                        "claim_type": ingested_data["claim_type"],
                        "additional_data": {
                            "amount_claimed": claim_amount,
                            **ingested_data.get("additional_data", {})
                        }
                    },
                    "policy_validation": {
                        "is_valid": policy_validation.get("is_valid", True),
                        "claim_type_covered": policy_validation.get("claim_type_covered", True),
                        **policy_validation  # Include any additional validation data
                    },
                    "fraud_analysis": {
                        "risk_score": fraud_analysis.get("risk_score", 0.0),
                        "needs_review": fraud_analysis.get("needs_review", False),
                        "fraud_indicators": fraud_analysis.get("fraud_indicators", []),
                        **fraud_analysis  # Include any additional fraud data
                    }
                }
                
                # Log the prepared payout data
                logging.info(f"[DEBUG] Prepared Payout Data: {payout_data}")
                
                # Calculate payout with all required data
                payout_result = await self.payout_estimator_agent.process(payout_data)
                if not payout_result.success:
                    raise ValueError(f"Payout estimation failed: {payout_result.error}")
                
                # Store the complete payout result from the payout estimator
                context["payout_estimation"] = payout_result.data.get("payout_estimation", {})
                
                # Get the approved amount from the payout result
                approved_amount = context["payout_estimation"].get("approved_amount", 0)
                
                # Update the result with the approved amount and currency
                result["approved_amount"] = approved_amount
                result["currency"] = context["payout_estimation"].get("currency", "USD")
                
                # Update result with all steps
                result["steps"] = {
                    "data_ingestion": context["ingested_claim"],
                    "policy_validation": context["policy_validation"],
                    "fraud_check": context["fraud_analysis"],
                    "payout_estimation": context["payout_estimation"]
                }
                
            except Exception as e:
                # Log the full error for debugging
                import traceback
                error_trace = traceback.format_exc()
                logging.error(f"Error in claim processing: {error_trace}")
                raise RuntimeError(f"Error processing claim: {str(e)}")
            
            # Get fraud analysis results with proper defaults
            fraud_analysis = result["steps"].get("fraud_check", {})
            risk_score = fraud_analysis.get("risk_score", 0)
            needs_review = fraud_analysis.get("needs_review", False)
            fraud_indicators = fraud_analysis.get("fraud_indicators", [])
            
            # Log the fraud analysis results for debugging
            logging.info(f"[FRAUD ANALYSIS] Risk Score: {risk_score}, Needs Review: {needs_review}")
            if fraud_indicators:
                logging.warning(f"[FRAUD INDICATORS] {', '.join(fraud_indicators)}")
            
            # Set final status based on workflow results and fraud analysis
            payout_data = result["steps"].get("payout_estimation", {})
            
            # Check for fraud indicators first
            if fraud_indicators:
                if risk_score >= 0.7:  # High risk of fraud
                    result["status"] = "rejected"
                    result["error"] = f"Claim rejected due to high fraud risk (score: {risk_score}). Indicators: {', '.join(fraud_indicators)}"
                elif needs_review or risk_score >= 0.4:  # Medium risk, needs review
                    result["status"] = "requires_review"
                    result["error"] = f"Claim requires manual review due to potential fraud indicators (score: {risk_score}). Indicators: {', '.join(fraud_indicators)}"
                elif payout_data and "approved_amount" in payout_data and payout_data["approved_amount"] > 0:
                    # Low risk, approve with warning if any indicators
                    result["status"] = "approved"
                    result["approved_amount"] = payout_data.get("approved_amount", 0)
                    result["currency"] = payout_data.get("currency", "USD")
                    if fraud_indicators:
                        result["warning"] = f"Claim approved but with fraud indicators (score: {risk_score}). Indicators: {', '.join(fraud_indicators)}"
            elif payout_data and "approved_amount" in payout_data and payout_data["approved_amount"] > 0:
                # No fraud indicators, approve if payout is valid
                result["status"] = "approved"
                result["approved_amount"] = payout_data.get("approved_amount", 0)
                result["currency"] = payout_data.get("currency", "USD")
            else:
                result["status"] = "requires_review"
                result["error"] = "Payout estimation failed or resulted in zero amount"
            
            return result
            
        except ValueError as ve:
            result["status"] = "rejected" if "validation" in str(ve).lower() else "requires_review"
            result["error"] = str(ve)
            return result
            
        except Exception as e:
            import traceback
            result["status"] = "error"
            result["error"] = f"Unexpected error: {str(e)}\n\n{traceback.format_exc()}"
            return result

# Create a global instance for easy access
insurance_processor = InsuranceClaimProcessor()
root_agent = insurance_processor.root_agent
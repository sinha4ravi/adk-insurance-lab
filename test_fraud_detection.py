import asyncio
import json
import logging
from insurance_agent.agent import InsuranceClaimProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Sample test cases
TEST_CLAIMS = [
    # Test Case 1: Normal claim
    {
        "policy_number": "POL-12345",
        "claim_type": "auto",
        "incident_date": "2025-09-10",
        "incident_details": "Rear-ended at a stop light",
        "claim_amount": 3500,
        "supporting_documents": ["police_report.pdf", "damage_photos.jpg"],
        "vehicle": {
            "make": "Toyota",
            "model": "Camry",
            "year": 2020
        },
        "policy_start_date": "2024-01-15"
    },
    # Test Case 2: High-value claim for minor damage
    {
        "policy_number": "POL-12346",
        "claim_type": "auto",
        "incident_date": "2025-09-12",
        "incident_details": "Minor fender bender in parking lot",
        "claim_amount": 25000,
        "supporting_documents": ["damage_photos.jpg"],
        "vehicle": {
            "make": "Honda",
            "model": "Civic",
            "year": 2021
        },
        "policy_start_date": "2025-09-01"
    },
    # Test Case 3: Claim right after policy start
    {
        "policy_number": "POL-12347",
        "claim_type": "auto",
        "incident_date": "2025-09-03",
        "incident_details": "Car theft from parking lot",
        "claim_amount": 30000,
        "supporting_documents": ["police_report.pdf"],
        "vehicle": {
            "make": "BMW",
            "model": "X5",
            "year": 2022
        },
        "policy_start_date": "2025-09-01"
    }
]

async def test_claim(claim_data):
    """Test a single claim through the system."""
    processor = InsuranceClaimProcessor()
    
    print("\n" + "="*80)
    print(f"TESTING CLAIM: {claim_data['incident_details']}")
    print("-"*80)
    
    try:
        # Process the claim
        result = await processor._process_claim_impl(claim_data)
        
        # Print the results
        print("\nPROCESSING RESULT:")
        print(json.dumps(result, indent=2, default=str))
        
        # Print fraud analysis details
        fraud_check = result.get("steps", {}).get("fraud_check", {})
        if fraud_check:
            print("\nFRAUD ANALYSIS:")
            print(f"Risk Score: {fraud_check.get('risk_score', 0)}")
            print(f"Recommendation: {fraud_check.get('recommendation', 'N/A')}")
            if fraud_check.get('fraud_indicators'):
                print("Fraud Indicators:")
                for indicator in fraud_check['fraud_indicators']:
                    print(f"  - {indicator}")
        
        return result
    except Exception as e:
        print(f"Error processing claim: {str(e)}")
        return None

async def main():
    """Run all test cases."""
    print("Starting fraud detection tests...")
    print("="*80)
    
    for i, claim in enumerate(TEST_CLAIMS, 1):
        print(f"\n{'*'*40}")
        print(f"TEST CASE {i}")
        print(f"{'*'*40}")
        await test_claim(claim)
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main())

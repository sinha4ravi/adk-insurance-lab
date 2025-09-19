import asyncio
import json
import logging
from datetime import datetime, timedelta
from insurance_agent.agent import InsuranceClaimProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Sample test cases with different fraud scenarios
test_cases = [
    # Test Case 1: Normal claim with reasonable details
    {
        "name": "Normal Claim - Minor Accident",
        "data": {
            "policy_number": "POL-12345",
            "claim_type": "auto",
            "incident_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "incident_details": "Rear-ended at a stop light. The other driver was at fault and police report #12345 was filed.",
            "claim_amount": 3500,
            "supporting_documents": ["police_report_12345.pdf", "damage_photos_1.jpg"],
            "vehicle": {
                "make": "Toyota",
                "model": "Camry",
                "year": 2020
            },
            "policy_start_date": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        },
        "expected_risk": "low"
    },
    
    # Test Case 2: High-value claim for minor damage (suspicious)
    {
        "name": "Suspicious - High Value for Minor Damage",
        "data": {
            "policy_number": "POL-12346",
            "claim_type": "auto",
            "incident_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "incident_details": "Minor fender bender in parking lot. Just a small scratch.",
            "claim_amount": 25000,
            "supporting_documents": ["damage_photos_2.jpg"],
            "vehicle": {
                "make": "Honda",
                "model": "Civic",
                "year": 2021
            },
            "policy_start_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        },
        "expected_risk": "high"
    },
    
    # Test Case 3: Claim right after policy start (suspicious timing)
    {
        "name": "Suspicious - Claim Immediately After Policy Start",
        "data": {
            "policy_number": "POL-12347",
            "claim_type": "auto",
            "incident_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "incident_details": "Car was stolen from parking lot overnight. No witnesses.",
            "claim_amount": 30000,
            "supporting_documents": ["police_report_12347.pdf"],
            "vehicle": {
                "make": "BMW",
                "model": "X5",
                "year": 2022
            },
            "policy_start_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        },
        "expected_risk": "high"
    },
    
    # Test Case 4: Staged accident indicators
    {
        "name": "Suspicious - Possible Staged Accident",
        "data": {
            "policy_number": "POL-12348",
            "claim_type": "auto",
            "incident_date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "incident_details": "I was driving when another car suddenly stopped in front of me. The driver waved me to go, then hit the brakes. I couldn't stop in time.",
            "claim_amount": 12000,
            "supporting_documents": ["damage_photos_3.jpg"],
            "vehicle": {
                "make": "Mercedes",
                "model": "C-Class",
                "year": 2021
            },
            "policy_start_date": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        },
        "expected_risk": "high"
    },
    
    # Test Case 5: Vague description with high claim amount
    {
        "name": "Suspicious - Vague Description with High Claim",
        "data": {
            "policy_number": "POL-12349",
            "claim_type": "auto",
            "incident_date": (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"),
            "incident_details": "Something happened to my car. Not sure what. It's damaged.",
            "claim_amount": 18000,
            "supporting_documents": [],
            "vehicle": {
                "make": "Ford",
                "model": "Focus",
                "year": 2019
            },
            "policy_start_date": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        },
        "expected_risk": "high"
    }
]

async def run_test_case(test_case):
    """Run a single test case and return the results."""
    print(f"\n{'='*80}")
    print(f"TEST CASE: {test_case['name']}")
    print(f"{'='*80}")
    
    # Initialize the processor
    processor = InsuranceClaimProcessor()
    
    # Get the process_claim tool from the root agent's tools
    process_claim_tool = None
    for tool in processor.root_agent.tools:
        if tool.name == 'process_claim':
            process_claim_tool = tool
            break
    
    if not process_claim_tool:
        raise ValueError("Could not find process_claim tool in agent's tools")
    
    # Process the claim
    try:
        # Call the tool's function directly
        result = await process_claim_tool.function(test_case['data'])
        
        # Print the results
        print("\nCLAIM DETAILS:")
        print(f"- Type: {test_case['data']['claim_type']}")
        print(f"- Amount: ${test_case['data']['claim_amount']:,.2f}")
        print(f"- Incident: {test_case['data']['incident_details'][:100]}...")
        
        print("\nFRAUD ANALYSIS:")
        fraud_analysis = result.get('fraud_analysis', {})
        risk_score = fraud_analysis.get('risk_score', 0)
        print(f"- Risk Score: {risk_score:.2f}")
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "HIGH"
        elif risk_score >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        print(f"- Risk Level: {risk_level}")
        
        # Print fraud indicators if any
        indicators = fraud_analysis.get('fraud_indicators', [])
        if indicators:
            print("\nFRAUD INDICATORS:")
            for indicator in indicators:
                print(f"- {indicator}")
        else:
            print("\nNo fraud indicators detected.")
            
        # Print recommendation
        print(f"\nRECOMMENDATION: {fraud_analysis.get('recommendation', 'N/A').upper()}")
        
        # Print expected vs actual
        print(f"\nEXPECTED: {test_case['expected_risk'].upper()} risk")
        print(f"ACTUAL: {risk_level} risk")
        
        # Determine if test passed
        passed = (
            (test_case['expected_risk'] == 'high' and risk_score >= 0.7) or
            (test_case['expected_risk'] == 'medium' and 0.4 <= risk_score < 0.7) or
            (test_case['expected_risk'] == 'low' and risk_score < 0.4)
        )
        
        print(f"\nRESULT: {'PASSED' if passed else 'FAILED'}")
        
        return {
            'name': test_case['name'],
            'expected_risk': test_case['expected_risk'],
            'actual_risk': risk_level.lower(),
            'risk_score': risk_score,
            'passed': passed,
            'indicators': indicators
        }
        
    except Exception as e:
        print(f"ERROR processing test case: {str(e)}")
        return {
            'name': test_case['name'],
            'error': str(e),
            'passed': False
        }

async def main():
    """Run all test cases and print a summary."""
    print("="*80)
    print("FRAUD DETECTION SYSTEM TEST")
    print("="*80)
    
    results = []
    
    # Run all test cases
    for test_case in test_cases:
        result = await run_test_case(test_case)
        results.append(result)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r.get('passed', False))
    total = len(results)
    
    print(f"\nTests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    # Print detailed results
    print("\nDETAILED RESULTS:")
    for result in results:
        status = "PASSED" if result.get('passed', False) else "FAILED"
        print(f"\n- {result['name']}: {status}")
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Expected: {result['expected_risk'].upper()} risk")
            print(f"  Actual: {result['actual_risk'].upper()} risk (Score: {result['risk_score']:.2f})")
            if result['indicators']:
                print(f"  Indicators: {', '.join(result['indicators'][:2])}...")
            else:
                print("  No fraud indicators")
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(main())

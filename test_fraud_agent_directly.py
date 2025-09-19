import asyncio
import logging
from datetime import datetime, timedelta
from insurance_agent.subagents.fraud_check import FraudCheckAgent
from insurance_agent.subagents.base_agent import ProcessingResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create test cases
test_cases = [
    # Test Case 1: Normal claim with reasonable details
    {
        "name": "Normal Claim - Minor Accident",
        "data": {
            "ingested_claim": {
                "claim_id": "CLAIM-12345",
                "policy_number": "POL-12345",
                "claim_type": "auto",
                "incident_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "policy_start_date": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                "additional_data": {
                    "amount_claimed": 3500,
                    "incident_details": "Rear-ended at a stop light. The other driver was at fault and police report #12345 was filed.",
                    "supporting_documents": ["police_report_12345.pdf", "damage_photos_1.jpg"]
                }
            },
            "claim_data": {
                "vehicle": {
                    "make": "Toyota",
                    "model": "Camry",
                    "year": 2020
                }
            }
        },
        "expected_risk": "low"
    },
    
    # Test Case 2: High-value claim for minor damage (suspicious)
    {
        "name": "Suspicious - High Value for Minor Damage",
        "data": {
            "ingested_claim": {
                "claim_id": "CLAIM-12346",
                "policy_number": "POL-12346",
                "claim_type": "auto",
                "incident_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
                "policy_start_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
                "additional_data": {
                    "amount_claimed": 25000,
                    "incident_details": "Minor fender bender in parking lot. Just a small scratch.",
                    "supporting_documents": ["damage_photos_2.jpg"]
                }
            },
            "claim_data": {
                "vehicle": {
                    "make": "Honda",
                    "model": "Civic",
                    "year": 2021
                }
            }
        },
        "expected_risk": "high"
    },
    
    # Test Case 3: Claim right after policy start (suspicious timing)
    {
        "name": "Suspicious - Claim Immediately After Policy Start",
        "data": {
            "ingested_claim": {
                "claim_id": "CLAIM-12347",
                "policy_number": "POL-12347",
                "claim_type": "auto",
                "incident_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                "policy_start_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                "additional_data": {
                    "amount_claimed": 30000,
                    "incident_details": "Car was stolen from parking lot overnight. No witnesses.",
                    "supporting_documents": ["police_report_12347.pdf"]
                }
            },
            "claim_data": {
                "vehicle": {
                    "make": "BMW",
                    "model": "X5",
                    "year": 2022
                }
            }
        },
        "expected_risk": "high"
    },
    
    # Test Case 4: Staged accident indicators
    {
        "name": "Suspicious - Possible Staged Accident",
        "data": {
            "ingested_claim": {
                "claim_id": "CLAIM-12348",
                "policy_number": "POL-12348",
                "claim_type": "auto",
                "incident_date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "policy_start_date": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
                "additional_data": {
                    "amount_claimed": 12000,
                    "incident_details": "I was driving when another car suddenly stopped in front of me. The driver waved me to go, then hit the brakes. I couldn't stop in time.",
                    "supporting_documents": ["damage_photos_3.jpg"]
                }
            },
            "claim_data": {
                "vehicle": {
                    "make": "Mercedes",
                    "model": "C-Class",
                    "year": 2021
                }
            }
        },
        "expected_risk": "high"
    },
    
    # Test Case 5: Vague description with high claim amount
    {
        "name": "Suspicious - Vague Description with High Claim",
        "data": {
            "ingested_claim": {
                "claim_id": "CLAIM-12349",
                "policy_number": "POL-12349",
                "claim_type": "auto",
                "incident_date": (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"),
                "policy_start_date": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                "additional_data": {
                    "amount_claimed": 18000,
                    "incident_details": "Something happened to my car. Not sure what. It's damaged.",
                    "supporting_documents": []
                }
            },
            "claim_data": {
                "vehicle": {
                    "make": "Ford",
                    "model": "Focus",
                    "year": 2019
                }
            }
        },
        "expected_risk": "high"
    }
]

async def run_test_case(test_case):
    """Run a single test case and return the results."""
    print(f"\n{'='*80}")
    print(f"TEST CASE: {test_case['name']}")
    print(f"{'='*80}")
    
    # Initialize the fraud check agent
    fraud_agent = FraudCheckAgent()
    
    try:
        # Process the claim
        result = await fraud_agent.process(test_case['data'])
        
        # Extract fraud analysis
        fraud_analysis = result.data.get("fraud_analysis", {})
        risk_score = fraud_analysis.get("risk_score", 0)
        indicators = fraud_analysis.get("fraud_indicators", [])
        
        # Print the results
        print("\nCLAIM DETAILS:")
        print(f"- Type: {test_case['data']['ingested_claim'].get('claim_type', 'unknown')}")
        print(f"- Amount: ${test_case['data']['ingested_claim'].get('additional_data', {}).get('amount_claimed', 0):,.2f}")
        print(f"- Incident: {test_case['data']['ingested_claim'].get('additional_data', {}).get('incident_details', '')[:100]}...")
        
        print("\nFRAUD ANALYSIS:")
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
        if indicators:
            print("\nFRAUD INDICATORS:")
            for indicator in indicators[:5]:  # Show up to 5 indicators
                print(f"- {indicator}")
            if len(indicators) > 5:
                print(f"- ... and {len(indicators) - 5} more indicators")
        else:
            print("\nNo fraud indicators detected.")
        
        # Print recommendation
        recommendation = fraud_analysis.get("recommendation", "review").upper()
        print(f"\nRECOMMENDATION: {recommendation}")
        
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
    print("FRAUD DETECTION AGENT TEST")
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
            if result.get('indicators'):
                print(f"  Indicators: {', '.join(result['indicators'][:2])}...")
            else:
                print("  No fraud indicators")
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(main())

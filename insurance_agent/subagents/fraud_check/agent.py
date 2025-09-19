import logging
from typing import Dict, Any, List, Tuple, Optional
from google.adk.agents import Agent
from ...subagents.base_agent import BaseAgent, ProcessingResult
from datetime import datetime, timedelta
import re
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ClaimData:
    """Data class to hold claim information with validation."""
    amount_claimed: float = 0.0
    incident_details: str = ""
    claim_type: str = "auto"
    policy_start_date: Optional[str] = None
    incident_date: Optional[str] = None
    vehicle: Optional[dict] = None
    previous_claims: int = 0
    policy_number: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ClaimData':
        """Create ClaimData from dictionary with validation."""
        claim = cls()
        
        # Extract from nested structure if present
        claim_data = data.get('claim_data', {})
        additional_data = data.get('additional_data', {})
        
        # Amount claimed
        try:
            claim.amount_claimed = float(additional_data.get('amount_claimed', 0) or claim_data.get('claim_amount', 0))
            if claim.amount_claimed < 0:
                raise ValueError("Claim amount cannot be negative")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid claim amount: {e}")
            claim.amount_claimed = 0.0
        
        # Other fields
        claim.incident_details = str(additional_data.get('incident_details', claim_data.get('incident_details', '')))
        claim.claim_type = str(data.get('claim_type', claim_data.get('claim_type', 'auto'))).lower()
        claim.policy_start_date = data.get('policy_start_date', claim_data.get('policy_start_date'))
        claim.incident_date = data.get('incident_date', claim_data.get('incident_date'))
        claim.vehicle = claim_data.get('vehicle', {}) or additional_data.get('vehicle', {})
        claim.previous_claims = int(claim_data.get('previous_claims', 0) or 0)
        claim.policy_number = data.get('policy_number', claim_data.get('policy_number'))
        
        return claim

class FraudCheckAgent(BaseAgent):
    """Agent responsible for detecting potential fraud in claims."""
    
    def __init__(self):
        """Initialize the fraud check agent with default thresholds."""
        super().__init__(
            name="fraud_check_agent",
            description="Analyzes claims for potential fraud indicators"
        )
        self.agent = Agent(
            name=self.name,
            model="gemini-2.0-flash",
            description=self.description,
            instruction=(
                "You are a fraud detection agent. Your role is to analyze "
                "insurance claims for potential fraud indicators such as "
                "suspicious patterns, unusual claim amounts, or inconsistent "
                "information."
            ),
        )
    
    def _check_claim_amount(self, claim: 'ClaimData') -> tuple[list[str], float]:
        """Check if the claim amount is suspicious.
        
        Args:
            claim: ClaimData object containing claim information
            
        Returns:
            Tuple of (fraud_indicators, risk_score) where:
            - fraud_indicators: List of strings describing potential fraud indicators
            - risk_score: Numeric score from 0.0 to 1.0 indicating fraud risk
        """
        fraud_indicators = []
        risk_score = 0.0
        
        if claim.amount_claimed <= 0:
            return ["invalid_claim_amount"], 0.0
            
        logger.info(f"[FRAUD CHECK] Checking claim amount: ${claim.amount_claimed:,.2f} for {claim.claim_type} claim")
        
        # Define reasonable claim amount thresholds by claim type
        claim_limits = {
            'auto': 15000,      # Typical max for auto claims
            'home': 50000,      # Typical max for home claims
            'health': 100000,   # Typical max for health claims
            'jewelry': 10000,   # Typical max for jewelry claims
            'theft': 25000,     # Theft claims
            'vandalism': 15000, # Vandalism claims
            'default': 25000    # Default threshold for other claim types
        }
        
        # Check for extremely high claims
        if claim.amount_claimed > 100000:
            fraud_indicators.append("extremely_high_claim_amount")
            risk_score = max(risk_score, 0.9)  # Very high risk
        
        # Get threshold based on claim type
        threshold = claim_limits.get(claim.claim_type.lower(), claim_limits['default'])
        
        # Check if claim amount exceeds the threshold for the claim type
        if claim.amount_claimed > threshold:
            fraud_indicators.append(f"high_claim_amount_for_{claim.claim_type}")
            # Increase risk score based on how much over the threshold (capped at 0.7)
            risk_score = min(0.7, 0.3 + (claim.amount_claimed / threshold - 1) * 0.1)
            
        # Check for round numbers (often a sign of made-up amounts)
        if claim.amount_claimed > 1000 and claim.amount_claimed % 1000 == 0:
            fraud_indicators.append("suspicious_round_number")
            risk_score = min(1.0, risk_score + 0.3)
            
        # Check claim amount against vehicle value if available
        if claim.vehicle and claim.claim_type.lower() == 'auto':
            risk_indicators, vehicle_risk = self._check_vehicle_value(claim.vehicle, claim.amount_claimed)
            fraud_indicators.extend(risk_indicators)
            risk_score = max(risk_score, vehicle_risk)
        
        logger.info(f"[FRAUD CHECK] Claim amount risk: {risk_score:.2f}, indicators: {fraud_indicators}")
        return fraud_indicators, risk_score
        
    def _check_vehicle_value(self, vehicle: dict, claim_amount: float) -> tuple[list[str], float]:
        """Check if claim amount is reasonable for the vehicle's value."""
        fraud_indicators = []
        risk_score = 0.0
        
        try:
            make = vehicle.get('make', '').lower()
            model = vehicle.get('model', '').lower()
            year = int(vehicle.get('year', datetime.now().year))
            
            # Simple vehicle value estimation based on make, model, and year
            base_values = {
                'toyota': {
                    'camry': 25000, 'corolla': 22000, 'rav4': 28000, 'highlander': 35000, 'tacoma': 32000
                },
                'honda': {
                    'civic': 23000, 'accord': 28000, 'crv': 30000, 'pilot': 38000, 'odyssey': 36000
                },
                'bmw': {
                    '3 series': 45000, '5 series': 55000, 'x3': 48000, 'x5': 60000, 'x7': 75000
                },
                'mercedes': {
                    'c-class': 45000, 'e-class': 55000, 's-class': 110000, 'gle': 60000, 'glc': 48000
                },
                'ford': {
                    'f-150': 40000, 'explorer': 38000, 'escape': 28000, 'edge': 35000, 'mustang': 45000
                },
                'chevrolet': {
                    'silverado': 38000, 'equinox': 28000, 'tahoe': 55000, 'traverse': 35000, 'malibu': 25000
                },
                'nissan': {
                    'altima': 26000, 'rogue': 28000, 'sentra': 21000, 'murano': 35000, 'pathfinder': 36000
                }
            }
            
            # Get base value for the make and model
            make_models = base_values.get(make, {})
            base_value = make_models.get(model, 25000)  # Default to $25,000 if make/model not found
            
            # Adjust for vehicle age (2% depreciation per year, max 50%)
            age = max(0, datetime.now().year - year)
            depreciation = min(0.5, age * 0.02)
            current_value = base_value * (1 - depreciation)
            
            logger.info(f"[FRAUD CHECK] Vehicle value - Make: {make}, Model: {model}, Year: {year}, "
                       f"Base: ${base_value:,.2f}, Current: ${current_value:,.2f}")
            
            # Check if claim amount exceeds vehicle value
            if claim_amount > current_value * 0.8:  # More than 80% of vehicle value
                fraud_indicators.append("claim_exceeds_vehicle_value")
                risk_score = min(1.0, 0.5 + (claim_amount / current_value - 0.8) * 2.5)  # Scale risk from 0.5 to 1.0
                logger.warning(f"[FRAUD CHECK] Claim amount (${claim_amount:,.2f}) exceeds 80% of vehicle value (${current_value:,.2f})")
                
        except (ValueError, TypeError) as e:
            logger.warning(f"[FRAUD CHECK] Error calculating vehicle value: {e}")
            fraud_indicators.append("vehicle_value_calculation_error")
            
        return fraud_indicators, risk_score
    
    def _check_incident_details(self, claim: 'ClaimData') -> tuple[list[str], float]:
        """
        Analyze incident details for potential fraud indicators.
        
        Args:
            claim: ClaimData object containing claim information
            
        Returns:
            Tuple of (fraud_indicators, risk_score) where:
            - fraud_indicators: List of strings describing potential fraud indicators
            - risk_score: Numeric score from 0.0 to 1.0 indicating fraud risk
        """
        fraud_indicators = []
        risk_score = 0.0
        
        if not claim.incident_details:
            logger.info("[FRAUD CHECK] No incident details provided")
            return fraud_indicators, risk_score
            
        incident_lower = claim.incident_details.lower()
        logger.info(f"[FRAUD CHECK] Analyzing incident details: {claim.incident_details[:200]}...")
        
        # List of phrases indicating minor damage with their risk weights
        minor_damage_phrases = [
            ('minor', 0.2), ('slight', 0.2), ('small', 0.2), ('tap', 0.3), 
            ('bump', 0.3), ('fender bender', 0.4), ('fender-bender', 0.4),
            ('low speed', 0.3), ('low-speed', 0.3), ('scrape', 0.2), 
            ('scratch', 0.2), ('small dent', 0.3), ('cosmetic', 0.2),
            ('superficial', 0.2), ('minor damage', 0.3), ('slight damage', 0.3)
        ]
        
        # Check for minor damage indicators
        found_minor_damage = False
        for phrase, weight in minor_damage_phrases:
            if phrase in incident_lower:
                fraud_indicators.append(f"minor_damage_{phrase.replace(' ', '_')}")
                risk_score = min(1.0, risk_score + weight)
                found_minor_damage = True
        
        # If minor damage is found, check claim amount
        if found_minor_damage:
            fraud_indicators.append("minor_damage_indicated")
            logger.info("[FRAUD CHECK] Minor damage indicators found in incident details")
            
            # Higher risk for higher claim amounts with minor damage
            if claim.amount_claimed > 2000:  # Lower threshold for minor damage
                risk_increase = min(0.6, (claim.amount_claimed / 10000) * 0.3)
                risk_score = min(1.0, risk_score + risk_increase)
                fraud_indicators.append("high_claim_for_minor_damage")
                
                if claim.amount_claimed > 10000:  # Very high claim for minor damage
                    risk_score = min(1.0, risk_score + 0.3)
                    fraud_indicators.append("very_high_claim_for_minor_damage")
        
        # Check for parking lot incidents
        if 'parking lot' in incident_lower or 'parking-lot' in incident_lower:
            fraud_indicators.append("parking_lot_incident")
            logger.info("[FRAUD CHECK] Parking lot incident detected")
            
            # Higher risk for high claims in parking lots
            if claim.amount_claimed > 5000:
                risk_score = min(1.0, risk_score + 0.3)
                fraud_indicators.append("high_claim_for_parking_lot_incident")
                
                if claim.amount_claimed > 15000:
                    risk_score = min(1.0, risk_score + 0.2)
                    fraud_indicators.append("very_high_parking_lot_claim")
        
        # Check for suspicious phrases with custom weights
        suspicious_patterns = [
            (r'hit[ -]?and[ -]?run', 0.4),  # hit and run
            ('stolen', 0.5),                # stolen vehicle
            ('vandalized', 0.4),            # vandalism
            ('arson', 0.7),                 # arson is always suspicious
            ('theft', 0.4),                 # theft
            ('broken into', 0.3),           # break-in
            ('forced entry', 0.5),          # forced entry
            ('no witnesses', 0.4),          # no witnesses
            ('no police report', 0.5),      # no police report
            ('lost', 0.3),                  # lost items
            ('mystery', 0.4),               # mysterious circumstances
            ('unknown', 0.3),               # unknown causes
            ('can\'t remember', 0.4),      # memory issues
            ('not sure', 0.3),              # uncertainty
            ('maybe', 0.2),                 # hesitancy
            ('i think', 0.2),               # lack of certainty
            ('i believe', 0.2),             # lack of certainty
            ('suspicious', 0.4),            # self-reported suspicion
            ('strange', 0.3)                 # unusual circumstances
        ]
        
        # Check for suspicious patterns in the incident details
        for pattern, weight in suspicious_patterns:
            if isinstance(pattern, str) and re.search(pattern, incident_lower, re.IGNORECASE):
                # Clean the pattern for the indicator name - first remove regex special chars
                clean_pattern = pattern.replace('\\', '').replace('^', '').replace('$', '')
                # Then replace spaces with underscores
                clean_pattern = clean_pattern.replace(' ', '_')
                # Now create the indicator name
                indicator = f"suspicious_phrase_{clean_pattern}"
                fraud_indicators.append(indicator)
                risk_score = min(1.0, risk_score + weight)
            
        if len(re.findall(r'[A-Z]{4,}', claim.incident_details)) > 2:  # More than 2 ALL CAPS words
            fraud_indicators.append("excessive_capitalization")
            risk_score = min(1.0, risk_score + 0.2)
        
        logger.info(f"[FRAUD CHECK] Incident details risk: {risk_score:.2f}, indicators: {fraud_indicators}")
        return fraud_indicators, risk_score
    
    def _check_claim_timing(self, claim: 'ClaimData') -> tuple[list[str], float]:
        """
        Check for suspicious timing patterns in the claim.
        
        Args:
            claim: ClaimData object containing claim information
            
        Returns:
            Tuple of (fraud_indicators, risk_score) where:
            - fraud_indicators: List of strings describing potential fraud indicators
            - risk_score: Numeric score from 0.0 to 1.0 indicating fraud risk
        """
        fraud_indicators = []
        risk_score = 0.0
        
        if not claim.policy_start_date or not claim.incident_date:
            logger.info("[FRAUD CHECK] Missing policy start date or incident date")
            return fraud_indicators, risk_score
            
        try:
            start = datetime.strptime(claim.policy_start_date, "%Y-%m-%d")
            incident = datetime.strptime(claim.incident_date, "%Y-%m-%d")
            today = datetime.now()
            
            # Check if dates are in the future
            if start > today:
                fraud_indicators.append("future_policy_start_date")
                risk_score = max(risk_score, 0.8)
                
            if incident > today:
                fraud_indicators.append("future_incident_date")
                risk_score = max(risk_score, 0.9)
                
            # Check if incident date is before policy start date
            if incident < start:
                fraud_indicators.append("incident_before_policy_start")
                risk_score = max(risk_score, 0.95)  # Very high risk
                logger.warning("[FRAUD CHECK] Incident occurred before policy start date!")
                return fraud_indicators, risk_score
                
            days_since_start = (incident - start).days
            logger.info(f"[FRAUD CHECK] Days since policy start: {days_since_start}")
            
            # Check for weekend claims (higher risk)
            if incident.weekday() >= 5:  # Saturday or Sunday
                fraud_indicators.append("weekend_incident")
                risk_score = min(1.0, risk_score + 0.2)
                logger.info("[FRAUD CHECK] Incident occurred on a weekend")
            
            # Check for holiday periods (higher risk)
            holiday_periods = [
                (12, 15, 1, 5),   # Winter holidays (Dec 15 - Jan 5)
                (6, 1, 9, 1),     # Summer (Jun 1 - Sep 1)
                (10, 15, 11, 15)  # Fall (Oct 15 - Nov 15)
            ]
            
            for start_month, start_day, end_month, end_day in holiday_periods:
                start_date = incident.replace(month=start_month, day=start_day)
                end_date = incident.replace(month=end_month, day=end_day)
                
                # Handle year wrap-around for holiday periods
                if start_month > end_month:  # e.g., Dec to Jan
                    if incident.month >= start_month or incident.month <= end_month:
                        fraud_indicators.append(f"holiday_season_incident_{start_month}_{end_month}")
                        risk_score = min(1.0, risk_score + 0.3)
                        logger.info(f"[FRAUD CHECK] Incident occurred during holiday season ({start_month}/{start_day} - {end_month}/{end_day})")
                else:
                    if start_date <= incident <= end_date:
                        fraud_indicators.append(f"holiday_season_incident_{start_month}_{end_month}")
                        risk_score = min(1.0, risk_score + 0.3)
                        logger.info(f"[FRAUD CHECK] Incident occurred during holiday season ({start_month}/{start_day} - {end_month}/{end_day})")
            
            # Higher risk for claims soon after policy start
            if days_since_start <= 30:  # Within first 30 days
                fraud_indicators.append("claim_within_30_days_of_policy_start")
                logger.info("[FRAUD CHECK] Claim within 30 days of policy start")
                
                # Base risk for new policy claim (0.4 to 0.8 based on claim amount)
                base_risk = min(0.8, 0.4 + (claim.amount_claimed / 50000))
                
                # Scale risk based on days since policy start (higher risk for newer policies)
                day_multiplier = 1.0 - (days_since_start / 30)
                risk_increase = base_risk * day_multiplier
                
                # Higher multiplier for large claims
                if claim.amount_claimed > 20000:
                    risk_increase *= 1.5
                
                risk_score = min(1.0, risk_score + risk_increase)
                
                # Additional check for claims within first week
                if days_since_start <= 7:
                    fraud_indicators.append("claim_within_7_days_of_policy_start")
                    risk_score = min(1.0, risk_score + 0.3)
                    logger.warning("[FRAUD CHECK] Claim within first week of policy!")
                    
                    # If it's also a high value claim, flag for immediate review
                    if claim.amount_claimed > 20000:
                        fraud_indicators.append("high_risk_new_policy_claim")
                        risk_score = max(risk_score, 0.95)  # Very high risk
                        logger.warning("[FRAUD CHECK] High value claim within first week of policy!")
            
            # Check for claims just before policy expiration
            policy_duration = 365  # Assuming 1-year policy for simplicity
            days_until_expiry = policy_duration - days_since_start
            
            if 0 <= days_until_expiry <= 30:  # Within last 30 days of policy
                fraud_indicators.append("claim_near_policy_expiry")
                risk_score = min(1.0, risk_score + 0.4)  # Higher risk for end-of-policy claims
                logger.info("[FRAUD CHECK] Claim near policy expiration")
                
                # If it's a high value claim near policy end, increase risk
                if claim.amount_claimed > 10000:
                    risk_score = min(1.0, risk_score + 0.3)
                    fraud_indicators.append("high_value_claim_near_policy_end")
                
        except (ValueError, TypeError) as e:
            logger.error(f"[FRAUD CHECK] Error processing dates: {e}")
            fraud_indicators.append("date_processing_error")
            
        logger.info(f"[FRAUD CHECK] Timing risk: {risk_score:.2f}, indicators: {fraud_indicators}")
        return fraud_indicators, risk_score
    
    async def process(self, ingested_data: dict) -> ProcessingResult:
        """
        Process the ingested data to check for potential fraud indicators.
        
        Args:
            ingested_data: Dictionary containing claim data with the following structure:
                - claim_data: Original claim data including vehicle information
                - additional_data: Additional claim details including amount_claimed, incident_details, etc.
                - policy_number: The policy number
                - policy_start_date: When the policy started (YYYY-MM-DD)
                - incident_date: When the incident occurred (YYYY-MM-DD)
                - claim_type: Type of claim (auto, home, etc.)
                
        Returns:
            ProcessingResult containing fraud analysis with risk score and indicators
        """
        try:
            logger.info("=" * 80)
            logger.info("[FRAUD CHECK] Starting fraud detection process")
            logger.info("-" * 80)
            
            # Parse and validate input data
            try:
                claim = ClaimData.from_dict(ingested_data)
                logger.info(f"[FRAUD CHECK] Processed claim data: {claim}")
            except Exception as e:
                logger.error(f"[FRAUD CHECK] Error parsing claim data: {e}", exc_info=True)
                return ProcessingResult(
                    success=False,
                    error={
                        'code': 'INVALID_CLAIM_DATA',
                        'message': 'The provided claim data is invalid',
                        'details': str(e)
                    }
                )
            
            # Log the claim being processed
            claim_id = ingested_data.get('claim_id', 'unknown')
            logger.info(f"[FRAUD CHECK] Processing claim: {claim_id}")
            logger.info(f"[FRAUD CHECK] Claim amount: ${claim.amount_claimed:,.2f}")
            logger.info(f"[FRAUD CHECK] Claim type: {claim.claim_type}")
            
            # Initialize results
            fraud_indicators = []
            risk_score = 0.0
            risk_factors = {}
            requires_manual_review = False
            fraud_analysis = {}  # Initialize fraud_analysis dictionary
            
            # Run fraud detection checks
            try:
                # 1. Check claim amount
                amount_indicators, amount_risk = self._check_claim_amount(claim)
                fraud_indicators.extend(amount_indicators)
                risk_score = max(risk_score, amount_risk)
                risk_factors["claim_amount_risk"] = round(amount_risk, 4)
                
                # 2. Check incident details
                incident_indicators, incident_risk = self._check_incident_details(claim)
                fraud_indicators.extend(incident_indicators)
                risk_score = max(risk_score, incident_risk)
                risk_factors["incident_details_risk"] = round(incident_risk, 4)
                
                # 3. Check claim timing
                timing_indicators, timing_risk = self._check_claim_timing(claim)
                fraud_indicators.extend(timing_indicators)
                risk_score = max(risk_score, timing_risk)
                risk_factors["timing_risk"] = round(timing_risk, 4)
                
                # 4. Check for previous claims
                if claim.previous_claims > 0:
                    prev_claims_risk = min(0.5, 0.1 * min(claim.previous_claims, 5))
                    fraud_indicators.append(f"previous_claims_{claim.previous_claims}")
                    risk_score = min(1.0, risk_score + prev_claims_risk)
                    risk_factors["previous_claims_risk"] = round(prev_claims_risk, 4)
                else:
                    risk_factors["previous_claims_risk"] = 0.0
                
                # 5. Check for high-value claims and vehicle value
                vehicle_value = self._estimate_vehicle_value(claim.vehicle)
                fraud_analysis["vehicle_value"] = vehicle_value
                fraud_analysis["fraud_indicators"] = fraud_indicators
                fraud_analysis["risk_score"] = risk_score
                
                if vehicle_value > 0:
                    excessive_claim_ratio = min(5.0, claim.amount_claimed / vehicle_value)
                    fraud_analysis["claim_to_value_ratio"] = excessive_claim_ratio
                    
                    # Check if claim amount is reasonable for the vehicle value
                    if excessive_claim_ratio > 1.5:  # Claim is 50%+ higher than vehicle value
                        risk_increase = min(0.9, 0.4 + (excessive_claim_ratio - 1.5) * 0.5)
                        fraud_indicators.append(f"excessive_claim_ratio_{excessive_claim_ratio:.1f}x")
                        risk_score = min(1.0, risk_score + risk_increase)
                        risk_factors["excessive_claim_ratio"] = round(excessive_claim_ratio, 2)
                    
                    # Flag claims that exceed vehicle value
                    if claim.amount_claimed > vehicle_value * 1.1:  # 10% over vehicle value
                        fraud_indicators.append("claim_exceeds_vehicle_value")
                        risk_score = min(1.0, risk_score + 0.6)
                
                # Check for absolute high value claims
                if claim.amount_claimed > 100000:  # Over $100k is extremely high for auto
                    fraud_indicators.append("extremely_high_value_claim")
                    risk_score = min(1.0, risk_score + 0.7)  # Very high risk
                    risk_factors["extremely_high_value"] = claim.amount_claimed
                elif claim.amount_claimed > 50000:  # $50k-$100k
                    fraud_indicators.append("very_high_value_claim")
                    risk_score = min(1.0, risk_score + 0.4)
                    risk_factors["very_high_value"] = claim.amount_claimed
                elif claim.amount_claimed > 20000:  # $20k-$50k
                    fraud_indicators.append("high_value_claim")
                    risk_score = min(1.0, risk_score + 0.2)
                    risk_factors["high_value"] = claim.amount_claimed
                
                # 6. Check for minor damage with high claim amount
                minor_damage_phrases = [
                    'minor', 'fender bender', 'scratch', 'dent', 'small damage',
                    'parking lot', 'low speed', 'bump', 'tap', 'scrape', 'ding',
                    'small dent', 'paint scratch', 'cosmetic', 'minor damage'
                ]
                
                incident_lower = claim.incident_details.lower()
                has_minor_damage = any(phrase in incident_lower for phrase in minor_damage_phrases)
                
                if has_minor_damage:
                    fraud_indicators.append("minor_damage_indicated")
                    risk_factors["minor_damage_incident"] = True
                    
                    # Base risk for any minor damage claim
                    base_risk = 0.4
                    risk_score = max(risk_score, base_risk)
                    
                    # Calculate additional risk based on claim amount for minor damage
                    if claim.amount_claimed > 5000:  # Over $5k for minor damage is suspicious
                        # More aggressive scaling for higher claim amounts
                        amount_factor = min(1.0, (claim.amount_claimed - 5000) / 10000)  # Scales from 0 to 1 as amount goes from 5k to 100k
                        risk_increase = 0.3 + (0.6 * amount_factor)  # Between 0.3 and 0.9 based on amount
                        
                        fraud_indicators.append("high_claim_for_minor_damage")
                        risk_score = min(1.0, max(risk_score, base_risk + risk_increase))
                        risk_factors["high_claim_minor_damage"] = claim.amount_claimed
                        
                        # Additional flags for very high claims
                        if claim.amount_claimed > 50000:  # Over $50k is extremely suspicious
                            fraud_indicators.append("extremely_high_claim_for_minor_damage")
                            risk_score = min(1.0, max(risk_score, 0.9))  # Very high risk
                        elif claim.amount_claimed > 20000:  # Over $20k is very suspicious
                            fraud_indicators.append("very_high_claim_for_minor_damage")
                            risk_score = min(1.0, max(risk_score, 0.7))  # High risk
                
                # Check for parking lot incidents specifically
                if 'parking' in incident_lower:
                    fraud_indicators.append("parking_lot_incident")
                    if claim.amount_claimed > 5000:
                        fraud_indicators.append("high_claim_parking_incident")
                        risk_increase = min(0.6, 0.3 + (min(claim.amount_claimed, 100000) - 5000) / 200000)
                        risk_score = min(1.0, risk_score + risk_increase)
                        risk_factors["parking_lot_high_claim"] = claim.amount_claimed
                
                # 7. Add vehicle value estimation to context
                if vehicle_value > 0:
                    fraud_analysis["vehicle_value"] = vehicle_value
                    fraud_analysis["claim_to_value_ratio"] = round(claim.amount_claimed / vehicle_value, 2)
                    
                    if claim.amount_claimed > vehicle_value * 1.1:  # Claim exceeds vehicle value + 10%
                        fraud_indicators.append("claim_exceeds_vehicle_value")
                        risk_score = min(1.0, risk_score + 0.6)
                
                # 8. Check for new policy claims
                if claim.policy_start_date and claim.incident_date:
                    try:
                        start = datetime.strptime(claim.policy_start_date, "%Y-%m-%d")
                        incident = datetime.strptime(claim.incident_date, "%Y-%m-%d")
                        days_since_start = (incident - start).days
                        
                        if 0 <= days_since_start <= 30:  # Within first 30 days
                            risk_increase = 0.3 * (1 - (days_since_start / 30))  # Gradual decrease in risk
                            fraud_indicators.append(f"claim_within_30_days_of_policy_start")
                            risk_score = min(1.0, risk_score + risk_increase)
                            
                            if days_since_start <= 7:  # Within first week
                                fraud_indicators.append("claim_within_first_week")
                                risk_score = min(1.0, risk_score + 0.2)  # Additional risk for first week
                                
                                if claim.amount_claimed > 50000:  # Only flag very high value claims in first week
                                    fraud_indicators.append("high_risk_new_policy_claim")
                                    risk_score = min(1.0, risk_score + 0.2)
                    except (ValueError, TypeError) as e:
                        logger.error(f"[FRAUD CHECK] Error processing policy dates: {e}")
                
                # Cap risk score at 1.0 and ensure high scores from any single factor are preserved
                risk_score = min(1.0, risk_score)
                
                # Special case: Any claim over $100k with minor damage should be flagged as high risk
                if has_minor_damage and claim.amount_claimed > 100000:
                    risk_score = max(risk_score, 0.95)  # Very high risk
                    if 'extremely_high_claim_for_minor_damage' not in fraud_indicators:
                        fraud_indicators.append("extremely_high_claim_for_minor_damage")
                
                # Update fraud_analysis with final values
                fraud_analysis["fraud_indicators"] = list(set(fraud_indicators))  # Remove duplicates
                fraud_analysis["risk_score"] = risk_score
                fraud_analysis["risk_factors"] = risk_factors
                
                # Determine recommendation
                needs_review = False
                recommendation = "approve"
                
                if risk_score >= 0.9:
                    needs_review = True
                    recommendation = "reject"
                    logger.warning(f"[FRAUD CHECK] Claim flagged for rejection. Risk score: {risk_score:.2f}")
                elif risk_score >= 0.7:
                    needs_review = True
                    recommendation = "review_required"
                    logger.info(f"[FRAUD CHECK] Claim requires review. Risk score: {risk_score:.2f}")
                elif risk_score >= 0.4:
                    needs_review = True
                    recommendation = "review_recommended"
                    logger.info(f"[FRAUD CHECK] Claim review recommended. Risk score: {risk_score:.2f}")
                else:
                    logger.info(f"[FRAUD CHECK] Claim appears legitimate. Risk score: {risk_score:.2f}")
                
                # Prepare claim context
                claim_context = {}
                try:
                    if claim.policy_start_date and claim.incident_date:
                        start = datetime.strptime(claim.policy_start_date, "%Y-%m-%d")
                        incident = datetime.strptime(claim.incident_date, "%Y-%m-%d")
                        days_since_start = (incident - start).days
                        claim_context = {
                            "days_since_policy_start": days_since_start,
                            "is_new_policy": days_since_start <= 30,
                            "is_very_new_policy": days_since_start <= 7,
                            "policy_duration_days": days_since_start
                        }
                except (ValueError, TypeError) as e:
                    logger.error(f"[FRAUD CHECK] Error preparing claim context: {e}")
                    claim_context = {"error": "Error calculating policy duration"}
                
                # Update the fraud analysis result with final values
                fraud_analysis.update({
                    "risk_score": round(risk_score, 4),
                    "fraud_indicators": sorted(list(set(fraud_indicators))),  # Remove duplicates
                    "needs_review": needs_review,
                    "recommendation": recommendation,
                    "risk_factors": risk_factors,
                    "claim_context": {
                        "claim_amount": claim.amount_claimed,
                        "claim_type": claim.claim_type,
                        "incident_date": claim.incident_date,
                        "policy_start_date": claim.policy_start_date,
                        "policy_number": claim.policy_number,
                        **claim_context
                    }
                })
                
                # Determine if manual review is required
                requires_manual_review = (
                    risk_score >= 0.8 or  # Higher threshold for auto-approval
                    any(indicator in [
                        'very_high_claim_for_minor_damage',
                        'high_risk_new_policy_claim',
                        'claim_within_first_week',
                        'suspicious_pattern_detected'
                    ] for indicator in fraud_indicators)
                )
                
                # Prepare the response with enhanced structure
                result_data = {
                    "fraud_analysis": fraud_analysis,
                    "claim_id": ingested_data.get('claim_id', 'unknown'),
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0.0",
                    "risk_assessment": {
                        "risk_score": round(risk_score, 2),
                        "risk_level": self._get_risk_level(risk_score),
                        "requires_manual_review": requires_manual_review,
                        "recommendation": "REVIEW_REQUIRED" if requires_manual_review else "AUTO_APPROVE",
                        "key_findings": self._get_key_findings(fraud_analysis, risk_score)
                    },
                    "next_steps": [
                        "Claim approved for processing" if not requires_manual_review 
                        else "Manual review required due to detected risk factors"
                    ]
                }
                
                # Log the final result with more details
                logger.info("=" * 80)
                logger.info("[FRAUD CHECK] Final fraud analysis result:")
                logger.info(f"- Risk Score: {risk_score:.2f}")
                logger.info(f"- Risk Level: {result_data['risk_assessment']['risk_level']}")
                logger.info(f"- Manual Review Required: {result_data['risk_assessment']['requires_manual_review']}")
                logger.info(f"- Recommendation: {result_data['risk_assessment']['recommendation']}")
                logger.info(f"- Fraud Indicators: {', '.join(sorted(list(set(fraud_indicators))))}")
                logger.info(f"- Key Findings: {', '.join(result_data['risk_assessment']['key_findings'])}")
                logger.info("=" * 80)
                
                return ProcessingResult(
                    success=True,
                    data=result_data
                )
                
            except Exception as e:
                logger.error(f"[FRAUD CHECK] Error during fraud detection: {e}", exc_info=True)
                raise  # Re-raise to be caught by the outer try-except
                
        except Exception as e:
            error_msg = f"Error analyzing claim for fraud: {str(e)}"
            logger.error(f"[FRAUD CHECK] Critical error processing claim: {error_msg}", exc_info=True)
            
            # Format the error response as a string to avoid validation issues
            error_response = (
                f"FRAUD_CHECK_ERROR: An error occurred during fraud detection. "
                f"Details: {str(e)[:500]}"
            )
            
            # Return a properly formatted ProcessingResult with error as a string
            return ProcessingResult(
                success=False,
                data={
                    "error": error_response,
                    "fraud_indicators": ["error_processing_fraud_check"],
                    "risk_score": 1.0,  # Maximum risk score for processing errors
                    "needs_review": True
                },
                error=error_response  # This must be a string
            )

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert numeric risk score to a human-readable level."""
        if risk_score >= 0.8:
            return "CRITICAL"
        elif risk_score >= 0.6:
            return "HIGH"
        elif risk_score >= 0.4:
            return "MEDIUM"
        elif risk_score >= 0.2:
            return "LOW"
        return "MINIMAL"
        
    def _get_key_findings(self, fraud_analysis: dict, risk_score: float) -> list[str]:
        """Extract key findings from the fraud analysis."""
        findings = []
        
        # Risk level indicators
        if risk_score >= 0.8:
            findings.append("CRITICAL RISK: High probability of potential fraud detected")
        elif risk_score >= 0.6:
            findings.append("HIGH RISK: Significant indicators of potential fraud detected")
        elif risk_score >= 0.4:
            findings.append("MODERATE RISK: Some indicators of potential fraud detected")
            
        # Check for new policy claims
        claim_timing = fraud_analysis.get("claim_context", {})
        if claim_timing.get("is_very_new_policy", False):
            findings.append("⚠️ Claim filed within 7 days of policy start (high risk)")
        elif claim_timing.get("is_new_policy", False):
            findings.append("⚠️ Claim filed within 30 days of policy start")
            
        # Check for high value claims
        claim_amount = fraud_analysis.get("claim_context", {}).get("claim_amount")
        if claim_amount:
            if claim_amount > 100000:
                findings.append(f"🚨 EXTREMELY HIGH VALUE CLAIM: ${claim_amount:,.2f}")
            elif claim_amount > 50000:
                findings.append(f"⚠️ High value claim: ${claim_amount:,.2f}")
                
        # Check for minor damage indicators
        if fraud_analysis.get("fraud_indicators"):
            indicators = fraud_analysis["fraud_indicators"]
            
            # Minor damage indicators
            minor_damage_indicators = [i for i in indicators if 'minor' in i or 'fender' in i or 'scratch' in i]
            if minor_damage_indicators and claim_amount and claim_amount > 10000:
                findings.append(f"🚨 Minor damage with high claim amount (${claim_amount:,.2f})")
            
            # Other suspicious indicators
            other_indicators = [i for i in indicators 
                              if not i.startswith("previous_claims_") 
                              and 'minor' not in i 
                              and 'fender' not in i 
                              and 'scratch' not in i]
            if other_indicators:
                findings.append("⚠️ Suspicious indicators detected")
                
        # Check vehicle value ratio if available
        if fraud_analysis.get("claim_context", {}).get("claim_amount") and \
           fraud_analysis.get("vehicle_value"):
            ratio = (fraud_analysis["claim_context"]["claim_amount"] / 
                    fraud_analysis["vehicle_value"])
            if ratio > 1.0:
                findings.append(f"⚠️ Claim amount is {ratio:.1f}x vehicle value")
            
        return findings or ["No significant risk factors detected"]
        
    def _estimate_vehicle_value(self, vehicle: dict) -> float:
        """Estimate the market value of a vehicle based on make, model, and year.
        
        In a production environment, this would call an external vehicle valuation service.
        For this example, we'll use simplified estimates.
        """
        if not vehicle or not all(k in vehicle for k in ['make', 'model', 'year']):
            return 0
            
        # Base values by vehicle type (simplified)
        current_year = datetime.now().year
        age = max(0, current_year - int(vehicle['year']))
        
        # Base values by make (simplified)
        make_values = {
            'toyota': {
                'camry': 25000,
                'corolla': 22000,
                'rav4': 28000,
                'highlander': 36000,
                'default': 25000
            },
            'honda': {
                'accord': 27000,
                'civic': 24000,
                'cr-v': 30000,
                'pilot': 38000,
                'default': 28000
            },
            'ford': {
                'f-150': 38000,
                'explorer': 35000,
                'escape': 28000,
                'mustang': 32000,
                'default': 30000
            },
            'default': {
                'default': 30000
            }
        }
        
        # Get base value for make and model
        make = vehicle['make'].lower()
        model = vehicle['model'].lower()
        
        make_dict = make_values.get(make, make_values['default'])
        base_value = make_dict.get(model, make_dict['default'])
        
        # Apply depreciation (simplified)
        # 15% depreciation in first year, 10% per year after
        if age == 0:
            value = base_value * 0.85
        else:
            value = base_value * (0.85 * (0.9 ** (age - 1)))
            
        # Ensure minimum value
        value = max(1000, value)
        
        logger.info(f"[FRAUD CHECK] Estimated value for {vehicle['year']} {make.title()} {model.title()}: ${value:,.2f}")
        return value

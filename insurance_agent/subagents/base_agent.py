from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# Import BaseModel from pydantic with a try-except for compatibility
try:
    from pydantic import BaseModel
except ImportError:
    # Fallback for older pydantic versions
    from pydantic.main import BaseModel

class ProcessingResult(BaseModel):
    """Base result model for agent processing."""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None

class BaseAgent(ABC):
    """Base class for all insurance claim processing agents."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def process(self, claim_data: Dict[str, Any]) -> ProcessingResult:
        """Process the claim data.
        
        Args:
            claim_data: The claim data to process
            
        Returns:
            ProcessingResult containing the result of processing
        """
        pass
    
    def __str__(self):
        return f"{self.name}: {self.description}"

from pydantic import BaseModel, Field, computed_field
from typing import Optional, Dict
from enum import Enum
from datetime import datetime, timezone

class EmploymentCompetency(str, Enum):
    """The 12 workplace competencies woven into all content."""
    COMMUNICATION = "communication"
    COLLABORATION = "collaboration"  
    PROBLEM_SOLVING = "problem_solving"
    LEARNING_AGILITY = "learning_agility"
    SELF_TIME_MANAGEMENT = "self_time_management"
    WORK_ETHIC = "work_ethic"
    RESULTS_ORIENTATION = "results_orientation"
    TECH_FLUENCY = "tech_fluency"
    INTERPERSONAL = "interpersonal"
    INITIATIVE = "initiative"
    INTEGRITY_ACCOUNTABILITY = "integrity_accountability"
    ADAPTABILITY = "adaptability"

class CompetencyLevel(BaseModel):
    """Tracks a learner's demonstrated competency level."""
    competency: EmploymentCompetency
    demonstrated_count: int = 0       
    prompted_count: int = 0           
    last_exposure: Optional[datetime] = None  # Crucial for the decay function
    strength: float = 0.0             # 0.0-1.0 Bayesian posterior probability
    
    @computed_field
    @property
    def days_since_exposure(self) -> float:
        """Calculates time decay to prevent competency starvation."""
        if not self.last_exposure:
            return 999.0 # Max priority for unseen competencies
        delta = datetime.now(timezone.utc) - self.last_exposure
        return delta.total_seconds() / 86400.0

class CompetencyProfile(BaseModel):
    """Full competency map for a learner, stored in PostgresStore."""
    learner_id: str
    competencies: Dict[EmploymentCompetency, CompetencyLevel] = Field(default_factory=dict)
    target_career_cluster: str = ""
    cluster_weight_overrides: Dict[EmploymentCompetency, float] = Field(default_factory=dict) 

    def calculate_injection_weights(self, current_academic_skill: str) -> dict[EmploymentCompetency, float]:
        """
        The core dynamic scheduling algorithm. 
        Calculates the exact priority of every competency right now.
        """
        weights = {}
        for comp in EmploymentCompetency:
            # 1. Initialize or get current state
            level = self.competencies.get(comp)
            if not level:
                level = CompetencyLevel(competency=comp)
                self.competencies[comp] = level

            # 2. Base need (inversely proportional to current strength)
            base_need = 1.0 - level.strength
            
            # 3. Apply career target multiplier (default 1.0, overridden if highly relevant)
            career_multiplier = self.cluster_weight_overrides.get(comp, 1.0)
            
            # 4. Time decay multiplier (increases weight if ignored for a long time)
            time_multiplier = 1.0 + (level.days_since_exposure * 0.1)

            # 5. Calculate final selection probability
            weights[comp] = base_need * career_multiplier * time_multiplier

        return weights

"""Threat prioritizer stub for Pylance availability."""

from enum import Enum

class ThreatLevel(Enum):
    CRITICAL = 0.9
    HIGH = 0.7
    MEDIUM = 0.5
    LOW = 0.25
    SAFE = 0.0

class ThreatType(Enum):
    COLLISION = "collision"
    PEDESTRIAN = "pedestrian"
    LANE_DEPARTURE = "lane_departure"
    BLIND_SPOT = "blind_spot"

class MultiThreatPrioritizer:
    def __init__(self):
        self.threats = []

    def register_threat(self, threat_type: ThreatType, score: float):
        self.threats.append((threat_type, score))

    def get_overall_risk(self):
        if not self.threats:
            return 0.0, ThreatType.SAFE
        highest = max(self.threats, key=lambda t: t[1])
        return highest[1], highest[0]

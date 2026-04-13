from pydantic import BaseModel, Field
from typing import List

class AiParseItem(BaseModel):
    label: str
    value: str
    conf: int

class Metrics(BaseModel):
    assembliesAffected: int
    inspectionSteps: int
    documents: int
    effort: int
    revisionType: str
    revisionLabel: str
    safetyFactor: float
    safetyStatus: str

class AssemblyImpactItem(BaseModel):
    assembly: str
    level: str
    constraint: str
    status: str

class InspectionImpactItem(BaseModel):
    stepId: str
    keywordMatch: str
    actionRequired: str

class RevisionRule(BaseModel):
    id: str
    desc: str
    triggered: bool

class EffortEstimateItem(BaseModel):
    label: str
    hours: int
    color: str

class BarlowValidation(BaseModel):
    s: str
    tOriginal: str
    tProposed: str
    d: str
    originalSf: float
    proposedSf: float
    status: str

class DocumentRegisterItem(BaseModel):
    docId: str
    title: str
    status: str

class EwrAnalysisResponse(BaseModel):
    aiParse: List[AiParseItem]
    metrics: Metrics
    assemblyImpact: List[AssemblyImpactItem]
    inspectionImpact: List[InspectionImpactItem]
    revisionRules: List[RevisionRule]
    effortEstimate: List[EffortEstimateItem]
    barlowValidation: BarlowValidation
    narrative: str
    documentRegister: List[DocumentRegisterItem]

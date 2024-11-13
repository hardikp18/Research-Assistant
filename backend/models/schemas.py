from pydantic import BaseModel
from typing import List, Optional, Dict

class Paper(BaseModel):
    id: str
    title: str
    authors: List[str]
    abstract: str
    year: int
    url: str
    has_full_text: bool
    has_images: bool
    full_text: Optional[str] = None
    images: Optional[List[Dict]] = None

class PaperRequest(BaseModel):
    topic: str
    year_range: Optional[int] = 5

class QuestionRequest(BaseModel):
    paper: List[Paper]
    question: str

class ReviewRequest(BaseModel):
    paper: List[Paper]

class SearchRequest(BaseModel):
    topic: str
    max_results: Optional[int] = 10
    
class FutureWorkRequest(BaseModel):
    paper_ids: List[str]

class ImprovementPlanRequest(BaseModel):
    paper_ids: List[str]

class GenerateReviewRequest(BaseModel):
    paper_ids: List[str]
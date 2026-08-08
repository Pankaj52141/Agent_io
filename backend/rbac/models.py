from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel

class Role(str, Enum):
    ceo = "ceo"
    cto = "cto"
    cfo = "cfo"

class User(BaseModel):
    email: str
    name: str
    role: Role
    password_hash: str

class TokenData(BaseModel):
    email: str
    role: Role
    exp: Optional[int] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_name: str
    user_role: str

class DataChunk(BaseModel):
    id: str
    content: str
    source_file: str
    page_or_sheet: Optional[str] = None
    section: Optional[str] = None
    data_category: str
    fiscal_year: Optional[str] = None
    fiscal_quarter: Optional[str] = None
    metadata: Dict = {}

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    access_note: Optional[str] = None

class FeedbackRequest(BaseModel):
    query_id: str
    rating: bool
    correction: Optional[str] = None
    preferred_answer: Optional[str] = None

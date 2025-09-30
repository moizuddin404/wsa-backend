from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VideoCreate(BaseModel):
    title: str
    description: str
    video_url: str
    thumbnail_url: str
    duration: int
    category: str
    difficulty: str

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None

class VideoResponse(BaseModel):
    id: str
    title: str
    description: str
    video_url: str
    thumbnail_url: str
    duration: int
    category: str
    difficulty: str
    views: int
    likes: int
    created_at: datetime
    updated_at: datetime
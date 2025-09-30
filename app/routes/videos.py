from fastapi import APIRouter, HTTPException, status
from app.database import get_database
from app.schemas.video import VideoCreate, VideoUpdate, VideoResponse
from typing import List
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/videos", tags=["videos"])

@router.get("/", response_model=List[VideoResponse])
async def get_all_videos(
    category: str = None,
    difficulty: str = None,
    skip: int = 0,
    limit: int = 20
):
    """Get all videos with optional filtering"""
    db = await get_database()
    
    query = {}
    if category:
        query["category"] = category
    if difficulty:
        query["difficulty"] = difficulty
    
    videos = await db.videos.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    return [
        VideoResponse(
            id=str(video["_id"]),
            title=video["title"],
            description=video["description"],
            video_url=video["video_url"],
            thumbnail_url=video["thumbnail_url"],
            duration=video["duration"],
            category=video["category"],
            difficulty=video["difficulty"],
            views=video.get("views", 0),
            likes=video.get("likes", 0),
            created_at=video.get("created_at", datetime.utcnow()),
            updated_at=video.get("updated_at", datetime.utcnow())
        )
        for video in videos
    ]

@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str):
    """Get a single video by ID"""
    db = await get_database()
    
    if not ObjectId.is_valid(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")
    
    video = await db.videos.find_one({"_id": ObjectId(video_id)})
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return VideoResponse(
        id=str(video["_id"]),
        title=video["title"],
        description=video["description"],
        video_url=video["video_url"],
        thumbnail_url=video["thumbnail_url"],
        duration=video["duration"],
        category=video["category"],
        difficulty=video["difficulty"],
        views=video.get("views", 0),
        likes=video.get("likes", 0),
        created_at=video.get("created_at", datetime.utcnow()),
        updated_at=video.get("updated_at", datetime.utcnow())
    )

@router.post("/", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(video: VideoCreate):
    """Create a new video tutorial"""
    db = await get_database()
    
    video_dict = video.dict()
    video_dict["views"] = 0
    video_dict["likes"] = 0
    video_dict["created_at"] = datetime.utcnow()
    video_dict["updated_at"] = datetime.utcnow()
    
    result = await db.videos.insert_one(video_dict)
    created_video = await db.videos.find_one({"_id": result.inserted_id})
    
    return VideoResponse(
        id=str(created_video["_id"]),
        **{k: v for k, v in created_video.items() if k != "_id"}
    )

@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(video_id: str, video_update: VideoUpdate):
    """Update a video"""
    db = await get_database()
    
    if not ObjectId.is_valid(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")
    
    update_data = {k: v for k, v in video_update.dict().items() if v is not None}
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.videos.update_one(
            {"_id": ObjectId(video_id)},
            {"$set": update_data}
        )
    
    updated_video = await db.videos.find_one({"_id": ObjectId(video_id)})
    
    if not updated_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return VideoResponse(
        id=str(updated_video["_id"]),
        **{k: v for k, v in updated_video.items() if k != "_id"}
    )

@router.post("/{video_id}/view")
async def increment_view(video_id: str):
    """Increment video view count"""
    db = await get_database()
    
    if not ObjectId.is_valid(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")
    
    result = await db.videos.update_one(
        {"_id": ObjectId(video_id)},
        {"$inc": {"views": 1}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {"message": "View counted"}

@router.post("/{video_id}/like")
async def toggle_like(video_id: str):
    """Toggle like for a video"""
    db = await get_database()
    
    if not ObjectId.is_valid(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")
    
    result = await db.videos.update_one(
        {"_id": ObjectId(video_id)},
        {"$inc": {"likes": 1}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {"message": "Like toggled"}

@router.delete("/{video_id}")
async def delete_video(video_id: str):
    """Delete a video"""
    db = await get_database()
    
    if not ObjectId.is_valid(video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID")
    
    result = await db.videos.delete_one({"_id": ObjectId(video_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {"message": "Video deleted successfully"}
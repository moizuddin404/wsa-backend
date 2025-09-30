from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.database import get_database

router = APIRouter(prefix="/contacts", tags=["contacts"])

# Pydantic Models
class TrustedContactBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    relationship: str = Field(..., min_length=1, max_length=50)
    
class TrustedContactCreate(TrustedContactBase):
    user_id: str = Field(..., description="ID of the user who owns this contact")

class TrustedContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    relationship: Optional[str] = Field(None, min_length=1, max_length=50)

class TrustedContactResponse(TrustedContactBase):
    id: str
    user_id: str
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NotifyContactRequest(BaseModel):
    contact_id: str
    message: str = "Emergency! I need help. Please check on me."
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None

# ✅ NEW MODEL for notify-all
class NotifyAllRequest(BaseModel):
    message: str = "Emergency! I need help. Please check on me."
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None

# Helper function to convert MongoDB document to dict
def contact_helper(contact) -> dict:
    return {
        "id": str(contact["_id"]),
        "user_id": contact["user_id"],
        "name": contact["name"],
        "phone": contact["phone"],
        "relationship": contact["relationship"],
        "is_verified": contact.get("is_verified", False),
        "created_at": contact["created_at"],
        "updated_at": contact["updated_at"]
    }

# GET all contacts for a user
@router.get("/user/{user_id}", response_model=List[TrustedContactResponse])
async def get_user_contacts(user_id: str):
    db = await get_database()
    contacts = []
    async for contact in db.trusted_contacts.find({"user_id": user_id}):
        contacts.append(contact_helper(contact))
    return contacts

# GET single contact by ID
@router.get("/{contact_id}", response_model=TrustedContactResponse)
async def get_contact(contact_id: str):
    db = await get_database()
    try:
        contact = await db.trusted_contacts.find_one({"_id": ObjectId(contact_id)})
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact ID format")
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact_helper(contact)

# POST create new contact
@router.post("/", response_model=TrustedContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(contact: TrustedContactCreate):
    db = await get_database()
    
    contact_count = await db.trusted_contacts.count_documents({"user_id": contact.user_id})
    if contact_count >= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum of 5 trusted contacts allowed")
    
    existing = await db.trusted_contacts.find_one({"user_id": contact.user_id, "phone": contact.phone})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contact with this phone number already exists")
    
    now = datetime.utcnow()
    contact_dict = {
        "user_id": contact.user_id,
        "name": contact.name,
        "phone": contact.phone,
        "relationship": contact.relationship,
        "is_verified": False,
        "created_at": now,
        "updated_at": now
    }
    
    result = await db.trusted_contacts.insert_one(contact_dict)
    contact_dict["_id"] = result.inserted_id
    return contact_helper(contact_dict)

# PUT update contact
@router.put("/{contact_id}", response_model=TrustedContactResponse)
async def update_contact(contact_id: str, contact_update: TrustedContactUpdate):
    db = await get_database()
    try:
        object_id = ObjectId(contact_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact ID format")
    
    existing_contact = await db.trusted_contacts.find_one({"_id": object_id})
    if not existing_contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    
    update_dict = {k: v for k, v in contact_update.dict(exclude_unset=True).items()}
    
    if not update_dict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    
    if "phone" in update_dict and update_dict["phone"] != existing_contact["phone"]:
        duplicate = await db.trusted_contacts.find_one({
            "user_id": existing_contact["user_id"],
            "phone": update_dict["phone"],
            "_id": {"$ne": object_id}
        })
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contact with this phone number already exists")
    
    update_dict["updated_at"] = datetime.utcnow()
    
    await db.trusted_contacts.update_one({"_id": object_id}, {"$set": update_dict})
    updated_contact = await db.trusted_contacts.find_one({"_id": object_id})
    return contact_helper(updated_contact)

# DELETE contact
@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: str):
    db = await get_database()
    try:
        object_id = ObjectId(contact_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact ID format")
    
    result = await db.trusted_contacts.delete_one({"_id": object_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    
    return None

# POST verify contact (test alert)
@router.post("/{contact_id}/verify", status_code=status.HTTP_200_OK)
async def verify_contact(contact_id: str):
    db = await get_database()
    try:
        object_id = ObjectId(contact_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact ID format")
    
    result = await db.trusted_contacts.update_one(
        {"_id": object_id},
        {"$set": {"is_verified": True, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    
    return {"message": "Test alert sent successfully", "verified": True}

# POST notify one contact
@router.post("/notify", status_code=status.HTTP_200_OK)
async def notify_contact(notify_request: NotifyContactRequest):
    db = await get_database()
    try:
        object_id = ObjectId(notify_request.contact_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact ID format")
    
    contact = await db.trusted_contacts.find_one({"_id": object_id})
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    
    notification = {
        "contact_id": notify_request.contact_id,
        "user_id": contact["user_id"],
        "contact_name": contact["name"],
        "contact_phone": contact["phone"],
        "message": notify_request.message,
        "latitude": notify_request.latitude,
        "longitude": notify_request.longitude,
        "location_name": notify_request.location_name,
        "sent_at": datetime.utcnow(),
        "status": "sent"
    }
    
    await db.notifications.insert_one(notification)
    
    return {
        "message": "Emergency alert sent successfully",
        "contact_name": contact["name"],
        "contact_phone": contact["phone"],
        "sent_at": notification["sent_at"]
    }

# ✅ UPDATED notify-all endpoint (JSON body support)
@router.post("/notify-all/{user_id}", status_code=status.HTTP_200_OK)
async def notify_all_contacts(user_id: str, req: NotifyAllRequest):
    db = await get_database()

    contacts = []
    async for contact in db.trusted_contacts.find({"user_id": user_id}):
        contacts.append(contact)
    
    if not contacts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trusted contacts found for this user"
        )
    
    notifications_sent = []
    
    for contact in contacts:
        notification = {
            "contact_id": str(contact["_id"]),
            "user_id": user_id,
            "contact_name": contact["name"],
            "contact_phone": contact["phone"],
            "message": req.message,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "location_name": req.location_name,
            "sent_at": datetime.utcnow(),
            "status": "sent"
        }
        
        await db.notifications.insert_one(notification)
        notifications_sent.append({
            "name": contact["name"],
            "phone": contact["phone"]
        })
    
    return {
        "message": f"Emergency alert sent to {len(notifications_sent)} contact(s)",
        "contacts": notifications_sent,
        "sent_at": datetime.utcnow()
    }

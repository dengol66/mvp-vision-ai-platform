"""Chat API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.db.database import get_db
from app.db.models import Session as SessionModel, Message as MessageModel
from app.schemas import chat
from app.utils.llm import intent_parser

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sessions", response_model=chat.SessionResponse)
async def create_session(db: DBSession = Depends(get_db)):
    """Create a new chat session."""
    session = SessionModel()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=chat.SessionResponse)
async def get_session(session_id: int, db: DBSession = Depends(get_db)):
    """Get a chat session by ID."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[chat.MessageResponse])
async def get_messages(session_id: int, db: DBSession = Depends(get_db)):
    """Get all messages in a session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(MessageModel)
        .filter(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at)
        .all()
    )
    return messages


@router.post("/message", response_model=chat.ChatResponse)
async def send_message(request: chat.ChatRequest, db: DBSession = Depends(get_db)):
    """
    Send a message and get AI response.

    This endpoint:
    1. Creates or retrieves a session
    2. Saves the user message
    3. Parses intent using Claude
    4. Generates and saves assistant response
    5. Returns both messages and parsed intent
    """
    logger.debug(f"Received chat request: session_id={request.session_id}, message={request.message[:50]}...")

    try:
        # Create or get session
        if request.session_id:
            session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            session = SessionModel()
            db.add(session)
            db.commit()
            db.refresh(session)

        logger.debug(f"Using session ID: {session.id}")

        # Save user message
        user_message = MessageModel(
            session_id=session.id,
            role="user",
            content=request.message,
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)

        logger.debug(f"Saved user message ID: {user_message.id}")

        # Get conversation context (last 5 messages)
        previous_messages = (
            db.query(MessageModel)
            .filter(MessageModel.session_id == session.id)
            .order_by(MessageModel.created_at.desc())
            .limit(5)
            .all()
        )
        context = "\n".join([f"{msg.role}: {msg.content}" for msg in reversed(previous_messages[:-1])])

        logger.debug("Calling LLM for intent parsing...")

        # Parse intent
        parsed_result = await intent_parser.parse_message(request.message, context if context else None)

        logger.debug(f"Parsed result status: {parsed_result.get('status')}")
        if parsed_result.get("status") == "error":
            logger.error(f"LLM error: {parsed_result.get('error')} - Detail: {parsed_result.get('detail')}")

        # Generate response
        assistant_content = await intent_parser.generate_response(request.message, parsed_result)

        logger.debug(f"Generated response: {assistant_content[:50]}...")

        # Save assistant message
        assistant_message = MessageModel(
            session_id=session.id,
            role="assistant",
            content=assistant_content,
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        logger.debug(f"Saved assistant message ID: {assistant_message.id}")

        # Return response
        return chat.ChatResponse(
            session_id=session.id,
            user_message=user_message,
            assistant_message=assistant_message,
            parsed_intent=parsed_result if parsed_result.get("status") == "complete" else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

"""
Conversation Manager (Phase 1+2)

Orchestrates conversation flow:
1. Parse user message with LLM (get structured action)
2. Execute action via ActionHandlers
3. Update session state and temp_data
4. Save messages to DB
5. Return response
"""

import logging
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.models import Session as SessionModel, Message as MessageModel
from app.models.conversation import ConversationState, GeminiActionResponse
from app.utils.llm_structured import structured_intent_parser
from app.services.action_handlers import ActionHandlers

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation flow with state machine + structured actions

    This replaces the old text-parsing approach with:
    - Explicit state management
    - LLM structured output (Gemini)
    - Action-based execution
    """

    def __init__(self, db: Session):
        self.db = db
        self.action_handlers = ActionHandlers(db)

    async def process_message(
        self,
        session_id: int,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Process user message through conversation flow

        Args:
            session_id: Current session ID
            user_message: User's message text

        Returns:
            dict: {
                "message": str,              # Response to user
                "state": str,                # New conversation state
                "training_job_id": int       # Optional, if training started
            }
        """
        try:
            # 1. Load session
            session = self.db.query(SessionModel).filter(
                SessionModel.id == session_id
            ).first()

            if not session:
                raise ValueError(f"Session {session_id} not found")

            current_state = ConversationState(session.state)
            temp_data = session.temp_data or {}

            logger.info(f"[Session {session_id}] Current state: {current_state}")
            logger.debug(f"[Session {session_id}] Temp data: {json.dumps(temp_data, ensure_ascii=False)}")

            # 2. Build conversation context (last 5 messages)
            context = self._build_context(session)

            # 3. Parse intent with LLM (get structured action)
            logger.info(f"[Session {session_id}] Parsing intent: '{user_message[:100]}...'")

            action_response: GeminiActionResponse = await structured_intent_parser.parse_intent(
                user_message=user_message,
                state=current_state,
                context=context,
                temp_data=temp_data
            )

            logger.info(f"[Session {session_id}] LLM action: {action_response.action}")
            logger.debug(f"[Session {session_id}] LLM message: {action_response.message}")

            # 4. Execute action
            result = await self.action_handlers.handle_action(
                action_response=action_response,
                session=session,
                user_message=user_message
            )

            new_state = result["new_state"]
            response_message = result["message"]
            updated_temp_data = result["temp_data"]
            training_job_id = result.get("training_job_id")

            logger.info(f"[Session {session_id}] State transition: {current_state} -> {new_state}")

            # 5. Update session in DB
            session.state = new_state.value
            session.temp_data = updated_temp_data

            # 6. Save messages
            # Save user message
            user_msg = MessageModel(
                session_id=session.id,
                role="user",
                content=user_message
            )
            self.db.add(user_msg)

            # Save assistant message
            assistant_msg = MessageModel(
                session_id=session.id,
                role="assistant",
                content=response_message
            )
            self.db.add(assistant_msg)

            # 7. Commit all changes
            self.db.commit()

            logger.info(f"[Session {session_id}] Response sent, state updated to {new_state}")

            # 8. Return response
            response = {
                "message": response_message,
                "state": new_state.value,
            }

            if training_job_id:
                response["training_job_id"] = training_job_id
                logger.info(f"[Session {session_id}] Training job created: {training_job_id}")

            return response

        except Exception as e:
            logger.error(f"[Session {session_id}] Error processing message: {e}", exc_info=True)

            # Save error message
            try:
                error_msg = MessageModel(
                    session_id=session_id,
                    role="assistant",
                    content=f"죄송합니다. 오류가 발생했습니다: {str(e)}"
                )
                self.db.add(error_msg)
                self.db.commit()
            except Exception as db_error:
                logger.error(f"Failed to save error message: {db_error}")

            return {
                "message": f"죄송합니다. 오류가 발생했습니다: {str(e)}",
                "state": ConversationState.ERROR.value
            }

    def _build_context(self, session: SessionModel, max_messages: int = 10) -> str:
        """
        Build conversation context from recent messages

        Args:
            session: Current session
            max_messages: Maximum number of messages to include

        Returns:
            str: Formatted conversation history
        """
        messages = (
            self.db.query(MessageModel)
            .filter(MessageModel.session_id == session.id)
            .order_by(MessageModel.created_at.desc())
            .limit(max_messages)
            .all()
        )

        # Reverse to chronological order
        messages = list(reversed(messages))

        if not messages:
            return ""

        context_lines = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            context_lines.append(f"{role}: {msg.content}")

        return "\n".join(context_lines)

    async def create_new_session(self) -> SessionModel:
        """
        Create a new conversation session

        Returns:
            SessionModel: Newly created session
        """
        new_session = SessionModel(
            state=ConversationState.INITIAL.value,
            temp_data={}
        )
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)

        logger.info(f"Created new session: {new_session.id}")
        return new_session

    def get_session_info(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Get session information

        Args:
            session_id: Session ID

        Returns:
            dict: Session info or None if not found
        """
        session = self.db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            return None

        # Count messages
        message_count = self.db.query(MessageModel).filter(
            MessageModel.session_id == session.id
        ).count()

        return {
            "id": session.id,
            "state": session.state,
            "temp_data": session.temp_data,
            "message_count": message_count,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    def reset_session(self, session_id: int) -> bool:
        """
        Reset session to initial state (clear conversation)

        Args:
            session_id: Session ID to reset

        Returns:
            bool: True if successful, False if session not found
        """
        session = self.db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            return False

        # Reset state and temp_data
        session.state = ConversationState.INITIAL.value
        session.temp_data = {}

        # Optional: Delete messages (or keep for history)
        # self.db.query(MessageModel).filter(
        #     MessageModel.session_id == session.id
        # ).delete()

        self.db.commit()

        logger.info(f"Reset session {session_id} to initial state")
        return True

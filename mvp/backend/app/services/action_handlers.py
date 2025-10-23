"""
Action handlers for conversation actions

Each action type has a corresponding handler that executes the actual logic.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.conversation import (
    ActionType,
    GeminiActionResponse,
    ConversationState,
)
from app.db.models import (
    Session as SessionModel,
    Message as MessageModel,
    Project,
    TrainingJob,
)

logger = logging.getLogger(__name__)


class ActionHandlers:
    """
    Handles all conversation actions

    Each handler returns:
    - new_state: New conversation state
    - message: Message to show user
    - temp_data: Updated temporary data
    """

    def __init__(self, db: Session):
        self.db = db

    async def handle_action(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Route action to appropriate handler

        Args:
            action_response: LLM's action response
            session: Current session
            user_message: Original user message

        Returns:
            dict: {
                "new_state": ConversationState,
                "message": str,
                "temp_data": dict,
                "training_job_id": int (optional)
            }
        """
        # CRITICAL: Apply fallback extraction BEFORE routing to handler
        # This ensures config data is extracted even if LLM fails
        temp_data = session.temp_data or {}
        existing_config = temp_data.get("config", {})

        # TRACE: Step 4 - Before merging
        print(f"\n[TRACE-4-MERGE] Action handler:")
        print(f"  existing_config (from session): {existing_config}")
        print(f"  action_response.current_config: {action_response.current_config}")

        # Merge LLM's config first
        if action_response.current_config:
            existing_config.update(action_response.current_config)
            print(f"  MERGED config: {existing_config}")
        else:
            print(f"  NO MERGE - action_response.current_config is None/empty")

        # Then apply fallback extraction from user message
        # CRITICAL DEBUG: Write to file
        try:
            import os
            import datetime
            log_path = "C:\\Users\\flyto\\Project\\Github\\mvp-vision-ai-platform\\mvp\\data\\logs\\fallback_debug.log"
            os.makedirs(os.path.dirname(log_path), exist_ok=True)

            with open(log_path, "a", encoding="utf-8") as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n[{timestamp}] Action: {action_response.action}\n")
                f.write(f"Before: {existing_config}\n")
                f.write(f"User message: {user_message}\n")
        except Exception as e:
            print(f"LOG ERROR: {e}")

        existing_config = self._extract_from_user_message(user_message, existing_config)

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"After: {existing_config}\n")
        except:
            pass

        logger.warning(f"[DEBUG] Before extraction: {existing_config}")
        logger.warning(f"[DEBUG] After extraction: {existing_config}")

        # Update session temp_data with extracted config
        temp_data["config"] = existing_config
        session.temp_data = temp_data

        logger.warning(f"[FALLBACK] Config after extraction: {existing_config}")

        action = action_response.action

        handlers = {
            ActionType.ASK_CLARIFICATION: self._handle_ask_clarification,
            ActionType.SHOW_PROJECT_OPTIONS: self._handle_show_project_options,
            ActionType.SHOW_PROJECT_LIST: self._handle_show_project_list,
            ActionType.CREATE_PROJECT: self._handle_create_project,
            ActionType.SELECT_PROJECT: self._handle_select_project,
            ActionType.SKIP_PROJECT: self._handle_skip_project,
            ActionType.CONFIRM_TRAINING: self._handle_confirm_training,
            ActionType.START_TRAINING: self._handle_start_training,
            ActionType.ERROR: self._handle_error,
        }

        handler = handlers.get(action)
        if not handler:
            logger.error(f"Unknown action: {action}")
            return self._handle_error(action_response, session, user_message)

        # Call handler
        result = await handler(action_response, session, user_message)

        # CRITICAL: Merge our extracted config with handler's temp_data
        # This ensures extracted data isn't lost when handler returns
        handler_temp_data = result.get("temp_data", {})
        handler_config = handler_temp_data.get("config", {})

        # Merge: extracted config (priority) + handler config
        final_config = {**handler_config, **existing_config}

        handler_temp_data["config"] = final_config
        result["temp_data"] = handler_temp_data

        logger.info(f"[MERGE] Final config: {final_config}")

        return result

    async def _handle_ask_clarification(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle ask_clarification action"""
        temp_data = session.temp_data or {}
        current_state = ConversationState(session.state)

        # Config is already extracted in handle_action, just retrieve it
        existing_config = temp_data.get("config", {})

        # Determine next state based on missing fields
        missing_fields = action_response.missing_fields or []

        # If asking for project_name, transition to CREATING_PROJECT
        if "project_name" in missing_fields:
            new_state = ConversationState.CREATING_PROJECT
        # If asking for config fields, stay in or go to GATHERING_CONFIG
        else:
            new_state = ConversationState.GATHERING_CONFIG

        logger.debug(f"After ask_clarification: config = {existing_config}")

        return {
            "new_state": new_state,
            "message": action_response.message,
            "temp_data": temp_data,
        }

    async def _handle_show_project_options(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle show_project_options action"""
        temp_data = session.temp_data or {}

        # Config is already extracted in handle_action, just retrieve it
        existing_config = temp_data.get("config", {})

        # Save experiment metadata
        if action_response.experiment:
            temp_data["experiment"] = action_response.experiment

        logger.debug(f"After show_project_options: config = {existing_config}")

        # Build project options message
        message = "설정이 완료되었습니다. 프로젝트를 선택해주세요.\n\n"
        message += "1️⃣ 신규 프로젝트 생성\n"
        message += "2️⃣ 기존 프로젝트 선택\n"
        message += "3️⃣ 프로젝트 없이 실험만 진행\n\n"
        message += "원하시는 방식의 번호를 입력해주세요."

        return {
            "new_state": ConversationState.SELECTING_PROJECT,
            "message": message,
            "temp_data": temp_data,
        }

    async def _handle_show_project_list(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle show_project_list action"""
        # Fetch projects (excluding Uncategorized)
        projects = self.db.query(Project).filter(
            Project.name != "Uncategorized"
        ).order_by(Project.updated_at.desc()).all()

        temp_data = session.temp_data or {}

        if not projects:
            message = "사용 가능한 프로젝트가 없습니다.\n\n"
            message += "다른 옵션을 선택하시겠습니까?\n"
            message += "1️⃣ 신규 프로젝트 생성\n"
            message += "3️⃣ 프로젝트 없이 실험만 진행"

            return {
                "new_state": ConversationState.SELECTING_PROJECT,
                "message": message,
                "temp_data": temp_data,
            }

        # Build project list
        message = "다음 프로젝트 중 하나를 선택해주세요:\n\n"
        available_projects = []

        for idx, project in enumerate(projects, start=1):
            desc = f" - {project.description}" if project.description else ""
            task = f" ({project.task_type})" if project.task_type else ""

            # Count experiments
            exp_count = self.db.query(TrainingJob).filter(
                TrainingJob.project_id == project.id
            ).count()

            message += f"{idx}. **{project.name}**{task}{desc} (실험 {exp_count}개)\n"

            available_projects.append({
                "id": project.id,
                "name": project.name,
            })

        message += "\n프로젝트 번호를 입력하거나 프로젝트 이름을 입력해주세요."

        # Save available projects to temp_data
        temp_data["available_projects"] = available_projects

        return {
            "new_state": ConversationState.SELECTING_PROJECT,
            "message": message,
            "temp_data": temp_data,
        }

    async def _handle_create_project(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle create_project action"""
        temp_data = session.temp_data or {}
        config = temp_data.get("config", {})

        # Create new project
        new_project = Project(
            name=action_response.project_name,
            description=action_response.project_description,
            task_type=config.get("task_type"),
        )
        self.db.add(new_project)
        self.db.commit()
        self.db.refresh(new_project)

        logger.info(f"Created project: {new_project.name} (ID: {new_project.id})")

        # Save project ID to temp_data
        temp_data["selected_project_id"] = new_project.id

        # Build confirmation message
        message = f"프로젝트 '{new_project.name}'이(가) 생성되었습니다.\n\n"
        message += self._format_config_summary(config)
        message += "\n\n학습을 시작하시겠습니까? (예/아니오)"

        return {
            "new_state": ConversationState.CONFIRMING,
            "message": message,
            "temp_data": temp_data,
        }

    async def _handle_select_project(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle select_project action"""
        temp_data = session.temp_data or {}
        config = temp_data.get("config", {})

        project_identifier = action_response.project_identifier

        # Try to find project
        project = None

        # Check if identifier is a number (project index)
        if project_identifier.isdigit():
            available_projects = temp_data.get("available_projects", [])
            project_idx = int(project_identifier) - 1

            if 0 <= project_idx < len(available_projects):
                project_id = available_projects[project_idx]["id"]
                project = self.db.query(Project).filter(Project.id == project_id).first()

        # If not found, try to search by name
        if not project:
            project = self.db.query(Project).filter(
                Project.name.ilike(f"%{project_identifier}%")
            ).first()

        if not project:
            return {
                "new_state": ConversationState.SELECTING_PROJECT,
                "message": f"'{project_identifier}' 프로젝트를 찾을 수 없습니다. 다시 선택해주세요.",
                "temp_data": temp_data,
            }

        # Save selected project
        temp_data["selected_project_id"] = project.id

        # Build confirmation message
        message = f"프로젝트 '{project.name}'을(를) 선택했습니다.\n\n"
        message += self._format_config_summary(config)
        message += "\n\n학습을 시작하시겠습니까? (예/아니오)"

        return {
            "new_state": ConversationState.CONFIRMING,
            "message": message,
            "temp_data": temp_data,
            "selected_project_id": project.id,  # For frontend to show project detail
        }

    async def _handle_skip_project(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle skip_project action"""
        temp_data = session.temp_data or {}
        config = temp_data.get("config", {})

        # Get or create Uncategorized project
        uncategorized = self.db.query(Project).filter(
            Project.name == "Uncategorized"
        ).first()

        if not uncategorized:
            uncategorized = Project(
                name="Uncategorized",
                description="프로젝트 없이 진행한 실험들",
            )
            self.db.add(uncategorized)
            self.db.commit()
            self.db.refresh(uncategorized)

        temp_data["selected_project_id"] = uncategorized.id

        # Build confirmation message
        message = "프로젝트 없이 진행합니다.\n\n"
        message += self._format_config_summary(config)
        message += "\n\n학습을 시작하시겠습니까? (예/아니오)"

        return {
            "new_state": ConversationState.CONFIRMING,
            "message": message,
            "temp_data": temp_data,
        }

    async def _handle_confirm_training(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle confirm_training action"""
        # This is just a confirmation display, wait for user response
        temp_data = session.temp_data or {}
        config = temp_data.get("config", {})

        message = self._format_config_summary(config)
        message += "\n\n학습을 시작하시겠습니까? (예/아니오)"

        return {
            "new_state": ConversationState.CONFIRMING,
            "message": message,
            "temp_data": temp_data,
        }

    async def _handle_start_training(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle start_training action"""
        temp_data = session.temp_data or {}
        config = action_response.config or temp_data.get("config", {})
        experiment = action_response.experiment or temp_data.get("experiment", {})
        project_id = action_response.project_id or temp_data.get("selected_project_id")

        # Create training job
        training_job = TrainingJob(
            session_id=session.id,
            project_id=project_id,
            framework=config.get("framework"),
            model_name=config.get("model_name"),
            task_type=config.get("task_type"),
            dataset_path=config.get("dataset_path"),
            dataset_format=config.get("dataset_format", "imagefolder"),
            num_classes=config.get("num_classes"),
            epochs=config.get("epochs"),
            batch_size=config.get("batch_size"),
            learning_rate=config.get("learning_rate"),
            output_dir=f"./outputs/{session.id}",
            experiment_name=experiment.get("name"),
            tags=experiment.get("tags"),
            notes=experiment.get("notes"),
            status="pending",
        )
        self.db.add(training_job)
        self.db.commit()
        self.db.refresh(training_job)

        logger.info(f"Created training job: ID={training_job.id}")

        message = f"학습 작업이 생성되었습니다! (Job ID: {training_job.id})\n\n"
        message += "학습이 시작됩니다. 우측 패널에서 진행 상황을 확인하실 수 있습니다."

        return {
            "new_state": ConversationState.COMPLETE,
            "message": message,
            "temp_data": {},  # Clear temp data
            "training_job_id": training_job.id,
        }

    async def _handle_error(
        self,
        action_response: GeminiActionResponse,
        session: SessionModel,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle error action"""
        error_msg = action_response.error_message or "알 수 없는 오류가 발생했습니다."
        logger.error(f"Action error: {error_msg}")

        return {
            "new_state": ConversationState.ERROR,
            "message": f"죄송합니다. 오류가 발생했습니다: {error_msg}\n\n처음부터 다시 시작해주세요.",
            "temp_data": {},
        }

    def _extract_from_user_message(
        self, user_message: str, existing_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract config values from user message (fallback for LLM limitations)

        This handles cases where LLM doesn't properly extract structured data.
        """
        import re
        import os

        msg_lower = user_message.lower().strip()

        # Extract dataset path (Windows/Unix paths)
        # Match patterns like: C:\path\to\dataset or /path/to/dataset
        path_pattern = r'[A-Za-z]:\\[\w\\\-\.]+|/[\w/\-\.]+'
        path_matches = re.findall(path_pattern, user_message)
        if path_matches:
            # Take the longest match (most likely to be the full path)
            dataset_path = max(path_matches, key=len)
            if 'dataset' in dataset_path.lower() or os.path.exists(dataset_path):
                existing_config["dataset_path"] = dataset_path
                logger.info(f"Extracted dataset_path from user message: {dataset_path}")

        # Extract default values (Korean & English)
        if any(keyword in msg_lower for keyword in ["기본", "default", "기본값"]):
            if "epochs" not in existing_config or existing_config.get("epochs") is None:
                existing_config["epochs"] = 50
                logger.info("Applied default epochs: 50")
            if "batch_size" not in existing_config or existing_config.get("batch_size") is None:
                existing_config["batch_size"] = 32
                logger.info("Applied default batch_size: 32")
            if "learning_rate" not in existing_config or existing_config.get("learning_rate") is None:
                existing_config["learning_rate"] = 0.001
                logger.info("Applied default learning_rate: 0.001")
            if "dataset_format" not in existing_config or existing_config.get("dataset_format") is None:
                existing_config["dataset_format"] = "imagefolder"

        # Extract epochs (숫자 + "epoch" or "에포크")
        epoch_match = re.search(r'(\d+)\s*(?:epoch|에포크)', msg_lower)
        if epoch_match:
            existing_config["epochs"] = int(epoch_match.group(1))
            logger.info(f"Extracted epochs: {existing_config['epochs']}")

        # Extract batch size (숫자 + "batch" or "배치")
        batch_match = re.search(r'(?:batch|배치)[\s:]*(\d+)', msg_lower)
        if batch_match:
            existing_config["batch_size"] = int(batch_match.group(1))
            logger.info(f"Extracted batch_size: {existing_config['batch_size']}")

        # Extract learning rate
        lr_match = re.search(r'(?:lr|learning.?rate|학습률)[\s:=]*(0?\.\d+)', msg_lower)
        if lr_match:
            existing_config["learning_rate"] = float(lr_match.group(1))
            logger.info(f"Extracted learning_rate: {existing_config['learning_rate']}")

        return existing_config

    def _format_config_summary(self, config: Dict[str, Any]) -> str:
        """Format config as readable summary"""
        lines = [
            "**학습 설정:**",
            f"- 프레임워크: {config.get('framework', 'N/A')}",
            f"- 모델: {config.get('model_name', 'N/A')}",
            f"- 작업 유형: {config.get('task_type', 'N/A')}",
            f"- 데이터셋: {config.get('dataset_path', 'N/A')}",
            f"- 에포크: {config.get('epochs', 'N/A')}",
            f"- 배치 크기: {config.get('batch_size', 'N/A')}",
            f"- 학습률: {config.get('learning_rate', 'N/A')}",
        ]
        return "\n".join(lines)

"""
LLM integration with Gemini Structured Output (Phase 1+2)

This module uses Gemini's structured output to get action-based responses.
"""

import json
import logging
from typing import Optional, Dict, Any
import google.generativeai as genai
from google.generativeai.types import content_types

from app.core.config import settings
from app.models.conversation import (
    ActionType,
    GeminiActionResponse,
    ConversationState,
)

logger = logging.getLogger(__name__)


class StructuredIntentParser:
    """
    Parse user intent using Gemini with structured output

    Instead of parsing text responses, we get structured JSON actions from Gemini.
    """

    def __init__(self):
        """Initialize the structured intent parser"""
        genai.configure(api_key=settings.GOOGLE_API_KEY)

        # Define response schema for Gemini
        self.response_schema = content_types.Schema(
            type=content_types.Type.OBJECT,
            properties={
                "action": content_types.Schema(
                    type=content_types.Type.STRING,
                    enum=[action.value for action in ActionType],
                    description="Action to perform based on user intent"
                ),
                "message": content_types.Schema(
                    type=content_types.Type.STRING,
                    description="Message to show to user in Korean"
                ),
                "missing_fields": content_types.Schema(
                    type=content_types.Type.ARRAY,
                    items=content_types.Schema(type=content_types.Type.STRING),
                    description="Missing configuration fields (for ask_clarification)"
                ),
                "current_config": content_types.Schema(
                    type=content_types.Type.OBJECT,
                    description="Current configuration (for ask_clarification)"
                ),
                "config": content_types.Schema(
                    type=content_types.Type.OBJECT,
                    description="Complete training configuration"
                ),
                "experiment": content_types.Schema(
                    type=content_types.Type.OBJECT,
                    description="Experiment metadata"
                ),
                "project_name": content_types.Schema(
                    type=content_types.Type.STRING,
                    description="Project name (for create_project)"
                ),
                "project_description": content_types.Schema(
                    type=content_types.Type.STRING,
                    description="Project description (for create_project)"
                ),
                "project_identifier": content_types.Schema(
                    type=content_types.Type.STRING,
                    description="Project ID or name (for select_project)"
                ),
                "project_id": content_types.Schema(
                    type=content_types.Type.INTEGER,
                    description="Project ID"
                ),
                "error_message": content_types.Schema(
                    type=content_types.Type.STRING,
                    description="Error message (for error action)"
                ),
            },
            required=["action", "message"]
        )

        # Create model with structured output
        self.model = genai.GenerativeModel(
            model_name=settings.LLM_MODEL,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": self.response_schema,
                "temperature": settings.LLM_TEMPERATURE,
            }
        )

    def _build_system_prompt(self, state: ConversationState) -> str:
        """Build state-specific system prompt"""

        base_prompt = """You are an AI assistant for a computer vision training platform.

LANGUAGE REQUIREMENT:
- You MUST respond in Korean (한국어) at all times
- All messages must be in Korean
- Never respond in English unless explicitly asked

You must respond with structured JSON containing:
- action: one of the supported action types
- message: user-friendly message in Korean
- other fields based on action type

SUPPORTED ACTIONS:
1. ask_clarification: Need more information
2. show_project_options: Show project selection menu (1: new, 2: existing, 3: skip)
3. show_project_list: List available projects
4. create_project: Create new project
5. select_project: Select existing project
6. skip_project: Skip project (use Uncategorized)
7. confirm_training: Ask for final confirmation
8. start_training: Start training (final action)
9. error: Error occurred

"""

        if state == ConversationState.INITIAL or state == ConversationState.GATHERING_CONFIG:
            return base_prompt + """
CURRENT STATE: Gathering training configuration

Your task: Extract training configuration from user messages.

SUPPORTED CAPABILITIES:
- Frameworks: timm (classification), ultralytics (detection/segmentation/pose)
- Models:
  * timm: resnet18, resnet50, efficientnet_b0
  * ultralytics: yolov8n, yolov8s, yolov8m
- Task types: image_classification, object_detection, instance_segmentation, pose_estimation
- Dataset formats: imagefolder, coco, yolo

REQUIRED FIELDS:
- framework
- model_name
- task_type
- dataset_path
- epochs
- batch_size
- learning_rate

OPTIONAL FIELDS:
- num_classes (for classification)
- dataset_format (default: imagefolder)

INFERENCE RULES:
1. If user mentions "ResNet" or "EfficientNet" → framework="timm", task_type="image_classification"
2. If user mentions "YOLO" → framework="ultralytics", task_type="object_detection" (or ask which task)
3. If user says "적절히" or "기본값" → use defaults (epochs=50, batch_size=32, learning_rate=0.001)
4. Build config incrementally across messages - don't forget previous information

WHEN CONFIG IS COMPLETE:
Return action="show_project_options" with the complete config.

WHEN INFO IS MISSING:
Return action="ask_clarification" with missing_fields list.

Example responses:
```json
{
  "action": "ask_clarification",
  "message": "어떤 모델을 사용하시겠어요? (resnet18, resnet50, efficientnet_b0)",
  "missing_fields": ["model_name"],
  "current_config": {"framework": "timm", "task_type": "image_classification"}
}
```

```json
{
  "action": "show_project_options",
  "message": "설정이 완료되었습니다. 프로젝트를 선택해주세요.\\n\\n1️⃣ 신규 프로젝트 생성\\n2️⃣ 기존 프로젝트 선택\\n3️⃣ 프로젝트 없이 실험만 진행",
  "config": {
    "framework": "timm",
    "model_name": "resnet50",
    "task_type": "image_classification",
    "dataset_path": "C:\\\\datasets\\\\cls\\\\imagenet-10",
    "dataset_format": "imagefolder",
    "num_classes": 10,
    "epochs": 50,
    "batch_size": 32,
    "learning_rate": 0.001
  }
}
```
"""

        elif state == ConversationState.SELECTING_PROJECT:
            return base_prompt + """
CURRENT STATE: Selecting project

User needs to choose:
1. Create new project
2. Select existing project
3. Skip project (Uncategorized)

If user input is:
- "1" or "1번" or "신규" → action="show_project_options" (wait for project name)
- "2" or "2번" or "기존" → action="show_project_list"
- "3" or "3번" or "건너뛰기" → action="skip_project"
- Project name/number → action="select_project" with project_identifier

Example:
```json
{
  "action": "show_project_list",
  "message": "기존 프로젝트를 조회합니다..."
}
```
"""

        elif state == ConversationState.CREATING_PROJECT:
            return base_prompt + """
CURRENT STATE: Creating new project

User is providing project name and optional description.

Parse format: "프로젝트 이름 - 설명" or just "프로젝트 이름"

Return action="create_project" with:
- project_name
- project_description (optional)

Example:
```json
{
  "action": "create_project",
  "message": "프로젝트를 생성합니다...",
  "project_name": "이미지 분류 프로젝트",
  "project_description": "고양이와 강아지 분류"
}
```
"""

        elif state == ConversationState.CONFIRMING:
            return base_prompt + """
CURRENT STATE: Confirming training

User needs to confirm whether to start training.

If user input is:
- "예", "yes", "y", "네", "확인", "ok" → action="start_training"
- "아니오", "no", "취소", "cancel" → action="error" (or back to initial)

Example:
```json
{
  "action": "start_training",
  "message": "학습을 시작합니다..."
}
```
"""

        else:
            return base_prompt

    async def parse_intent(
        self,
        user_message: str,
        state: ConversationState,
        context: Optional[str] = None,
        temp_data: Optional[Dict[str, Any]] = None
    ) -> GeminiActionResponse:
        """
        Parse user intent with current state and context

        Args:
            user_message: User's message
            state: Current conversation state
            context: Previous conversation context
            temp_data: Temporary data from session (config, etc.)

        Returns:
            GeminiActionResponse: Structured action response
        """
        try:
            # Build system prompt based on state
            system_prompt = self._build_system_prompt(state)

            # Build full prompt
            prompt_parts = [system_prompt]

            # Add context if available
            if context:
                prompt_parts.append(f"\n\n=== CONVERSATION HISTORY ===\n{context}\n")

            # Add current config if available
            if temp_data and "config" in temp_data:
                config_str = json.dumps(temp_data["config"], ensure_ascii=False, indent=2)
                prompt_parts.append(f"\n\n=== CURRENT CONFIG ===\n{config_str}\n")

            # Add user message
            prompt_parts.append(f"\n\n=== USER MESSAGE ===\n{user_message}\n")

            prompt_parts.append("\n\nRespond with JSON action:")

            full_prompt = "\n".join(prompt_parts)

            logger.debug(f"Gemini prompt (state={state}):\n{full_prompt[:500]}...")

            # Call Gemini
            response = self.model.generate_content(full_prompt)

            # Parse response
            response_text = response.text
            logger.debug(f"Gemini response: {response_text}")

            # Parse JSON
            response_data = json.loads(response_text)

            # Validate with Pydantic
            action_response = GeminiActionResponse(**response_data)

            logger.info(f"Parsed action: {action_response.action}")

            return action_response

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}\nResponse: {response_text}")
            return GeminiActionResponse(
                action=ActionType.ERROR,
                message="죄송합니다. 응답 처리 중 오류가 발생했습니다.",
                error_message=f"JSON parsing failed: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Intent parsing error: {e}", exc_info=True)
            return GeminiActionResponse(
                action=ActionType.ERROR,
                message="죄송합니다. 요청 처리 중 오류가 발생했습니다.",
                error_message=str(e)
            )


# Global instance
structured_intent_parser = StructuredIntentParser()

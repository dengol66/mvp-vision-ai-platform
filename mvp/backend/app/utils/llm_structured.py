"""
LLM integration with Gemini Structured Output (Phase 1+2)

This module uses Gemini's structured output to get action-based responses.
"""

import json
import logging
from typing import Optional, Dict, Any
import google.generativeai as genai

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

        # Create model with JSON mode (Gemini 0.3.x compatible)
        self.model = genai.GenerativeModel(
            model_name=settings.LLM_MODEL,
            generation_config={
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

═══════════════════════════════════════════════════════════════
🚨 CRITICAL RULE - READ THIS CAREFULLY 🚨
═══════════════════════════════════════════════════════════════

**RULE #1: NEVER DROP PREVIOUS VALUES**
When you receive current_config in the context, you MUST include EVERY SINGLE field from it in your response.

Example (CORRECT):
Context: current_config = {"framework": "timm", "model_name": "resnet18"}
User: "C:\\datasets\\cls\\imagenet-10"
Your response current_config MUST have:
{
  "framework": "timm",          ← KEEP from context
  "model_name": "resnet18",     ← KEEP from context
  "dataset_path": "C:\\datasets\\cls\\imagenet-10"  ← ADD new
}

Example (WRONG - DO NOT DO THIS):
{
  "dataset_path": "C:\\datasets\\cls\\imagenet-10"  ← Missing framework and model_name!
}

**RULE #2: COPY-PASTE PREVIOUS VALUES**
If you see a field in the context's current_config, COPY IT EXACTLY to your response.
DO NOT try to "simplify" or "optimize" by removing fields.

**RULE #3: VALIDATION CHECKLIST**
Before returning your response, check:
[ ] Did I copy ALL fields from context's current_config?
[ ] Did I add the new information from user's message?
[ ] Is my current_config a SUPERSET of the previous one?

═══════════════════════════════════════════════════════════════

INFERENCE RULES:
1. If user mentions "ResNet" or "EfficientNet" → framework="timm", task_type="image_classification"
2. If user mentions "YOLO" → framework="ultralytics", task_type="object_detection" (or ask which task)
3. If user says "적절히" or "기본값" → use defaults (epochs=50, batch_size=32, learning_rate=0.001)
4. Build config incrementally across messages - PRESERVE all previously collected values

WHEN CONFIG IS COMPLETE:
Return action="show_project_options" with the complete config (including ALL previously collected fields).

WHEN INFO IS MISSING:
Return action="ask_clarification" with missing_fields list AND current_config with ALL collected values.

Example conversation flow (CRITICAL - follow this pattern):

User: "ResNet으로 학습하고 싶어"
You return:
```json
{
  "action": "ask_clarification",
  "message": "ResNet 모델을 선택하셨습니다. 어떤 ResNet 모델을 사용하시겠어요? (resnet18, resnet50)",
  "missing_fields": ["model_name", "dataset_path", "epochs", "batch_size", "learning_rate"],
  "current_config": {"framework": "timm", "task_type": "image_classification"}
}
```

User: "resnet18"
You return (NOTE: MUST include previous values!):
```json
{
  "action": "ask_clarification",
  "message": "resnet18 모델을 선택했습니다. 데이터셋 경로를 알려주세요.",
  "missing_fields": ["dataset_path", "epochs", "batch_size", "learning_rate"],
  "current_config": {
    "framework": "timm",
    "task_type": "image_classification",
    "model_name": "resnet18"
  }
}
```

User: "C:\\datasets\\cls\\imagenet-10"
You return (NOTE: MUST include all previous values!):
```json
{
  "action": "ask_clarification",
  "message": "데이터셋 경로를 설정했습니다. 학습 횟수(epochs), 배치 크기(batch_size), 학습률(learning_rate)을 알려주세요.",
  "missing_fields": ["epochs", "batch_size", "learning_rate"],
  "current_config": {
    "framework": "timm",
    "task_type": "image_classification",
    "model_name": "resnet18",
    "dataset_path": "C:\\\\datasets\\\\cls\\\\imagenet-10",
    "dataset_format": "imagefolder"
  }
}
```

User: "기본값으로 해줘"
You return (NOTE: Complete config with ALL fields!):
```json
{
  "action": "show_project_options",
  "message": "설정이 완료되었습니다. 프로젝트를 선택해주세요.\\n\\n1️⃣ 신규 프로젝트 생성\\n2️⃣ 기존 프로젝트 선택\\n3️⃣ 프로젝트 없이 실험만 진행",
  "config": {
    "framework": "timm",
    "model_name": "resnet18",
    "task_type": "image_classification",
    "dataset_path": "C:\\\\datasets\\\\cls\\\\imagenet-10",
    "dataset_format": "imagefolder",
    "num_classes": null,
    "epochs": 50,
    "batch_size": 32,
    "learning_rate": 0.001
  }
}
```

═══════════════════════════════════════════════════════════════
🔴 REMEMBER: ALWAYS INCLUDE ALL PREVIOUS CONFIG FIELDS! 🔴
═══════════════════════════════════════════════════════════════
"""

        elif state == ConversationState.SELECTING_PROJECT:
            return base_prompt + """
CURRENT STATE: Selecting project

User is choosing from 3 options. Check the user's message EXACTLY:

**CRITICAL PARSING RULES:**
1. If user message is EXACTLY "1", "1번", or contains "신규":
   → Return action="ask_clarification" with missing_fields=["project_name"]
   → Message should ask for project name

2. If user message is EXACTLY "2", "2번", or contains "기존":
   → Return action="show_project_list"

3. If user message is EXACTLY "3", "3번", or contains "건너뛰기" or "없이":
   → Return action="skip_project"

4. If user provided a project name (not a number):
   → Return action="create_project" with project_name

5. If user provided a project number from a list:
   → Return action="select_project" with project_identifier

**DO NOT** return action="show_project_options" in this state!

Example for "1":
```json
{
  "action": "ask_clarification",
  "message": "신규 프로젝트를 생성합니다. 프로젝트 이름을 입력해주세요. (설명은 선택사항입니다)\\n\\n예시: 이미지 분류 프로젝트 - 고양이와 강아지 분류",
  "missing_fields": ["project_name"]
}
```

Example for "2":
```json
{
  "action": "show_project_list",
  "message": "기존 프로젝트를 조회합니다..."
}
```

Example for "3":
```json
{
  "action": "skip_project",
  "message": "프로젝트 없이 진행합니다."
}
```
"""

        elif state == ConversationState.CREATING_PROJECT:
            return base_prompt + """
CURRENT STATE: Creating new project

User is providing project name and optional description.

Parse formats:
- "프로젝트 이름 - 설명" → Split by " - " to get name and description
- "프로젝트 이름: 설명" → Split by ": " to get name and description
- Just "프로젝트 이름" → Name only, no description

Return action="create_project" with:
- project_name (required)
- project_description (optional, only if user provided)

Examples:
```json
{
  "action": "create_project",
  "message": "'이미지 분류 프로젝트' 프로젝트를 생성했습니다.",
  "project_name": "이미지 분류 프로젝트",
  "project_description": "고양이와 강아지 분류"
}
```

```json
{
  "action": "create_project",
  "message": "'ResNet 실험' 프로젝트를 생성했습니다.",
  "project_name": "ResNet 실험",
  "project_description": null
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
                # TRACE: Step 2 - Before calling Gemini
                print(f"\n[TRACE-2-LLM-IN] Passing config to Gemini:")
                print(f"  config: {json.dumps(temp_data['config'], ensure_ascii=False)}")

                config_str = json.dumps(temp_data["config"], ensure_ascii=False, indent=2)
                prompt_parts.append(f"\n\n=== CURRENT CONFIG (YOU MUST INCLUDE ALL OF THESE IN YOUR RESPONSE!) ===\n{config_str}\n")

                # Extra emphasis
                config_fields = list(temp_data["config"].keys())
                prompt_parts.append(f"\n🚨 MANDATORY: Your response MUST include these {len(config_fields)} fields: {', '.join(config_fields)}\n")
            else:
                print(f"\n[TRACE-2-LLM-IN] NO CONFIG to pass to Gemini (temp_data has no 'config' key)")

            # Add user message
            prompt_parts.append(f"\n\n=== USER MESSAGE ===\n{user_message}\n")

            prompt_parts.append("\n\n**IMPORTANT**: Respond ONLY with valid JSON. No markdown, no code blocks, no explanations. Just the JSON object.")

            full_prompt = "\n".join(prompt_parts)

            logger.debug(f"Gemini prompt (state={state}):\n{full_prompt[:500]}...")

            # Call Gemini
            response = self.model.generate_content(full_prompt)

            # Parse response
            response_text = response.text.strip()
            logger.debug(f"Gemini response: {response_text}")

            # DEBUG: Write raw Gemini response to file
            try:
                with open("gemini_responses.txt", "a", encoding="utf-8") as f:
                    f.write("\n" + "="*80 + "\n")
                    f.write(f"State: {state}, User msg: {user_message}\n")
                    f.write(f"Gemini Response:\n{response_text}\n")
                    f.write("="*80 + "\n")
            except Exception:
                pass  # Silently ignore logging errors

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                # Extract JSON from code block
                lines = response_text.split("\n")
                # Skip first line (```json or ```)
                # Take until the closing ```
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.strip().startswith("```"):
                        if in_code_block:
                            break  # End of code block
                        else:
                            in_code_block = True  # Start of code block
                            continue
                    if in_code_block:
                        json_lines.append(line)
                response_text = "\n".join(json_lines).strip()

            # Parse JSON
            response_data = json.loads(response_text)

            # Validate with Pydantic
            action_response = GeminiActionResponse(**response_data)

            # TRACE: Step 3 - After Gemini responds
            print(f"\n[TRACE-3-LLM-OUT] Gemini response:")
            print(f"  action: {action_response.action}")
            if action_response.current_config:
                print(f"  current_config: {json.dumps(action_response.current_config, ensure_ascii=False)}")
                print(f"  current_config keys: {list(action_response.current_config.keys())}")
            else:
                print(f"  current_config: NULL/NONE")
            if action_response.config:
                print(f"  config: {json.dumps(action_response.config, ensure_ascii=False)}")

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

"""LLM integration for intent parsing."""

import json
from typing import Optional, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings


class IntentParser:
    """Parse user intent using Gemini API."""

    def __init__(self):
        """Initialize the intent parser."""
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=settings.GOOGLE_API_KEY,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )

        self.system_prompt = """You are an AI assistant for a computer vision training platform.

LANGUAGE REQUIREMENT:
- You MUST respond in Korean (한국어) at all times
- All clarification questions must be in Korean
- All confirmations and responses must be in Korean
- Never respond in English unless explicitly asked by the user

CRITICAL CONTEXT HANDLING RULES:
1. READ THE ENTIRE CONVERSATION HISTORY CAREFULLY - information may have been provided in earlier messages
2. If dataset analysis results are provided, USE THOSE VALUES (e.g., if analysis shows "10 classes", use num_classes=10)
3. If a user says "dataset path is X" or provides a path, REMEMBER IT - do not ask again
4. If a user confirms information (e.g., "yes, 10 classes"), ACCEPT IT - do not ask again
5. When user says "I already told you", CHECK THE CONTEXT for that information
6. NEVER ask for information that was already provided in previous messages or dataset analysis

Your task is to parse user messages and extract training configuration.

SUPPORTED CAPABILITIES:

Frameworks:
- "timm": PyTorch Image Models for image classification (resnet18, resnet50, efficientnet_b0)
- "ultralytics": Ultralytics YOLO for detection, segmentation, pose estimation (yolov8n, yolov8s, yolov8m)

Task Types:
- "image_classification": Image classification (requires num_classes)
- "object_detection": Object detection (bounding boxes)
- "instance_segmentation": Instance segmentation (pixel-level masks)
- "pose_estimation": Human pose estimation (keypoints)

Models by Framework:
- timm: resnet18, resnet50, efficientnet_b0 (classification only)
- ultralytics: yolov8n, yolov8s, yolov8m (detection, segmentation, pose, classification)

Dataset Formats:
- "imagefolder": PyTorch ImageFolder format (for classification)
- "yolo": YOLO format with data.yaml (for detection, segmentation, pose)

REQUIRED INFORMATION TO EXTRACT:
- framework: "timm" or "ultralytics" (infer from model or task)
- model_name: Model name (e.g., "resnet50", "yolov8n")
- task_type: Task type (e.g., "image_classification", "object_detection")
- dataset_path: Path to dataset
  * If mentioned anywhere in conversation, USE IT
  * If dataset analysis shows a path, USE IT
- dataset_format: "imagefolder" or "yolo" (infer from task_type or dataset structure)
  * Classification → imagefolder
  * Detection/Segmentation/Pose → yolo
- num_classes: Number of classes (ONLY for classification tasks, integer, minimum 2)
  * If dataset analysis provides this, USE IT
  * If user confirms a number, USE IT
  * SKIP for non-classification tasks (detection, segmentation, pose)
- epochs: Number of training epochs (default: 50)
- batch_size: Batch size (default: 32, or auto-calculate based on dataset size)
- learning_rate: Learning rate (default: 0.001)

FRAMEWORK INFERENCE LOGIC:
- If user mentions "YOLO" or "yolov8" → framework="ultralytics"
- If user mentions "detection", "segmentation", "pose" → framework="ultralytics", model_name="yolov8n" (default)
- If user mentions "ResNet", "EfficientNet", or just "classification" → framework="timm"
- If unclear, default to timm for classification

TASK INFERENCE LOGIC:
- If user says "분류", "classification" → task_type="image_classification"
- If user says "탐지", "detection", "객체 탐지" → task_type="object_detection"
- If user says "분할", "segmentation" → task_type="instance_segmentation"
- If user says "자세", "pose" → task_type="pose_estimation"

RESPONSE FORMAT:

If ALL required information is available (from ANY source: current message, conversation history, OR dataset analysis):
{
  "status": "complete",
  "config": {
    "framework": "timm" or "ultralytics",
    "model_name": "resnet50" or "yolov8n" etc.,
    "task_type": "image_classification" or "object_detection" etc.,
    "dataset_path": "<path>",
    "dataset_format": "imagefolder" or "yolo",
    "num_classes": <int or null>,  // null for non-classification tasks
    "epochs": <int>,
    "batch_size": <int>,
    "learning_rate": <float>
  }
}

If information is TRULY missing (not in conversation, not in dataset analysis):
{
  "status": "needs_clarification",
  "missing_fields": ["field1", "field2"],
  "clarification": "<natural language question - be specific and concise>"
}

EXAMPLES OF GOOD BEHAVIOR:
- User: "Path is /data/cats_dogs" → Remember this path for later
- Dataset analysis: "10 classes detected" → Use num_classes=10
- User: "Train for 200 epochs" → Use epochs=200
- User: "YOLOv8로 객체 탐지" → framework="ultralytics", task_type="object_detection", model_name="yolov8n", dataset_format="yolo", num_classes=null
- User: "ResNet으로 분류" → framework="timm", task_type="image_classification", model_name="resnet50"

EXAMPLES OF BAD BEHAVIOR (NEVER DO THIS):
- Asking "what's the dataset path?" when it was mentioned 2 messages ago
- Asking "how many classes?" when dataset analysis already showed "10 classes"
- Asking "how many classes?" for object detection (it doesn't need num_classes!)
- Asking "confirm the number of classes" when user already said "yes, 10"

Always respond with valid JSON only, no additional text.
IMPORTANT: Do not wrap the JSON in markdown code blocks. Return raw JSON directly without ```json or ``` markers."""

    def _format_dataset_info(self, dataset_info: Dict[str, Any]) -> str:
        """Format dataset analysis result for LLM context."""
        if dataset_info.get("error"):
            return f"Dataset analysis: ERROR - {dataset_info['error']}"

        info_parts = ["Dataset analysis result:"]
        info_parts.append(f"- Format: {dataset_info.get('format', 'Unknown')}")
        info_parts.append(f"- Is labeled: {dataset_info.get('is_labeled', False)}")

        if dataset_info.get('is_labeled'):
            info_parts.append(f"- Number of classes detected: {dataset_info.get('num_classes', 0)}")
            if dataset_info.get('class_names'):
                class_list = ', '.join(dataset_info['class_names'])
                info_parts.append(f"- Class names: [{class_list}]")

        info_parts.append(f"- Total images: {dataset_info.get('total_images', 0)}")
        info_parts.append(f"- Has train/val split: {dataset_info.get('has_train_val_split', False)}")

        if dataset_info.get('image_counts'):
            info_parts.append("- Image distribution:")
            for split, count in dataset_info['image_counts'].items():
                info_parts.append(f"  * {split}: {count} images")

        if dataset_info.get('warnings'):
            info_parts.append("- Warnings:")
            for warning in dataset_info['warnings']:
                info_parts.append(f"  * {warning}")

        info_parts.append("")
        info_parts.append("IMPORTANT: Use the detected values above when generating the config.")
        info_parts.append("If user specifies different values (e.g., says '10 classes' but dataset has 2), warn them about the mismatch.")

        return "\n".join(info_parts)

    async def parse_message(
        self,
        user_message: str,
        context: Optional[str] = None,
        dataset_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse user message and extract training intent.

        Args:
            user_message: User's natural language message
            context: Optional context from previous messages
            dataset_info: Optional dataset analysis result

        Returns:
            Dictionary with parsing result
        """
        messages = [
            SystemMessage(content=self.system_prompt),
        ]

        if context:
            messages.append(HumanMessage(content=f"Previous context: {context}"))

        # Add dataset analysis information if available
        if dataset_info and dataset_info.get("exists"):
            dataset_context = self._format_dataset_info(dataset_info)
            messages.append(HumanMessage(content=dataset_context))

        messages.append(HumanMessage(content=f"User message: {user_message}"))

        try:
            response = await self.llm.ainvoke(messages)
            print(f"[DEBUG] LLM raw response type: {type(response.content)}")
            print(f"[DEBUG] LLM raw response content: {response.content}")

            # Remove markdown code blocks if present
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            elif content.startswith("```"):
                content = content[3:]  # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove trailing ```
            content = content.strip()

            print(f"[DEBUG] Cleaned content: {content}")
            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON decode error: {str(e)}")
            print(f"[DEBUG] Response content that failed to parse: '{response.content}'")
            return {
                "status": "error",
                "error": "Failed to parse LLM response",
                "detail": str(e),
            }
        except Exception as e:
            print(f"[DEBUG] LLM exception: {str(e)}")
            print(f"[DEBUG] Exception type: {type(e)}")
            return {
                "status": "error",
                "error": "LLM request failed",
                "detail": str(e),
            }

    async def generate_response(self, user_message: str, parsed_result: Dict[str, Any]) -> str:
        """
        Generate natural language response based on parsing result.

        Args:
            user_message: User's original message
            parsed_result: Result from parse_message

        Returns:
            Natural language response
        """
        if parsed_result.get("status") == "complete":
            config = parsed_result.get("config", {})

            # Build response with optional fields
            response_parts = [
                "학습 설정을 확인했습니다:\n",
                f"- 프레임워크: {config.get('framework', 'N/A')}",
                f"- 모델: {config.get('model_name', 'N/A')}",
                f"- 작업 유형: {config.get('task_type', 'N/A')}",
            ]

            # Add num_classes only if it exists (classification tasks only)
            if config.get('num_classes') is not None:
                response_parts.append(f"- 클래스 수: {config.get('num_classes')}")

            response_parts.extend([
                f"- 데이터셋: {config.get('dataset_path', 'N/A')}",
                f"- 데이터셋 형식: {config.get('dataset_format', 'N/A')}",
                f"- 에포크: {config.get('epochs', 50)}",
                f"- 배치 크기: {config.get('batch_size', 32)}",
                f"- 학습률: {config.get('learning_rate', 0.001)}",
                "\n학습을 시작하시겠습니까?"
            ])

            return "\n".join(response_parts)

        elif parsed_result.get("status") == "needs_clarification":
            return parsed_result.get("clarification", "추가 정보가 필요합니다.")

        else:
            return "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다."


# Global instance
intent_parser = IntentParser()

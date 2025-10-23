'use client'

import { useState, useEffect } from 'react'
import { ArrowLeftIcon, ArrowRightIcon, CheckIcon } from 'lucide-react'
import { cn } from '@/lib/utils/cn'

interface TrainingConfig {
  framework?: string
  model_name?: string
  task_type?: string
  dataset_path?: string
  dataset_format?: string
  epochs?: number
  batch_size?: number
  learning_rate?: number
}

interface TrainingConfigPanelProps {
  projectId?: number | null
  initialConfig?: TrainingConfig | null
  onCancel: () => void
  onTrainingStarted: (jobId: number) => void
}

export default function TrainingConfigPanel({
  projectId,
  initialConfig,
  onCancel,
  onTrainingStarted,
}: TrainingConfigPanelProps) {
  const [step, setStep] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Step 1: Model & Task
  const [framework, setFramework] = useState(initialConfig?.framework || 'timm')
  const [modelName, setModelName] = useState(initialConfig?.model_name || '')
  const [taskType, setTaskType] = useState(initialConfig?.task_type || 'image_classification')

  // Step 2: Dataset
  const [datasetPath, setDatasetPath] = useState(initialConfig?.dataset_path || '')
  const [datasetFormat, setDatasetFormat] = useState(initialConfig?.dataset_format || 'imagefolder')

  // Step 3: Hyperparameters
  const [epochs, setEpochs] = useState(initialConfig?.epochs || 50)
  const [batchSize, setBatchSize] = useState(initialConfig?.batch_size || 32)
  const [learningRate, setLearningRate] = useState(initialConfig?.learning_rate || 0.001)

  // Framework options
  const frameworks = [
    { value: 'timm', label: 'timm (PyTorch Image Models)' },
    { value: 'ultralytics', label: 'Ultralytics YOLO' },
  ]

  // Model options based on framework
  const getModelOptions = () => {
    if (framework === 'timm') {
      return [
        { value: 'resnet18', label: 'ResNet-18', supportedTasks: ['image_classification'] },
        { value: 'resnet50', label: 'ResNet-50', supportedTasks: ['image_classification'] },
        { value: 'efficientnet_b0', label: 'EfficientNet-B0', supportedTasks: ['image_classification'] },
      ]
    } else if (framework === 'ultralytics') {
      return [
        {
          value: 'yolov8n',
          label: 'YOLOv8n (Nano)',
          supportedTasks: ['object_detection', 'instance_segmentation', 'pose_estimation', 'image_classification']
        },
        {
          value: 'yolov8s',
          label: 'YOLOv8s (Small)',
          supportedTasks: ['object_detection', 'instance_segmentation', 'pose_estimation', 'image_classification']
        },
        {
          value: 'yolov8m',
          label: 'YOLOv8m (Medium)',
          supportedTasks: ['object_detection', 'instance_segmentation', 'pose_estimation', 'image_classification']
        },
      ]
    }
    return []
  }

  // All task types
  const allTaskTypes = [
    { value: 'image_classification', label: '이미지 분류 (Image Classification)' },
    { value: 'object_detection', label: '객체 탐지 (Object Detection)' },
    { value: 'semantic_segmentation', label: '의미론적 분할 (Semantic Segmentation)' },
    { value: 'instance_segmentation', label: '인스턴스 분할 (Instance Segmentation)' },
    { value: 'pose_estimation', label: '포즈 추정 (Pose Estimation)' },
  ]

  // Get supported task types for current model
  const getSupportedTaskTypes = () => {
    const models = getModelOptions()
    const currentModel = models.find(m => m.value === modelName)

    if (!currentModel) return allTaskTypes

    return allTaskTypes.filter(task =>
      currentModel.supportedTasks.includes(task.value)
    )
  }

  // Dataset format options
  const datasetFormats = [
    { value: 'imagefolder', label: 'ImageFolder (PyTorch)' },
    { value: 'yolo', label: 'YOLO Format' },
    { value: 'coco', label: 'COCO Format' },
  ]

  // Update model when framework changes
  useEffect(() => {
    const models = getModelOptions()
    if (models.length > 0 && !models.find(m => m.value === modelName)) {
      setModelName(models[0].value)
    }
  }, [framework])

  // Update task type when model changes (auto-select if only one supported)
  useEffect(() => {
    const supportedTasks = getSupportedTaskTypes()

    // If current task type is not supported by the model, change it
    if (!supportedTasks.find(t => t.value === taskType)) {
      if (supportedTasks.length > 0) {
        setTaskType(supportedTasks[0].value)
      }
    }
  }, [modelName, framework])

  // Validation
  const canProceedStep1 = framework && modelName && taskType
  const canProceedStep2 = datasetPath.trim() !== '' && datasetFormat
  const canSubmit = canProceedStep1 && canProceedStep2 && epochs > 0 && batchSize > 0 && learningRate > 0

  const handleNext = () => {
    setError(null)
    if (step < 3) {
      setStep(step + 1)
    }
  }

  const handlePrev = () => {
    setError(null)
    if (step > 1) {
      setStep(step - 1)
    }
  }

  const handleSubmit = async () => {
    if (!canSubmit) return

    setIsSubmitting(true)
    setError(null)

    try {
      const config = {
        framework,
        model_name: modelName,
        task_type: taskType,
        dataset_path: datasetPath.trim(),
        dataset_format: datasetFormat,
        epochs,
        batch_size: batchSize,
        learning_rate: learningRate,
      }

      const requestBody: any = { config }
      if (projectId) {
        requestBody.project_id = projectId
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/training/jobs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || '학습 작업 생성에 실패했습니다')
      }

      const job = await response.json()
      console.log('Training job created:', job)

      // Notify parent
      onTrainingStarted(job.id)
    } catch (err) {
      console.error('Error creating training job:', err)
      setError(err instanceof Error ? err.message : '학습 작업 생성 중 오류가 발생했습니다')
    } finally {
      setIsSubmitting(false)
    }
  }

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-6">
      {[1, 2, 3].map((stepNum) => (
        <div key={stepNum} className="flex items-center">
          <div
            className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
              step >= stepNum
                ? 'bg-violet-600 text-white'
                : 'bg-gray-200 text-gray-600'
            )}
          >
            {step > stepNum ? <CheckIcon className="w-5 h-5" /> : stepNum}
          </div>
          {stepNum < 3 && (
            <div
              className={cn(
                'w-16 h-1 mx-2',
                step > stepNum ? 'bg-violet-600' : 'bg-gray-200'
              )}
            />
          )}
        </div>
      ))}
    </div>
  )

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={onCancel}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeftIcon className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {initialConfig ? '설정 복사하여 새 학습' : '새 학습 시작'}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {step === 1 && '모델과 작업 유형을 선택하세요'}
                {step === 2 && '데이터셋 경로를 지정하세요'}
                {step === 3 && '학습 하이퍼파라미터를 설정하세요'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto">
          {renderStepIndicator()}

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Step 1: Model & Task */}
          {step === 1 && (
            <div className="space-y-6">
              {initialConfig && (
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800">
                    📋 기존 설정을 복사했습니다. 원하는 부분만 수정하세요.
                  </p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  프레임워크 <span className="text-red-500">*</span>
                </label>
                <select
                  value={framework}
                  onChange={(e) => setFramework(e.target.value)}
                  className={cn(
                    'w-full px-4 py-2.5 border border-gray-300 rounded-lg',
                    'focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent',
                    'text-sm bg-white'
                  )}
                >
                  {frameworks.map((fw) => (
                    <option key={fw.value} value={fw.value}>
                      {fw.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  모델 <span className="text-red-500">*</span>
                </label>
                <select
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className={cn(
                    'w-full px-4 py-2.5 border border-gray-300 rounded-lg',
                    'focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent',
                    'text-sm bg-white'
                  )}
                >
                  {getModelOptions().map((model) => (
                    <option key={model.value} value={model.value}>
                      {model.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  작업 유형 <span className="text-red-500">*</span>
                </label>
                <select
                  value={taskType}
                  onChange={(e) => setTaskType(e.target.value)}
                  className={cn(
                    'w-full px-4 py-2.5 border border-gray-300 rounded-lg',
                    'focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent',
                    'text-sm bg-white'
                  )}
                >
                  {getSupportedTaskTypes().map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  선택한 모델이 지원하는 작업 유형만 표시됩니다
                </p>
              </div>
            </div>
          )}

          {/* Step 2: Dataset */}
          {step === 2 && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  데이터셋 경로 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={datasetPath}
                  onChange={(e) => setDatasetPath(e.target.value)}
                  placeholder="예: C:\datasets\cls\imagenet-10"
                  className={cn(
                    'w-full px-4 py-2.5 border border-gray-300 rounded-lg',
                    'focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent',
                    'text-sm'
                  )}
                />
                <p className="text-xs text-gray-500 mt-1">
                  절대 경로로 입력하세요 (Windows: C:\path, Linux/Mac: /path)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  데이터셋 형식 <span className="text-red-500">*</span>
                </label>
                <select
                  value={datasetFormat}
                  onChange={(e) => setDatasetFormat(e.target.value)}
                  className={cn(
                    'w-full px-4 py-2.5 border border-gray-300 rounded-lg',
                    'focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent',
                    'text-sm bg-white'
                  )}
                >
                  {datasetFormats.map((format) => (
                    <option key={format.value} value={format.value}>
                      {format.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Step 3: Hyperparameters */}
          {step === 3 && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Epochs <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={epochs}
                  onChange={(e) => setEpochs(parseInt(e.target.value) || 0)}
                  min="1"
                  max="1000"
                  className={cn(
                    'w-full px-4 py-2.5 border border-gray-300 rounded-lg',
                    'focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent',
                    'text-sm'
                  )}
                />
                <p className="text-xs text-gray-500 mt-1">
                  학습 반복 횟수 (1-1000)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Batch Size <span className="text-red-500">*</span>
                </label>
                <select
                  value={batchSize}
                  onChange={(e) => setBatchSize(parseInt(e.target.value))}
                  className={cn(
                    'w-full px-4 py-2.5 border border-gray-300 rounded-lg',
                    'focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent',
                    'text-sm bg-white'
                  )}
                >
                  <option value="8">8</option>
                  <option value="16">16</option>
                  <option value="32">32</option>
                  <option value="64">64</option>
                  <option value="128">128</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  한 번에 처리할 데이터 개수 (GPU 메모리에 따라 조정)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Learning Rate <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={learningRate}
                  onChange={(e) => setLearningRate(parseFloat(e.target.value) || 0)}
                  step="0.0001"
                  min="0.0001"
                  max="1"
                  className={cn(
                    'w-full px-4 py-2.5 border border-gray-300 rounded-lg',
                    'focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent',
                    'text-sm'
                  )}
                />
                <p className="text-xs text-gray-500 mt-1">
                  학습 속도 (0.0001-1.0, 일반적으로 0.001)
                </p>
              </div>

              {/* Summary */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">설정 요약</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">모델:</span>
                    <span className="font-medium">{modelName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">작업:</span>
                    <span className="font-medium">{taskType}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">데이터셋:</span>
                    <span className="font-medium text-xs truncate max-w-[200px]">
                      {datasetPath}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Epochs:</span>
                    <span className="font-medium">{epochs}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Batch Size:</span>
                    <span className="font-medium">{batchSize}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Learning Rate:</span>
                    <span className="font-medium">{learningRate}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer - Navigation Buttons */}
      <div className="p-6 border-t border-gray-200">
        <div className="max-w-2xl mx-auto flex gap-3">
          {step > 1 && (
            <button
              onClick={handlePrev}
              disabled={isSubmitting}
              className={cn(
                'flex-1 px-4 py-2.5 border border-gray-300 rounded-lg',
                'text-gray-700 font-medium hover:bg-gray-50',
                'transition-colors flex items-center justify-center gap-2',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <ArrowLeftIcon className="w-4 h-4" />
              이전
            </button>
          )}

          {step < 3 ? (
            <button
              onClick={handleNext}
              disabled={
                (step === 1 && !canProceedStep1) ||
                (step === 2 && !canProceedStep2)
              }
              className={cn(
                'flex-1 px-4 py-2.5 bg-violet-600 text-white rounded-lg',
                'font-medium hover:bg-violet-700',
                'transition-colors flex items-center justify-center gap-2',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              다음
              <ArrowRightIcon className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!canSubmit || isSubmitting}
              className={cn(
                'flex-1 px-4 py-2.5 bg-violet-600 text-white rounded-lg',
                'font-medium hover:bg-violet-700',
                'transition-colors flex items-center justify-center gap-2',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {isSubmitting ? '학습 시작 중...' : '학습 시작 🚀'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

'use client'

import { useState, useEffect } from 'react'
import { Settings, AlertTriangle, CheckCircle, Sparkles } from 'lucide-react'
import OptimizerConfigPanel from './OptimizerConfigPanel'
import SchedulerConfigPanel from './SchedulerConfigPanel'
import AugmentationConfigPanel from './AugmentationConfigPanel'

interface AdvancedConfigPanelProps {
  config: any | null
  onChange: (config: any) => void
  onClose: () => void
}

export default function AdvancedConfigPanel({
  config,
  onChange,
  onClose
}: AdvancedConfigPanelProps) {
  const [currentConfig, setCurrentConfig] = useState<any>(null)
  const [presets, setPresets] = useState<any>(null)
  const [validation, setValidation] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  // Load defaults and presets
  useEffect(() => {
    const loadDefaults = async () => {
      try {
        const [defaultsRes, presetsRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/training/config/defaults`),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/training/config/presets`)
        ])

        const defaults = await defaultsRes.json()
        const presets = await presetsRes.json()

        setPresets(presets)

        // Use provided config or defaults
        if (config) {
          setCurrentConfig(config)
        } else {
          setCurrentConfig(defaults.complete)
        }
      } catch (error) {
        console.error('Failed to load config defaults:', error)
      } finally {
        setLoading(false)
      }
    }

    loadDefaults()
  }, [])

  // Apply preset
  const applyPreset = (presetName: string) => {
    if (presets && presets[presetName]) {
      setCurrentConfig(presets[presetName])
    }
  }

  // Validate config
  const validateConfig = async () => {
    if (!currentConfig) return

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/training/config/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentConfig)
      })
      const result = await res.json()
      setValidation(result)
    } catch (error) {
      console.error('Failed to validate config:', error)
    }
  }

  // Save and close
  const handleSave = () => {
    if (currentConfig) {
      onChange(currentConfig)
      onClose()
    }
  }

  if (loading || !currentConfig) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-gray-900 rounded-lg p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-violet-500"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-violet-500/20 rounded-lg">
              <Settings className="w-6 h-6 text-violet-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Advanced Training Configuration</h2>
              <p className="text-sm text-gray-400">Optimizer, Scheduler, Augmentation 등 고급 설정</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        {/* Presets */}
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-yellow-400" />
            <h3 className="text-sm font-semibold text-white">프리셋 선택</h3>
          </div>
          <div className="grid grid-cols-4 gap-2">
            {presets && Object.keys(presets).map((presetName) => (
              <button
                key={presetName}
                onClick={() => applyPreset(presetName)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-sm transition-colors"
              >
                {presetName === 'basic' && 'Basic'}
                {presetName === 'standard' && 'Standard'}
                {presetName === 'aggressive' && 'Aggressive'}
                {presetName === 'fine_tuning' && 'Fine-tuning'}
              </button>
            ))}
          </div>
        </div>

        {/* Config Panels */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <OptimizerConfigPanel
            config={currentConfig.optimizer}
            onChange={(optimizer) => setCurrentConfig({ ...currentConfig, optimizer })}
          />

          <SchedulerConfigPanel
            config={currentConfig.scheduler}
            onChange={(scheduler) => setCurrentConfig({ ...currentConfig, scheduler })}
          />

          <AugmentationConfigPanel
            config={currentConfig.augmentation}
            onChange={(augmentation) => setCurrentConfig({ ...currentConfig, augmentation })}
          />

          {/* Simple configs inline */}
          <div className="bg-gray-800 rounded-lg p-4 space-y-3">
            <h3 className="text-lg font-semibold text-white">기타 설정</h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Mixed Precision Training
                </label>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="mixed-precision"
                    checked={currentConfig.mixed_precision}
                    onChange={(e) => setCurrentConfig({ ...currentConfig, mixed_precision: e.target.checked })}
                    className="w-4 h-4 text-violet-600 bg-gray-700 border-gray-600 rounded focus:ring-violet-500"
                  />
                  <label htmlFor="mixed-precision" className="ml-2 text-sm text-gray-300">
                    활성화 (FP16, 메모리 절약)
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Gradient Clipping
                </label>
                <input
                  type="number"
                  value={currentConfig.gradient_clip_value || ''}
                  onChange={(e) => setCurrentConfig({
                    ...currentConfig,
                    gradient_clip_value: e.target.value ? parseFloat(e.target.value) : null
                  })}
                  step="0.1"
                  min="0"
                  placeholder="비활성화"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                />
              </div>
            </div>
          </div>

          {/* Validation Results */}
          {validation && (
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <h3 className="text-sm font-semibold text-white">검증 결과</h3>
              </div>

              {validation.warnings && validation.warnings.length > 0 && (
                <div className="space-y-2 mb-3">
                  {validation.warnings.map((warning: string, idx: number) => (
                    <div key={idx} className="flex items-start gap-2 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded text-sm text-yellow-300">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                      <span>{warning}</span>
                    </div>
                  ))}
                </div>
              )}

              {validation.suggestions && validation.suggestions.length > 0 && (
                <div className="space-y-2">
                  {validation.suggestions.map((suggestion: string, idx: number) => (
                    <div key={idx} className="flex items-start gap-2 p-2 bg-blue-500/10 border border-blue-500/30 rounded text-sm text-blue-300">
                      <span className="text-blue-400">💡</span>
                      <span>{suggestion}</span>
                    </div>
                  ))}
                </div>
              )}

              {!validation.warnings?.length && !validation.suggestions?.length && (
                <p className="text-sm text-green-400">설정이 올바릅니다!</p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-800 flex items-center justify-between">
          <button
            onClick={validateConfig}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            검증하기
          </button>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              취소
            </button>
            <button
              onClick={handleSave}
              className="px-6 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition-colors"
            >
              저장
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

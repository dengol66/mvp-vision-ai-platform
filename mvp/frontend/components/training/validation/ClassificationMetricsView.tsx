/**
 * ClassificationMetricsView Component
 *
 * Displays classification validation metrics including:
 * - Overall metrics (accuracy, precision, recall, f1)
 * - Confusion matrix heatmap
 * - Per-class metrics table
 */

import React from 'react';
import { ConfusionMatrixView } from './ConfusionMatrixView';
import { PerClassMetricsTable } from './PerClassMetricsTable';

interface ValidationResult {
  id: number;
  job_id: number;
  epoch: number;
  task_type: string;
  primary_metric_name: string | null;
  primary_metric_value: number | null;
  overall_loss: number | null;
  metrics: any;
  per_class_metrics: any;
  confusion_matrix: number[][] | null;
  pr_curves: any;
  class_names: string[] | null;
  visualization_data: any;
  created_at: string;
}

interface ClassificationMetricsViewProps {
  validationResult: ValidationResult;
  jobId: number;
}

export const ClassificationMetricsView: React.FC<ClassificationMetricsViewProps> = ({
  validationResult,
  jobId
}) => {
  const { metrics, per_class_metrics, confusion_matrix, class_names, overall_loss } = validationResult;

  // Format percentage
  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  // Format float
  const formatFloat = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    return value.toFixed(4);
  };

  return (
    <div className="space-y-6">
      {/* Overall Metrics */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Overall Metrics</h3>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {/* Accuracy */}
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide">Accuracy</div>
            <div className="text-2xl font-bold text-white mt-1">
              {formatPercent(metrics?.accuracy)}
            </div>
          </div>

          {/* Precision */}
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide">Precision</div>
            <div className="text-2xl font-bold text-white mt-1">
              {formatPercent(metrics?.precision)}
            </div>
          </div>

          {/* Recall */}
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide">Recall</div>
            <div className="text-2xl font-bold text-white mt-1">
              {formatPercent(metrics?.recall)}
            </div>
          </div>

          {/* F1 Score */}
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide">F1 Score</div>
            <div className="text-2xl font-bold text-white mt-1">
              {formatPercent(metrics?.f1_score)}
            </div>
          </div>

          {/* Loss */}
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide">Val Loss</div>
            <div className="text-2xl font-bold text-white mt-1">
              {formatFloat(overall_loss)}
            </div>
          </div>
        </div>

        {/* Top-5 Accuracy if available */}
        {metrics?.top5_accuracy && (
          <div className="mt-4 bg-gray-700 rounded-lg p-4 inline-block">
            <div className="text-xs text-gray-400 uppercase tracking-wide">Top-5 Accuracy</div>
            <div className="text-2xl font-bold text-white mt-1">
              {formatPercent(metrics.top5_accuracy)}
            </div>
          </div>
        )}
      </div>

      {/* Confusion Matrix and Per-Class Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Confusion Matrix */}
        {confusion_matrix && class_names && (
          <ConfusionMatrixView
            confusionMatrix={confusion_matrix}
            classNames={class_names}
          />
        )}

        {/* Per-Class Metrics */}
        {per_class_metrics && (
          <PerClassMetricsTable
            perClassMetrics={per_class_metrics}
          />
        )}
      </div>
    </div>
  );
};

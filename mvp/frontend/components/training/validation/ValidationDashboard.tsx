/**
 * ValidationDashboard Component
 *
 * Main dashboard for displaying validation results and metrics.
 * Automatically routes to task-specific visualization based on task type.
 */

import React, { useEffect, useState } from 'react';
import { TaskSpecificVisualization } from './TaskSpecificVisualization';

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

interface ValidationSummary {
  job_id: number;
  task_type: string;
  total_epochs: number;
  best_epoch: number | null;
  best_metric_value: number | null;
  best_metric_name: string | null;
  epoch_metrics: any[];
}

interface ValidationDashboardProps {
  jobId: number;
  currentEpoch?: number;
}

export const ValidationDashboard: React.FC<ValidationDashboardProps> = ({
  jobId,
  currentEpoch
}) => {
  const [summary, setSummary] = useState<ValidationSummary | null>(null);
  const [selectedEpoch, setSelectedEpoch] = useState<number | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch validation summary on mount
  useEffect(() => {
    fetchValidationSummary();
  }, [jobId]);

  // Fetch specific epoch when selected or currentEpoch changes
  useEffect(() => {
    const epochToFetch = selectedEpoch || currentEpoch;
    if (epochToFetch) {
      fetchValidationResult(epochToFetch);
    }
  }, [selectedEpoch, currentEpoch]);

  const fetchValidationSummary = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/validation/jobs/${jobId}/summary`);

      if (!response.ok) {
        if (response.status === 404) {
          setError('No validation results available yet');
          return;
        }
        throw new Error(`Failed to fetch validation summary: ${response.status}`);
      }

      const data = await response.json();
      setSummary(data);

      // Auto-select best epoch if no epoch is selected
      if (!selectedEpoch && data.best_epoch) {
        setSelectedEpoch(data.best_epoch);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch validation summary');
      console.error('Error fetching validation summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchValidationResult = async (epoch: number) => {
    try {
      const response = await fetch(`/api/v1/validation/jobs/${jobId}/results/${epoch}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch validation result: ${response.status}`);
      }

      const data = await response.json();
      setValidationResult(data);
    } catch (err) {
      console.error('Error fetching validation result:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading validation results...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">{error}</div>
      </div>
    );
  }

  if (!summary || !validationResult) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">No validation results available</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Header */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Validation Results</h2>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Task Type</div>
            <div className="text-lg font-medium text-white mt-1">
              {summary.task_type.replace('_', ' ').toUpperCase()}
            </div>
          </div>

          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Total Epochs</div>
            <div className="text-lg font-medium text-white mt-1">
              {summary.total_epochs}
            </div>
          </div>

          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Best Epoch</div>
            <div className="text-lg font-medium text-white mt-1">
              {summary.best_epoch || 'N/A'}
            </div>
          </div>

          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">
              Best {summary.best_metric_name}
            </div>
            <div className="text-lg font-medium text-white mt-1">
              {summary.best_metric_value?.toFixed(4) || 'N/A'}
            </div>
          </div>
        </div>
      </div>

      {/* Epoch Selector */}
      <div className="bg-gray-800 rounded-lg p-4">
        <label className="text-sm text-gray-400 mb-2 block">Select Epoch</label>
        <select
          value={selectedEpoch || ''}
          onChange={(e) => setSelectedEpoch(Number(e.target.value))}
          className="w-full bg-gray-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {summary.epoch_metrics.map((epochData) => (
            <option key={epochData.epoch} value={epochData.epoch}>
              Epoch {epochData.epoch} - {summary.best_metric_name}: {epochData.primary_metric?.toFixed(4)}
            </option>
          ))}
        </select>
      </div>

      {/* Task-Specific Visualization */}
      <TaskSpecificVisualization
        taskType={validationResult.task_type}
        validationResult={validationResult}
        jobId={jobId}
      />
    </div>
  );
};

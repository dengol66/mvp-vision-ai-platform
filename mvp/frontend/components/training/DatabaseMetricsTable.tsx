"use client";

import React from "react";
import { CheckCircle2, XCircle } from "lucide-react";

interface TrainingMetric {
  id: number;
  job_id: number;
  epoch: number;
  step?: number;
  loss?: number;
  accuracy?: number;
  learning_rate?: number;
  checkpoint_path?: string;
  extra_metrics?: Record<string, any>;
  created_at: string;
}

interface DatabaseMetricsTableProps {
  metrics: TrainingMetric[];
  onCheckpointSelect?: (checkpointPath: string, epoch: number) => void;
}

export default function DatabaseMetricsTable({
  metrics,
  onCheckpointSelect,
}: DatabaseMetricsTableProps) {
  console.log('[DatabaseMetricsTable] Received metrics:', metrics);
  console.log('[DatabaseMetricsTable] Metrics length:', metrics?.length);

  if (!metrics || metrics.length === 0) {
    console.log('[DatabaseMetricsTable] No metrics, showing empty state');
    return (
      <div className="p-6 bg-amber-50 rounded-lg border border-amber-200 text-center">
        <p className="text-sm text-amber-800">
          학습 데이터가 없습니다.
        </p>
      </div>
    );
  }

  // Show last 10 epochs
  const recentMetrics = metrics.slice(-10).reverse();
  console.log('[DatabaseMetricsTable] Recent metrics count:', recentMetrics.length);

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h4 className="text-sm font-semibold text-gray-900">
          학습 메트릭 (최근 {recentMetrics.length} Epochs)
        </h4>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-2 text-left font-semibold text-gray-700">
                Epoch
              </th>
              <th className="px-4 py-2 text-right font-semibold text-gray-700">
                Loss
              </th>
              <th className="px-4 py-2 text-right font-semibold text-gray-700">
                Accuracy
              </th>
              <th className="px-4 py-2 text-right font-semibold text-gray-700">
                Learning Rate
              </th>
              <th className="px-4 py-2 text-center font-semibold text-gray-700">
                Checkpoint
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {recentMetrics.map((metric, index) => (
              <tr
                key={metric.id}
                className={index === 0 ? "bg-violet-50" : "hover:bg-gray-50"}
              >
                <td className="px-4 py-2 font-medium text-gray-900">
                  {metric.epoch}
                  {index === 0 && (
                    <span className="ml-2 text-xs text-violet-600 font-semibold">
                      Latest
                    </span>
                  )}
                </td>
                <td className="px-4 py-2 text-right text-gray-700 font-mono">
                  {metric.loss !== undefined && metric.loss !== null
                    ? metric.loss.toFixed(4)
                    : "-"}
                </td>
                <td className="px-4 py-2 text-right text-gray-700 font-mono">
                  {metric.accuracy !== undefined && metric.accuracy !== null
                    ? `${(metric.accuracy * 100).toFixed(2)}%`
                    : "-"}
                </td>
                <td className="px-4 py-2 text-right text-gray-700 font-mono text-xs">
                  {metric.learning_rate !== undefined &&
                  metric.learning_rate !== null
                    ? metric.learning_rate.toFixed(6)
                    : "-"}
                </td>
                <td className="px-4 py-2 text-center">
                  {metric.checkpoint_path ? (
                    <div className="flex items-center justify-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                      {onCheckpointSelect && (
                        <button
                          onClick={() =>
                            onCheckpointSelect(
                              metric.checkpoint_path!,
                              metric.epoch
                            )
                          }
                          className="text-xs text-violet-600 hover:text-violet-700 font-medium hover:underline"
                        >
                          Load
                        </button>
                      )}
                    </div>
                  ) : (
                    <XCircle className="w-4 h-4 text-gray-300 mx-auto" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {metrics.length > 10 && (
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-center">
          <p className="text-xs text-gray-500">
            총 {metrics.length} epochs (최근 10개만 표시)
          </p>
        </div>
      )}
    </div>
  );
}

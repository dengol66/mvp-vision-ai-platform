/**
 * PerClassMetricsTable Component
 *
 * Displays per-class metrics (precision, recall, f1-score, support)
 * in a sortable table format.
 */

import React, { useState } from 'react';

interface PerClassMetric {
  precision: number;
  recall: number;
  f1_score: number;
  support: number;
}

interface PerClassMetricsTableProps {
  perClassMetrics: Record<string, PerClassMetric>;
}

type SortField = 'class' | 'precision' | 'recall' | 'f1_score' | 'support';
type SortOrder = 'asc' | 'desc';

export const PerClassMetricsTable: React.FC<PerClassMetricsTableProps> = ({
  perClassMetrics
}) => {
  const [sortField, setSortField] = useState<SortField>('class');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Format percentage
  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  // Convert object to array for sorting
  const metricsArray = Object.entries(perClassMetrics).map(([className, metrics]) => ({
    class: className,
    ...metrics
  }));

  // Sort data
  const sortedData = [...metricsArray].sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];

    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = (bVal as string).toLowerCase();
    }

    if (sortOrder === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  // Handle column header click
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // Render sort icon
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <span className="text-gray-600 ml-1">⇅</span>;
    }
    return <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Per-Class Metrics</h3>

      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-700 border-b border-gray-600">
            <tr>
              <th
                className="text-left px-4 py-3 text-gray-300 font-medium cursor-pointer hover:bg-gray-600"
                onClick={() => handleSort('class')}
              >
                Class <SortIcon field="class" />
              </th>
              <th
                className="text-right px-4 py-3 text-gray-300 font-medium cursor-pointer hover:bg-gray-600"
                onClick={() => handleSort('precision')}
              >
                Precision <SortIcon field="precision" />
              </th>
              <th
                className="text-right px-4 py-3 text-gray-300 font-medium cursor-pointer hover:bg-gray-600"
                onClick={() => handleSort('recall')}
              >
                Recall <SortIcon field="recall" />
              </th>
              <th
                className="text-right px-4 py-3 text-gray-300 font-medium cursor-pointer hover:bg-gray-600"
                onClick={() => handleSort('f1_score')}
              >
                F1-Score <SortIcon field="f1_score" />
              </th>
              <th
                className="text-right px-4 py-3 text-gray-300 font-medium cursor-pointer hover:bg-gray-600"
                onClick={() => handleSort('support')}
              >
                Support <SortIcon field="support" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedData.map((row, idx) => (
              <tr
                key={row.class}
                className={`border-b border-gray-700 ${idx % 2 === 0 ? 'bg-gray-800' : 'bg-gray-750'} hover:bg-gray-700`}
              >
                <td className="px-4 py-3 text-white font-medium">{row.class}</td>
                <td className="px-4 py-3 text-right text-gray-300">
                  {formatPercent(row.precision)}
                </td>
                <td className="px-4 py-3 text-right text-gray-300">
                  {formatPercent(row.recall)}
                </td>
                <td className="px-4 py-3 text-right text-gray-300">
                  {formatPercent(row.f1_score)}
                </td>
                <td className="px-4 py-3 text-right text-gray-300">
                  {row.support}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary Stats */}
      <div className="mt-4 pt-4 border-t border-gray-700 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
        <div>
          <div className="text-gray-400">Avg Precision</div>
          <div className="text-white font-medium">
            {formatPercent(
              metricsArray.reduce((sum, row) => sum + row.precision, 0) / metricsArray.length
            )}
          </div>
        </div>
        <div>
          <div className="text-gray-400">Avg Recall</div>
          <div className="text-white font-medium">
            {formatPercent(
              metricsArray.reduce((sum, row) => sum + row.recall, 0) / metricsArray.length
            )}
          </div>
        </div>
        <div>
          <div className="text-gray-400">Avg F1-Score</div>
          <div className="text-white font-medium">
            {formatPercent(
              metricsArray.reduce((sum, row) => sum + row.f1_score, 0) / metricsArray.length
            )}
          </div>
        </div>
        <div>
          <div className="text-gray-400">Total Samples</div>
          <div className="text-white font-medium">
            {metricsArray.reduce((sum, row) => sum + row.support, 0)}
          </div>
        </div>
      </div>
    </div>
  );
};

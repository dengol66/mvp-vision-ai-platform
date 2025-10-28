/**
 * ConfusionMatrixView Component
 *
 * Displays confusion matrix as a heatmap with color intensity
 * representing the number of predictions.
 */

import React from 'react';

interface ConfusionMatrixViewProps {
  confusionMatrix: number[][];
  classNames: string[];
}

export const ConfusionMatrixView: React.FC<ConfusionMatrixViewProps> = ({
  confusionMatrix,
  classNames
}) => {
  // Find max value for normalization
  const maxValue = Math.max(...confusionMatrix.flat());

  // Get color intensity based on value (0-255)
  const getColorIntensity = (value: number): string => {
    const intensity = Math.floor((value / maxValue) * 255);
    // Use blue color scale
    return `rgb(${255 - intensity}, ${255 - intensity}, 255)`;
  };

  // Calculate cell size based on number of classes
  const numClasses = classNames.length;
  const cellSize = numClasses <= 5 ? 'w-20 h-20' : numClasses <= 10 ? 'w-16 h-16' : 'w-12 h-12';
  const fontSize = numClasses <= 5 ? 'text-base' : numClasses <= 10 ? 'text-sm' : 'text-xs';

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Confusion Matrix</h3>

      <div className="overflow-auto">
        <div className="inline-block min-w-full">
          {/* Matrix Table */}
          <table className="border-collapse">
            <thead>
              <tr>
                <th className={`${cellSize} border border-gray-600`}></th>
                <th
                  colSpan={numClasses}
                  className="text-center text-sm text-gray-400 py-2 border border-gray-600"
                >
                  Predicted
                </th>
              </tr>
              <tr>
                <th className={`${cellSize} border border-gray-600`}></th>
                {classNames.map((className, idx) => (
                  <th
                    key={idx}
                    className={`${cellSize} ${fontSize} text-gray-300 border border-gray-600 p-2`}
                    title={className}
                  >
                    <div className="truncate">{className}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {confusionMatrix.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {rowIdx === 0 && (
                    <th
                      rowSpan={numClasses}
                      className="text-center text-sm text-gray-400 px-2 border border-gray-600 align-middle"
                      style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
                    >
                      Actual
                    </th>
                  )}
                  {rowIdx > 0 && rowIdx === 0 && <th className={`${cellSize} border border-gray-600`}></th>}
                  <th
                    className={`${cellSize} ${fontSize} text-gray-300 border border-gray-600 p-2`}
                    title={classNames[rowIdx]}
                  >
                    <div className="truncate">{classNames[rowIdx]}</div>
                  </th>
                  {row.map((value, colIdx) => {
                    const isCorrect = rowIdx === colIdx;
                    return (
                      <td
                        key={colIdx}
                        className={`${cellSize} ${fontSize} border border-gray-600 text-center font-semibold relative`}
                        style={{
                          backgroundColor: isCorrect
                            ? getColorIntensity(value)
                            : `rgba(255, ${255 - (value / maxValue) * 200}, ${255 - (value / maxValue) * 200}, ${(value / maxValue) * 0.7})`
                        }}
                        title={`${classNames[rowIdx]} → ${classNames[colIdx]}: ${value}`}
                      >
                        <div className="text-gray-900">{value}</div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Legend */}
          <div className="mt-4 flex items-center justify-center space-x-6 text-sm text-gray-400">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-blue-200 border border-gray-600"></div>
              <span>Correct</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-red-200 border border-gray-600"></div>
              <span>Incorrect</span>
            </div>
            <div className="text-xs">
              (Color intensity = frequency)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

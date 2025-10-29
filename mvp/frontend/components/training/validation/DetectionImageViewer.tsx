/**
 * DetectionImageViewer Component
 *
 * Displays validation images with bounding box overlays for object detection.
 * Supports toggling true/predicted bbox visibility.
 */

import React, { useState, useEffect, useRef } from 'react';

interface BoundingBox {
  class_id: number;
  bbox: number[];  // [x, y, w, h] - format can vary
  confidence?: number;
  format?: 'yolo' | 'coco' | 'xyxy';  // yolo: normalized, coco: absolute, xyxy: [x1, y1, x2, y2]
}

interface DetectionImage {
  id: number;
  image_path: string;
  image_name: string;
  true_label: string;
  true_label_id: number;
  predicted_label: string | null;
  predicted_label_id: number | null;
  confidence: number | null;
  true_boxes: BoundingBox[];
  predicted_boxes: BoundingBox[];
  is_correct: boolean;
}

interface DetectionImageViewerProps {
  jobId: number;
  epoch: number;
  classId: number;
  className: string;
  showTrueBoxes: boolean;
  showPredictedBoxes: boolean;
  onClose: () => void;
}

export const DetectionImageViewer: React.FC<DetectionImageViewerProps> = ({
  jobId,
  epoch,
  classId,
  className,
  showTrueBoxes,
  showPredictedBoxes,
  onClose,
}) => {
  const [images, setImages] = useState<DetectionImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Fetch images filtered by class_id
  useEffect(() => {
    fetchImages();
  }, [jobId, epoch, classId]);

  // Redraw canvas when boxes visibility changes or image changes
  useEffect(() => {
    if (images.length > 0 && imageRef.current?.complete) {
      drawBoundingBoxes();
    }
  }, [images, currentIndex, showTrueBoxes, showPredictedBoxes]);

  const fetchImages = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/validation/jobs/${jobId}/results/${epoch}/images?true_label_id=${classId}&limit=1000`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch images: ${response.statusText}`);
      }

      const data = await response.json();
      setImages(data.images || []);
      setCurrentIndex(0);
    } catch (err) {
      console.error('Failed to fetch detection images:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch images');
    } finally {
      setLoading(false);
    }
  };

  const drawBoundingBoxes = () => {
    const canvas = canvasRef.current;
    const image = imageRef.current;
    if (!canvas || !image || !image.complete) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size to match image
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const currentImage = images[currentIndex];
    if (!currentImage) return;

    // Draw true boxes (green)
    if (showTrueBoxes && currentImage.true_boxes) {
      ctx.strokeStyle = '#10B981'; // green
      ctx.lineWidth = 3;
      currentImage.true_boxes.forEach((box) => {
        drawBox(ctx, box, canvas.width, canvas.height);
      });
    }

    // Draw predicted boxes (red)
    if (showPredictedBoxes && currentImage.predicted_boxes) {
      ctx.strokeStyle = '#EF4444'; // red
      ctx.lineWidth = 3;
      currentImage.predicted_boxes.forEach((box) => {
        drawBox(ctx, box, canvas.width, canvas.height);

        // Draw confidence label
        if (box.confidence !== undefined) {
          const [x, y] = getBboxCoords(box, canvas.width, canvas.height);
          ctx.fillStyle = '#EF4444';
          ctx.font = '14px sans-serif';
          ctx.fillText(`${(box.confidence * 100).toFixed(1)}%`, x, y - 5);
        }
      });
    }
  };

  const drawBox = (
    ctx: CanvasRenderingContext2D,
    box: BoundingBox,
    imageWidth: number,
    imageHeight: number
  ) => {
    const [x, y, w, h] = getBboxCoords(box, imageWidth, imageHeight);
    ctx.strokeRect(x, y, w, h);
  };

  const getBboxCoords = (
    box: BoundingBox,
    imageWidth: number,
    imageHeight: number
  ): [number, number, number, number] => {
    const [b0, b1, b2, b3] = box.bbox;

    if (box.format === 'yolo') {
      // YOLO format: normalized [x_center, y_center, width, height]
      const x = (b0 - b2 / 2) * imageWidth;
      const y = (b1 - b3 / 2) * imageHeight;
      const w = b2 * imageWidth;
      const h = b3 * imageHeight;
      return [x, y, w, h];
    } else if (box.format === 'xyxy') {
      // XYXY format: [x1, y1, x2, y2]
      return [b0, b1, b2 - b0, b3 - b1];
    } else {
      // COCO format (default): [x, y, width, height] in absolute coordinates
      return [b0, b1, b2, b3];
    }
  };

  const handleImageLoad = () => {
    drawBoundingBoxes();
  };

  const handlePrevious = () => {
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => Math.min(images.length - 1, prev + 1));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-red-500">에러: {error}</div>
      </div>
    );
  }

  if (images.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">이미지가 없습니다</div>
      </div>
    );
  }

  const currentImage = images[currentIndex];

  return (
    <div className="flex flex-col h-full">
      {/* Image Display */}
      <div className="flex-1 relative bg-gray-100 flex items-center justify-center overflow-hidden">
        <div className="relative">
          <img
            ref={imageRef}
            src={`${process.env.NEXT_PUBLIC_API_URL}/validation/images/${currentImage.id}`}
            alt={currentImage.image_name}
            className="max-w-full max-h-[70vh] object-contain"
            onLoad={handleImageLoad}
          />
          <canvas
            ref={canvasRef}
            className="absolute top-0 left-0 w-full h-full pointer-events-none"
            style={{ imageRendering: 'crisp-edges' }}
          />
        </div>
      </div>

      {/* Navigation Controls */}
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="flex items-center justify-between mb-3">
          <button
            onClick={handlePrevious}
            disabled={currentIndex === 0}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 rounded text-sm font-medium transition-colors"
          >
            이전
          </button>
          <div className="text-sm text-gray-600">
            {currentIndex + 1} / {images.length}
          </div>
          <button
            onClick={handleNext}
            disabled={currentIndex === images.length - 1}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 rounded text-sm font-medium transition-colors"
          >
            다음
          </button>
        </div>

        {/* Image Info */}
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-gray-600">이미지:</span>
            <span className="font-medium text-gray-900">{currentImage.image_name}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">True Class:</span>
            <span className="font-medium text-gray-900">{currentImage.true_label}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Predicted Class:</span>
            <span className="font-medium text-gray-900">
              {currentImage.predicted_label || 'N/A'}
              {currentImage.confidence && (
                <span className="text-gray-600 ml-1">
                  ({(currentImage.confidence * 100).toFixed(1)}%)
                </span>
              )}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">True Boxes:</span>
            <span className="font-medium text-green-600">
              {currentImage.true_boxes?.length || 0}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Predicted Boxes:</span>
            <span className="font-medium text-red-600">
              {currentImage.predicted_boxes?.length || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="border-t border-gray-200 bg-gray-50 p-3">
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-green-500"></div>
            <span className="text-gray-700">True Boxes</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-red-500"></div>
            <span className="text-gray-700">Predicted Boxes</span>
          </div>
        </div>
      </div>
    </div>
  );
};

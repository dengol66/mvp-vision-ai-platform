import React from 'react';
import Link from 'next/link';
import { Globe, Lock } from 'lucide-react';
import { Dataset } from '@/types/dataset';
import { cn } from '@/lib/utils/cn';

interface DatasetCardProps {
  dataset: Dataset;
  onSelect?: (dataset: Dataset) => void;
  selected?: boolean;
}

const formatNames: Record<string, string> = {
  imagefolder: 'ImageFolder',
  yolo: 'YOLO',
  coco: 'COCO',
  pascal_voc: 'Pascal VOC',
  dice: 'DICE Format',
};

// Avatar helper functions
const getAvatarColor = (email: string | null | undefined): string => {
  if (!email) return 'bg-gray-400';
  const colors = [
    'bg-red-500', 'bg-orange-500', 'bg-amber-500', 'bg-yellow-500',
    'bg-lime-500', 'bg-green-500', 'bg-emerald-500', 'bg-teal-500',
    'bg-cyan-500', 'bg-sky-500', 'bg-blue-500', 'bg-indigo-500',
    'bg-violet-500', 'bg-purple-500', 'bg-fuchsia-500', 'bg-pink-500',
    'bg-rose-500'
  ];
  const hash = email.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
};

const getAvatarInitials = (owner_name: string | null | undefined, owner_email: string | null | undefined): string => {
  if (owner_name) {
    if (/[가-힣]/.test(owner_name)) {
      return owner_name.slice(0, 2);
    }
    const parts = owner_name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return owner_name.slice(0, 2).toUpperCase();
  }
  if (owner_email) {
    return owner_email.slice(0, 2).toUpperCase();
  }
  return '?';
};

export default function DatasetCard({ dataset, onSelect, selected }: DatasetCardProps) {
  const formatName = formatNames[dataset.format] || dataset.format;
  const labeledBadge = dataset.labeled
    ? { color: 'bg-green-100 text-green-800', text: 'Labeled' }
    : { color: 'bg-gray-100 text-gray-600', text: 'Unlabeled' };

  const avatarColor = getAvatarColor(dataset.owner_email);
  const avatarInitials = getAvatarInitials(dataset.owner_name, dataset.owner_email);

  return (
    <div
      onClick={() => onSelect?.(dataset)}
      className={`
        relative p-4 rounded-lg border-2 cursor-pointer transition-all
        ${selected
          ? 'border-indigo-500 bg-indigo-50 shadow-md'
          : 'border-gray-200 hover:border-indigo-300 hover:shadow-sm'
        }
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">
            {dataset.name}
          </h3>
          <p className="text-sm text-gray-600 mt-1 line-clamp-2">
            {dataset.description}
          </p>
        </div>
        {selected && (
          <div className="ml-2">
            <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
        )}
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-2 mb-3">
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${labeledBadge.color}`}>
          {labeledBadge.text}
        </span>
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
          {formatName}
        </span>
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
          {dataset.source}
        </span>
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 flex items-center gap-1">
          {dataset.visibility === 'public' ? (
            <Globe className="w-3 h-3 text-green-600" />
          ) : (
            <Lock className="w-3 h-3 text-gray-600" />
          )}
          <span className="capitalize">{dataset.visibility || 'private'}</span>
        </span>
      </div>

      {/* Owner */}
      {(dataset.owner_name || dataset.owner_email) && (
        <div className="mb-3 flex items-center gap-2">
          <div
            className={cn(
              'w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold text-white',
              avatarColor
            )}
            title={dataset.owner_email || ''}
          >
            {avatarInitials}
          </div>
          <div className="text-xs text-gray-600">
            {dataset.owner_name || dataset.owner_email}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-500">Images:</span>
          <span className="ml-1 font-medium text-gray-900">
            {dataset.num_items.toLocaleString()}
          </span>
        </div>
        {dataset.size_mb && (
          <div>
            <span className="text-gray-500">Size:</span>
            <span className="ml-1 font-medium text-gray-900">
              {dataset.size_mb.toFixed(1)} MB
            </span>
          </div>
        )}
      </div>

      {/* Tags */}
      {dataset.tags && dataset.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {dataset.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-gray-50 text-gray-600 rounded"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* View Details Button */}
      <div className="mt-4 pt-3 border-t border-gray-200">
        <Link
          href={`/datasets/${dataset.id}`}
          onClick={(e) => e.stopPropagation()}
          className="block w-full px-4 py-2 text-center text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded transition-colors"
        >
          View Details & Images →
        </Link>
      </div>
    </div>
  );
}

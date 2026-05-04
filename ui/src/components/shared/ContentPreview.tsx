import type { ContentItem } from '../../types/models';
import { MessageSquare, Image, Video } from 'lucide-react';

interface Props {
  items: ContentItem[];
}

export function ContentPreview({ items }: Props) {
  if (!items || items.length === 0) return null;
  return (
    <div className="space-y-1 mb-3">
      {items.map((item, idx) => (
        <div key={idx} className="flex items-center bg-gray-50 border border-gray-100 rounded-md px-2 py-1.5 text-xs text-gray-600">
          <span className="font-bold text-gray-400 mr-2 w-4">#{idx + 1}</span>
          {item.type === 'text' ? (
            <MessageSquare size={12} className="text-blue-500 mr-1.5" />
          ) : item.type === 'image' ? (
            <Image size={12} className="text-green-500 mr-1.5" />
          ) : (
            <Video size={12} className="text-orange-500 mr-1.5" />
          )}
          <span className="truncate flex-1">{item.value || '(empty)'}</span>
        </div>
      ))}
    </div>
  );
}

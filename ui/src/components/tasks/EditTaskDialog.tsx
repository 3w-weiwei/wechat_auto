import { useState } from 'react';
import type { Task } from '../../types/models';
import { X } from 'lucide-react';
import type { ContentItem } from '../../types/models';

interface Props {
  task: Task;
  onSave: (id: string, data: Record<string, unknown>) => void;
  onClose: () => void;
}

export function EditTaskDialog({ task, onSave, onClose }: Props) {
  const [group, setGroup] = useState(task.group);
  const [datetime, setDatetime] = useState(task.datetime);
  const [contents, setContents] = useState<ContentItem[]>([...task.contents]);

  const addContent = (type: ContentItem['type']) => {
    setContents([...contents, { type, value: '', sort_order: contents.length }]);
  };

  const updateContent = (idx: number, value: string) => {
    setContents(contents.map((c, i) => (i === idx ? { ...c, value } : c)));
  };

  const removeContent = (idx: number) => {
    setContents(contents.filter((_, i) => i !== idx));
  };

  const handleSave = () => {
    onSave(task.id, { group, datetime, contents });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl p-5 w-[340px] max-h-[560px] overflow-y-auto shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold text-gray-800 text-lg">编辑任务</h3>
          <button onClick={onClose}><X size={18} className="text-gray-400" /></button>
        </div>

        <label className="text-xs font-bold text-gray-600 mb-1 block">目标群聊</label>
        <input value={group} onChange={(e) => setGroup(e.target.value)}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:border-green-500" />

        <label className="text-xs font-bold text-gray-600 mb-1 block">计划时间</label>
        <input type="datetime-local" value={datetime.replace(' ', 'T')} onChange={(e) => setDatetime(e.target.value.replace('T', ' '))}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:border-green-500" />

        <label className="text-xs font-bold text-gray-600 mb-2 block">推送内容 ({contents.length})</label>
        <div className="space-y-2 mb-3">
          {contents.map((c, idx) => (
            <div key={idx} className="bg-gray-50 border border-gray-200 rounded-lg p-2">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-bold text-gray-500">#{idx + 1} {c.type === 'text' ? '📝 文字' : c.type === 'image' ? '🖼 图片' : '🎬 视频'}</span>
                <button onClick={() => removeContent(idx)}><X size={14} className="text-gray-400 hover:text-red-500" /></button>
              </div>
              <textarea rows={2} value={c.value}
                onChange={(e) => updateContent(idx, e.target.value)}
                placeholder={c.type === 'text' ? '输入文字内容...' : '文件路径...'}
                className="w-full text-xs p-1.5 border border-gray-200 rounded bg-white focus:outline-none" />
            </div>
          ))}
        </div>

        <div className="flex space-x-2 mb-4">
          <button onClick={() => addContent('text')}
            className="flex-1 py-1.5 border border-dashed border-blue-300 text-blue-500 bg-blue-50 rounded-md text-xs font-bold">+ 文字</button>
          <button onClick={() => addContent('image')}
            className="flex-1 py-1.5 border border-dashed border-green-300 text-green-600 bg-green-50 rounded-md text-xs font-bold">+ 图片</button>
          <button onClick={() => addContent('video')}
            className="flex-1 py-1.5 border border-dashed border-orange-300 text-orange-500 bg-orange-50 rounded-md text-xs font-bold">+ 视频</button>
        </div>

        <button onClick={handleSave}
          className="w-full bg-green-500 text-white py-2.5 rounded-xl text-sm font-bold hover:bg-green-600">
          保存修改
        </button>
      </div>
    </div>
  );
}

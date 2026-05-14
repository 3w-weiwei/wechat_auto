import type { Task } from '../../types/models';
import { ToggleSwitch } from '../shared/ToggleSwitch';
import { ContentPreview } from '../shared/ContentPreview';
import { Calendar, Layers, MessageSquare, Image, Video, Play, Edit, Trash2 } from 'lucide-react';

interface Props {
  task: Task;
  onToggle: (id: string) => void;
  onRunNow: (id: string) => void;
  onEdit: (task: Task) => void;
  onDelete: (id: string) => void;
}

export function TaskCard({ task, onToggle, onRunNow, onEdit, onDelete }: Props) {
  const now = new Date();
  const taskDate = new Date(task.datetime);
  const isExpired = taskDate < now;

  const getIcon = () => {
    if (task.contents.length > 1) return <Layers size={18} />;
    const first = task.contents[0];
    if (!first) return <MessageSquare size={18} />;
    if (first.type === 'image') return <Image size={18} />;
    if (first.type === 'video') return <Video size={18} />;
    return <MessageSquare size={18} />;
  };

  return (
    <div className={`bg-white rounded-2xl p-4 shadow-sm border transition-all ${
      isExpired ? 'border-gray-200 opacity-50' :
      task.active ? 'border-green-100 shadow-green-50/30' :
      'border-gray-200 opacity-70'
    }`}>
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${task.contents.length > 1 ? 'bg-orange-50 text-orange-500' : 'bg-blue-50 text-blue-500'}`}>
            {getIcon()}
          </div>
          <div>
            <h3 className="font-bold text-gray-800 text-sm">{task.group}</h3>
            <div className="flex items-center space-x-2 mt-0.5">
              <span className="flex items-center text-xs text-gray-500">
                <Calendar size={12} className="mr-1" /> {task.datetime}
              </span>
              {isExpired && (
                <span className="text-[10px] font-bold text-red-400 bg-red-50 px-1.5 py-0.5 rounded">已过期</span>
              )}
              <span className="text-[10px] font-bold text-blue-500 bg-blue-50 px-1.5 py-0.5 rounded">
                {task.contents.length} 条
              </span>
            </div>
          </div>
        </div>
        <ToggleSwitch checked={task.active} onChange={() => onToggle(task.id)} />
      </div>

      <ContentPreview items={task.contents} />

      <div className="flex items-center space-x-2 mt-2 pt-2 border-t border-gray-50">
        <button
          onClick={() => onRunNow(task.id)}
          className="flex items-center text-xs font-bold text-orange-500 bg-orange-50 hover:bg-orange-100 px-2 py-1.5 rounded-md border border-orange-100 transition-colors"
        >
          <Play size={12} className="mr-1" /> 发送
        </button>
        <button
          onClick={() => onEdit(task)}
          className="flex items-center text-xs font-bold text-blue-500 bg-blue-50 hover:bg-blue-100 px-2 py-1.5 rounded-md border border-blue-100 transition-colors"
        >
          <Edit size={12} className="mr-1" /> 编辑
        </button>
        <div className="flex-1" />
        <button
          onClick={() => onDelete(task.id)}
          className="flex items-center text-xs font-bold text-red-400 bg-red-50 hover:bg-red-100 px-2 py-1.5 rounded-md border border-red-100 transition-colors"
        >
          <Trash2 size={12} className="mr-1" /> 删除
        </button>
      </div>
    </div>
  );
}

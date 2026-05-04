import { useState } from 'react';
import { useTasks } from '../../hooks/useTasks';
import { Users, Layers, Calendar, PlusCircle, XCircle, Upload, CheckCircle2 } from 'lucide-react';

interface ContentItemForm {
  id: number;
  type: 'text' | 'image' | 'video';
  value: string;
}

interface SlotForm {
  id: number;
  date: string;
  time: string;
  contents: ContentItemForm[];
}

export function CreatePage() {
  const { createTasks } = useTasks();
  const [groups, setGroups] = useState<string[]>(['产品研发沟通群']);
  const [groupInput, setGroupInput] = useState('');
  const [slots, setSlots] = useState<SlotForm[]>([
    { id: Date.now(), date: new Date().toISOString().slice(0, 10), time: '10:00', contents: [{ id: 1, type: 'text', value: '' }] }
  ]);

  const handleAddGroup = () => {
    const trimmed = groupInput.trim();
    if (!trimmed) return;
    const names = trimmed.replace(/，/g, ',').split(',').map(s => s.trim()).filter(Boolean);
    const newGroups = names.filter(n => !groups.includes(n));
    if (newGroups.length > 0) {
      setGroups([...groups, ...newGroups]);
      setGroupInput('');
    }
  };

  const handleRemoveGroup = (name: string) => {
    setGroups(groups.filter(g => g !== name));
  };

  const handleAddSlot = () => {
    setSlots([...slots, { id: Date.now(), date: new Date().toISOString().slice(0, 10), time: '12:00', contents: [] }]);
  };

  const handleRemoveSlot = (id: number) => {
    if (slots.length <= 1) return;
    setSlots(slots.filter(s => s.id !== id));
  };

  const handleAddContent = (slotId: number, type: ContentItemForm['type']) => {
    setSlots(slots.map(s => s.id === slotId
      ? { ...s, contents: [...s.contents, { id: Date.now(), type, value: type === 'text' ? '' : '待上传文件...' }] }
      : s
    ));
  };

  const handleRemoveContent = (slotId: number, contentId: number) => {
    setSlots(slots.map(s => s.id === slotId
      ? { ...s, contents: s.contents.filter(c => c.id !== contentId) }
      : s
    ));
  };

  const handleUpdateContent = (slotId: number, contentId: number, value: string) => {
    setSlots(slots.map(s => s.id === slotId
      ? { ...s, contents: s.contents.map(c => c.id === contentId ? { ...c, value } : c) }
      : s
    ));
  };

  const handleUpdateSlot = (slotId: number, field: 'date' | 'time', value: string) => {
    setSlots(slots.map(s => s.id === slotId ? { ...s, [field]: value } : s));
  };

  const handleSubmit = async () => {
    if (groups.length === 0) { alert('请至少添加一个目标群聊'); return; }
    if (slots.length === 0) { alert('请至少添加一个时段'); return; }

    await createTasks({
      groups,
      slots: slots.map(s => ({
        date: s.date,
        time: s.time,
        contents: s.contents.filter(c => c.value.trim() !== ''),
      })),
    });
  };

  const activeSlots = slots.filter(s => s.contents.some(c => c.value.trim() !== ''));
  const totalTasks = groups.length * activeSlots.length;
  const accentColors = ['border-l-blue-500', 'border-l-purple-500', 'border-l-orange-500', 'border-l-green-500', 'border-l-indigo-500'];

  return (
    <div className="flex-1 overflow-y-auto bg-white p-4">
      <h2 className="text-xl font-bold text-gray-800 mb-4">新建推送任务</h2>

      {/* 目标群聊 */}
      <div className="bg-gray-50 border border-gray-100 rounded-xl p-3 mb-4">
        <div className="flex items-center mb-3">
          <Users size={16} className="text-green-600 mr-2" />
          <span className="font-bold text-gray-700 text-sm">目标群聊 / 联系人</span>
        </div>
        <div className="flex space-x-2 mb-3">
          <input type="text" placeholder="输入群名，多个用逗号隔开"
            className="flex-1 bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-green-500"
            value={groupInput} onChange={e => setGroupInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAddGroup()} />
          <button onClick={handleAddGroup} className="bg-green-500 text-white px-3 py-2 rounded-lg text-xs font-bold hover:bg-green-600">添加</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {groups.length === 0 ? (
            <div className="w-full text-center text-xs text-gray-400 py-2">💡 输入群名后点击添加</div>
          ) : (
            groups.map((g, i) => (
              <div key={i} className="flex items-center bg-green-50 border border-green-200 text-green-700 text-xs px-2 py-1 rounded-full">
                <Users size={10} className="mr-1" /> {g}
                <button onClick={() => handleRemoveGroup(g)}><XCircle size={12} className="ml-1 text-green-500 hover:text-red-500" /></button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 推送时段 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center">
          <Layers size={16} className="text-indigo-500 mr-2" />
          <span className="font-bold text-gray-700 text-sm">推送时段</span>
        </div>
        <span className="text-xs font-bold text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded">{slots.length} 个时段</span>
      </div>

      <div className="space-y-4 mb-4">
        {slots.map((slot, idx) => (
          <div key={slot.id} className={`bg-white border border-gray-200 border-l-4 ${accentColors[idx % accentColors.length]} rounded-xl p-3 shadow-sm`}>
            <div className="flex justify-between items-center mb-3">
              <span className="font-bold text-sm text-gray-600">⏰ 时段 {idx + 1}</span>
              <button onClick={() => handleRemoveSlot(slot.id)} className="text-gray-400 hover:text-red-500"><XCircle size={16} /></button>
            </div>

            <div className="flex items-center space-x-2 mb-3">
              <Calendar size={14} className="text-gray-400" />
              <input type="date" value={slot.date}
                onChange={e => handleUpdateSlot(slot.id, 'date', e.target.value)}
                className="flex-1 bg-gray-50 border border-gray-200 rounded-md px-2 py-1.5 text-xs" />
              <input type="time" value={slot.time}
                onChange={e => handleUpdateSlot(slot.id, 'time', e.target.value)}
                className="w-24 bg-gray-50 border border-gray-200 rounded-md px-2 py-1.5 text-xs" />
            </div>

            {/* 内容列表 */}
            <div className="space-y-2 mb-3">
              {slot.contents.map((c, ci) => (
                <div key={c.id} className="bg-gray-50 border border-gray-200 rounded-lg p-2 relative group">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-bold text-gray-500">#{ci + 1} {c.type === 'text' ? '📝 文字' : c.type === 'image' ? '🖼 图片' : '🎬 视频'}</span>
                    <button onClick={() => handleRemoveContent(slot.id, c.id)}><XCircle size={14} className="text-gray-400 hover:text-red-500" /></button>
                  </div>
                  {c.type === 'text' ? (
                    <textarea rows={2} placeholder="输入文字内容..."
                      className="w-full text-xs p-1.5 border border-gray-200 rounded bg-white focus:outline-none"
                      value={c.value} onChange={e => handleUpdateContent(slot.id, c.id, e.target.value)} />
                  ) : (
                    <div className="flex items-center p-1.5 border border-dashed border-gray-300 rounded bg-white text-xs text-gray-500 cursor-pointer hover:bg-gray-100">
                      <Upload size={14} className="mr-2 text-blue-400" /> {c.value || '点击选择文件'}
                    </div>
                  )}
                </div>
              ))}
              {slot.contents.length === 0 && (
                <div className="text-center text-xs text-gray-400 py-2">💡 添加文字或图片/视频内容</div>
              )}
            </div>

            <div className="flex space-x-2">
              <button onClick={() => handleAddContent(slot.id, 'text')} className="flex-1 py-1.5 border border-dashed border-blue-300 text-blue-500 bg-blue-50 rounded-md text-xs font-bold hover:bg-blue-100 transition-colors">+ 文字</button>
              <button onClick={() => handleAddContent(slot.id, 'image')} className="flex-1 py-1.5 border border-dashed border-green-300 text-green-600 bg-green-50 rounded-md text-xs font-bold hover:bg-green-100 transition-colors">+ 图片</button>
              <button onClick={() => handleAddContent(slot.id, 'video')} className="flex-1 py-1.5 border border-dashed border-orange-300 text-orange-500 bg-orange-50 rounded-md text-xs font-bold hover:bg-orange-100 transition-colors">+ 视频</button>
            </div>
          </div>
        ))}
      </div>

      <button onClick={handleAddSlot} className="w-full border-2 border-dashed border-indigo-200 text-indigo-500 bg-indigo-50 py-3 rounded-xl text-sm font-bold flex items-center justify-center hover:bg-indigo-100 transition-colors mb-4">
        <PlusCircle size={16} className="mr-2" /> 新增时段
      </button>

      <div className="text-center text-xs text-gray-500 mb-4">
        📊 {groups.length} 个群聊 × {activeSlots.length} 个时段 = <span className="font-bold text-indigo-500">{totalTasks}</span> 个任务
      </div>

      <button onClick={handleSubmit}
        className="w-full bg-green-500 text-white py-3.5 rounded-xl text-sm font-bold flex items-center justify-center shadow-lg shadow-green-500/30 hover:bg-green-600 active:scale-[0.98] transition-all">
        <CheckCircle2 size={18} className="mr-2" /> 保存并加入队列
      </button>
      <div className="h-10" />
    </div>
  );
}

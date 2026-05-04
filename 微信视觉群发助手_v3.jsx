import React, { useState, useEffect, useRef } from 'react';
import { 
  CheckCircle2, Clock, Image as ImageIcon, MessageSquare, PlusCircle, 
  Settings, Video, Search, Play, Trash2, MonitorSmartphone, Eye,
  Users, Layers, Calendar, XCircle, ArrowUp, ArrowDown, Upload,
  ChevronDown, ChevronUp, Edit, Save, Terminal, Paperclip, Folder,
  Sun, Moon
} from 'lucide-react';

const AutoSenderApp = () => {
  const [activeTab, setActiveTab] = useState('tasks');
  const [engineStatus, setEngineStatus] = useState('ready'); 
  const logsEndRef = useRef(null);

  // --- 1. 模拟任务数据 (对齐 PyQt 的 contents 结构) ---
  const [tasks, setTasks] = useState([
    { 
      id: 1, group: '产品研发沟通群', datetime: '2026-05-05 10:00', active: true,
      contents: [
        { type: 'text', value: '大家早上好，今日晨会资料如下：' },
        { type: 'image', value: 'a1b2c3d4_晨会数据图.png' }
      ]
    },
    { 
      id: 2, group: 'VIP客户维护群', datetime: '2026-05-05 14:30', active: true,
      contents: [
        { type: 'video', value: 'e5f6g7h8_新品演示视频.mp4' }
      ]
    }
  ]);

  // --- 2. 新建任务表单状态 ---
  const [createGroups, setCreateGroups] = useState(['交流群A']);
  const [groupInput, setGroupInput] = useState('');
  const [createSlots, setCreateSlots] = useState([
    { id: Date.now(), time: '10:00', contents: [{ id: 1, type: 'text', value: '' }] }
  ]);

  // --- 3. 日志系统 ---
  const [logs, setLogs] = useState([
    { id: 1, text: '[System] 已加载 2 个任务，DPI=144', color: 'text-gray-500' },
    { id: 2, text: '[Attach] 📁 附件目录: ~/WePush/attachments', color: 'text-teal-500' },
  ]);

  const addLog = (text, color = 'text-gray-500') => {
    setLogs(prev => [...prev, { id: Date.now(), text, color }]);
  };

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // --- 交互逻辑函数 ---
  const handleAddGroup = () => {
    if (groupInput.trim() && !createGroups.includes(groupInput.trim())) {
      setCreateGroups([...createGroups, groupInput.trim()]);
      setGroupInput('');
    }
  };

  const handleAddSlot = () => {
    setCreateSlots([...createSlots, { id: Date.now(), time: '12:00', contents: [] }]);
  };

  const handleAddContentToSlot = (slotId, type) => {
    setCreateSlots(slots => slots.map(slot => {
      if (slot.id === slotId) {
        return { ...slot, contents: [...slot.contents, { id: Date.now(), type, value: type === 'text' ? '' : '待上传文件...' }] };
      }
      return slot;
    }));
  };

  const handleDeleteContent = (slotId, contentId) => {
    setCreateSlots(slots => slots.map(slot => {
      if (slot.id === slotId) {
        return { ...slot, contents: slot.contents.filter(c => c.id !== contentId) };
      }
      return slot;
    }));
  };

  const handleBatchCreate = () => {
    if (createGroups.length === 0 || createSlots.length === 0) {
      alert("请至少添加一个目标群聊和一个时段");
      return;
    }
    const newTasks = [];
    createGroups.forEach(group => {
      createSlots.forEach((slot, idx) => {
        newTasks.push({
          id: Date.now() + Math.random(),
          group: group,
          datetime: `2026-05-06 ${slot.time}`,
          active: true,
          contents: slot.contents.filter(c => c.value.trim() !== '')
        });
      });
    });
    setTasks([...tasks, ...newTasks]);
    addLog(`[Task] ✅ 批量新增 ${newTasks.length} 个任务`, 'text-green-500');
    setActiveTab('tasks');
  };

  // ================= 渲染区 =================

  const renderHeader = () => (
    <div className="bg-white border-b border-gray-100 px-4 py-3 flex justify-between items-center z-10 rounded-t-3xl">
      <div className="flex items-center space-x-2">
        <MonitorSmartphone size={18} className="text-gray-700" />
        <span className="font-bold text-gray-800 text-base tracking-wide">智推助手</span>
      </div>
      <div className="flex items-center space-x-1.5 bg-gray-50 px-3 py-1 rounded-full border border-gray-100">
        <div className={`w-2 h-2 rounded-full ${engineStatus === 'ready' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`}></div>
        <span className="text-xs text-gray-600 font-medium">
          {engineStatus === 'ready' ? '视觉就绪' : '未见微信'}
        </span>
      </div>
    </div>
  );

  const renderTasks = () => (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-4 space-y-4">
      <div className="flex justify-between items-end mb-2">
        <div>
          <h2 className="text-lg font-bold text-gray-800">执行队列</h2>
          <p className="text-xs text-gray-500 mt-1">请保持微信窗口可见</p>
        </div>
        <div className="text-sm font-bold text-green-600 bg-green-50 px-3 py-1 rounded-lg">
          {tasks.filter(t => t.active).length} 个待办
        </div>
      </div>

      {tasks.map(task => (
        <div key={task.id} className={`bg-white rounded-2xl p-4 shadow-sm border transition-all ${task.active ? 'border-green-100 shadow-green-50/30' : 'border-gray-200 opacity-70'}`}>
          <div className="flex justify-between items-start mb-3">
            <div className="flex items-center space-x-3">
              <div className={`p-2 rounded-lg ${task.contents.length > 1 ? 'bg-orange-50 text-orange-500' : 'bg-blue-50 text-blue-500'}`}>
                {task.contents.length > 1 ? <Layers size={18} /> : 
                 task.contents[0]?.type === 'text' ? <MessageSquare size={18} /> : 
                 task.contents[0]?.type === 'video' ? <Video size={18} /> : <ImageIcon size={18} />}
              </div>
              <div>
                <h3 className="font-bold text-gray-800 text-sm">{task.group}</h3>
                <div className="flex items-center space-x-2 mt-0.5">
                  <span className="flex items-center text-xs text-gray-500">
                    <Calendar size={12} className="mr-1" /> {task.datetime}
                  </span>
                  <span className="text-[10px] font-bold text-blue-500 bg-blue-50 px-1.5 py-0.5 rounded">
                    {task.contents.length} 条
                  </span>
                </div>
              </div>
            </div>
            {/* Toggle Switch */}
            <button onClick={() => setTasks(tasks.map(t => t.id === task.id ? { ...t, active: !t.active } : t))}
              className={`w-11 h-6 rounded-full relative transition-colors ${task.active ? 'bg-green-500' : 'bg-gray-200'}`}>
              <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${task.active ? 'translate-x-6' : 'translate-x-1'}`}></div>
            </button>
          </div>

          {/* Content Preview List */}
          <div className="space-y-1 mb-3">
            {task.contents.map((item, idx) => (
              <div key={idx} className="flex items-center bg-gray-50 border border-gray-100 rounded-md px-2 py-1.5 text-xs text-gray-600">
                <span className="font-bold text-gray-400 mr-2 w-4">#{idx+1}</span>
                {item.type === 'text' ? <MessageSquare size={12} className="text-blue-500 mr-1.5"/> : 
                 item.type === 'image' ? <ImageIcon size={12} className="text-green-500 mr-1.5"/> : <Video size={12} className="text-orange-500 mr-1.5"/>}
                <span className="truncate flex-1">{item.value || '空内容'}</span>
              </div>
            ))}
          </div>

          {/* Action Row */}
          <div className="flex items-center space-x-2 mt-2 pt-2 border-t border-gray-50">
            <button className="flex items-center text-xs font-bold text-orange-500 bg-orange-50 hover:bg-orange-100 px-2 py-1.5 rounded-md border border-orange-100 transition-colors"
              onClick={() => { addLog(`[Manual] 强制执行: ${task.group}`, 'text-orange-500') }}>
              <Play size={12} className="mr-1" /> 发送
            </button>
            <button className="flex items-center text-xs font-bold text-blue-500 bg-blue-50 hover:bg-blue-100 px-2 py-1.5 rounded-md border border-blue-100 transition-colors">
              <Edit size={12} className="mr-1" /> 编辑
            </button>
            <div className="flex-1"></div>
            <button className="flex items-center text-xs font-bold text-red-400 bg-red-50 hover:bg-red-100 px-2 py-1.5 rounded-md border border-red-100 transition-colors"
              onClick={() => setTasks(tasks.filter(t => t.id !== task.id))}>
              <Trash2 size={12} className="mr-1" /> 删除
            </button>
          </div>
        </div>
      ))}
    </div>
  );

  const renderCreate = () => (
    <div className="flex-1 overflow-y-auto bg-white p-4">
      <h2 className="text-xl font-bold text-gray-800 mb-4">新建推送任务</h2>
      
      {/* 区域 1: 目标群聊 */}
      <div className="bg-gray-50 border border-gray-100 rounded-xl p-3 mb-4">
        <div className="flex items-center mb-3">
          <Users size={16} className="text-green-600 mr-2" />
          <span className="font-bold text-gray-700 text-sm">目标群聊 / 联系人</span>
        </div>
        <div className="flex space-x-2 mb-3">
          <input 
            type="text" placeholder="输入群名，多个用逗号隔开" 
            className="flex-1 bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-green-500"
            value={groupInput} onChange={e => setGroupInput(e.target.value)} onKeyPress={e => e.key === 'Enter' && handleAddGroup()}
          />
          <button onClick={handleAddGroup} className="bg-green-500 text-white px-3 py-2 rounded-lg text-xs font-bold hover:bg-green-600">添加</button>
        </div>
        {/* Tags */}
        <div className="flex flex-wrap gap-2">
          {createGroups.length === 0 ? (
            <div className="w-full text-center text-xs text-gray-400 py-2">💡 输入群名后点击添加</div>
          ) : (
            createGroups.map((g, i) => (
              <div key={i} className="flex items-center bg-green-50 border border-green-200 text-green-700 text-xs px-2 py-1 rounded-full">
                <Users size={10} className="mr-1" /> {g}
                <button onClick={() => setCreateGroups(createGroups.filter(x => x !== g))} className="ml-1 text-green-500 hover:text-red-500"><XCircle size={12}/></button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 区域 2: 推送时段 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center">
          <Layers size={16} className="text-indigo-500 mr-2" />
          <span className="font-bold text-gray-700 text-sm">推送时段</span>
        </div>
        <span className="text-xs font-bold text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded">{createSlots.length} 个时段</span>
      </div>

      <div className="space-y-4 mb-4">
        {createSlots.map((slot, index) => {
          const colors = ['text-blue-500', 'text-purple-500', 'text-orange-500', 'text-green-500'];
          const borderColors = ['border-blue-500', 'border-purple-500', 'border-orange-500', 'border-green-500'];
          const accentColor = colors[index % colors.length];
          const accentBorder = borderColors[index % borderColors.length];

          return (
            <div key={slot.id} className={`bg-white border border-gray-200 border-l-4 ${accentBorder} rounded-xl p-3 shadow-sm`}>
              <div className="flex justify-between items-center mb-3">
                <span className={`font-bold text-sm ${accentColor}`}>⏰ 时段 {index + 1}</span>
                <button onClick={() => setCreateSlots(slots => slots.filter(s => s.id !== slot.id))} className="text-gray-400 hover:text-red-500"><XCircle size={16}/></button>
              </div>
              <div className="flex items-center space-x-2 mb-3">
                <Calendar size={14} className="text-gray-400" />
                <input type="time" value={slot.time} onChange={e => {
                  const val = e.target.value;
                  setCreateSlots(slots => slots.map(s => s.id === slot.id ? {...s, time: val} : s))
                }} className="flex-1 bg-gray-50 border border-gray-200 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:border-indigo-500" />
              </div>

              {/* Contents for this slot */}
              <div className="space-y-2 mb-3">
                {slot.contents.map((content, cIdx) => (
                  <div key={content.id} className="bg-gray-50 border border-gray-200 rounded-lg p-2 relative group">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-bold text-gray-500">#{cIdx+1} {content.type === 'text' ? '📝 文字' : content.type === 'image' ? '🖼 图片' : '🎬 视频'}</span>
                      <button onClick={() => handleDeleteContent(slot.id, content.id)} className="text-gray-400 hover:text-red-500"><XCircle size={14}/></button>
                    </div>
                    {content.type === 'text' ? (
                      <textarea rows="2" placeholder="输入文字..." className="w-full text-xs p-1.5 border border-gray-200 rounded bg-white focus:outline-none"
                        value={content.value} onChange={e => {
                          const val = e.target.value;
                          setCreateSlots(slots => slots.map(s => s.id === slot.id ? {...s, contents: s.contents.map(c => c.id === content.id ? {...c, value: val} : c)} : s))
                        }}
                      />
                    ) : (
                      <div className="flex items-center p-1.5 border border-dashed border-gray-300 rounded bg-white text-xs text-gray-500 cursor-pointer hover:bg-gray-100">
                        <Upload size={14} className="mr-2 text-blue-400"/> {content.value || '点击选择文件'}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex space-x-2">
                <button onClick={() => handleAddContentToSlot(slot.id, 'text')} className="flex-1 py-1.5 border border-dashed border-blue-300 text-blue-500 bg-blue-50 rounded-md text-xs font-bold hover:bg-blue-100 transition-colors">+ 文字</button>
                <button onClick={() => handleAddContentToSlot(slot.id, 'image')} className="flex-1 py-1.5 border border-dashed border-green-300 text-green-600 bg-green-50 rounded-md text-xs font-bold hover:bg-green-100 transition-colors">+ 图/视</button>
              </div>
            </div>
          );
        })}
      </div>

      <button onClick={handleAddSlot} className="w-full border-2 border-dashed border-indigo-200 text-indigo-500 bg-indigo-50 py-3 rounded-xl text-sm font-bold flex items-center justify-center hover:bg-indigo-100 transition-colors mb-4">
        <PlusCircle size={16} className="mr-2" /> 新增时段
      </button>

      <div className="text-center text-xs text-gray-500 mb-4">
        📊 {createGroups.length} 个群聊 × {createSlots.length} 个时段 = <span className="font-bold text-indigo-500">{createGroups.length * createSlots.length}</span> 个任务
      </div>

      <button onClick={handleBatchCreate} className="w-full bg-green-500 text-white py-3.5 rounded-xl text-sm font-bold flex items-center justify-center shadow-lg shadow-green-500/30 hover:bg-green-600 active:scale-[0.98] transition-all">
        <CheckCircle2 size={18} className="mr-2" /> 保存并加入队列
      </button>
      <div className="h-10"></div>
    </div>
  );

  const renderSettings = () => (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 mb-2">系统配置</h2>

      {/* 校准 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <button onClick={() => { setEngineStatus('ready'); addLog('[Vision] ✅ (0,0) 1920x1080 DPI=144', 'text-green-500'); }}
          className="w-full border border-blue-500 text-blue-500 bg-blue-50 hover:bg-blue-100 font-bold py-2.5 rounded-lg text-sm transition-colors flex items-center justify-center">
          <MonitorSmartphone size={16} className="mr-2" /> 重新校准微信窗口
        </button>
      </div>

      {/* 附件管理 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center mb-2">
          <Paperclip size={18} className="text-teal-500 mr-2" />
          <h3 className="font-bold text-gray-800">附件管理</h3>
        </div>
        <p className="text-xs text-gray-500 mb-3 whitespace-pre-line leading-relaxed">
          📁 目录: ~/WePush/attachments<br/>
          📊 总计 12 个文件 (45.2 MB)<br/>
          ✅ 引用 8 个 | ⚠️ 未引用 4 个
        </p>
        <div className="flex space-x-2">
          <button className="flex-1 flex items-center justify-center border border-blue-200 text-blue-500 bg-blue-50 py-1.5 rounded-md text-xs font-bold">
            <Folder size={14} className="mr-1" /> 打开目录
          </button>
          <button onClick={() => addLog('[Attach] ✅ 已清理 4 个未引用附件', 'text-teal-500')} className="flex-1 flex items-center justify-center border border-red-200 text-red-400 bg-red-50 py-1.5 rounded-md text-xs font-bold">
            <Trash2 size={14} className="mr-1" /> 清理未引用
          </button>
        </div>
      </div>

      {/* 主题配置 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
         <div className="flex items-center mb-3">
          <ImageIcon size={18} className="text-purple-500 mr-2" />
          <h3 className="font-bold text-gray-800">微信主题模板</h3>
        </div>
        <div className="flex space-x-2">
          <button onClick={() => addLog('[Theme] 切换到 ☀️浅色')} className="flex-1 py-3 border-2 border-amber-400 bg-amber-50 rounded-xl flex flex-col items-center">
            <Sun size={20} className="text-amber-500 mb-1" />
            <span className="text-xs font-bold text-gray-700">浅色</span>
          </button>
          <button onClick={() => addLog('[Theme] 切换到 🌙深色')} className="flex-1 py-3 border border-gray-200 bg-gray-50 rounded-xl flex flex-col items-center opacity-70 hover:opacity-100">
            <Moon size={20} className="text-indigo-500 mb-1" />
            <span className="text-xs font-bold text-gray-700">深色</span>
          </button>
        </div>
      </div>

      {/* 偏好 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 space-y-4">
        <h3 className="font-bold text-gray-800 border-b border-gray-50 pb-2 mb-2">模拟行为偏好</h3>
        <div className="flex justify-between items-center">
          <div><div className="text-sm font-bold text-gray-700">执行前自动唤醒</div><div className="text-[10px] text-gray-400">强制窗口前置</div></div>
          <div className="w-10 h-6 bg-green-500 rounded-full relative cursor-pointer"><div className="w-4 h-4 bg-white rounded-full absolute top-1 translate-x-5"></div></div>
        </div>
        <div className="flex justify-between items-center">
          <div><div className="text-sm font-bold text-gray-700">模拟人工延迟</div><div className="text-[10px] text-gray-400">防封号保护</div></div>
          <div className="w-10 h-6 bg-green-500 rounded-full relative cursor-pointer"><div className="w-4 h-4 bg-white rounded-full absolute top-1 translate-x-5"></div></div>
        </div>
      </div>

      {/* Terminal Log */}
      <div className="bg-gray-100 border border-gray-200 rounded-xl overflow-hidden flex flex-col h-40">
        <div className="bg-gray-200 px-3 py-1.5 flex items-center">
          <Terminal size={12} className="text-gray-500 mr-2" />
          <span className="text-[10px] font-bold text-gray-500">运行日志</span>
        </div>
        <div className="p-2 overflow-y-auto flex-1 font-mono text-[10px] space-y-1">
          {logs.map(log => (
            <div key={log.id} className={log.color}>{log.text}</div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>
      <div className="h-4"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-800 flex items-center justify-center p-4 font-sans selection:bg-green-200">
      {/* 核心应用窗口：严格对齐 PyQt 的 390x760 比例 */}
      <div className="w-[390px] h-[760px] bg-white rounded-[28px] overflow-hidden flex flex-col relative shadow-2xl border-[5px] border-gray-900">
        
        {renderHeader()}

        {/* 动态内容区 */}
        {activeTab === 'tasks' && renderTasks()}
        {activeTab === 'create' && renderCreate()}
        {activeTab === 'settings' && renderSettings()}

        {/* 底部导航栏 */}
        <div className="bg-white border-t border-gray-100 flex justify-around items-center pb-6 pt-2 px-2 z-10 rounded-b-3xl">
          <button onClick={() => setActiveTab('tasks')} className={`flex flex-col items-center w-16 transition-colors ${activeTab === 'tasks' ? 'text-green-500' : 'text-gray-400'}`}>
            <Clock size={22} className="mb-1" />
            <span className="text-[10px] font-bold">任务</span>
          </button>
          
          <button onClick={() => setActiveTab('create')} className="flex flex-col items-center -translate-y-3">
            <div className={`p-3.5 rounded-[26px] shadow-lg ${activeTab === 'create' ? 'bg-green-500 shadow-green-500/40' : 'bg-gray-800 shadow-gray-800/40'} text-white transition-all`}>
              <PlusCircle size={28} />
            </div>
            <span className={`text-[10px] font-bold mt-1 ${activeTab === 'create' ? 'text-green-500' : 'text-gray-600'}`}>新建</span>
          </button>
          
          <button onClick={() => setActiveTab('settings')} className={`flex flex-col items-center w-16 transition-colors ${activeTab === 'settings' ? 'text-green-500' : 'text-gray-400'}`}>
            <Settings size={22} className="mb-1" />
            <span className="text-[10px] font-bold">设置</span>
          </button>
        </div>

      </div>
    </div>
  );
};

export default AutoSenderApp;
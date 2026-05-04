import { useState } from 'react';
import { Clock, PlusCircle, Settings, MonitorSmartphone } from 'lucide-react';

type TabId = 'tasks' | 'create' | 'settings';

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('tasks');

  return (
    <div className="min-h-screen bg-gray-800 flex items-center justify-center p-4 font-sans selection:bg-green-200">
      <div className="w-[390px] h-[760px] bg-white rounded-[28px] overflow-hidden flex flex-col relative shadow-2xl border-[5px] border-gray-900">

        {/* Header */}
        <div className="bg-white border-b border-gray-100 px-4 py-3 flex justify-between items-center z-10 rounded-t-3xl">
          <div className="flex items-center space-x-2">
            <MonitorSmartphone size={18} className="text-gray-700" />
            <span className="font-bold text-gray-800 text-base tracking-wide">智推助手</span>
          </div>
          <div className="flex items-center space-x-1.5 bg-gray-50 px-3 py-1 rounded-full border border-gray-100">
            <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
            <span className="text-xs text-gray-600 font-medium">引擎就绪</span>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto bg-gray-50 p-4">
          {activeTab === 'tasks' && (
            <div className="flex-1">
              <div className="flex justify-between items-end mb-4">
                <div>
                  <h2 className="text-lg font-bold text-gray-800">执行队列</h2>
                  <p className="text-xs text-gray-500 mt-1">请保持微信窗口可见</p>
                </div>
                <div className="text-sm font-bold text-green-600 bg-green-50 px-3 py-1 rounded-lg">
                  0 个待办
                </div>
              </div>
              <div className="text-center text-gray-400 py-20">
                <Clock size={48} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm">暂无定时任务</p>
                <p className="text-xs mt-1">点击下方 + 新建推送</p>
              </div>
            </div>
          )}

          {activeTab === 'create' && (
            <div className="flex-1">
              <h2 className="text-xl font-bold text-gray-800 mb-4">新建推送任务</h2>
              <p className="text-center text-gray-400 py-20 text-sm">
                任务创建表单（对接 engine API 中）
              </p>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="flex-1">
              <h2 className="text-xl font-bold text-gray-800 mb-4">系统配置</h2>
              <p className="text-center text-gray-400 py-20 text-sm">
                系统设置（对接 engine API 中）
              </p>
            </div>
          )}
        </div>

        {/* Bottom Navigation */}
        <div className="bg-white border-t border-gray-100 flex justify-around items-center pb-6 pt-2 px-2 z-10 rounded-b-3xl">
          <button
            onClick={() => setActiveTab('tasks')}
            className={`flex flex-col items-center w-16 transition-colors ${activeTab === 'tasks' ? 'text-green-500' : 'text-gray-400'}`}
          >
            <Clock size={22} className="mb-1" />
            <span className="text-[10px] font-bold">任务</span>
          </button>

          <button
            onClick={() => setActiveTab('create')}
            className="flex flex-col items-center -translate-y-3"
          >
            <div className={`p-3.5 rounded-[26px] shadow-lg ${activeTab === 'create' ? 'bg-green-500 shadow-green-500/40' : 'bg-gray-800 shadow-gray-800/40'} text-white transition-all`}>
              <PlusCircle size={28} />
            </div>
            <span className={`text-[10px] font-bold mt-1 ${activeTab === 'create' ? 'text-green-500' : 'text-gray-600'}`}>新建</span>
          </button>

          <button
            onClick={() => setActiveTab('settings')}
            className={`flex flex-col items-center w-16 transition-colors ${activeTab === 'settings' ? 'text-green-500' : 'text-gray-400'}`}
          >
            <Settings size={22} className="mb-1" />
            <span className="text-[10px] font-bold">设置</span>
          </button>
        </div>

      </div>
    </div>
  );
}

export default App;

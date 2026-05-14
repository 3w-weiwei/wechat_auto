import { useWebSocket } from './hooks/useWebSocket';
import { useAppStore } from './store/appStore';
import { TasksPage } from './components/tasks/TasksPage';
import { CreatePage } from './components/create/CreatePage';
import { SettingsPage } from './components/settings/SettingsPage';
import { MonitorSmartphone, Clock, PlusCircle, Settings, Minus, X } from 'lucide-react';

function App() {
  useWebSocket();
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const engineStatus = useAppStore((s) => s.engineStatus);
  const connected = useAppStore((s) => s.connected);

  const statusLabel = connected
    ? engineStatus === 'ready' ? '视觉就绪' : engineStatus === 'minimized' ? '已最小化' : '未见微信'
    : '未连接';

  return (
    <div className="w-full h-screen bg-white rounded-[28px] overflow-hidden flex flex-col shadow-2xl select-none">
      {/* Header — drag region for frameless window */}
      <div className="drag-region bg-white border-b border-gray-100 px-4 py-3 flex justify-between items-center z-10 rounded-t-3xl">
        <div className="flex items-center space-x-2 no-drag">
          <button
            onClick={() => (window as any).electronAPI?.minimizeWindow?.()}
            className="w-5 h-5 flex items-center justify-center rounded-full bg-yellow-400 hover:bg-yellow-500 transition-colors"
            title="最小化"
          >
            <Minus size={10} className="text-yellow-900" strokeWidth={3} />
          </button>
          <button
            onClick={() => (window as any).electronAPI?.closeWindow?.()}
            className="w-5 h-5 flex items-center justify-center rounded-full bg-red-400 hover:bg-red-500 transition-colors"
            title="关闭"
          >
            <X size={10} className="text-red-900" strokeWidth={3} />
          </button>
          <MonitorSmartphone size={18} className="text-gray-700" />
          <span className="font-bold text-gray-800 text-base tracking-wide">智推助手</span>
        </div>
        <div className="flex items-center space-x-1.5 bg-gray-50 px-3 py-1 rounded-full border border-gray-100 no-drag">
          <div className={`w-2 h-2 rounded-full ${engineStatus === 'ready' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`} />
          <span className="text-xs text-gray-600 font-medium">{statusLabel}</span>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'tasks' && <TasksPage />}
      {activeTab === 'create' && <CreatePage />}
      {activeTab === 'settings' && <SettingsPage />}

      {/* Bottom Navigation */}
      <div className="bg-white border-t border-gray-100 flex justify-around items-center pb-6 pt-2 px-2 z-10 rounded-b-3xl no-drag">
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
  );
}

export default App;

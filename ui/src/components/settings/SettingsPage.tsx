import { useEffect } from 'react';
import { useConfig } from '../../hooks/useConfig';
import { useAppStore } from '../../store/appStore';
import { MonitorSmartphone, Paperclip, Folder, Trash2, Image, Sun, Moon, Terminal } from 'lucide-react';

const logColor: Record<string, string> = {
  info: 'text-gray-500',
  error: 'text-red-500',
  success: 'text-green-500',
  warn: 'text-orange-500',
  debug: 'text-gray-300',
};

export function SettingsPage() {
  const { fetchAttachmentStats, calibrate, cleanupAttachments, openAttachmentDir } = useConfig();
  const { logs, attachmentStats, engineStatus } = useAppStore();

  useEffect(() => {
    fetchAttachmentStats();
  }, [fetchAttachmentStats]);

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 mb-2">System Config</h2>

      {/* Calibration */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <button onClick={calibrate}
          className="w-full border border-blue-500 text-blue-500 bg-blue-50 hover:bg-blue-100 font-bold py-2.5 rounded-lg text-sm transition-colors flex items-center justify-center">
          <MonitorSmartphone size={16} className="mr-2" /> Recalibrate WeChat Window
        </button>
        <p className="text-xs text-gray-500 mt-2 text-center">Status: {engineStatus}</p>
      </div>

      {/* Attachments */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center mb-2">
          <Paperclip size={18} className="text-teal-500 mr-2" />
          <h3 className="font-bold text-gray-800">Attachment Manager</h3>
        </div>
        {attachmentStats ? (
          <p className="text-xs text-gray-500 mb-3 leading-relaxed">
            Total {attachmentStats.total_count} files ({attachmentStats.total_size_mb} MB)<br />
            Referenced {attachmentStats.referenced_count} | Unreferenced {attachmentStats.unreferenced_count}
          </p>
        ) : (
          <p className="text-xs text-gray-400 mb-3">Loading stats...</p>
        )}
        <div className="flex space-x-2">
          <button onClick={openAttachmentDir}
            className="flex-1 flex items-center justify-center border border-blue-200 text-blue-500 bg-blue-50 py-1.5 rounded-md text-xs font-bold">
            <Folder size={14} className="mr-1" /> Open Folder
          </button>
          <button onClick={cleanupAttachments}
            className="flex-1 flex items-center justify-center border border-red-200 text-red-400 bg-red-50 py-1.5 rounded-md text-xs font-bold">
            <Trash2 size={14} className="mr-1" /> Clean Unreferenced
          </button>
        </div>
      </div>

      {/* Theme */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center mb-3">
          <Image size={18} className="text-purple-500 mr-2" />
          <h3 className="font-bold text-gray-800">WeChat Theme Template</h3>
        </div>
        <div className="flex space-x-2">
          <button className="flex-1 py-3 border-2 border-amber-400 bg-amber-50 rounded-xl flex flex-col items-center">
            <Sun size={20} className="text-amber-500 mb-1" />
            <span className="text-xs font-bold text-gray-700">Light</span>
          </button>
          <button className="flex-1 py-3 border border-gray-200 bg-gray-50 rounded-xl flex flex-col items-center opacity-70">
            <Moon size={20} className="text-indigo-500 mb-1" />
            <span className="text-xs font-bold text-gray-700">Dark</span>
          </button>
        </div>
      </div>

      {/* Preferences */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 space-y-4">
        <h3 className="font-bold text-gray-800 border-b border-gray-50 pb-2 mb-2">Behavior Preferences</h3>
        <div className="flex justify-between items-center">
          <div>
            <div className="text-sm font-bold text-gray-700">Auto-wake before exec</div>
            <div className="text-[10px] text-gray-400">Force window to foreground</div>
          </div>
          <div className="w-10 h-6 bg-green-500 rounded-full relative cursor-pointer">
            <div className="w-4 h-4 bg-white rounded-full absolute top-1 translate-x-5" />
          </div>
        </div>
        <div className="flex justify-between items-center">
          <div>
            <div className="text-sm font-bold text-gray-700">Simulate human delay</div>
            <div className="text-[10px] text-gray-400">Anti-ban protection</div>
          </div>
          <div className="w-10 h-6 bg-green-500 rounded-full relative cursor-pointer">
            <div className="w-4 h-4 bg-white rounded-full absolute top-1 translate-x-5" />
          </div>
        </div>
      </div>

      {/* Log Console */}
      <div className="bg-gray-100 border border-gray-200 rounded-xl overflow-hidden flex flex-col h-40">
        <div className="bg-gray-200 px-3 py-1.5 flex items-center">
          <Terminal size={12} className="text-gray-500 mr-2" />
          <span className="text-[10px] font-bold text-gray-500">Runtime Logs</span>
        </div>
        <div className="p-2 overflow-y-auto flex-1 font-mono text-[10px] space-y-1">
          {logs.map(log => (
            <div key={log.id} className={logColor[log.level] || 'text-gray-500'}>
              [{log.timestamp.slice(11, 19)}] {log.message}
            </div>
          ))}
          {logs.length === 0 && <div className="text-gray-400">No logs yet...</div>}
        </div>
      </div>
      <div className="h-4" />
    </div>
  );
}

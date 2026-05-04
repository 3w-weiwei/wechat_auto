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
      <h2 className="text-xl font-bold text-gray-800 mb-2">系统配置</h2>

      {/* 校准 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <button onClick={calibrate}
          className="w-full border border-blue-500 text-blue-500 bg-blue-50 hover:bg-blue-100 font-bold py-2.5 rounded-lg text-sm transition-colors flex items-center justify-center">
          <MonitorSmartphone size={16} className="mr-2" /> 重新校准微信窗口
        </button>
        <p className="text-xs text-gray-500 mt-2 text-center">
          状态: {engineStatus === 'ready' ? '就绪' : engineStatus === 'minimized' ? '已最小化' : '未找到'}
        </p>
      </div>

      {/* 附件管理 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center mb-2">
          <Paperclip size={18} className="text-teal-500 mr-2" />
          <h3 className="font-bold text-gray-800">附件管理</h3>
        </div>
        {attachmentStats ? (
          <p className="text-xs text-gray-500 mb-3 leading-relaxed">
            📁 总计 {attachmentStats.total_count} 个文件 ({attachmentStats.total_size_mb} MB)<br />
            ✅ 引用 {attachmentStats.referenced_count} 个 | ⚠️ 未引用 {attachmentStats.unreferenced_count} 个
          </p>
        ) : (
          <p className="text-xs text-gray-400 mb-3">加载中...</p>
        )}
        <div className="flex space-x-2">
          <button onClick={openAttachmentDir}
            className="flex-1 flex items-center justify-center border border-blue-200 text-blue-500 bg-blue-50 py-1.5 rounded-md text-xs font-bold">
            <Folder size={14} className="mr-1" /> 打开目录
          </button>
          <button onClick={cleanupAttachments}
            className="flex-1 flex items-center justify-center border border-red-200 text-red-400 bg-red-50 py-1.5 rounded-md text-xs font-bold">
            <Trash2 size={14} className="mr-1" /> 清理未引用
          </button>
        </div>
      </div>

      {/* 微信主题模板 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center mb-3">
          <Image size={18} className="text-purple-500 mr-2" />
          <h3 className="font-bold text-gray-800">微信主题模板</h3>
        </div>
        <div className="flex space-x-2">
          <button className="flex-1 py-3 border-2 border-amber-400 bg-amber-50 rounded-xl flex flex-col items-center">
            <Sun size={20} className="text-amber-500 mb-1" />
            <span className="text-xs font-bold text-gray-700">浅色</span>
          </button>
          <button className="flex-1 py-3 border border-gray-200 bg-gray-50 rounded-xl flex flex-col items-center opacity-70">
            <Moon size={20} className="text-indigo-500 mb-1" />
            <span className="text-xs font-bold text-gray-700">深色</span>
          </button>
        </div>
      </div>

      {/* 行为偏好 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 space-y-4">
        <h3 className="font-bold text-gray-800 border-b border-gray-50 pb-2 mb-2">模拟行为偏好</h3>
        <div className="flex justify-between items-center">
          <div>
            <div className="text-sm font-bold text-gray-700">执行前自动唤醒</div>
            <div className="text-[10px] text-gray-400">强制窗口前置</div>
          </div>
          <div className="w-10 h-6 bg-green-500 rounded-full relative cursor-pointer">
            <div className="w-4 h-4 bg-white rounded-full absolute top-1 translate-x-5" />
          </div>
        </div>
        <div className="flex justify-between items-center">
          <div>
            <div className="text-sm font-bold text-gray-700">模拟人工延迟</div>
            <div className="text-[10px] text-gray-400">防封号保护</div>
          </div>
          <div className="w-10 h-6 bg-green-500 rounded-full relative cursor-pointer">
            <div className="w-4 h-4 bg-white rounded-full absolute top-1 translate-x-5" />
          </div>
        </div>
      </div>

      {/* 运行日志 */}
      <div className="bg-gray-100 border border-gray-200 rounded-xl overflow-hidden flex flex-col h-40">
        <div className="bg-gray-200 px-3 py-1.5 flex items-center">
          <Terminal size={12} className="text-gray-500 mr-2" />
          <span className="text-[10px] font-bold text-gray-500">运行日志</span>
        </div>
        <div className="p-2 overflow-y-auto flex-1 font-mono text-[10px] space-y-1">
          {logs.map(log => (
            <div key={log.id} className={logColor[log.level] || 'text-gray-500'}>
              [{log.timestamp.slice(11, 19)}] {log.message}
            </div>
          ))}
          {logs.length === 0 && <div className="text-gray-400">暂无日志...</div>}
        </div>
      </div>
      <div className="h-4" />
    </div>
  );
}

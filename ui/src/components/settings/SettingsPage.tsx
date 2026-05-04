import { useEffect, useState } from 'react';
import { useConfig } from '../../hooks/useConfig';
import { useAppStore } from '../../store/appStore';
import { apiClient } from '../../services/api';
import {
  MonitorSmartphone, Paperclip, Folder, Trash2, Image, Sun, Moon, Terminal, ChevronDown, ChevronUp
} from 'lucide-react';

const TEMPLATE_KEYS = ['search', 'group_label', 'recent_label'] as const;
const TEMPLATE_LABELS: Record<string, string> = {
  search: '搜索框',
  group_label: '群聊标签',
  recent_label: '最常使用',
};

const logColor: Record<string, string> = {
  info: 'text-gray-500',
  error: 'text-red-500',
  success: 'text-green-500',
  warn: 'text-orange-500',
  debug: 'text-gray-300',
};

interface TemplatePreview {
  key: string;
  theme: string;
  filename: string;
  data: string; // base64 data URL
  size: number;
}

export function SettingsPage() {
  const { fetchAttachmentStats, calibrate, cleanupAttachments, openAttachmentDir } = useConfig();
  const { logs, attachmentStats, engineStatus, addLog } = useAppStore();
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [previews, setPreviews] = useState<Record<string, TemplatePreview>>({});
  const [templateOpen, setTemplateOpen] = useState(false);

  useEffect(() => {
    fetchAttachmentStats();
    loadTheme();
    loadPreviews();
  }, []);

  const loadTheme = async () => {
    try {
      const result = await apiClient.call('config.get', { key: 'template_theme' }) as { value: string };
      setTheme((result.value === 'dark' ? 'dark' : 'light') as 'light' | 'dark');
    } catch { /* ignore */ }
  };

  const loadPreviews = async () => {
    const all: Record<string, TemplatePreview> = {};
    for (const key of TEMPLATE_KEYS) {
      for (const th of ['light', 'dark']) {
        try {
          const result = await apiClient.call('template.preview', { key, theme: th }) as TemplatePreview;
          if (result.data) all[`${key}_${th}`] = result;
        } catch { /* template might not exist yet */ }
      }
    }
    setPreviews(all);
  };

  const handleSetTheme = async (newTheme: 'light' | 'dark') => {
    try {
      await apiClient.call('template.set_theme', { theme: newTheme });
      setTheme(newTheme);
      addLog('success', `已切换到 ${newTheme === 'light' ? '☀️ 浅色' : '🌙 深色'} 主题`);
    } catch (e) {
      addLog('error', `切换主题失败: ${e}`);
    }
  };

  const handleUploadTemplate = async (key: string, th: 'light' | 'dark') => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/png,image/jpeg';
    input.onchange = async (evt) => {
      const file = (evt.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          await apiClient.call('template.upload', { key, theme: th, filename: file.name, data: reader.result });
          addLog('success', `模板 ${TEMPLATE_LABELS[key] || key} (${th}) 已更新`);
          await loadPreviews();
        } catch (e) {
          addLog('error', `上传模板失败: ${e}`);
        }
      };
      reader.readAsDataURL(file);
    };
    input.click();
  };

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
          状态: {engineStatus === 'ready' ? '视觉就绪' : engineStatus === 'minimized' ? '窗口最小化' : '未检测到微信'}
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

      {/* 微信主题模板 — collapsible */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setTemplateOpen(!templateOpen)}>
          <div className="flex items-center">
            <Image size={18} className="text-purple-500 mr-2" />
            <h3 className="font-bold text-gray-800">微信主题模板</h3>
          </div>
          {templateOpen ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
        </div>
        {templateOpen && (
        <>

        {/* Theme switch */}
        <div className="flex space-x-2 mb-4">
          <button onClick={() => handleSetTheme('light')}
            className={`flex-1 py-3 rounded-xl flex flex-col items-center transition-all ${theme === 'light' ? 'border-2 border-amber-400 bg-amber-50' : 'border border-gray-200 bg-gray-50'}`}
          >
            <Sun size={20} className={theme === 'light' ? 'text-amber-500 mb-1' : 'text-gray-400 mb-1'} />
            <span className="text-xs font-bold text-gray-700">浅色模式</span>
          </button>
          <button onClick={() => handleSetTheme('dark')}
            className={`flex-1 py-3 rounded-xl flex flex-col items-center transition-all ${theme === 'dark' ? 'border-2 border-indigo-400 bg-indigo-50' : 'border border-gray-200 bg-gray-50'}`}
          >
            <Moon size={20} className={theme === 'dark' ? 'text-indigo-500 mb-1' : 'text-gray-400 mb-1'} />
            <span className="text-xs font-bold text-gray-700">深色模式</span>
          </button>
        </div>

        {/* Template preview rows */}
        <div className="space-y-3">
          {TEMPLATE_KEYS.map((key) => (
            <div key={key} className="border border-gray-100 rounded-lg p-2">
              <span className="text-xs font-bold text-gray-600 block mb-2">{TEMPLATE_LABELS[key]}</span>
              <div className="flex space-x-2">
                {(['light', 'dark'] as const).map((th) => {
                  const preview = previews[`${key}_${th}`];
                  const isActive = theme === th;
                  return (
                    <div key={th} className={`flex-1 rounded-lg border-2 p-2 ${isActive ? 'border-green-300 bg-green-50/50' : 'border-gray-100 bg-gray-50'}`}>
                      <div className="text-[10px] font-bold mb-1.5 text-center text-gray-500 flex items-center justify-center gap-1">
                        {th === 'light' ? <Sun size={10} /> : <Moon size={10} />}
                        {th === 'light' ? '浅色' : '深色'}
                        {isActive && <span className="text-green-500 text-[8px]">●使用中</span>}
                      </div>
                      {preview?.data ? (
                        <div className="relative group">
                          <img src={preview.data} alt={`${key}_${th}`}
                            className="w-full h-10 object-contain rounded bg-white border border-gray-100" />
                          <span className="text-[8px] text-gray-400 text-center block mt-0.5 truncate">
                            {preview.filename}
                          </span>
                        </div>
                      ) : (
                        <div className="w-full h-10 rounded bg-gray-200 flex items-center justify-center text-[10px] text-gray-400">
                          无模板
                        </div>
                      )}
                      <button
                        onClick={() => handleUploadTemplate(key, th)}
                        className="w-full mt-1.5 text-[10px] py-1 rounded border border-dashed border-gray-300 text-gray-500 hover:border-blue-300 hover:text-blue-500 hover:bg-blue-50 transition-colors"
                      >
                        更换
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        </>
        )}
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
      <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden flex flex-col h-52">
        <div className="bg-gray-800 px-3 py-1.5 flex items-center justify-between">
          <div className="flex items-center">
            <Terminal size={12} className="text-green-400 mr-2" />
            <span className="text-[10px] font-bold text-gray-300">运行日志</span>
          </div>
          <span className="text-[10px] text-gray-500">{logs.length} 条</span>
        </div>
        <div className="p-2 overflow-y-auto flex-1 font-mono text-[10px] space-y-0.5 leading-relaxed">
          {logs.map(log => (
            <div key={log.id} className={logColor[log.level] || 'text-gray-400'}>
              <span className="text-gray-600">[{log.timestamp.slice(11, 19)}]</span> {log.message}
            </div>
          ))}
          {logs.length === 0 && <div className="text-gray-500">等待引擎连接...</div>}
        </div>
      </div>
      <div className="h-4" />
    </div>
  );
}

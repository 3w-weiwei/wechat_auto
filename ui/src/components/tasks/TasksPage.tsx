import { useEffect, useState } from 'react';
import { useTasks } from '../../hooks/useTasks';
import { TaskCard } from './TaskCard';
import { EditTaskDialog } from './EditTaskDialog';
import { Clock } from 'lucide-react';
import type { Task } from '../../types/models';

export function TasksPage() {
  const { tasks, fetchTasks, toggleTask, runNow, editTask, deleteTask } = useTasks();
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const activeCount = tasks.filter(t => t.active).length;

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-4 space-y-4">
      <div className="flex justify-between items-end mb-2">
        <div>
          <h2 className="text-lg font-bold text-gray-800">Execution Queue</h2>
          <p className="text-xs text-gray-500 mt-1">Keep WeChat window visible</p>
        </div>
        <div className="text-sm font-bold text-green-600 bg-green-50 px-3 py-1 rounded-lg">
          {activeCount} pending
        </div>
      </div>

      {tasks.length === 0 ? (
        <div className="text-center text-gray-400 py-20">
          <Clock size={48} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No scheduled tasks</p>
          <p className="text-xs mt-1">Tap + below to create one</p>
        </div>
      ) : (
        tasks.map(task => (
          <TaskCard
            key={task.id}
            task={task}
            onToggle={toggleTask}
            onRunNow={runNow}
            onEdit={setEditingTask}
            onDelete={deleteTask}
          />
        ))
      )}

      {editingTask && (
        <EditTaskDialog
          task={editingTask}
          onSave={editTask}
          onClose={() => setEditingTask(null)}
        />
      )}
    </div>
  );
}

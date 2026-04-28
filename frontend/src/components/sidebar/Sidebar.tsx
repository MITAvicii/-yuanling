'use client';

import { useState, useEffect } from 'react';
import { MessageSquare, FileText, Sparkles, Plus, Trash2, Database, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { 
  Session, KnowledgeFile, KnowledgeStats, 
  getKnowledgeFiles, getKnowledgeStats, 
  getSkills, Skill
} from '@/lib/api';

interface SidebarProps {
  view: 'chat' | 'memory' | 'skills' | 'knowledge';
  onViewChange: (view: 'chat' | 'memory' | 'skills' | 'knowledge') => void;
  sessions: Session[];
  currentSession: Session | null;
  onSelectSession: (session: Session) => void;
  onNewSession: () => void;
  onDeleteSession: (sessionId: string) => void;
  onSelectFile: (file: string) => void;
  onSelectKnowledgeFile?: (filename: string) => void;
  knowledgeStats?: KnowledgeStats | null;
  onSelectSkill?: (skillName: string) => void;
}

export function Sidebar({
  view,
  onViewChange,
  sessions,
  currentSession,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onSelectFile,
  onSelectKnowledgeFile,
  knowledgeStats,
  onSelectSkill,
}: SidebarProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [knowledgeFiles, setKnowledgeFiles] = useState<KnowledgeFile[]>([]);
  const [loadingKnowledge, setLoadingKnowledge] = useState(false);
  
  // 技能状态
  const [skillsByCategory, setSkillsByCategory] = useState<Record<string, Skill[]>>({});
  const [categories, setCategories] = useState<string[]>([]);
  const [loadingSkills, setLoadingSkills] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['团队协作', '后端框架', '前端框架']));

  // 加载知识库文件
  useEffect(() => {
    if (view === 'knowledge') {
      loadKnowledgeFiles();
    }
  }, [view]);

  // 加载技能
  useEffect(() => {
    if (view === 'skills') {
      loadSkills();
    }
  }, [view]);

  const loadKnowledgeFiles = async () => {
    setLoadingKnowledge(true);
    try {
      const files = await getKnowledgeFiles();
      setKnowledgeFiles(files);
    } catch (error) {
      console.error('Failed to load knowledge files:', error);
    }
    setLoadingKnowledge(false);
  };

  const loadSkills = async () => {
    setLoadingSkills(true);
    try {
      const data = await getSkills();
      setCategories(data.categories);
      setSkillsByCategory(data.skills_by_category);
    } catch (error) {
      console.error('Failed to load skills:', error);
    }
    setLoadingSkills(false);
  };

  const handleDelete = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    setDeletingId(sessionId);
    onDeleteSession(sessionId);
    setTimeout(() => setDeletingId(null), 500);
  };

  const handleKnowledgeFileClick = (file: KnowledgeFile) => {
    if (onSelectKnowledgeFile) {
      onSelectKnowledgeFile(file.name);
    }
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  const handleSkillClick = (skill: Skill) => {
    // 点击技能时打开 SKILL.md 文件
    onSelectFile(`backend/skills/${skill.name}/SKILL.md`);
    if (onSelectSkill) {
      onSelectSkill(skill.name);
    }
  };

  const navItems = [
    { id: 'chat' as const, icon: MessageSquare, label: '对话' },
    { id: 'memory' as const, icon: FileText, label: '记忆' },
    { id: 'skills' as const, icon: Sparkles, label: '技能' },
    { id: 'knowledge' as const, icon: Database, label: '知识库' },
  ];

  const memoryFiles = [
    { name: 'MEMORY.md', path: 'backend/memory/MEMORY.md', desc: '长期记忆' },
    { name: 'SOUL.md', path: 'backend/workspace/SOUL.md', desc: '核心设定' },
    { name: 'IDENTITY.md', path: 'backend/workspace/IDENTITY.md', desc: '自我认知' },
    { name: 'USER.md', path: 'backend/workspace/USER.md', desc: '用户画像' },
    { name: 'AGENTS.md', path: 'backend/workspace/AGENTS.md', desc: '行为准则' },
  ];

  return (
    <aside className="w-72 bg-white border-r border-gray-200 flex flex-col shrink-0">
      {/* 导航标签 - 图标 + tooltip */}
      <div className="px-3 pt-3 pb-2 flex gap-1 border-b border-gray-100">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onViewChange(item.id)}
            className={`nav-tab flex-1 justify-center relative group ${
              view === item.id ? 'active' : ''
            }`}
            title={item.label}
          >
            <item.icon size={18} />
            {/* Tooltip */}
            <span className="absolute -bottom-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-gray-800 text-white text-xs rounded-md whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
              {item.label}
            </span>
          </button>
        ))}
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-auto">
        {view === 'chat' && (
          <div className="p-3">
            <button
              onClick={onNewSession}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors font-medium"
            >
              <Plus size={18} />
              <span>新建对话</span>
            </button>
            
            <div className="mt-4 space-y-1">
              <div className="header-label">历史会话</div>
              
              {sessions.length === 0 ? (
                <div className="text-center text-gray-400 text-sm py-8">
                  暂无会话记录
                </div>
              ) : (
                sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`sidebar-item group ${
                      currentSession?.id === session.id ? 'active' : ''
                    }`}
                  >
                    <button
                      onClick={() => onSelectSession(session)}
                      className="flex-1 flex items-center gap-3 min-w-0"
                    >
                      <MessageSquare size={16} className="text-gray-400 shrink-0" />
                      <div className="min-w-0 flex-1 text-left">
                        <div className="text-sm truncate">{session.title}</div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          {session.message_count} 条消息
                        </div>
                      </div>
                    </button>
                    <button
                      onClick={(e) => handleDelete(e, session.id)}
                      className={`p-1.5 rounded-lg transition-all ${
                        deletingId === session.id
                          ? 'bg-red-100 text-red-500'
                          : 'opacity-0 group-hover:opacity-100 hover:bg-red-50 text-gray-400 hover:text-red-500'
                      }`}
                      title="删除会话"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {view === 'memory' && (
          <div className="p-3">
            <div className="header-label">系统提示词组件</div>
            
            <div className="space-y-1">
              {memoryFiles.map((file) => (
                <button
                  key={file.path}
                  onClick={() => onSelectFile(file.path)}
                  className="sidebar-item"
                >
                  <div className="flex items-center gap-3">
                    <FileText size={16} className="text-indigo-500 shrink-0" />
                    <div className="min-w-0 flex-1 text-left">
                      <div className="text-sm truncate">{file.name}</div>
                      <div className="text-xs text-gray-400 mt-0.5">{file.desc}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {view === 'skills' && (
          <div className="p-3">
            <div className="header-label flex items-center justify-between">
              <span>技能列表</span>
              <button
                onClick={loadSkills}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title="刷新"
              >
                <RefreshCw size={14} className={`text-gray-400 ${loadingSkills ? 'animate-spin' : ''}`} />
              </button>
            </div>
            
            {loadingSkills ? (
              <div className="text-center text-gray-400 text-sm py-8">
                加载中...
              </div>
            ) : categories.length === 0 ? (
              <div className="text-center text-gray-400 text-sm py-8">
                暂无技能
              </div>
            ) : (
              <div className="space-y-2">
                {categories.map((category) => {
                  const skills = skillsByCategory[category] || [];
                  const isExpanded = expandedCategories.has(category);
                  
                  return (
                    <div key={category} className="category-group">
                      {/* 分类标题 */}
                      <button
                        onClick={() => toggleCategory(category)}
                        className="w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
                      >
                        {isExpanded ? (
                          <ChevronDown size={14} className="text-gray-400" />
                        ) : (
                          <ChevronRight size={14} className="text-gray-400" />
                        )}
                        <span>{category}</span>
                        <span className="text-xs text-gray-400 ml-auto">{skills.length}</span>
                      </button>
                      
                      {/* 技能列表 */}
                      {isExpanded && (
                        <div className="mt-1 space-y-0.5 pl-4">
                          {skills.map((skill) => (
                            <button
                              key={skill.name}
                              onClick={() => handleSkillClick(skill)}
                              className="sidebar-item w-full"
                            >
                              <div className="flex items-center gap-2 min-w-0 flex-1">
                                <div className="w-6 h-6 bg-orange-100 rounded-md flex items-center justify-center shrink-0">
                                  <Sparkles size={12} className="text-orange-600" />
                                </div>
                                <div className="min-w-0 flex-1 text-left">
                                  <div className="text-sm truncate">{skill.cn_name}</div>
                                  <div className="text-xs text-gray-400 truncate">
                                    {skill.tags.slice(0, 2).join(' · ')}
                                  </div>
                                </div>
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            
            <div className="mt-6 p-3 bg-orange-50 rounded-xl">
              <div className="text-xs text-orange-600 text-center">
                技能存放在 <code className="bg-orange-100 px-1 rounded">backend/skills/</code>
              </div>
            </div>
          </div>
        )}

        {view === 'knowledge' && (
          <div className="p-3">
            {/* 状态栏 */}
            {knowledgeStats && (
              <div className="mb-3 p-3 bg-gray-50 rounded-xl">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">
                    📄 {knowledgeStats.file_count} 个文件
                  </span>
                  <span className="text-gray-400">
                    {knowledgeStats.total_size_str}
                  </span>
                </div>
                {knowledgeStats.index_exists && (
                  <div className="flex items-center gap-1 mt-1 text-xs text-green-600">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                    索引已构建
                  </div>
                )}
              </div>
            )}

            <div className="header-label flex items-center justify-between">
              <span>知识库文件</span>
              <button
                onClick={loadKnowledgeFiles}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title="刷新"
              >
                <RefreshCw size={14} className={`text-gray-400 ${loadingKnowledge ? 'animate-spin' : ''}`} />
              </button>
            </div>
            
            {loadingKnowledge ? (
              <div className="text-center text-gray-400 text-sm py-8">
                加载中...
              </div>
            ) : knowledgeFiles.length === 0 ? (
              <div className="text-center text-gray-400 text-sm py-8">
                暂无知识库文件<br />
                <span className="text-xs">在右侧面板上传文件</span>
              </div>
            ) : (
              <div className="space-y-1">
                {knowledgeFiles.map((file) => (
                  <button
                    key={file.name}
                    onClick={() => handleKnowledgeFileClick(file)}
                    className="sidebar-item w-full"
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <FileText size={16} className="text-blue-500 shrink-0" />
                      <div className="min-w-0 flex-1 text-left">
                        <div className="text-sm truncate">{file.name}</div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          {file.size_str} · {file.updated_at}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
            
            <div className="mt-6 p-3 bg-blue-50 rounded-xl">
              <div className="text-xs text-blue-600 text-center">
                知识库存放在 <code className="bg-blue-100 px-1 rounded">backend/knowledge/</code>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

'use client';

import { useState, useEffect, useCallback } from 'react';
import { Settings, Sparkles } from 'lucide-react';
import { Sidebar } from '@/components/sidebar/Sidebar';
import { ChatArea } from '@/components/chat/ChatArea';
import { Inspector } from '@/components/editor/Inspector';
import SettingsPanel from '@/components/layout/SettingsPanel';
import { 
  Session, getSessions, createSession, deleteSession, 
  getRAGMode, setRAGMode, getKnowledgeStats, KnowledgeStats
} from '@/lib/api';

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [currentFile, setCurrentFile] = useState<string | null>(null);
  const [sidebarView, setSidebarView] = useState<'chat' | 'memory' | 'skills' | 'knowledge'>('chat');
  const [ragEnabled, setRagEnabled] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  
  // 知识库状态
  const [selectedKnowledgeFile, setSelectedKnowledgeFile] = useState<string | null>(null);
  const [knowledgeStats, setKnowledgeStats] = useState<KnowledgeStats | null>(null);

  useEffect(() => {
    loadSessions();
    loadRAGMode();
  }, []);

  // 切换到知识库视图时加载统计
  useEffect(() => {
    if (sidebarView === 'knowledge') {
      loadKnowledgeStats();
    }
  }, [sidebarView]);

  const loadSessions = async () => {
    try {
      const data = await getSessions();
      setSessions(data);
      // 自动选择最近的会话
      if (data.length > 0 && !currentSession) {
        setCurrentSession(data[0]);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  const loadRAGMode = async () => {
    try {
      const data = await getRAGMode();
      setRagEnabled(data.enabled);
    } catch (error) {
      console.error('Failed to load RAG mode:', error);
    }
  };

  const loadKnowledgeStats = async () => {
    try {
      const stats = await getKnowledgeStats();
      setKnowledgeStats(stats);
    } catch (error) {
      console.error('Failed to load knowledge stats:', error);
    }
  };

  const handleNewSession = async () => {
    try {
      const session = await createSession();
      setSessions([session, ...sessions]);
      setCurrentSession(session);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const handleSelectSession = (session: Session) => {
    setCurrentSession(session);
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      setSessions(sessions.filter(s => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const handleRAGToggle = async () => {
    try {
      const newMode = !ragEnabled;
      await setRAGMode(newMode);
      setRagEnabled(newMode);
    } catch (error) {
      console.error('Failed to toggle RAG mode:', error);
    }
  };

  const handleViewChange = (view: 'chat' | 'memory' | 'skills' | 'knowledge') => {
    setSidebarView(view);
    // 切换视图时清除选中的知识库文件
    if (view !== 'knowledge') {
      setSelectedKnowledgeFile(null);
    }
  };

  const handleKnowledgeUpdate = useCallback(() => {
    loadKnowledgeStats();
  }, []);

  return (
    <div className="h-screen flex flex-col bg-[#f8f9fb]">
      {/* 顶部导航栏 */}
      <header className="h-14 flex items-center justify-between px-6 bg-white border-b border-gray-200 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Sparkles size={18} className="text-white" />
          </div>
          <h1 className="text-lg font-semibold text-gray-800">源灵AI</h1>
        </div>
        
        <div className="flex items-center gap-3">
          {/* RAG 开关 */}
          <button
            onClick={handleRAGToggle}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
              ragEnabled 
                ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${ragEnabled ? 'bg-green-500' : 'bg-gray-400'}`} />
            RAG
          </button>
          
          {/* 设置按钮 */}
          <button
            onClick={() => setShowSettings(true)}
            className="btn-icon"
            title="设置"
          >
            <Settings size={20} />
          </button>
        </div>
      </header>

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧边栏 */}
        <Sidebar
          view={sidebarView}
          onViewChange={handleViewChange}
          sessions={sessions}
          currentSession={currentSession}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          onDeleteSession={handleDeleteSession}
          onSelectFile={setCurrentFile}
          onSelectKnowledgeFile={setSelectedKnowledgeFile}
          knowledgeStats={knowledgeStats}
        />

        {/* 中间对话区 */}
        <ChatArea
          session={currentSession}
          onSessionUpdate={setCurrentSession}
          ragEnabled={ragEnabled}
        />

        {/* 右侧编辑器 */}
        <Inspector
          file={currentFile}
          view={sidebarView}
          selectedKnowledgeFile={selectedKnowledgeFile}
          onKnowledgeUpdate={handleKnowledgeUpdate}
        />
      </div>

      {/* 设置面板 */}
      <SettingsPanel 
        isOpen={showSettings}
        onClose={() => setShowSettings(false)} 
      />
    </div>
  );
}

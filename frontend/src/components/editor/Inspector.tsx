'use client';

import { useState, useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { 
  FileText, Save, FolderOpen, X, Upload, RefreshCw, Search, 
  Trash2, AlertCircle, CheckCircle, Database, Info
} from 'lucide-react';
import { 
  getFile, saveFile, 
  getKnowledgeStats, uploadKnowledgeFile, deleteKnowledgeFile,
  rebuildKnowledgeIndex, searchKnowledge, getKnowledgeContent,
  updateKnowledgeContent, KnowledgeStats, SearchResult
} from '@/lib/api';

interface InspectorProps {
  file: string | null;
  view: 'chat' | 'memory' | 'skills' | 'knowledge';
  selectedKnowledgeFile?: string | null;
  onKnowledgeUpdate?: () => void;
}

// 支持的文件类型
const ACCEPTED_FILE_TYPES = ".md,.txt,.pdf,.doc,.docx,.csv,.xls,.xlsx,.py,.js,.ts,.jsx,.tsx,.java,.go,.rs,.c,.cpp,.h,.hpp,.json,.yaml,.yml,.xml,.toml,.ini,.cfg,.html,.htm,.css,.scss,.sql,.sh,.bash,.mdx";

export function Inspector({ 
  file, 
  view, 
  selectedKnowledgeFile,
  onKnowledgeUpdate 
}: InspectorProps) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modified, setModified] = useState(false);

  // 知识库管理状态
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [uploading, setUploading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // 知识库文件编辑状态
  const [editingKnowledge, setEditingKnowledge] = useState<string | null>(null);
  const [knowledgeContent, setKnowledgeContent] = useState('');
  const [knowledgeModified, setKnowledgeModified] = useState(false);

  // 加载普通文件
  useEffect(() => {
    if (file && view !== 'knowledge') {
      loadFile(file);
    } else {
      setContent('');
      setModified(false);
    }
  }, [file, view]);

  // 加载知识库统计
  useEffect(() => {
    if (view === 'knowledge') {
      loadStats();
    }
  }, [view]);

  // 加载选中的知识库文件
  useEffect(() => {
    if (selectedKnowledgeFile && view === 'knowledge') {
      loadKnowledgeContent(selectedKnowledgeFile);
    } else {
      setEditingKnowledge(null);
      setKnowledgeContent('');
      setKnowledgeModified(false);
    }
  }, [selectedKnowledgeFile, view]);

  const loadFile = async (path: string) => {
    setLoading(true);
    try {
      const data = await getFile(path);
      setContent(data.content);
      setModified(false);
    } catch (error) {
      setContent(`# 文件加载失败\n\n${error}`);
    }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!file || saving) return;
    
    setSaving(true);
    try {
      await saveFile(file, content);
      setModified(false);
    } catch (error) {
      console.error('Save failed:', error);
    }
    setSaving(false);
  };

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined && value !== content) {
      setContent(value);
      setModified(true);
    }
  };

  // 知识库管理函数
  const loadStats = async () => {
    try {
      const data = await getKnowledgeStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const loadKnowledgeContent = async (filename: string) => {
    setLoading(true);
    try {
      const data = await getKnowledgeContent(filename);
      setEditingKnowledge(filename);
      setKnowledgeContent(data.content);
      setKnowledgeModified(false);
    } catch (error) {
      console.error('Failed to load knowledge content:', error);
      showMessage('error', '加载文件失败');
    }
    setLoading(false);
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await uploadKnowledgeFile(file);
      showMessage('success', `✓ ${file.name} 上传成功`);
      loadStats();
      onKnowledgeUpdate?.();
    } catch (error: any) {
      showMessage('error', error.message || '上传失败');
    }
    setUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDeleteFile = async (filename: string) => {
    if (!confirm(`确定删除 "${filename}" ？`)) return;

    try {
      await deleteKnowledgeFile(filename);
      showMessage('success', '✓ 文件已删除');
      setEditingKnowledge(null);
      setKnowledgeContent('');
      loadStats();
      onKnowledgeUpdate?.();
    } catch (error: any) {
      showMessage('error', error.message || '删除失败');
    }
  };

  const handleRebuild = async () => {
    setRebuilding(true);
    try {
      const result = await rebuildKnowledgeIndex();
      showMessage('success', `✓ ${result.message}`);
      loadStats();
    } catch (error: any) {
      showMessage('error', error.message || '重建索引失败');
    }
    setRebuilding(false);
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setSearching(true);
    setSearchResults([]);
    try {
      const result = await searchKnowledge(searchQuery);
      setSearchResults(result.results);
    } catch (error: any) {
      showMessage('error', error.message || '搜索失败');
    }
    setSearching(false);
  };

  const handleKnowledgeSave = async () => {
    if (!editingKnowledge || !knowledgeModified) return;

    setSaving(true);
    try {
      await updateKnowledgeContent(editingKnowledge, knowledgeContent);
      showMessage('success', '✓ 保存成功');
      setKnowledgeModified(false);
    } catch (error: any) {
      showMessage('error', error.message || '保存失败');
    }
    setSaving(false);
  };

  const handleKnowledgeEditorChange = (value: string | undefined) => {
    if (value !== undefined && value !== knowledgeContent) {
      setKnowledgeContent(value);
      setKnowledgeModified(true);
    }
  };

  // 对话视图
  if (view === 'chat') {
    return (
      <aside className="w-80 bg-white border-l border-gray-200 flex flex-col shrink-0">
        <div className="h-14 flex items-center px-4 border-b border-gray-100">
          <span className="font-medium text-gray-700">信息面板</span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mb-3">
            <FolderOpen size={24} className="text-gray-400" />
          </div>
          <p className="text-gray-500 text-sm">
            切换到「记忆」「技能」或「知识库」<br />查看和编辑文件
          </p>
        </div>
      </aside>
    );
  }

  // 知识库管理视图
  if (view === 'knowledge') {
    return (
      <aside className="w-96 bg-white border-l border-gray-200 flex flex-col shrink-0">
        {/* 标题栏 */}
        <div className="h-14 flex items-center justify-between px-5 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <Database size={18} className="text-blue-500" />
            <span className="font-semibold text-gray-800">知识库</span>
          </div>
        </div>

        {/* 消息提示 */}
        {message && (
          <div className={`mx-5 mt-4 px-4 py-2.5 rounded-lg flex items-center gap-2 text-sm font-medium ${
            message.type === 'success' 
              ? 'bg-green-50 text-green-700 border border-green-100' 
              : 'bg-red-50 text-red-700 border border-red-100'
          }`}>
            {message.type === 'success' 
              ? <CheckCircle size={16} className="shrink-0" /> 
              : <AlertCircle size={16} className="shrink-0" />
            }
            <span>{message.text}</span>
          </div>
        )}

        <div className="flex-1 overflow-auto">
          <div className="p-5 space-y-5">
            {/* 上传区域 */}
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_FILE_TYPES}
                onChange={handleUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50"
              >
                <Upload size={18} />
                <span>{uploading ? '上传中...' : '上传文件'}</span>
              </button>
              <p className="mt-2 text-xs text-gray-400 text-center">
                支持 .md .txt .pdf .docx .py .js .json .yaml 等格式
              </p>
            </div>

            {/* 状态卡片 */}
            {stats && (
              <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-600">状态概览</span>
                  <button
                    onClick={handleRebuild}
                    disabled={rebuilding}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
                    title="重建索引"
                  >
                    <RefreshCw size={12} className={rebuilding ? 'animate-spin' : ''} />
                    <span>{rebuilding ? '重建中' : '重建索引'}</span>
                  </button>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="text-center p-2.5 bg-white rounded-lg border border-gray-100">
                    <div className="text-2xl font-semibold text-gray-800">{stats.file_count}</div>
                    <div className="text-xs text-gray-500 mt-0.5">文件数</div>
                  </div>
                  <div className="text-center p-2.5 bg-white rounded-lg border border-gray-100">
                    <div className="text-2xl font-semibold text-gray-800">{stats.total_size_str}</div>
                    <div className="text-xs text-gray-500 mt-0.5">总大小</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
                  <span className={`w-2 h-2 rounded-full ${stats.index_exists ? 'bg-green-500' : 'bg-amber-400'}`} />
                  <span className={`text-sm ${stats.index_exists ? 'text-green-600' : 'text-amber-600'}`}>
                    {stats.index_exists ? '索引就绪' : '需要重建索引'}
                  </span>
                  {stats.index_updated_at && (
                    <span className="text-xs text-gray-400 ml-auto">
                      {stats.index_updated_at}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* 检索测试 */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Search size={16} className="text-gray-400" />
                <span className="text-sm font-medium text-gray-600">检索测试</span>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="输入查询内容..."
                  className="flex-1 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                />
                <button
                  onClick={handleSearch}
                  disabled={searching || !searchQuery.trim()}
                  className="px-4 py-2.5 bg-gray-100 text-gray-600 rounded-xl hover:bg-gray-200 disabled:opacity-50 transition-colors"
                >
                  {searching ? (
                    <RefreshCw size={18} className="animate-spin" />
                  ) : (
                    <Search size={18} />
                  )}
                </button>
              </div>

              {/* 搜索结果 */}
              {searchResults.length > 0 && (
                <div className="mt-4 space-y-3">
                  <div className="text-xs text-gray-500 font-medium">
                    找到 {searchResults.length} 条结果
                  </div>
                  {searchResults.map((result, i) => (
                    <div key={i} className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-blue-700 flex items-center gap-1.5">
                          <FileText size={12} />
                          {result.source}
                        </span>
                        <span className="text-xs font-mono text-blue-500 bg-blue-100 px-2 py-0.5 rounded">
                          {(result.rerank_score || result.score).toFixed(3)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 leading-relaxed line-clamp-3">{result.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 文件编辑器 */}
            {editingKnowledge && (
              <div className="border-t border-gray-100 pt-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <FileText size={16} className="text-blue-500 shrink-0" />
                    <span className="text-sm font-medium text-gray-700 truncate">
                      {editingKnowledge}
                    </span>
                    {knowledgeModified && (
                      <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full font-medium">
                        未保存
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={handleKnowledgeSave}
                      disabled={!knowledgeModified || saving}
                      className="p-2 hover:bg-indigo-50 rounded-lg disabled:opacity-30 transition-colors group"
                      title="保存"
                    >
                      <Save size={16} className={knowledgeModified ? 'text-indigo-600' : 'text-gray-400'} />
                    </button>
                    <button
                      onClick={() => handleDeleteFile(editingKnowledge)}
                      className="p-2 hover:bg-red-50 rounded-lg text-red-400 hover:text-red-500 transition-colors"
                      title="删除"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                <div className="h-56 border border-gray-200 rounded-xl overflow-hidden">
                  <Editor
                    height="100%"
                    defaultLanguage="markdown"
                    value={knowledgeContent}
                    onChange={handleKnowledgeEditorChange}
                    theme="vs-light"
                    options={{
                      minimap: { enabled: false },
                      fontSize: 12,
                      lineNumbers: 'off',
                      wordWrap: 'on',
                      scrollBeyondLastLine: false,
                      padding: { top: 12, bottom: 12 },
                      renderLineHighlight: 'none',
                      folding: false,
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </aside>
    );
  }

  // 记忆/技能视图 - 文件编辑器
  return (
    <aside className="w-80 bg-white border-l border-gray-200 flex flex-col shrink-0">
      {/* 标题栏 */}
      <div className="h-14 flex items-center justify-between px-5 border-b border-gray-100">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <FileText size={16} className="text-indigo-500 shrink-0" />
          <span className="font-medium text-gray-700 truncate text-sm">
            {file?.split('/').pop() || '未选择文件'}
          </span>
          {modified && (
            <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full font-medium shrink-0">
              未保存
            </span>
          )}
        </div>
        {file && (
          <button
            onClick={handleSave}
            disabled={!modified || saving}
            className="p-2 rounded-lg hover:bg-indigo-50 disabled:opacity-30 transition-colors"
            title="保存 (Ctrl+S)"
          >
            <Save size={18} className={modified ? 'text-indigo-600' : 'text-gray-400'} />
          </button>
        )}
      </div>

      {/* 编辑器 */}
      <div className="flex-1 min-h-0">
        {loading ? (
          <div className="h-full flex items-center justify-center text-gray-400">
            加载中...
          </div>
        ) : file ? (
          <Editor
            height="100%"
            defaultLanguage="markdown"
            value={content}
            onChange={handleEditorChange}
            theme="vs-light"
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: 'off',
              wordWrap: 'on',
              scrollBeyondLastLine: false,
              padding: { top: 16, bottom: 16 },
              renderLineHighlight: 'none',
              folding: false,
              glyphMargin: false,
              lineDecorationsWidth: 0,
            }}
            onMount={(editor, monaco) => {
              editor.addCommand(
                monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
                () => {
                  handleSave();
                }
              );
            }}
          />
        ) : (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center">
            <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mb-3">
              <FileText size={24} className="text-gray-400" />
            </div>
            <p className="text-gray-500 text-sm">
              从左侧选择文件<br />进行查看或编辑
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}

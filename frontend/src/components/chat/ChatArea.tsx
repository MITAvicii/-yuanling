'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, Wrench, Database, CheckCircle, Image, BarChart3, Cog, FileSearch, Terminal, Paperclip, X, Film } from 'lucide-react';
import { Session, sendMessage, getSession, ChatFile, getConfig } from '@/lib/api';

// 工具名称映射到图标
const toolIcons: Record<string, React.ReactNode> = {
  'terminal': <Terminal size={12} />,
  'bash': <Terminal size={12} />,
  'python_repl': <Cog size={12} />,
  'read_file': <FileSearch size={12} />,
  'web_fetch': <FileSearch size={12} />,
  'search_knowledge_base': <Database size={12} />,
  'ask-search': <FileSearch size={12} />,
};

interface ToolCall {
  name: string;
  args: Record<string, any>;
  output?: string;
  status: 'pending' | 'running' | 'completed';
}

// 运行状态类型
interface RunningStatus {
  phase: 'thinking' | 'tool' | 'idle';
  toolName?: string;
  message?: string;
}

interface RetrievalResult {
  text: string;
  score: number;
  rerank_score: number | null;
  source: string;
}

interface RetrievalInfo {
  query: string;
  context: string;
  results: RetrievalResult[];
  above_threshold: boolean;
  auto_chart?: string;
}
interface Message {
  id: string;
  role: 'user' | 'assistant';
  type?: 'human' | 'ai' | 'tool';
  content: string;
  files?: ChatFile[];
  toolCalls?: ToolCall[];
  retrieval?: RetrievalInfo;
  isNew?: boolean;
}

// 图表组件 - 带保存功能
function ChartImage({ src, alt }: { src: string; alt?: string }) {
  const [showActions, setShowActions] = useState(false);
  
  const handleSave = () => {
    // 创建下载链接
    const link = document.createElement('a');
    link.href = src;
    link.download = `chart-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  return (
    <div 
      className="mt-2 relative inline-block"
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <img 
        src={src}
        alt={alt || '图表'} 
        className="max-w-full rounded-lg border border-gray-200"
      />
      {/* 保存按钮 - 悬停时显示 */}
      {showActions && (
        <button
          onClick={handleSave}
          className="absolute top-2 right-2 bg-white/90 hover:bg-white text-gray-700 px-2 py-1 rounded shadow text-xs flex items-center gap-1 transition-colors"
          title="保存图表"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          保存
        </button>
      )}
    </div>
  );
}

function ToolOutput({ output }: { output: string }) {
  // 检查是否是 Base64 图片 - 支持两种格式
  // 1. 直接格式: data:image/png;base64,xxx
  // 2. Markdown格式: ![图表](data:image/png;base64,xxx)
  
  // 先检查简单的 data:image 格式（+ 需要转义）
  const simpleMatch = output.match(/data:image\/(\w+);base64,([A-Za-z0-9+/=]+)/);
  if (simpleMatch) {
    const mimeType = simpleMatch[1];
    const imageData = simpleMatch[2];
    const src = `data:image/${mimeType};base64,${imageData}`;
    return (
      <div className="mt-2">
        <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
          <Image size={14} />
          <span>图表</span>
        </div>
        <ChartImage src={src} alt="图表" />
      </div>
    );
  }
  
  // 检查 Markdown 格式
  const mdMatch = output.match(/!\[([^\]]+)\]\((data:image\/(\w+);base64,([A-Za-z0-9+/=]+))\)/);
  if (mdMatch) {
    const imageData = mdMatch[4];
    const src = `data:image/${mdMatch[3] || 'png'};base64,${imageData}`;
    return (
      <div className="mt-2">
        <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
          <Image size={14} />
          <span>图表</span>
        </div>
        <ChartImage src={src} alt="图表" />
      </div>
    );
  }
  
  // 检查是否包含 Markdown 表格
  const hasMarkdownTable = output.includes('|') && output.includes('---');
  if (hasMarkdownTable) {
    return (
      <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded-lg overflow-x-auto">
        <pre className="whitespace-pre-wrap">{output}</pre>
      </div>
    );
  }
  
  // 默认：纯文本输出
  return (
    <div className="mt-1 text-xs text-gray-600 bg-gray-100 p-2 rounded max-h-60 overflow-auto">
      <pre className="whitespace-pre-wrap">{output}</pre>
    </div>
  );
}

interface ChatAreaProps {
  session: Session | null;
  onSessionUpdate: (session: Session | null) => void;
  ragEnabled?: boolean;
}

export function ChatArea({ session, onSessionUpdate, ragEnabled = true }: ChatAreaProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [runningStatus, setRunningStatus] = useState<RunningStatus>({ phase: 'idle' });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // 跟踪当前显示消息所属的会话ID，用于防止流式过程中被历史加载覆盖
  const displaySessionIdRef = useRef<string | null>(null);
  
  // 文件上传相关
  const [attachedFiles, setAttachedFiles] = useState<ChatFile[]>([]);
  const [supportsUpload, setSupportsUpload] = useState(false);
  const [currentModelCaps, setCurrentModelCaps] = useState<string[]>([]);

  // 加载会话历史消息（仅在切换会话时加载，流式过程中不加载）
  useEffect(() => {
    if (session?.id) {
      // 如果当前已显示的消息就属于该会话，跳过加载（避免覆盖流式消息）
      if (displaySessionIdRef.current === session.id) return;
      displaySessionIdRef.current = session.id;
      loadSessionHistory(session.id);
    } else {
      displaySessionIdRef.current = null;
      setMessages([]);
    }
  }, [session?.id]);

  // 加载模型能力（判断是否支持文件上传）
  useEffect(() => {
    loadModelCapabilities();
  }, []);

  const loadModelCapabilities = async () => {
    try {
      const data = await getConfig();
      const provider = data.providers?.[data.chat_provider];
      if (provider) {
        const caps = provider.model_capabilities?.[data.chat_model] || [];
        setCurrentModelCaps(caps);
        // 非纯文本模型（有 vision/image_gen/video_gen 能力）支持上传
        const canUpload = caps.some((c: string) => c !== 'chat');
        setSupportsUpload(canUpload);
      }
    } catch (error) {
      console.error('Failed to load model capabilities:', error);
    }
  };

  // 从可能的多模态 content 中提取纯文本
  // 后端多模态消息的 content 是 [{type:"text",text:"..."}, {type:"image_url",...}] 格式
  const extractText = (content: any): string => {
    if (typeof content === 'string') return content;
    if (Array.isArray(content)) {
      return content
        .filter((block: any) => block?.type === 'text')
        .map((block: any) => block?.text || '')
        .join('\n');
    }
    return String(content || '');
  };

  const loadSessionHistory = async (sessionId: string) => {
    setLoadingHistory(true);
    try {
      const data = await getSession(sessionId);
      
      // 过滤并合并消息：只保留用户消息和最终的 AI 回复
      // 跳过 tool_calls 和 tool response 等中间过程
      const historyMessages: Message[] = [];
      let lastAiContent = '';
      
      for (const msg of data.messages) {
        if (msg.type === 'human') {
          // 保存之前的 AI 消息（如果有内容）
          if (lastAiContent) {
            historyMessages.push({
              id: `${sessionId}-${historyMessages.length}`,
              role: 'assistant',
              type: 'ai',
              content: lastAiContent,
            });
            lastAiContent = '';
          }
          // 添加用户消息（从多模态 content 中提取文本）
          historyMessages.push({
            id: `${sessionId}-${historyMessages.length}`,
            role: 'user',
            type: 'human',
            content: extractText(msg.content),
          });
        } else if (msg.type === 'ai') {
          // AI 消息：保留内容，如果最后有 tool_calls 则等待 tool response
          if (!msg.tool_calls || msg.tool_calls.length === 0) {
            // 没有 tool_calls，这是最终回复
            lastAiContent = extractText(msg.content);
          }
          // 如果有 tool_calls，先等待后续的 tool response
        } else if (msg.type === 'tool') {
          // tool response 后，继续等待下一个 AI 消息
        }
      }
      
      // 保存最后一条 AI 消息
      if (lastAiContent) {
        historyMessages.push({
          id: `${sessionId}-${historyMessages.length}`,
          role: 'assistant',
          type: 'ai',
          content: lastAiContent,
        });
      }
      
      setMessages(historyMessages);
    } catch (error) {
      console.error('Failed to load session history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 处理文件选择
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const newFiles: Promise<ChatFile>[] = Array.from(files).map((file) => {
      return new Promise<ChatFile>((resolve, reject) => {
        // 文件大小限制：图片 10MB，视频 50MB
        const isVideo = file.type.startsWith('video/');
        const maxSize = isVideo ? 50 * 1024 * 1024 : 10 * 1024 * 1024;
        if (file.size > maxSize) {
          reject(new Error(`文件 ${file.name} 超过大小限制（${isVideo ? '50MB' : '10MB'}）`));
          return;
        }
        
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = (reader.result as string).split(',')[1]; // 去掉 data:xxx;base64, 前缀
          resolve({
            name: file.name,
            data: base64,
            mime_type: file.type,
          });
        };
        reader.onerror = () => reject(new Error(`读取文件 ${file.name} 失败`));
        reader.readAsDataURL(file);
      });
    });
    
    Promise.all(newFiles)
      .then((results) => {
        setAttachedFiles((prev) => [...prev, ...results]);
      })
      .catch((err) => {
        alert(err.message);
      });
    
    // 重置 input 以允许重新选择同一文件
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  // 移除已附加的文件
  const removeFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };
  
  // 触发文件选择
  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const handleSend = async () => {
    if ((!input.trim() && attachedFiles.length === 0) || loading) return;

    // 保留当前文件引用
    const filesToSend = attachedFiles.length > 0 ? [...attachedFiles] : undefined;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      files: filesToSend,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setAttachedFiles([]);
    setLoading(true);

    const aiMessageId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev,
      { id: aiMessageId, role: 'assistant', type: 'ai', content: '', toolCalls: [], isNew: true },
    ]);

    try {
      await sendMessage(
        input.trim(),
        session?.id,
        (chunk: any) => {
          if (chunk.type === 'session') {
            // 标记当前显示的消息已属于该会话，防止 useEffect 覆盖
            displaySessionIdRef.current = chunk.session_id;
            onSessionUpdate({ ...session, id: chunk.session_id } as Session);
          } else if (chunk.type === 'retrieval') {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { 
                      ...msg, 
                      retrieval: {
                        query: chunk.query,
                        context: chunk.context || '',
                        results: chunk.results || [],
                        above_threshold: chunk.above_threshold ?? true,
                        auto_chart: chunk.auto_chart,
                      }
                    }
                  : msg
              )
            );
          } else if (chunk.type === 'token') {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, content: msg.content + chunk.content }
                  : msg
              )
            );
            // 停止打字效果，开始显示实际内容
            setRunningStatus({ phase: 'idle' });
          } else if (chunk.type === 'tool_start') {
            setRunningStatus({ 
              phase: 'tool', 
              toolName: chunk.tool,
              message: `正在执行 ${chunk.tool}...`
            });
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { 
                      ...msg, 
                      toolCalls: [
                        ...(msg.toolCalls || []),
                        { 
                          name: chunk.tool, 
                          args: chunk.input,
                          status: 'running' 
                        }
                      ]
                    }
                  : msg
              )
            );
          } else if (chunk.type === 'tool_end') {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { 
                      ...msg, 
                      toolCalls: (msg.toolCalls || []).map((tc) =>
                        tc.name === chunk.tool
                          ? { ...tc, output: chunk.output, status: 'completed' }
                          : tc
                      )
                    }
                  : msg
              )
            );
            setRunningStatus({ phase: 'thinking', message: '思考中...' });
          } else if (chunk.type === 'new_response') {
            // Tool completed, agent is generating new text
            // Tool completed, agent is generating new text
          } else if (chunk.type === 'done') {
            setLoading(false);
            setRunningStatus({ phase: 'idle' });
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, isNew: false }
                  : msg
              )
            );
          } else if (chunk.type === 'title') {
            onSessionUpdate({ 
              ...session, 
              id: chunk.session_id,
              title: chunk.title 
            } as Session);
          } else if (chunk.type === 'error') {
            setRunningStatus({ phase: 'idle' });
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, content: `错误: ${chunk.message}`, isNew: false }
                  : msg
              )
            );
            setLoading(false);
          }
        },
        ragEnabled,
        filesToSend
      );
    } catch (error) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId
            ? { ...msg, content: `请求失败: ${error}`, isNew: false }
            : msg
        )
      );
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <main className="flex-1 flex flex-col bg-[#f8f9fb] min-w-0">
      {/* 消息列表 */}
      <div className="flex-1 overflow-auto">
        {loadingHistory ? (
          <div className="h-full flex items-center justify-center">
            <div className="flex items-center gap-2 text-gray-400">
              <Loader2 className="animate-spin" size={20} />
              <span>加载历史消息...</span>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex items-center justify-center p-6">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                <Sparkles size={32} className="text-white" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                你好，我是源灵AI
              </h2>
              <p className="text-gray-500 mb-6">
                一个本地优先、透明可控的 AI Agent 系统。我可以帮你完成任务、回答问题、管理知识。
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {['帮我查天气', '阅读并总结文档', '执行 Python 代码'].map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => setInput(prompt)}
                    className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto p-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                } animate-fadeIn`}
              >
                {message.role === 'user' ? (
                  <div className="message-user">
                    {message.content && <p>{message.content}</p>}
                    {message.files && message.files.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {message.files.map((file, i) => (
                          file.mime_type.startsWith('image/') ? (
                            <img
                              key={i}
                              src={`data:${file.mime_type};base64,${file.data}`}
                              alt={file.name}
                              className="max-w-[200px] max-h-[200px] rounded-lg object-cover border border-gray-200"
                            />
                          ) : file.mime_type.startsWith('video/') ? (
                            <div key={i} className="w-40 h-24 rounded-lg overflow-hidden border border-gray-200 bg-gray-900 flex items-center justify-center relative">
                              <Film size={24} className="text-gray-400" />
                              <span className="absolute bottom-1 left-1 right-1 text-[10px] text-gray-400 truncate text-center">{file.name}</span>
                            </div>
                          ) : null
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="w-full max-w-[85%]">
                    {message.retrieval && message.retrieval.results.length > 0 && (
                      <details className={`mb-3 rounded-lg border ${ message.retrieval.above_threshold ? 'bg-purple-50 border-purple-200' : 'bg-gray-50 border-gray-200' }`}>
                        <summary className={`cursor-pointer font-medium flex items-center gap-2 p-3 text-sm ${ message.retrieval.above_threshold ? 'text-purple-700' : 'text-gray-500' }`}>
                          <Database size={14} />
                          <span>知识检索</span>
                          {!message.retrieval.above_threshold && (
                            <span className="text-xs font-normal text-gray-400 ml-1">(相关度不足，未注入)</span>
                          )}
                          <span className={`ml-auto text-xs font-normal px-1.5 py-0.5 rounded-full ${ message.retrieval.above_threshold ? 'bg-purple-100 text-purple-600' : 'bg-gray-200 text-gray-500' }`}>
                            {message.retrieval.results.length} 条结果
                          </span>
                        </summary>
                        <div className="p-3 pt-0 space-y-2">
                          {message.retrieval.results.map((r: any, i: number) => (
                            <div key={i} className={`rounded-lg p-2.5 border ${r.source_type === 'knowledge' ? 'bg-blue-50 border-blue-100' : 'bg-purple-50 border-purple-100'}`}>
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${r.source_type === 'knowledge' ? 'bg-blue-200 text-blue-800' : 'bg-purple-200 text-purple-800'}`}>
                                  {r.source_type === 'knowledge' ? '知识库' : '记忆'}
                                </span>
                                <span className="text-xs text-gray-500">{r.source}</span>
                                <div className="ml-auto flex items-center gap-2">
                                  <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
                                    相似度 {(r.score * 100).toFixed(1)}%
                                  </span>
                                  {r.rerank_score !== null && (
                                    <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700">
                                      重排序 {r.rerank_score.toFixed(3)}
                                    </span>
                                  )}
                                </div>
                              </div>
                              <p className="text-xs text-gray-600 leading-relaxed line-clamp-3">{r.text}</p>
                            </div>
                          ))}
                          {/* 自动生成的图表 */}
                          {message.retrieval.auto_chart && (
                            <div className="mt-3 p-2 rounded-lg bg-green-50 border border-green-200">
                              <div className="flex items-center gap-2 text-xs text-green-700 mb-2">
                                <BarChart3 size={14} />
                                <span className="font-medium">自动数据分析</span>
                              </div>
                              <ChartImage src={message.retrieval.auto_chart} alt="数据分析图表" />
                            </div>
                          )}
                        </div>
                      </details>
                    )}
                    
                    {/* 工具调用显示 */}
                    {message.toolCalls && message.toolCalls.length > 0 && (
                      <details className="thinking-block mb-3">
                        <summary className="cursor-pointer font-medium flex items-center gap-2">
                          <Wrench size={14} />
                          工具调用 ({message.toolCalls.length})
                        </summary>
                        <div className="mt-3 space-y-2">
                          {message.toolCalls.map((call, i) => (
                            <div key={i} className="bg-white/50 rounded-lg p-2 border border-amber-200">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-amber-900">{call.name}</span>
                                {call.status === 'running' && (
                                  <Loader2 className="animate-spin text-amber-500" size={12} />
                                )}
                                {call.status === 'completed' && (
                                  <CheckCircle className="text-green-500" size={12} />
                                )}
                              </div>
                              {call.args && Object.keys(call.args).length > 0 && (
                                <pre className="text-xs mt-1 text-amber-800 overflow-auto">
                                  {JSON.stringify(call.args, null, 2)}
                                </pre>
                              )}
                              {/* 只显示纯文本输出，不显示图表 */}
                              {call.output && (
                                <div className="text-xs mt-1 text-amber-700 bg-amber-50 p-2 rounded max-h-40 overflow-auto">
                                  {call.output.length > 500 ? call.output.substring(0, 500) + '...' : call.output}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                    
                    {/* AI 回复 - 提取图表后显示纯文本 */}
                    <div className="message-assistant whitespace-pre-wrap">
                      {(() => {
                        // 提取图表并清理内容
                        const content = message.content || '';
                        const imgMatch = content.match(/data:image\/(\w+);base64,([A-Za-z0-9+\/=]+)/);
                        // 移除markdown图片语法，只显示文字
                        const cleanContent = content.replace(/!\[([^\]]*)\]\([^)]+\)/g, '').trim();
                        
                        // 如果没有内容且正在加载，显示状态指示器
                        if (!cleanContent && loading && message.isNew) {
                          return (
                            <div className="flex items-center gap-3">
                              {/* 状态指示器 */}
                              <div className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-full border border-indigo-200">
                                {runningStatus.phase === 'tool' ? (
                                  <>
                                    <div className="flex items-center gap-1.5 text-indigo-600">
                                      <Cog size={14} className="animate-spin" />
                                      <span className="text-sm font-medium">{runningStatus.message || '执行工具中...'}</span>
                                    </div>
                                  </>
                                ) : runningStatus.phase === 'thinking' ? (
                                  <>
                                    <div className="flex items-center gap-1.5 text-purple-600">
                                      <Sparkles size={14} />
                                      <span className="text-sm font-medium">{runningStatus.message || '思考中...'}</span>
                                    </div>
                                  </>
                                ) : (
                                  <>
                                    <div className="flex items-center gap-1.5 text-gray-500">
                                      <Loader2 size={14} className="animate-spin" />
                                      <span className="text-sm">思考中...</span>
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>
                          );
                        }
                        
                        return cleanContent || null;
                      })()}
                    </div>
                    {/* 图表显示 */}
                    {(() => {
                      const imgMatch = message.content ? message.content.match(/data:image\/(\w+);base64,([A-Za-z0-9+\/=]+)/) : null;
                      if (!imgMatch) return null;
                      const imgSrc = `data:${imgMatch[1]};base64,${imgMatch[2]}`;
                      return (
                        <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
                            <BarChart3 size={16} />
                            <span className="font-medium">数据分析图表</span>
                            <span className="text-xs text-gray-400 ml-auto">悬停保存</span>
                          </div>
                          <ChartImage src={imgSrc} alt="数据分析图表" />
                        </div>
                      );
                    })()}

                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="p-4 bg-white border-t border-gray-100">
        <div className="max-w-3xl mx-auto">
          {/* 文件预览区 */}
          {attachedFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {attachedFiles.map((file, index) => (
                <div key={index} className="relative group">
                  {file.mime_type.startsWith('image/') ? (
                    <div className="w-16 h-16 rounded-lg overflow-hidden border border-gray-200 bg-gray-50">
                      <img
                        src={`data:${file.mime_type};base64,${file.data}`}
                        alt={file.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : file.mime_type.startsWith('video/') ? (
                    <div className="w-16 h-16 rounded-lg overflow-hidden border border-gray-200 bg-gray-900 flex items-center justify-center">
                      <Film size={24} className="text-gray-400" />
                    </div>
                  ) : (
                    <div className="w-16 h-16 rounded-lg overflow-hidden border border-gray-200 bg-gray-50 flex items-center justify-center">
                      <Paperclip size={24} className="text-gray-400" />
                    </div>
                  )}
                  <button
                    onClick={() => removeFile(index)}
                    className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X size={12} />
                  </button>
                  <span className="absolute bottom-0 left-0 right-0 text-[9px] text-center truncate bg-black/40 text-white rounded-b-lg px-1">
                    {file.name.length > 10 ? file.name.slice(0, 8) + '..' : file.name}
                  </span>
                </div>
              ))}
            </div>
          )}
          
          <div className="flex gap-3 items-end">
            {/* 文件上传按钮（仅多模态模型显示） */}
            {supportsUpload && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp,video/mp4,video/webm"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <button
                  onClick={triggerFileUpload}
                  disabled={loading}
                  className="h-12 w-12 flex items-center justify-center bg-gray-100 text-gray-500 rounded-xl hover:bg-gray-200 hover:text-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  title="上传图片或视频"
                >
                  <Paperclip size={20} />
                </button>
              </>
            )}
            
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={supportsUpload ? "输入消息，可上传图片/视频..." : "输入消息..."}
                className="input resize-none pr-12"
                rows={1}
                disabled={loading}
                style={{ minHeight: '48px', maxHeight: '200px' }}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={(!input.trim() && attachedFiles.length === 0) || loading}
              className="h-12 px-5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium flex items-center gap-2"
            >
              {loading ? (
                <Loader2 className="animate-spin" size={18} />
              ) : (
                <Send size={18} />
              )}
            </button>
          </div>
          <div className="text-xs text-gray-400 mt-2 text-center">
            按 Enter 发送，Shift + Enter 换行{currentModelCaps.includes('vision') && ' | 支持图片/视频输入'}
          </div>
        </div>
      </div>
    </main>
  );
}

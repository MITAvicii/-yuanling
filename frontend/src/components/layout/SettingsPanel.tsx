'use client';

import { useState, useEffect } from 'react';
import { X, Plus, Trash2, MessageSquare, Plug } from 'lucide-react';
import { getConfig, setConfig, addPlatformApp, deletePlatformApp, getPlatformApps, PlatformApp } from '@/lib/api';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// 预设提供商模板
const PROVIDER_TEMPLATES: Array<{
  id: string;
  name: string;
  baseUrl: string;
  models: string[];
  modelCapabilities?: Record<string, string[]>;
}> = [
  { id: 'deepseek', name: 'DeepSeek', baseUrl: 'https://api.deepseek.com', models: ['deepseek-chat', 'deepseek-reasoner'] },
  { id: 'openai', name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', models: ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'], modelCapabilities: { 'gpt-4o': ['chat', 'vision'], 'gpt-4-turbo': ['chat', 'vision'] } },
  { id: 'dashscope', name: '阿里云 DashScope', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: ['qwen-turbo', 'qwen-plus', 'qwen-max'] },
  { id: 'nvidia', name: 'NVIDIA NIM', baseUrl: 'https://integrate.api.nvidia.com/v1', models: ['meta/llama-3.1-8b-instruct', 'nvidia/llama-3.1-nemotron-70b-instruct'] },
  { id: 'ollama', name: 'Ollama (本地)', baseUrl: 'http://localhost:11434/v1', models: ['llama3.1', 'qwen2.5', 'mistral'] },
  { id: 'agnes-ai', name: 'Agnes AI (全模态)', baseUrl: 'https://apihub.agnes-ai.com/v1', models: ['agnes-2.0-flash', 'agnes-1.5-flash', 'agnes-image-2.0-flash', 'agnes-image-2.1-flash', 'agnes-video-v2.0'], modelCapabilities: { 'agnes-2.0-flash': ['chat', 'vision'], 'agnes-1.5-flash': ['chat', 'vision'], 'agnes-image-2.0-flash': ['image_gen'], 'agnes-image-2.1-flash': ['image_gen'], 'agnes-video-v2.0': ['video_gen'] } },
  { id: 'custom', name: '自定义', baseUrl: '', models: [] },
];

// 能力标签映射
const CAPABILITY_LABELS: Record<string, string> = {
  'chat': '💬 对话',
  'vision': '👁 视觉理解',
  'image_gen': '🎨 图片生成',
  'video_gen': '🎬 视频生成',
};

const PLATFORMS = [
  { id: 'feishu', name: '飞书', icon: '📢' },
  { id: 'wechat', name: '微信', icon: '💬' },
];

type TabType = 'chat' | 'platform';

export default function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  
  // 对话模型配置
  const [chatProvider, setChatProvider] = useState('deepseek');
  const [chatProviderName, setChatProviderName] = useState('DeepSeek');
  const [chatBaseUrl, setChatBaseUrl] = useState('https://api.deepseek.com');
  const [chatApiKey, setChatApiKey] = useState('');
  const [chatModel, setChatModel] = useState('deepseek-chat');
  const [chatTemperature, setChatTemperature] = useState(0.7);
  
  // 保存所有提供商的 API Keys（切换提供商时不会丢失）
  const [allApiKeys, setAllApiKeys] = useState<Record<string, string>>({});
  
  // 保存每个提供商最后使用的模型
  const [providerModels, setProviderModels] = useState<Record<string, string>>({});
  
  // 动态注册的提供商（不在预设模板中）
  const [dynamicProviders, setDynamicProviders] = useState<Array<{id: string; name: string}>>([]);
  
  // 平台应用
  const [platformApps, setPlatformApps] = useState<PlatformApp[]>([]);
  const [showAddPlatform, setShowAddPlatform] = useState(false);
  const [newPlatform, setNewPlatform] = useState({
    type: 'feishu',
    appId: '',
    appSecret: '',
    encryptKey: '',
  });

  useEffect(() => {
    if (isOpen) {
      loadConfig();
      loadPlatformApps();
    }
  }, [isOpen]);

  const loadConfig = async () => {
    try {
      const data = await getConfig();
      
      // 加载对话模型配置
      const provider = data.chat_provider || 'deepseek';
      setChatProvider(provider);
      setChatModel(data.chat_model || 'deepseek-chat');
      setChatTemperature(data.temperature || 0.7);
      
      // 保存所有 API Keys
      if (data.provider_api_keys) {
        setAllApiKeys(data.provider_api_keys);
        // 设置当前提供商的 API Key
        if (data.provider_api_keys[provider]) {
          setChatApiKey(data.provider_api_keys[provider]);
        } else {
          setChatApiKey('');
        }
        
        // 收集不在预设模板中的提供商
        const presetIds = PROVIDER_TEMPLATES.map(t => t.id);
        const dynamic = Object.keys(data.provider_api_keys)
          .filter(id => !presetIds.includes(id) && id !== provider)
          .map(id => ({ id, name: id }));
        setDynamicProviders(dynamic);
      }
      
      // 加载每个提供商最后使用的模型
      if (data.provider_models) {
        setProviderModels(data.provider_models);
      }
      
      // 从 providers 中获取 Base URL 和名称
      if (data.providers?.[provider]) {
        const p = data.providers[provider];
        setChatBaseUrl(p.base_url || '');
      } else {
        // 对预设提供商使用默认 base URL
        const template = PROVIDER_TEMPLATES.find(t => t.id === provider);
        if (template) {
          setChatBaseUrl(template.baseUrl);
          setChatProviderName(template.name);
        } else if (provider !== 'custom') {
          // 是注册过的自定义提供商，但没在 providers 中找到
          setChatBaseUrl('');
          setChatProviderName(provider);
        }
      }
      
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPlatformApps = async () => {
    try {
      const apps = await getPlatformApps();
      setPlatformApps(apps);
    } catch (error) {
      console.error('Failed to load platform apps:', error);
    }
  };

  const handleProviderChange = (providerId: string) => {
    const template = PROVIDER_TEMPLATES.find(p => p.id === providerId);
    
    setChatProvider(providerId);
    
    if (template) {
      // 预设提供商：使用预设的 name 和 baseUrl
      if (providerId !== 'custom') {
        setChatProviderName(template.name);
      } else {
        // 自定义：保留之前填写的名称
        setChatProviderName(allApiKeys[providerId] ? providerId : '');
      }
      setChatBaseUrl(template.baseUrl);
      
      // 优先使用保存的模型，否则使用预设的第一个模型
      const savedModel = providerModels[providerId];
      if (savedModel) {
        setChatModel(savedModel);
      } else if (template.models.length > 0) {
        setChatModel(template.models[0]);
      } else {
        setChatModel('');
      }
    } else {
      // 不在模板中的已有提供商（如之前手动添加的）
      setChatProviderName(providerId);
      setChatBaseUrl('');
      const savedModel = providerModels[providerId];
      setChatModel(savedModel || '');
    }
    
    // 从已保存的 API Keys 中加载该提供商的 Key
    setChatApiKey(allApiKeys[providerId] || '');
  };

  const handleSave = async () => {
    try {
      // 确定实际的 provider ID
      // 对于自定义提供商，使用用户输入的名称作为 ID
      let actualProvider = chatProvider;
      if (chatProvider === 'custom') {
        if (!chatProviderName.trim()) {
          alert('请输入提供商名称');
          return;
        }
        actualProvider = chatProviderName.trim().toLowerCase().replace(/\s+/g, '-');
      }
      
      // 合并所有 API Keys，保留之前保存的其他提供商的 Key
      const mergedApiKeys = {
        ...allApiKeys,
        [actualProvider]: chatApiKey,
      };
      
      // 更新当前提供商的模型
      const updatedProviderModels = {
        ...providerModels,
        [actualProvider]: chatModel,
      };
      
      // 构建 providers 配置更新（用于注册新的或自定义的提供商）
      const providersUpdate: Record<string, any> = {};
      
      // 对所有非预设提供商，注册其配置
      const presetIds = PROVIDER_TEMPLATES.filter(t => t.id !== 'custom').map(t => t.id);
      if (!presetIds.includes(actualProvider)) {
        const modelList = chatModel ? [chatModel] : [];
        providersUpdate[actualProvider] = {
          base_url: chatBaseUrl,
          api_key_env: `${actualProvider.toUpperCase().replace(/-/g, '_')}_API_KEY`,
          models: modelList,
        };
      }
      
      // 对预设提供商，传递 model_capabilities
      const template = PROVIDER_TEMPLATES.find(t => t.id === actualProvider);
      if (template?.modelCapabilities) {
        providersUpdate[actualProvider] = {
          ...(providersUpdate[actualProvider] || {
            base_url: template.baseUrl,
            api_key_env: `${actualProvider.toUpperCase().replace(/-/g, '_')}_API_KEY`,
            models: template.models,
          }),
          model_capabilities: template.modelCapabilities,
        };
      }
      
      await setConfig({
        chat_provider: actualProvider,
        chat_model: chatModel,
        temperature: chatTemperature,
        provider_api_keys: mergedApiKeys,
        custom_models: providersUpdate as any,
        provider_models: updatedProviderModels,
      });
      
      // 更新本地保存的 API Keys 和模型
      setAllApiKeys(mergedApiKeys);
      setProviderModels(updatedProviderModels);
      
      // 如果切换了 provider ID（自定义场景），同步更新状态
      if (actualProvider !== chatProvider) {
        setChatProvider(actualProvider);
      }
      
      alert('配置已保存，请刷新页面后开始对话');
    } catch (error) {
      console.error('Failed to save config:', error);
      alert('保存失败');
    }
  };

  const handleAddPlatformApp = async () => {
    if (!newPlatform.appId || !newPlatform.appSecret) {
      alert('请填写 App ID 和 App Secret');
      return;
    }
    
    try {
      await addPlatformApp({
        platform: newPlatform.type,
        app_id: newPlatform.appId,
        app_secret: newPlatform.appSecret,
        encrypt_key: newPlatform.encryptKey || undefined,
      });
      setNewPlatform({ type: 'feishu', appId: '', appSecret: '', encryptKey: '' });
      setShowAddPlatform(false);
      loadPlatformApps();
      alert('平台应用已添加');
    } catch (error) {
      console.error('Failed to add platform app:', error);
      alert('添加失败');
    }
  };

  if (!isOpen) return null;

  const tabs = [
    { id: 'chat' as const, label: '对话模型', icon: MessageSquare },
    { id: 'platform' as const, label: '平台接入', icon: Plug },
  ];

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="text-xl font-semibold text-gray-800">设置</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-100">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-indigo-600 border-b-2 border-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-5">
          {loading ? (
            <div className="text-center py-10 text-gray-500">加载中...</div>
          ) : (
            <>
              {/* 对话模型配置 */}
              {activeTab === 'chat' && (
                <div className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">提供商</label>
                    <select
                      value={chatProvider}
                      onChange={(e) => handleProviderChange(e.target.value)}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                    >
                      {PROVIDER_TEMPLATES.map(p => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                      {dynamicProviders.length > 0 && (
                        <option disabled>──── 已配置的提供商 ────</option>
                      )}
                      {dynamicProviders.map(p => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>

                  {/* 自定义提供商名称 */}
                  {chatProvider === 'custom' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">提供商名称</label>
                      <input
                        type="text"
                        value={chatProviderName}
                        onChange={(e) => setChatProviderName(e.target.value)}
                        placeholder="如：OpenRouter"
                        className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Base URL</label>
                    <input
                      type="text"
                      value={chatBaseUrl}
                      onChange={(e) => setChatBaseUrl(e.target.value)}
                      placeholder="https://api.example.com/v1"
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                    />
                    {chatProvider === 'ollama' && (
                      <p className="text-xs text-gray-500 mt-1">确保 Ollama 服务已启动：ollama serve</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
                    <input
                      type="password"
                      value={chatApiKey}
                      onChange={(e) => setChatApiKey(e.target.value)}
                      placeholder={chatProvider === 'ollama' ? '本地模型无需 API Key' : 'sk-...'}
                      disabled={chatProvider === 'ollama'}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 disabled:opacity-50"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">模型名称</label>
                    <input
                      type="text"
                      value={chatModel}
                      onChange={(e) => setChatModel(e.target.value)}
                      placeholder="输入模型名称"
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                    />
                    {PROVIDER_TEMPLATES.find(p => p.id === chatProvider)?.models.length ? (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {PROVIDER_TEMPLATES.find(p => p.id === chatProvider)?.models.map(m => (
                          <button
                            key={m}
                            onClick={() => setChatModel(m)}
                            className={`px-3 py-1 text-xs rounded-full transition-colors ${
                              chatModel === m
                                ? 'bg-indigo-100 text-indigo-700'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                          >
                            {m}
                          </button>
                        ))}
                      </div>
                    ) : null}
                    {/* 显示当前选中模型的能力 */}
                    {(() => {
                      const template = PROVIDER_TEMPLATES.find(p => p.id === chatProvider);
                      const caps = template?.modelCapabilities?.[chatModel] || [];
                      if (caps.length === 0) return null;
                      return (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {caps.map((cap: string) => (
                            <span key={cap} className="px-2 py-0.5 text-[10px] rounded-md bg-green-50 text-green-700 border border-green-200">
                              {CAPABILITY_LABELS[cap] || cap}
                            </span>
                          ))}
                        </div>
                      );
                    })()}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Temperature: {chatTemperature}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={chatTemperature}
                      onChange={(e) => setChatTemperature(parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-400 mt-1">
                      <span>精确</span>
                      <span>创意</span>
                    </div>
                  </div>
                  
                  {/* Embedding 模型说明 */}
                  <div className="p-4 bg-gray-50 rounded-xl text-sm text-gray-600">
                    <p className="font-medium mb-1">📌 向量模型</p>
                    <p>Embedding 模型使用本地 <code className="bg-gray-100 px-1 rounded">bge-base-zh-v1.5</code>，无需配置 API Key。</p>
                  </div>
                </div>
              )}

              {/* 平台接入配置 */}
              {activeTab === 'platform' && (
                <div className="space-y-5">
                  {/* 已配置的平台 */}
                  {platformApps.length > 0 && (
                    <div className="space-y-3">
                      {platformApps.map(app => (
                        <div key={app.platform} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                          <div className="flex items-center gap-3">
                            <span className="text-xl">{PLATFORMS.find(p => p.id === app.platform)?.icon}</span>
                            <div>
                              <div className="font-medium text-gray-700">
                                {PLATFORMS.find(p => p.id === app.platform)?.name}
                              </div>
                              <div className="text-xs text-gray-400">App ID: {app.app_id}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full">已配置</span>
                            <button
                              onClick={() => deletePlatformApp(app.platform).then(loadPlatformApps)}
                              className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 添加新平台 */}
                  {showAddPlatform ? (
                    <div className="space-y-4 p-4 border border-dashed border-gray-300 rounded-xl">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">平台</label>
                        <select
                          value={newPlatform.type}
                          onChange={(e) => setNewPlatform(prev => ({ ...prev, type: e.target.value }))}
                          className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl"
                        >
                          {PLATFORMS.map(p => (
                            <option key={p.id} value={p.id}>{p.icon} {p.name}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">App ID</label>
                        <input
                          type="text"
                          value={newPlatform.appId}
                          onChange={(e) => setNewPlatform(prev => ({ ...prev, appId: e.target.value }))}
                          placeholder="cli_xxx"
                          className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">App Secret</label>
                        <input
                          type="password"
                          value={newPlatform.appSecret}
                          onChange={(e) => setNewPlatform(prev => ({ ...prev, appSecret: e.target.value }))}
                          placeholder="xxx"
                          className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl"
                        />
                      </div>

                      {newPlatform.type === 'feishu' && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Encrypt Key (可选)</label>
                          <input
                            type="password"
                            value={newPlatform.encryptKey}
                            onChange={(e) => setNewPlatform(prev => ({ ...prev, encryptKey: e.target.value }))}
                            className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl"
                          />
                        </div>
                      )}

                      <div className="flex gap-2">
                        <button
                          onClick={handleAddPlatformApp}
                          className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 font-medium"
                        >
                          保存
                        </button>
                        <button
                          onClick={() => setShowAddPlatform(false)}
                          className="flex-1 py-2.5 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 font-medium"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowAddPlatform(true)}
                      className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-indigo-400 hover:text-indigo-600 transition-colors flex items-center justify-center gap-2"
                    >
                      <Plus size={18} />
                      添加平台应用
                    </button>
                  )}

                  {/* 飞书配置说明 */}
                  <div className="p-4 bg-green-50 rounded-xl text-sm text-green-800">
                    <p className="font-medium mb-2">📋 飞书长连接模式（无需公网地址）：</p>
                    <ol className="list-decimal list-inside space-y-1 text-green-700">
                      <li>在飞书开放平台创建企业自建应用</li>
                      <li>获取 App ID 和 App Secret，填入上方表单</li>
                      <li>在「事件与回调」切换为「使用长连接接收事件」</li>
                      <li>添加事件订阅：<code className="bg-green-100 px-1 rounded">im.message.receive_v1</code></li>
                      <li>配置权限：<code className="bg-green-100 px-1 rounded">im:message</code>, <code className="bg-green-100 px-1 rounded">im:message:send_as_bot</code></li>
                      <li>重启服务后自动建立连接</li>
                    </ol>
                    <p className="mt-2 text-green-600 text-xs">
                      ✅ 长连接模式无需公网地址、无需内网穿透、无需配置加密策略
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-5 border-t border-gray-100 bg-gray-50">
          <button
            onClick={onClose}
            className="px-5 py-2.5 text-gray-700 hover:bg-gray-100 rounded-xl font-medium transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 font-medium transition-colors"
          >
            保存设置
          </button>
        </div>
      </div>
    </div>
  );
}

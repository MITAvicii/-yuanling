/**
 * API 工具函数
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '';

export async function fetchAPI<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return response.json();
}

// Chat API
export async function sendMessage(
  message: string,
  sessionId?: string,
  onChunk?: (chunk: any) => void,
  ragEnabled?: boolean
): Promise<void> {
  const url = `${API_BASE}/api/chat`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      stream: true,
      rag_enabled: ragEnabled,
    }),
  });
  
  if (!response.ok) {
    throw new Error(`Chat Error: ${response.status}`);
  }
  
  const reader = response.body?.getReader();
  if (!reader) return;
  
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const text = decoder.decode(value);
    const lines = text.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          onChunk?.(data);
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
  }
}

// Session API
export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export async function getSessions(): Promise<Session[]> {
  return fetchAPI<Session[]>('/api/sessions');
}

export async function createSession(title: string = '新会话'): Promise<Session> {
  return fetchAPI<Session>('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetchAPI(`/api/sessions/${sessionId}`, { method: 'DELETE' });
}

// 获取会话详情（包含消息历史）
export async function getSession(sessionId: string): Promise<Session & { messages: Array<{ type: string; content: string; tool_calls?: any[] }> }> {
  return fetchAPI(`/api/sessions/${sessionId}`);
}

// Files API
export async function getFile(path: string): Promise<{ path: string; content: string }> {
  return fetchAPI(`/api/files?path=${encodeURIComponent(path)}`);
}

export async function saveFile(path: string, content: string): Promise<void> {
  await fetchAPI('/api/files', {
    method: 'POST',
    body: JSON.stringify({ path, content }),
  });
}





// Config API
export interface ConfigResponse {
  chat_provider: string;
  chat_model: string;
  temperature: number;
  rag_enabled: boolean;
  providers: Record<string, { base_url: string; models: string[] }>;
  provider_api_keys?: Record<string, string>;
  provider_models?: Record<string, string>;
}

export interface PlatformApp {
  platform: string;
  app_id: string;
  enabled: boolean;
}

export interface SetConfigRequest {
  chat_provider?: string;
  chat_model?: string;
  temperature?: number;
  provider_api_keys?: Record<string, string>;
  custom_models?: Record<string, string[]>;
  provider_models?: Record<string, string>;
}

export async function getConfig(): Promise<ConfigResponse> {
  return fetchAPI<ConfigResponse>('/api/config');
}

export async function setConfig(config: SetConfigRequest): Promise<void> {
  await fetchAPI('/api/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

export async function getRAGMode(): Promise<{ enabled: boolean }> {
  return fetchAPI('/api/config/rag-mode');
}

export async function setRAGMode(enabled: boolean): Promise<void> {
  await fetchAPI(`/api/config/rag-mode?enabled=${enabled}`, {
    method: 'PUT',
  });
}

export async function getProviders(): Promise<{ providers: any[] }> {
  return fetchAPI('/api/config/providers');
}

// Platform Apps API
export async function getPlatformApps(): Promise<PlatformApp[]> {
  try {
    const result = await fetchAPI<{ apps: PlatformApp[] }>('/api/config/platforms');
    return result.apps || [];
  } catch {
    return [];
  }
}

export async function addPlatformApp(app: {
  platform: string;
  app_id: string;
  app_secret: string;
  encrypt_key?: string;
  verification_token?: string;
}): Promise<void> {
  await fetchAPI('/api/config/platforms', {
    method: 'POST',
    body: JSON.stringify(app),
  });
}

export async function deletePlatformApp(platform: string): Promise<void> {
  await fetchAPI(`/api/config/platforms/${platform}`, {
    method: 'DELETE',
  });
}

// Token API
export async function getSessionTokens(sessionId: string): Promise<any> {
  return fetchAPI(`/api/tokens/session/${sessionId}`);
}

// Knowledge API


export interface KnowledgeFile {
  name: string;
  path: string;
  size: number;
  size_str: string;
  updated_at: string;
  extension: string;
}

export interface KnowledgeStats {
  file_count: number;
  total_size: number;
  total_size_str: string;
  index_exists: boolean;
  index_updated_at: string | null;
}

export interface SearchResult {
  text: string;
  score: number;
  source: string;
  rerank_score?: number;
}

export async function getKnowledgeFiles(): Promise<KnowledgeFile[]> {
  return fetchAPI<KnowledgeFile[]>('/api/knowledge');
}

export async function getKnowledgeStats(): Promise<KnowledgeStats> {
  return fetchAPI<KnowledgeStats>('/api/knowledge/stats');
}

export async function uploadKnowledgeFile(file: File): Promise<{ message: string; filename: string; size: number }> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE}/api/knowledge/upload`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }
  
  return response.json();
}

export async function deleteKnowledgeFile(filename: string): Promise<void> {
  await fetchAPI(`/api/knowledge/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });
}

export async function rebuildKnowledgeIndex(): Promise<{ message: string }> {
  return fetchAPI<{ message: string }>('/api/knowledge/rebuild', {
    method: 'POST',
  });
}

export async function searchKnowledge(query: string, topK: number = 5): Promise<{ query: string; count: number; results: SearchResult[] }> {
  return fetchAPI('/api/knowledge/search', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  });
}

export async function getKnowledgeContent(filename: string): Promise<{ filename: string; content: string; path: string }> {
  return fetchAPI(`/api/knowledge/content/${encodeURIComponent(filename)}`);
}

export async function updateKnowledgeContent(filename: string, content: string): Promise<{ message: string }> {
  const formData = new FormData();
  formData.append('content', content);
  
  const response = await fetch(`${API_BASE}/api/knowledge/content/${encodeURIComponent(filename)}`, {
    method: 'PUT',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Update failed');
  }
  
  return response.json();
}

// Skills API
export interface Skill {
  name: string;
  cn_name: string;
  category: string;
  tags: string[];
  description: string;
  location: string;
  version: string;
  author: string;
}

export interface SkillsResponse {
  categories: string[];
  skills_by_category: Record<string, Skill[]>;
  skills: Skill[];
}

export async function getSkills(): Promise<SkillsResponse> {
  return fetchAPI<SkillsResponse>('/api/files/skills');
}

export async function getSkillContent(skillName: string): Promise<{ name: string; content: string; path: string }> {
  return fetchAPI(`/api/files/skills/${encodeURIComponent(skillName)}`);
}



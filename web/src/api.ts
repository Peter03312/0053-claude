import type { ProjectInfo, SolveResult, Spec, VersionInfo } from './types'

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public details: string[],
  ) {
    super(details.join('；'))
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(BASE + path, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    throw new ApiError(0, 'network', ['无法连接 API 服务，请确认后端已启动'])
  }
  const text = await resp.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      throw new ApiError(resp.status, 'bad_response', [`服务器返回了非 JSON 内容（HTTP ${resp.status}）`])
    }
  }
  if (!resp.ok) {
    const e = (body as { error?: { code?: string; message?: string; details?: string[] } })?.error
    throw new ApiError(
      resp.status,
      e?.code ?? `http_${resp.status}`,
      e?.details ?? [e?.message ?? `请求失败（HTTP ${resp.status}）`],
    )
  }
  return body as T
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  solve: (spec: Spec) =>
    request<SolveResult>('/api/solve', { method: 'POST', body: JSON.stringify({ spec }) }),
  listProjects: () => request<{ projects: ProjectInfo[] }>('/api/projects'),
  createProject: (name: string, spec: Spec) =>
    request<{ id: number; version: number }>('/api/projects', {
      method: 'POST',
      body: JSON.stringify({ name, spec }),
    }),
  getProject: (id: number) =>
    request<{ id: number; name: string; version: number; spec: Spec }>(`/api/projects/${id}`),
  putProject: (id: number, name: string, spec: Spec) =>
    request<{ id: number; version: number }>(`/api/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name, spec }),
    }),
  listVersions: (id: number) => request<{ versions: VersionInfo[] }>(`/api/projects/${id}/versions`),
  getVersion: (id: number, version: number) =>
    request<{ id: number; version: number; spec: Spec }>(`/api/projects/${id}/versions/${version}`),
}

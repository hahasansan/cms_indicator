export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json; charset=utf-8', ...(options.headers ?? {}) },
      body: options.body,
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    throw new Error(`无法连接后端服务（8800）：${message}`)
  }

  const bodyText = await res.text()
  let data: Record<string, unknown> = {}
  if (bodyText) {
    try {
      data = JSON.parse(bodyText) as Record<string, unknown>
    } catch {
      throw new Error(`后端返回了无效响应（HTTP ${res.status}）`)
    }
  }
  if (!res.ok) throw new Error(String(data.detail || data.error || `请求失败（HTTP ${res.status}）`))
  return data as T
}

export function jsonBody(data: unknown): string {
  return JSON.stringify(data)
}

/** 下载文件（POST），从 Content-Disposition 解析文件名并触发浏览器保存。 */
export async function apiDownload(path: string, options: RequestInit = {}): Promise<void> {
  let res: Response
  try {
    res = await fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json; charset=utf-8', ...(options.headers ?? {}) },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    throw new Error(`无法连接后端服务（8800）：${message}`)
  }
  if (!res.ok) {
    let msg = `请求失败（HTTP ${res.status}）`
    try {
      const data = (await res.json()) as Record<string, unknown>
      msg = String(data.detail || data.error || msg)
    } catch { /* 非 JSON 错误体，保留默认信息 */ }
    throw new Error(msg)
  }
  const blob = await res.blob()
  const disposition = res.headers.get('Content-Disposition') || ''
  const match = /filename="?([^";]+)"?/i.exec(disposition)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = match?.[1] || 'export.json'
  a.click()
  URL.revokeObjectURL(url)
}

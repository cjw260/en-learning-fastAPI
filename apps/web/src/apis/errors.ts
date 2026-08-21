import axios from 'axios'

interface FailureEnvelope {
  message?: unknown
}

export const apiErrorMessage = (error: unknown, fallback = '服务器异常，请稍后再试') => {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error && error.message ? error.message : fallback
  }
  if (error.code === 'ERR_NETWORK') return '网络连接失败，请重试'
  if (error.code === 'ECONNABORTED') return '请求超时，请稍后重试'
  const data = error.response?.data as FailureEnvelope | string | undefined
  if (typeof data === 'string' && data.trim()) return data
  if (data && typeof data === 'object' && typeof data.message === 'string') {
    return data.message
  }
  return fallback
}

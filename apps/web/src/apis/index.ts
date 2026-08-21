import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { useUserStore } from '@/stores/user'
import { expireSession, refreshAccessToken } from './session'

export const uploadUrl = import.meta.env.VITE_MINIO_ENDPOINT
export const socketUrl = import.meta.env.VITE_SOCKET_URL
export const timeout = 50000

interface SessionRequestConfig extends InternalAxiosRequestConfig {
  _sessionRetry?: boolean
}

const attachAccessToken = (config: InternalAxiosRequestConfig) => {
  const accessToken = useUserStore().getAccessToken
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
}

const attachSessionInterceptors = (instance: AxiosInstance) => {
  instance.interceptors.request.use(attachAccessToken)
  instance.interceptors.response.use(
    (response) => response.data,
    async (error: AxiosError) => {
      const request = error.config as SessionRequestConfig | undefined
      const status = error.response?.status
      const hadAuthorization = Boolean(request?.headers?.Authorization)

      if (status !== 401 || !request || !hadAuthorization) {
        return Promise.reject(error)
      }
      if (request._sessionRetry) {
        expireSession()
        return Promise.reject(error)
      }

      request._sessionRetry = true
      try {
        const accessToken = await refreshAccessToken()
        request.headers.Authorization = `Bearer ${accessToken}`
        return instance(request)
      } catch (refreshError) {
        return Promise.reject(refreshError)
      }
    },
  )
}

export const serverApi = axios.create({
  baseURL: '/api/v1',
  timeout,
})

export const aiApi = axios.create({
  baseURL: '/ai/v1',
  timeout,
})

attachSessionInterceptors(serverApi)
attachSessionInterceptors(aiApi)

export interface Response<T = unknown> {
  timestamp: string
  path: string
  message: string
  code: number
  success: boolean
  data: T
}

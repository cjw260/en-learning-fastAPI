import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'
import { createRefreshCoordinator, SessionExpiredError } from '@/auth/session'
import { refreshTokenApi } from './auth'

let expiryNoticeVisible = false

const clearExpiredSession = () => {
  const userStore = useUserStore()
  userStore.logout()
  if (!expiryNoticeVisible) {
    expiryNoticeVisible = true
    ElMessage.error('登录已过期，请重新登录')
    void router.replace('/')
    window.setTimeout(() => {
      expiryNoticeVisible = false
    }, 1000)
  }
}

const coordinator = createRefreshCoordinator({
  getRefreshToken: () => useUserStore().getRefreshToken,
  requestRefresh: async (refreshToken) => {
    const response = await refreshTokenApi({ refreshToken })
    if (!response.success) throw new SessionExpiredError()
    return response.data
  },
  applyTokens: (tokens) => {
    expiryNoticeVisible = false
    useUserStore().updateToken(tokens)
  },
  clearSession: clearExpiredSession,
})

export const refreshAccessToken = coordinator.refreshAccessToken
export const expireSession = coordinator.clear

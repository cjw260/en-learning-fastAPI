export interface SessionTokenPair {
  accessToken: string
  refreshToken: string
}

interface RefreshCoordinatorOptions {
  getRefreshToken: () => string | undefined
  requestRefresh: (refreshToken: string) => Promise<SessionTokenPair>
  applyTokens: (tokens: SessionTokenPair) => void
  clearSession: () => void
}

export class SessionExpiredError extends Error {
  constructor(message = '登录已过期，请重新登录') {
    super(message)
    this.name = 'SessionExpiredError'
  }
}

export interface RefreshCoordinator {
  refreshAccessToken: () => Promise<string>
  clear: () => void
}

/**
 * Shares exactly one refresh operation across every HTTP/SSE caller. Each caller
 * replays its own request after this promise resolves; one failure rejects every
 * waiter and clears the local session once, so no queued promise can hang.
 */
export const createRefreshCoordinator = (
  options: RefreshCoordinatorOptions,
): RefreshCoordinator => {
  let refreshPromise: Promise<string> | null = null

  const clear = () => {
    refreshPromise = null
    options.clearSession()
  }

  const refreshAccessToken = (): Promise<string> => {
    if (refreshPromise) return refreshPromise

    const refreshToken = options.getRefreshToken()
    if (!refreshToken) {
      clear()
      return Promise.reject(new SessionExpiredError())
    }

    const executeRefresh = async () => {
      try {
        const tokens = await options.requestRefresh(refreshToken)
        if (!tokens.accessToken || !tokens.refreshToken) {
          throw new SessionExpiredError()
        }
        options.applyTokens(tokens)
        return tokens.accessToken
      } catch (error) {
        options.clearSession()
        if (error instanceof SessionExpiredError) throw error
        throw new SessionExpiredError()
      } finally {
        if (refreshPromise === currentRefresh) refreshPromise = null
      }
    }

    const currentRefresh = Promise.resolve().then(executeRefresh)

    refreshPromise = currentRefresh
    return currentRefresh
  }

  return { refreshAccessToken, clear }
}

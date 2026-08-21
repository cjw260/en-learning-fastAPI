export interface EventSourceMessageLike {
  data: string
}

export interface EventSourceRequestLike {
  method: string
  headers: Record<string, string>
  body: string
  signal: AbortSignal
  openWhenHidden: boolean
  onopen: (response: globalThis.Response) => Promise<void>
  onmessage: (event: EventSourceMessageLike) => void
  onclose: () => void
  onerror: (error: unknown) => never
}

export type EventSourceFetcher = (
  url: string,
  request: EventSourceRequestLike,
) => Promise<void>

export class StreamHttpError extends Error {
  readonly status: number

  constructor(status: number) {
    super(`流式请求失败（${status}）`)
    this.name = 'StreamHttpError'
    this.status = status
  }
}

export class StreamTimeoutError extends Error {
  readonly kind: 'first-event' | 'total'

  constructor(kind: 'first-event' | 'total') {
    super(kind === 'first-event' ? '等待回复超时，请重试' : '回复时间过长，请重试')
    this.name = 'StreamTimeoutError'
    this.kind = kind
  }
}

export interface JsonEventStreamOptions<TMessage, TBody> {
  url: string
  method: string
  body: TBody
  fetchEventSource: EventSourceFetcher
  getAccessToken: () => string | undefined
  refreshAccessToken: () => Promise<string>
  onMessage: (message: TMessage) => void
  firstEventTimeoutMs?: number
  totalTimeoutMs?: number
}

export interface EventStreamHandle {
  abort: () => void
  done: Promise<void>
}

/**
 * Starts one JSON SSE request. It may retry exactly once after a pre-stream 401
 * and a successful shared token refresh. Network/upstream errors after any data
 * frame are terminal, preventing duplicated assistant output.
 */
export const startJsonEventStream = <TMessage, TBody>(
  options: JsonEventStreamOptions<TMessage, TBody>,
): EventStreamHandle => {
  const controller = new AbortController()
  let cancelled = false
  let timeoutKind: StreamTimeoutError['kind'] | null = null
  let receivedFrame = false

  const abort = () => {
    cancelled = true
    controller.abort()
  }

  const done = (async () => {
    const totalTimer = globalThis.setTimeout(() => {
      timeoutKind = 'total'
      controller.abort()
    }, options.totalTimeoutMs ?? 130_000)

    try {
      for (let attempt = 0; attempt < 2; attempt += 1) {
        const attemptController = new AbortController()
        const relayAbort = () => attemptController.abort()
        controller.signal.addEventListener('abort', relayAbort, { once: true })
        let firstEventTimer = globalThis.setTimeout(() => {
          timeoutKind = 'first-event'
          attemptController.abort()
        }, options.firstEventTimeoutMs ?? 35_000)

        try {
          const accessToken = options.getAccessToken()
          await options.fetchEventSource(options.url, {
            method: options.method.toLowerCase(),
            headers: {
              'Content-Type': 'application/json',
              ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
            },
            body: JSON.stringify(options.body),
            signal: attemptController.signal,
            openWhenHidden: true,
            onopen: async (response) => {
              if (response.status === 401) throw new StreamHttpError(401)
              if (!response.ok) throw new StreamHttpError(response.status)
            },
            onmessage: (event) => {
              if (!event.data) return
              globalThis.clearTimeout(firstEventTimer)
              receivedFrame = true
              options.onMessage(JSON.parse(event.data) as TMessage)
            },
            onclose: () => {
              globalThis.clearTimeout(firstEventTimer)
            },
            onerror: (error) => {
              throw error
            },
          })

          if (timeoutKind) throw new StreamTimeoutError(timeoutKind)
          if (cancelled) return
          return
        } catch (error) {
          if (cancelled) return
          if (timeoutKind) throw new StreamTimeoutError(timeoutKind)
          if (
            error instanceof StreamHttpError &&
            error.status === 401 &&
            attempt === 0 &&
            !receivedFrame
          ) {
            await options.refreshAccessToken()
            continue
          }
          throw error
        } finally {
          globalThis.clearTimeout(firstEventTimer)
          controller.signal.removeEventListener('abort', relayAbort)
        }
      }
    } finally {
      globalThis.clearTimeout(totalTimer)
    }
  })()

  return { abort, done }
}

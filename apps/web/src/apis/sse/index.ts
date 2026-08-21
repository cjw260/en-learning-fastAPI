import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { Method } from 'axios'
import { useUserStore } from '@/stores/user'
import { refreshAccessToken } from '@/apis/session'
import { startJsonEventStream, type EventStreamHandle } from './stream'

export const CHAT_URL = '/ai/v1/chat'

export const sse = <T, V = unknown>(
  url: string,
  method: Method = 'POST',
  body: V,
  callback?: (data: T) => void,
): EventStreamHandle =>
  startJsonEventStream<T, V>({
    url,
    method,
    body,
    fetchEventSource,
    getAccessToken: () => useUserStore().getAccessToken,
    refreshAccessToken,
    onMessage: (message) => callback?.(message),
  })

export { StreamHttpError, StreamTimeoutError } from './stream'

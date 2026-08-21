import assert from 'node:assert/strict'
import test from 'node:test'
import {
  startJsonEventStream,
  StreamTimeoutError,
  type EventSourceFetcher,
} from '../src/apis/sse/stream.ts'

test('a pre-stream 401 refreshes once and emits each frame once', async () => {
  let token = 'expired-access'
  let attempts = 0
  let refreshes = 0
  const authorization: Array<string | undefined> = []
  const messages: Array<{ content: string }> = []
  const fetcher: EventSourceFetcher = async (_url, request) => {
    attempts += 1
    authorization.push(request.headers.Authorization)
    if (attempts === 1) {
      await request.onopen(new Response(null, { status: 401 }))
      return
    }
    await request.onopen(new Response(null, { status: 200 }))
    request.onmessage({ data: JSON.stringify({ content: 'only-once' }) })
    request.onclose()
  }

  const stream = startJsonEventStream({
    url: '/ai/v1/chat',
    method: 'POST',
    body: { content: 'hello' },
    fetchEventSource: fetcher,
    getAccessToken: () => token,
    refreshAccessToken: async () => {
      refreshes += 1
      token = 'fresh-access'
      return token
    },
    onMessage: (message: { content: string }) => messages.push(message),
    firstEventTimeoutMs: 100,
    totalTimeoutMs: 500,
  })
  await stream.done

  assert.equal(attempts, 2)
  assert.equal(refreshes, 1)
  assert.deepEqual(authorization, ['Bearer expired-access', 'Bearer fresh-access'])
  assert.deepEqual(messages, [{ content: 'only-once' }])
})

test('a failure after the first frame is terminal and never duplicates output', async () => {
  let attempts = 0
  const messages: string[] = []
  const fetcher: EventSourceFetcher = async (_url, request) => {
    attempts += 1
    await request.onopen(new Response(null, { status: 200 }))
    request.onmessage({ data: JSON.stringify({ content: 'partial' }) })
    throw new Error('upstream disconnected')
  }
  const stream = startJsonEventStream({
    url: '/ai/v1/chat',
    method: 'POST',
    body: {},
    fetchEventSource: fetcher,
    getAccessToken: () => 'access',
    refreshAccessToken: async () => 'unused',
    onMessage: (message: { content: string }) => messages.push(message.content),
    firstEventTimeoutMs: 100,
    totalTimeoutMs: 500,
  })

  await assert.rejects(stream.done, /upstream disconnected/)
  assert.equal(attempts, 1)
  assert.deepEqual(messages, ['partial'])
})

test('first-event timeout aborts the transport and reports a bounded error', async () => {
  const fetcher: EventSourceFetcher = async (_url, request) =>
    new Promise<void>((resolve) => {
      request.signal.addEventListener('abort', () => resolve(), { once: true })
    })
  const stream = startJsonEventStream({
    url: '/ai/v1/chat',
    method: 'POST',
    body: {},
    fetchEventSource: fetcher,
    getAccessToken: () => 'access',
    refreshAccessToken: async () => 'unused',
    onMessage: () => undefined,
    firstEventTimeoutMs: 5,
    totalTimeoutMs: 100,
  })

  await assert.rejects(
    stream.done,
    (error: unknown) => error instanceof StreamTimeoutError && error.kind === 'first-event',
  )
})

test('caller cancellation aborts the transport without surfacing an error', async () => {
  let transportAborted = false
  const fetcher: EventSourceFetcher = async (_url, request) =>
    new Promise<void>((resolve) => {
      request.signal.addEventListener(
        'abort',
        () => {
          transportAborted = true
          resolve()
        },
        { once: true },
      )
    })
  const stream = startJsonEventStream({
    url: '/ai/v1/chat',
    method: 'POST',
    body: {},
    fetchEventSource: fetcher,
    getAccessToken: () => 'access',
    refreshAccessToken: async () => 'unused',
    onMessage: () => assert.fail('a cancelled stream must not emit data'),
    firstEventTimeoutMs: 100,
    totalTimeoutMs: 500,
  })

  stream.abort()
  await stream.done
  assert.equal(transportAborted, true)
})

test('total timeout terminates a stream that stalls after its first frame', async () => {
  const messages: string[] = []
  const fetcher: EventSourceFetcher = async (_url, request) => {
    await request.onopen(new Response(null, { status: 200 }))
    request.onmessage({ data: JSON.stringify({ content: 'partial' }) })
    await new Promise<void>((resolve) => {
      request.signal.addEventListener('abort', () => resolve(), { once: true })
    })
  }
  const stream = startJsonEventStream({
    url: '/ai/v1/chat',
    method: 'POST',
    body: {},
    fetchEventSource: fetcher,
    getAccessToken: () => 'access',
    refreshAccessToken: async () => 'unused',
    onMessage: (message: { content: string }) => messages.push(message.content),
    firstEventTimeoutMs: 100,
    totalTimeoutMs: 5,
  })

  await assert.rejects(
    stream.done,
    (error: unknown) => error instanceof StreamTimeoutError && error.kind === 'total',
  )
  assert.deepEqual(messages, ['partial'])
})

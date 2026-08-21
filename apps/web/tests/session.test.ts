import assert from 'node:assert/strict'
import test from 'node:test'
import { createRefreshCoordinator, SessionExpiredError } from '../src/auth/session.ts'

test('concurrent callers share one refresh and all receive the new access token', async () => {
  let releaseRefresh: ((value: { accessToken: string; refreshToken: string }) => void) | null = null
  let refreshCalls = 0
  let applied = 0
  let cleared = 0
  const coordinator = createRefreshCoordinator({
    getRefreshToken: () => 'refresh-1',
    requestRefresh: () => {
      refreshCalls += 1
      return new Promise((resolve) => {
        releaseRefresh = resolve
      })
    },
    applyTokens: () => {
      applied += 1
    },
    clearSession: () => {
      cleared += 1
    },
  })

  const waiters = [
    coordinator.refreshAccessToken(),
    coordinator.refreshAccessToken(),
    coordinator.refreshAccessToken(),
  ]
  await Promise.resolve()
  assert.equal(refreshCalls, 1)
  assert.ok(releaseRefresh)
  releaseRefresh({ accessToken: 'access-2', refreshToken: 'refresh-2' })

  assert.deepEqual(await Promise.all(waiters), ['access-2', 'access-2', 'access-2'])
  assert.equal(applied, 1)
  assert.equal(cleared, 0)
})

test('one failed refresh rejects every waiter and clears the session once', async () => {
  let refreshCalls = 0
  let cleared = 0
  const coordinator = createRefreshCoordinator({
    getRefreshToken: () => 'expired-refresh',
    requestRefresh: async () => {
      refreshCalls += 1
      await Promise.resolve()
      throw new Error('401')
    },
    applyTokens: () => assert.fail('failed refresh must not apply tokens'),
    clearSession: () => {
      cleared += 1
    },
  })

  const results = await Promise.allSettled([
    coordinator.refreshAccessToken(),
    coordinator.refreshAccessToken(),
    coordinator.refreshAccessToken(),
  ])

  assert.equal(refreshCalls, 1)
  assert.equal(cleared, 1)
  assert.ok(results.every((result) => result.status === 'rejected'))
  for (const result of results) {
    if (result.status === 'rejected') assert.ok(result.reason instanceof SessionExpiredError)
  }
})

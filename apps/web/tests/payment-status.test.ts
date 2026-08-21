import assert from 'node:assert/strict'
import test from 'node:test'
import { PaymentStatusPoller, paymentOrderNumber } from '../src/payments/status.ts'

test('payment order uses the additive field and supports legacy Alipay URL fallback', () => {
  assert.equal(
    paymentOrderNumber({ payUrl: 'https://pay.invalid', timeExpire: 1, outTradeNo: 'ORDER-1' }),
    'ORDER-1',
  )
  const businessContent = encodeURIComponent(JSON.stringify({ out_trade_no: 'LEGACY-2' }))
  assert.equal(
    paymentOrderNumber({
      payUrl: `https://pay.invalid/gateway?biz_content=${businessContent}`,
      timeExpire: 1,
    }),
    'LEGACY-2',
  )
  assert.equal(paymentOrderNumber({ payUrl: 'not a url', timeExpire: 1 }), null)
})

test('concurrent status checks share one request and publish success once', async () => {
  let fetchCalls = 0
  let purchasedEvents = 0
  let resolveStatus: ((value: {
    outTradeNo: string
    tradeStatus: string
    isPurchased: boolean
  }) => void) | null = null
  const poller = new PaymentStatusPoller(
    () => {
      fetchCalls += 1
      return new Promise((resolve) => {
        resolveStatus = resolve
      })
    },
    () => {
      purchasedEvents += 1
    },
  )

  const first = poller.check()
  const second = poller.check()
  assert.equal(first, second)
  assert.equal(fetchCalls, 1)
  assert.ok(resolveStatus)
  resolveStatus({ outTradeNo: 'ORDER', tradeStatus: 'TRADE_SUCCESS', isPurchased: true })
  await Promise.all([first, second])
  assert.equal(purchasedEvents, 1)

  const next = poller.check()
  assert.equal(fetchCalls, 2)
  assert.ok(resolveStatus)
  resolveStatus({ outTradeNo: 'ORDER', tradeStatus: 'TRADE_FINISHED', isPurchased: true })
  await next
  assert.equal(purchasedEvents, 1)
})

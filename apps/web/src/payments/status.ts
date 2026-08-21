import type { PaymentStatus, ResultPay } from '@en/common/pay'

export const paymentOrderNumber = (result: ResultPay): string | null => {
  if (result.outTradeNo) return result.outTradeNo
  try {
    const paymentUrl = new URL(result.payUrl)
    const rawBusinessContent = paymentUrl.searchParams.get('biz_content')
    if (!rawBusinessContent) return null
    const businessContent = JSON.parse(rawBusinessContent) as { out_trade_no?: unknown }
    return typeof businessContent.out_trade_no === 'string' && businessContent.out_trade_no
      ? businessContent.out_trade_no
      : null
  } catch {
    return null
  }
}

export class PaymentStatusPoller {
  private interval: ReturnType<typeof setInterval> | null = null
  private checking: Promise<PaymentStatus> | null = null
  private completed = false
  private readonly fetchStatus: () => Promise<PaymentStatus>
  private readonly onPurchased: (status: PaymentStatus) => void

  constructor(
    fetchStatus: () => Promise<PaymentStatus>,
    onPurchased: (status: PaymentStatus) => void,
  ) {
    this.fetchStatus = fetchStatus
    this.onPurchased = onPurchased
  }

  check(): Promise<PaymentStatus> {
    if (this.checking) return this.checking
    const request = this.fetchStatus()
      .then((status) => {
        if (status.isPurchased && !this.completed) {
          this.completed = true
          this.stop()
          this.onPurchased(status)
        }
        return status
      })
      .finally(() => {
        if (this.checking === request) this.checking = null
      })
    this.checking = request
    return request
  }

  start(intervalMs: number, onError: (error: unknown) => void): void {
    this.stop()
    void this.check().catch(onError)
    this.interval = globalThis.setInterval(() => {
      void this.check().catch(onError)
    }, intervalMs)
  }

  stop(): void {
    if (this.interval) globalThis.clearInterval(this.interval)
    this.interval = null
  }
}

import { reportEvent } from '@/event';
import { getFingerprint } from '@/uv';
import type { TrackerConfig } from '@en/common/tracker';
import { reportError } from '@/error';
import { reportPv } from '@/pv';
import { reportPerformance } from '@/performance';
import { reportFetch } from '@/report';

export class Tracker {
    private config: TrackerConfig
    private visitorId: string | null = null
    private initPromise: Promise<void> | null = null
    constructor(config: TrackerConfig) {
        this.config = config
        void this.init().catch(() => undefined)
    }
    //protected 运行子类和自身调用
    protected async init() {
        if (this.initPromise) {
            return this.initPromise
        }
        const operation = (async () => {
            let config = this.config 
            const visitorId = await getFingerprint(config)
            this.visitorId = visitorId
            reportEvent(visitorId, config)//上报事件
            reportError(visitorId, config)
            reportPv(visitorId, config)
            reportPerformance(visitorId, config)
        })()
        this.initPromise = operation
        try {
            await operation
        } catch (error) {
            if (this.initPromise === operation) this.initPromise = null
            throw error
        }
    }

    async setUserId(userId: string, accessToken: string) {
        await this.init()
        if (!this.visitorId) throw new Error('Tracker visitor is unavailable')
        let url = this.config.baseUrl + this.config.uv.updateApi
        await reportFetch(url, {
            visitorId: this.visitorId,
            userId
        }, accessToken)
    }
}

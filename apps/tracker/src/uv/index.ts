import { reportFetch } from "@/report";
import type { TrackerConfig, UvDto } from "@en/common/tracker";
import FingerprintJs from "@fingerprintjs/fingerprintjs";
import { UAParser } from "ua-parser-js"


export const getBrowserInfo = () => {
    const ua = new UAParser()
    return {
        browser: ua.getBrowser().name || 'unknown',
        os: ua.getOS().name || 'unknown',
        device: ua.getDevice().type || 'desktop'
    }
}

export const getFingerprint = async (config: TrackerConfig) => {
    const browserInfo = getBrowserInfo()
    const fp = await FingerprintJs.load()
    const result = await fp.get()
    const body: UvDto = {
        anonymousId: result.visitorId,
        browser: browserInfo.browser,
        os: browserInfo.os,
        device: browserInfo.device
    }
    //上报给后端
    let url = config.baseUrl + config.uv.api
    const res = await reportFetch(url, body)
    return res.data
}

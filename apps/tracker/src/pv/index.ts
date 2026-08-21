import { report } from "@/report";
import type { PvDto, TrackerConfig } from "@en/common/tracker";

const reportView = (visitorId: string,config: TrackerConfig) => {
    let url = config.baseUrl + config.pv.api

    const isHash = window.location.href.includes('#')
    const body: PvDto = {
        visitorId,
        url: window.location.protocol + '//' + window.location.host,
        referrer: document.referrer,
        path:isHash ? '/' +  window.location.hash : window.location.pathname,
    }
    report(url, body)
}

export const reportPv = (visitorId: string,config: TrackerConfig) => {
    reportView(visitorId,config)
    window.addEventListener("hashchange", (e) => {
        reportView(visitorId,config)
    })

    window.addEventListener("popstate", (e) => {
        reportView(visitorId,config)

    })
    const originalPushState = history.pushState;//获取原生的pushState方法
    history.pushState = function (data: unknown, unused: string, url?: string | URL | null) {
        originalPushState.call(this, data, unused, url);//执行原生的pushState方法
        reportView(visitorId,config)

    }
    const originalReplaceState = history.replaceState;//获取原生的replaceState方法
    history.replaceState = function (data: unknown, unused: string, url?: string | URL | null) {
        originalReplaceState.call(this, data, unused, url);//执行原生的replaceState方法
        reportView(visitorId,config)
    }
}

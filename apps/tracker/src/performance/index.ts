import { report } from "@/report";
import type { PerformanceDto, TrackerConfig } from "@en/common/tracker";
import {onINP, onCLS, onLCP} from 'web-vitals'

export const reportPerformance = (visitorId: string,config: TrackerConfig) => {
    let url = config.baseUrl + config.performance.api
    let fp = 0 //首次绘制
    let fcp = 0//首次内容绘制
    let lcp = 0//最大内容绘制
    let cls = 0//累积布局偏移
    let inp = 0//输入延迟
    //FP和FCP
    let perFormanceEntries = performance.getEntriesByType("paint");
    const fpEntry = perFormanceEntries.find((item) => item.name === "first-paint");
    const fcpEntry = perFormanceEntries.find((item) => item.name === "first-contentful-paint");
    if (fpEntry) {
        fp = fpEntry.startTime;
    }
    if (fcpEntry) {
        fcp = fcpEntry.startTime;
    }
    onLCP((metric) => {
        lcp = metric.value
    })
    //INP
    onINP((metric) => {
        inp = metric.value
    })
    //CLS
    onCLS((metric) => {
        cls = metric.value
    })
    window.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
            const body: PerformanceDto = {
                visitorId,
                fp,
                fcp,
                lcp,
                cls,
                inp
            }
            report(url, body)
        }
    },{once: true})
}

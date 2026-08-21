import type { ErrorDto, TrackerConfig } from "@en/common/tracker";
import { report } from "@/report";

export const reportError = (visitorId: string,config: TrackerConfig) => {
    //捕获全局js错误
    let url = config.baseUrl + config.error.api
    window.addEventListener('error', (e: ErrorEvent) => {
        const body: ErrorDto = {
            visitorId,//访问者id
            message: e.message,//错误信息
            stack: e.error.stack,//错误堆栈
            url: e.filename,//错误文件
            error: 'js'//js错误
        }
        report(url, body)
    })
    //捕获promise错误
    window.addEventListener('unhandledrejection', (e: PromiseRejectionEvent) => {
        const isError = e.reason instanceof Error
        const body: ErrorDto = {
            visitorId,//访问者id
            message: isError ? e.reason.message : JSON.stringify(e.reason),//错误信息
            stack: isError ? (e.reason.stack || e.reason.message) : 'Promise Rejection',//错误堆栈
            url: window.location.href,//错误地址
            error: 'promise'//promise错误
        }
        report(url, body)
    })
}

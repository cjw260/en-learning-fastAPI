import { fetchEventSource } from '@microsoft/fetch-event-source';
import type { Method } from 'axios';
import { useUserStore } from '@/stores/user';
export const CHAT_URL = '/ai/v1/chat'

export const sse = <T,V = any>(url:string,method:Method = 'POST',body:V,callback?:(data:T)=>void,errorCallback?:(error:Error)=>void) => {
    const accessToken = useUserStore().getAccessToken
    fetchEventSource(url,{
        method: method.toLowerCase(),
        headers:{
            'Content-Type': 'application/json',
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify(body),
        onmessage:(event)=>{
            callback?.(JSON.parse(event.data) as T)
        },
        onerror:(error)=>{
            errorCallback?.(error)
        }
    })
}

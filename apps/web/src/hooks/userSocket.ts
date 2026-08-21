import {io, type Socket} from 'socket.io-client';
import { socketUrl } from '@/apis';
import { useUserStore } from '@/stores/user';
let socket: Socket | null = null;
export const useSocket = () => {
    const userStore = useUserStore()
    //连接socket
    const connect = () => {
        const userId = userStore.user?.id
        const accessToken = userStore.getAccessToken
        if (!userId || !accessToken) return
        if (socket) return//如果已经连接了，则不再连接
        socket = io(socketUrl, {
            transports: ['websocket'],//使用websocket协议
            autoConnect: true,//自动连接
            reconnection: true,//断开后自动重连
            reconnectionAttempts: 5,//重连次数
            reconnectionDelay: 1000,//重连间隔
            reconnectionDelayMax: 5000,//重连间隔最大值
            query: {
                userId
            },
            auth: {
                token: accessToken
            }
        })
        //为了treeeshaking，将socket保存到import.meta.hot.data中, 在生产环境中，socket会被treeeshaking掉
        if(import.meta.hot){
            import.meta.hot.data.socket = socket
        }
    }

    //断开连接
    const disconnect = () => {
        if (socket) {
            socket.disconnect()
            socket.removeAllListeners()
            socket = null
            if(import.meta.hot){
                import.meta.hot.data.socket = null
            }
        }
    }
    //获取socket
    const getSocket = (): Socket | null => {
        if (socket) {
            return socket
        }
        if(import.meta.hot){
            return import.meta.hot.data.socket
        }
        return null
    }
    return {
        connect,
        disconnect,
        getSocket
    }
}

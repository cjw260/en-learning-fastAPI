import { io, type Socket } from 'socket.io-client'
import { socketUrl } from '@/apis'
import { useUserStore } from '@/stores/user'

interface SocketHotData {
  socket?: Socket | null
  accessToken?: string | null
}

const hotData = import.meta.hot?.data as SocketHotData | undefined
let socket: Socket | null = hotData?.socket ?? null
let activeAccessToken: string | null = hotData?.accessToken ?? null

const saveHotState = () => {
  if (!import.meta.hot) return
  const data = import.meta.hot.data as SocketHotData
  data.socket = socket
  data.accessToken = activeAccessToken
}

export const useSocket = () => {
  const userStore = useUserStore()

  const disconnect = () => {
    if (socket) {
      socket.disconnect()
      socket.removeAllListeners()
      socket = null
    }
    activeAccessToken = null
    saveHotState()
  }

  const connect = () => {
    const accessToken = userStore.getAccessToken
    if (!userStore.user?.id || !accessToken) {
      disconnect()
      return
    }

    if (!socket) {
      socket = io(socketUrl, {
        transports: ['websocket'],
        autoConnect: false,
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        auth: { token: accessToken },
        // The old NestJS rollback target only understands this query. FastAPI
        // treats it as a compatibility hint and rejects it unless it matches
        // the authenticated JWT identity.
        query: { userId: userStore.user.id },
      })
      activeAccessToken = accessToken
      saveHotState()
      socket.connect()
      return
    }

    if (activeAccessToken !== accessToken) {
      activeAccessToken = accessToken
      socket.auth = { token: accessToken }
      socket.disconnect().connect()
    } else if (!socket.connected) {
      socket.connect()
    }
    saveHotState()
  }

  const getSocket = (): Socket | null => socket

  return { connect, disconnect, getSocket }
}

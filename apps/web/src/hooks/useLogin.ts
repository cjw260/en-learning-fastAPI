import { IS_SHOW_LOGIN } from '@/components/Login/type'
import { inject,ref } from 'vue'
import { useUserStore } from '@/stores/user'
import router from '@/router'
export const useLogin = () => {
    const isShowLogin = inject(IS_SHOW_LOGIN, ref(false))
    const userStore = useUserStore()
    
    const login = (): Promise<boolean> => {
        if(userStore.getUser) return Promise.resolve(true)
        isShowLogin.value = true
        return Promise.resolve(false)
    }
    const hide = () => {
        isShowLogin.value = false
    }
    const logout = () => {
        // 清除用户信息
        userStore.logout()
        router.push('/')
    }
    return {
        login,
        hide,
        logout
    }
}

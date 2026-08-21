<template>
  <section class="w-80 overflow-hidden rounded-[14px] bg-linear-to-b from-white/95 to-slate-50/95 backdrop-blur"
    aria-label="用户资料卡">
    <div class="flex items-center gap-3 px-4 pb-3 pt-3.5">
      <div class="grid size-11 shrink-0 place-items-center rounded-full border border-gray-200">
        <img class="size-10 rounded-full object-cover" :src="avatar" loading="lazy" />
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex min-w-0 items-center gap-2">
          <div class="flex flex-col gap-1">
            <div class="truncate text-sm font-extrabold leading-5 text-slate-900" :title="displayName">
              {{ displayName }}
            </div>
            <div v-if="bio" class="truncate text-xs leading-4 text-slate-500/90" :title="bio">
              {{ bio }}
            </div>
          </div>
        </div>
        <div v-if="!isLoggedIn" class="mt-1 text-xs leading-4 text-slate-500/90">
          登录后可同步词库进度与打卡数据
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-2.5 px-4 pb-3 pt-2" v-if="isLoggedIn">
      <div class="rounded-xl border border-slate-900/5 bg-white/65 px-2.5 py-2.5">
        <div class="text-xs leading-4 text-slate-500/95">单词数量</div>
        <div class="mt-1 text-lg font-black leading-[22px] text-slate-900">
          {{ userStore?.getUser?.wordNumber ?? 0 }}
        </div>
      </div>
      <div class="rounded-xl border border-amber-500/20 bg-amber-50/90 px-2.5 py-2.5">
        <div class="text-xs leading-4 text-slate-500/95">打卡天数</div>
        <div class="mt-1 text-lg font-black leading-[22px] text-slate-900">
          {{ userStore?.getUser?.dayNumber ?? 0 }}
        </div>
      </div>
    </div>

    <div class="flex gap-2.5 border-t border-slate-900/5 bg-white/75 px-4 pb-3.5 pt-3">
      <button v-if="!isLoggedIn"
        class="h-9 flex-1 cursor-pointer rounded-[10px] border border-blue-600/25 bg-blue-600/10 text-[13px] font-extrabold text-blue-700 transition duration-150 hover:-translate-y-0.5 hover:shadow-[0_10px_16px_rgba(15,23,42,0.10)] active:translate-y-0 active:shadow-none motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:hover:shadow-none"
        type="button" @click="loginHandle">
        去登录
      </button>
      <template v-else>
        <button
          class="h-9 flex-1 cursor-pointer rounded-[10px] border border-slate-900/10 bg-white/90 text-[13px] font-extrabold text-slate-900/90 transition duration-150 hover:-translate-y-0.5 hover:shadow-[0_10px_16px_rgba(15,23,42,0.10)] active:translate-y-0 active:shadow-none motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:hover:shadow-none"
          type="button" @click="gotoPath('/setting/index')">
          个人资料
        </button>
        <button
          class="h-9 flex-1 cursor-pointer rounded-[10px] border border-red-500/20 bg-red-500/10 text-[13px] font-extrabold text-red-700 transition duration-150 hover:-translate-y-0.5 hover:shadow-[0_10px_16px_rgba(15,23,42,0.10)] active:translate-y-0 active:shadow-none motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:hover:shadow-none"
          type="button" @click="logoutHandle">
          退出登录
        </button>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAvatar } from '@/hooks/useAvatar'
import { useLogin } from '@/hooks/useLogin'
import { ElMessageBox } from 'element-plus'
const { login, logout } = useLogin()
const { avatar } = useAvatar()
const router = useRouter()
const userStore = useUserStore()
const isLoggedIn = computed(() => !!userStore.getUser)//是否登录
const displayName = computed(() => userStore.getUser?.name ?? '游客')//用户名
const bio = computed(() => userStore.getUser?.bio ?? '')//用户简介
//跳转页面
const gotoPath = (path: string) => {
  router.push(path)
}
//去登录
const loginHandle = () => {
  void login()
}
//退出登录
const logoutHandle = () => {
  ElMessageBox.confirm('确定退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      logout()
    })
}
</script>

<template>
    <div class="p-5 rounded-[5px] w-[256px] bg-purple-50 border border-right-1 border-t-0 border-b-0 border-l-0 border-gray-200">
        <el-skeleton v-if="loading" :rows="5" animated />
        <el-alert v-else-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />
        <div @click="changeActive(value)" :class="{'bg-purple-300': active === value.id}" class="rounded-[5px] p-2 transition-all duration-300" v-for="value in chatMode" :key="value.id">
            <div class="text-sm  cursor-pointer p-2 px-4 text-gray-700">
                {{ value.label }}
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import type { ChatMode, ChatModeList } from '@en/common/chat';
import { ref, onMounted } from 'vue'
import { getChatMode } from '@/apis/chat';
import { apiErrorMessage } from '@/apis/errors';
const emits = defineEmits(['onGetRole'])
const chatMode = ref<ChatModeList>([])//消息模式列表
const active = ref<string | null>(null)//当前激活的id
const loading = ref(false)
const errorMessage = ref('')
    //切换消息模式
const changeActive = (value:ChatMode) => {
    active.value = value.id
    emits('onGetRole', value.role)//派发role
}
const getChatModeList = async () => {
    loading.value = true
    errorMessage.value = ''
    try {
        const res = await getChatMode()
        chatMode.value = res.data
        const firstMode = res.data[0]
        if (firstMode) {
            active.value = firstMode.id
            emits('onGetRole', firstMode.role)
        }
    } catch (error) {
        errorMessage.value = apiErrorMessage(error, '聊天模式加载失败')
    } finally {
        loading.value = false
    }
}
onMounted(() => {
    getChatModeList()
})
</script>

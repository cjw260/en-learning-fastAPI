<template>
    <div class="w-[1200px] mx-auto flex mt-10">
        <Conversations @onGetRole="getRole" />
        <Bubble
            :list="list"
            :history-loading="historyLoading"
            :is-streaming="isStreaming"
            :status-message="statusMessage"
            @onSendMessage="sendMessage"
            @onCancel="cancelStream"
        />
    </div>
</template>
<script setup lang="ts">
import Conversations from './components/Conversations.vue';
import Bubble from './components/Bubble.vue';
import { useUserStore } from '@/stores/user';
import { onBeforeUnmount, ref } from 'vue';
import { getChatHistory } from '@/apis/chat';
import type { ChatDto, ChatMessage, ChatMessageList, ChatRoleType } from '@en/common/chat';
import { sse, CHAT_URL } from '@/apis/sse';
import type { EventStreamHandle } from '@/apis/sse/stream';
import { apiErrorMessage } from '@/apis/errors';
const role = ref<ChatRoleType>('normal')//存储角色
const userStore = useUserStore()
const list = ref<ChatMessageList>([])
const historyLoading = ref(false)
const isStreaming = ref(false)
const statusMessage = ref('')
let activeStream: EventStreamHandle | null = null

const cancelStream = () => {
    if (!activeStream) return
    const stream = activeStream
    activeStream = null
    stream.abort()
    isStreaming.value = false
    statusMessage.value = '已停止生成'
}

const getRole = async (params: ChatRoleType) => {
    cancelStream()
    role.value = params
    const userId = userStore.user?.id
    if (!userId) return
    historyLoading.value = true
    statusMessage.value = ''
    try {
        const res = await getChatHistory(userId, params)//获取历史记录
        list.value = res.data//存储历史记录
    } catch (error) {
        list.value = []
        statusMessage.value = apiErrorMessage(error, '聊天历史加载失败')
    } finally {
        historyLoading.value = false
    }
}
const sendMessage = (message: string,deepThink: boolean,webSearch: boolean) => {
    const userId = userStore.user?.id
    if (!userId || activeStream) return
    statusMessage.value = ''
    list.value.push({role: 'human', content: message, type: 'chat'})//添加用户的信息
    const assistantMessage: ChatMessage = {role: 'ai', content: '', reasoning:'',type: 'chat'}
    list.value.push(assistantMessage)//添加ai的信息
    isStreaming.value = true
    const stream = sse<ChatMessage, ChatDto>(CHAT_URL, "POST", {role: role.value, content: message, userId,deepThink,webSearch},//发送请求
        (data) => {
            if(data.type === 'reasoning'){
                assistantMessage.reasoning = (assistantMessage.reasoning || '') + data.content
            }
            if(data.type === 'chat'){
                assistantMessage.content += data.content
            }
        },
    )
    activeStream = stream
    void stream.done
        .catch((error) => {
            if (activeStream !== stream) return
            statusMessage.value = apiErrorMessage(error, 'AI 回复失败，请重试')
            if (!assistantMessage.content && !assistantMessage.reasoning) {
                list.value = list.value.filter((item) => item !== assistantMessage)
            }
        })
        .finally(() => {
            if (activeStream !== stream) return
            activeStream = null
            isStreaming.value = false
        })
}

onBeforeUnmount(cancelStream)
</script>

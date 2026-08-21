<template>
    <div class="flex-1 h-[750px] p-5 bg-purple-50 flex flex-col">
        <div class="flex-1 overflow-y-auto">
            <el-skeleton v-if="historyLoading" :rows="6" animated />
            <el-empty v-else-if="list?.length === 0" description="暂无聊天记录，开始一段新对话吧" />
            <div v-for="(item, index) in list" :key="index">
                <div class="flex justify-end items-center  gap-4 mt-5 mb-5 mr-5" v-if="item.role === 'human'">
                    <div class="text-sm text-white max-w-[80%] rounded-lg p-2 bg-blue-500 shadow-md">
                        {{ item.content }}
                    </div>
                    <div>
                        <el-avatar :size="35">user</el-avatar>
                    </div>
                </div>
                <div class="flex justify-start items-center gap-4 mt-5 mb-5" v-else>
                    <div> <el-avatar :size="35">AI</el-avatar></div>
                    <div>
                        <span v-if="item.role === 'ai' && isStreaming && index === (list?.length ?? 0) - 1 && !item.reasoning && !item.content"
                            class="text-xs text-zinc-400">AI 正在思考…</span>
                        <div v-if="item.role === 'ai' && item.reasoning" class="text-[12px] text-gray-500 max-w-[80%] p-2">
                            {{ item.reasoning }}
                        </div>
                        <div v-if="item.role === 'ai' && item.content !== ''"
                            class="text-sm text-gray-700 max-w-[80%] bg-white rounded-lg mt-2 deepseek-markdown"
                            v-html="parseMarkdown(item.content)" />
                    </div>
                </div>
            </div>
            <div ref="chatRef"></div>
        </div>
        <div class="flex p-5 border-t border-gray-200 box-border flex-col gap-3">
            <!-- 功能选项 -->
            <div class="flex items-center gap-3">
                <div class="flex items-center gap-1 px-3 py-1 rounded-full text-xs cursor-pointer transition-all border"
                    :class="deepThink
                        ? 'bg-purple-100 border-purple-400 text-purple-700'
                        : 'bg-gray-100 border-gray-200 text-gray-500 hover:bg-gray-200'"
                    @click="deepThink = !deepThink">
                    <span>🧠</span>
                    <span>深度思考</span>
                </div>
                <div class="flex items-center gap-1 px-3 py-1 rounded-full text-xs cursor-pointer transition-all border"
                    :class="webSearch
                        ? 'bg-blue-100 border-blue-400 text-blue-700'
                        : 'bg-gray-100 border-gray-200 text-gray-500 hover:bg-gray-200'"
                    @click="webSearch = !webSearch">
                    <span>🌐</span>
                    <span>联网搜索</span>
                </div>
            </div>
            <el-alert v-if="statusMessage" class="mb-3" :title="statusMessage" type="warning" show-icon :closable="false" />
            <!-- 输入框 -->
            <div class="flex">
                <el-input @keyup.enter="sendMessage" type="textarea" :rows="2" v-model="message" placeholder="请输入内容" :disabled="isStreaming" />
                <el-button v-if="!isStreaming" class="ml-2" :icon="Position" type="primary" @click="sendMessage" aria-label="发送消息"></el-button>
                <el-button v-else class="ml-2" type="danger" plain @click="emits('onCancel')">停止</el-button>
                <el-button v-if="!isRecording" class="ml-2" :icon="Mic" type="primary" @click="startRecording"></el-button>
                <el-button v-else class="ml-2" :icon="VideoPause" type="primary" @click="stopRecording"></el-button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef, watch, nextTick } from 'vue'
import { Position, Mic, VideoPause} from '@element-plus/icons-vue'
import type { ChatMessageList } from '@en/common/chat'
import { marked } from 'marked'
import '@/assets/css/deep-seek.css'
import { useVoiceToText } from '@/hooks/useVoiceToText'
const deepThink = ref(false)//深度思考
const webSearch = ref(false)//网络搜索
const emits = defineEmits(['onSendMessage', 'onCancel'])
const chatRef = useTemplateRef<HTMLDivElement>('chatRef')
const props = defineProps<{
    list?: ChatMessageList
    historyLoading?: boolean
    isStreaming?: boolean
    statusMessage?: string
}>()//消息列表
const message = ref<string>('')
const { isRecording, start, stop } = useVoiceToText({
    lang: 'zh-CN',
    continuous: true,
})
//发送消息
const sendMessage = () => {
    if (!message.value.trim() || props.isStreaming) return
    emits('onSendMessage', message.value, deepThink.value, webSearch.value)
    message.value = ''
}
//解析markdown
const parseMarkdown = (content: string) => {
    if (!content) return ''
    return marked.parse(content)
}
//开始录音
const startRecording = () => {
    start((result) => {
        message.value = result
    })
}
 //停止录音
const stopRecording = () => {
    stop()
   sendMessage()
}
watch(() => props.list, () => {
    nextTick(() => {
        chatRef.value?.scrollIntoView({ behavior: 'smooth' })
    })
}, {
    immediate: true,
    deep: true
})

</script>

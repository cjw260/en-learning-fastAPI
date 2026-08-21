<template>
    <div class="min-h-[60vh] bg-zinc-50/80">
        <div class="w-[1200px] mx-auto px-4 pt-12 pb-24">
            <header class="mb-10 text-center">
                <h1 class="text-3xl font-bold text-zinc-900 tracking-tight sm:text-4xl">{{ title }}</h1>
                <p class="mt-3 text-zinc-500 text-sm">请根据释义和翻译拼写单词</p>
            </header>

            <el-skeleton v-if="isLoading" :rows="10" animated />
            <el-alert v-else-if="errorMessage" class="mb-6" :title="errorMessage" type="error" show-icon :closable="false" />

            <div v-if="!isLoading && !errorMessage && list.length === 0" class="flex justify-center py-20">
                <el-empty description="暂无单词或您尚未购买该课程" />
            </div>

            <template v-else>
                <!-- 本组已学完 -->
                <div v-if="currentIndex >= list.length"
                    class="text-center py-16 px-6 bg-white rounded-2xl border border-zinc-100 shadow-sm">
                    <p class="text-zinc-600 mb-6">本组 10 个词已学完</p>
                    <el-button type="primary" size="large" @click="saveWordMaster">
                        再练一组
                    </el-button>
                </div>

                <!-- 当前单词卡片 -->
                <div v-else>
                    <div class="mb-4 flex items-center justify-between text-sm text-zinc-500">
                        <span>第 {{ currentIndex + 1 }} / {{ list.length }} 个</span>
                    </div>
                    <article class="bg-white rounded-2xl border border-zinc-100 shadow-sm overflow-hidden">
                        <div class="p-8 sm:p-10 relative">
                            <div class="flex justify-center mb-6">
                                <div :class="{ 'filter blur-md select-none': isWordBlurred }"
                                    class="transition-all duration-300 min-h-10 flex flex-col items-center text-center">
                                    <div class="text-2xl sm:text-3xl font-bold text-indigo-600 tracking-tight">
                                        {{ currentWord?.word }}
                                    </div>
                                    <div class="flex items-center justify-center gap-2 mt-1">
                                        <span v-if="currentWord?.phonetic" class="text-base text-zinc-500 font-mono">
                                            {{ currentWord.phonetic }}
                                        </span>
                                        <el-icon v-if="currentWord?.word"
                                            class="shrink-0 cursor-pointer text-slate-400 hover:text-indigo-400 transition-colors"
                                            :size="18" title="发音" @click="playAudio(currentWord!.word)">
                                            <VideoPlay />
                                        </el-icon>
                                    </div>
                                </div>
                                <el-icon
                                    class="absolute! right-10 top-10 cursor-pointer text-slate-400 hover:text-indigo-400 transition-colors"
                                    :size="18" :title="isWordBlurred ? '点击显示单词' : '点击隐藏单词'"
                                    @click="isWordBlurred = !isWordBlurred">
                                    <View v-if="isWordBlurred" />
                                    <Hide v-else />
                                </el-icon>
                            </div>
                            <!-- 释义 -->
                            <div class="mb-4 rounded-lg bg-zinc-50/80 border border-zinc-100 p-4">
                                <p class="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">释义</p>
                                <div class="text-zinc-700 leading-relaxed prose prose-sm max-w-none"
                                    v-html="currentWord?.definition" />
                            </div>
                            <!-- 翻译 -->
                            <div class="rounded-lg bg-zinc-50/80 border border-zinc-100 p-4">
                                <p class="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">翻译</p>
                                <div class="text-zinc-600 leading-relaxed whitespace-pre-line prose prose-sm max-w-none"
                                    v-html="currentWord?.translation" />
                            </div>
                            <!--拼写练习-->
                            <div class="rounded-lg bg-zinc-50/80 border border-zinc-100 p-4">
                                <p class="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">拼写</p>
                                <div class="flex items-center gap-2 justify-center">
                                    <input :maxlength="1" ref="inputRefs" @input="onInput(index)" v-for="(item, index) in wordList"
                                        @keydown="onKeyDown(index, $event)" :key="index" type="text" v-model="item.input"
                                        :class="{ 'border-indigo-500!': item.isTrue === true, 'border-red-500!': item.isTrue === false }"
                                        class="border-0 border-b-2 border-zinc-300 focus:border-indigo-500 bg-transparent outline-none w-10 text-center text-2xl font-bold" />
                                </div>
                            </div>
                            <!--控制按钮-->
                            <div class="flex justify-end gap-2">
                                <el-button type="primary" @click="pagePrev">
                                    上一个
                                </el-button>
                                <el-button type="primary" @click="pageNext">
                                    下一个
                                </el-button>
                            </div>
                        </div>
                    </article>
                </div>
            </template>
        </div>
    </div>
</template>

<script setup lang="ts">
import { useAudio } from '@/hooks/useAudio';
import type { Word } from '@en/common/word';
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from 'vue';
import { useRoute } from 'vue-router';
import { VideoPlay, View, Hide } from '@element-plus/icons-vue';
import { getWordList, saveWordMaster as saveWordMasterApi } from '@/apis/learn';
import { ElMessage } from 'element-plus';
import { useUserStore } from '@/stores/user';
import { apiErrorMessage } from '@/apis/errors';
interface WordItem {
    word: string;
    input: string;
    isTrue: boolean | undefined;
}

const inputRefs = useTemplateRef<HTMLInputElement[]>('inputRefs')
const {playAudio} = useAudio({})//发音的api
const route = useRoute();
const title = route.params.title || '我的课程';
const isLoading = ref(false);//默认不加载
const errorMessage = ref('')
const list = ref<Word[]>([]);//单词列表
const currentIndex = ref(0);//当前索引
const isWordBlurred = ref(true);//是否隐藏单词
const currentWord = computed<Word | undefined>(() => list.value[currentIndex.value]);//当前单词
const wordList = ref<WordItem[]>([]);//拼写列表
const userStore =  useUserStore()
watch(currentWord, () => {
    isWordBlurred.value = true;
    const current = currentWord.value?.word || '';//读取当前单词
     wordList.value =  Array.from(current).map((item) => {
        return {
            word:item,
            input:'',
            isTrue:undefined
        }
    })
}, { immediate: true })


//上一个
const pagePrev = () => {
    if(currentIndex.value <= 0)return
    currentIndex.value--
}

//下一个
const pageNext = () => {
    if(wordList.value.some(item => !item.isTrue)){
        ElMessage.warning('请完成当前单词的拼写')
        return
    }
    currentIndex.value++
}

//保存的方法
const saveWordMaster = async () => {
    //找到单词所有的id并且是一个数组
    const wordIds = list.value.map((item) => item.id);
    try {
        const res = await saveWordMasterApi(wordIds);
        currentIndex.value = 0;
        void getWordListData();
        userStore.updateUserWordNumber(res.data.wordNumber)
        ElMessage.success(res.message)
    } catch (error) {
        ElMessage.error(apiErrorMessage(error, '学习进度保存失败'))
    }
}

//输入的方法
const onInput = (index: number) => {
    const current = wordList.value[index];
    current!.isTrue = current!.word === current!.input;
    nextTick(() => {
        const inputs = inputRefs.value as HTMLInputElement[];
        if(index < inputs.length - 1){//不是最后一个
            inputs[index + 1]!.focus()//下一个输入框获取焦点
        }
    })
}

//按键的方法
const onKeyDown = (index: number, event: KeyboardEvent) => {
    if(event.key === 'Backspace'){
        event.preventDefault();
        const current = wordList.value[index];
        current!.input = ''
        current!.isTrue = undefined;
        nextTick(() => {
            const inputs = inputRefs.value as HTMLInputElement[];
            if(index > 0){//不是第一个
                inputs[index - 1]!.focus()//上一个输入框获取焦点
            }
        })
    }
    if(event.key.length == 1 && !event.ctrlKey && !event.metaKey && !event.altKey){
        const current = wordList.value[index];
        if(current?.input && index < wordList.value.length - 1){
            event.preventDefault();
            wordList.value[index + 1]!.input = event.key;
            wordList.value[index + 1]!.isTrue = wordList.value[index + 1]!.word === event.key;
            nextTick(() => {
                const inputs = inputRefs.value as HTMLInputElement[];
                inputs[index + 1]!.focus()//下一个输入框获取焦点
            })
        }
    }
}

const getWordListData = async () => {
    isLoading.value = true;
    errorMessage.value = ''
    try {
        const res = await getWordList(route.params.courseId as string);
        list.value = res.data
    } catch (error) {
        list.value = []
        errorMessage.value = apiErrorMessage(error, '课程单词加载失败')
    } finally {
        isLoading.value = false;
    }
}
onMounted(() => {
    getWordListData();
})
</script>

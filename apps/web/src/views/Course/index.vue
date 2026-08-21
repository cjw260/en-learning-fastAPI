<template>
    <div class="min-h-[60vh] bg-zinc-50/80">
        <div class="w-[1200px] mx-auto px-4 pt-12 pb-24">
            <!-- 标题 -->
            <header class="mb-12 text-center">
                <p class="text-sm font-medium text-indigo-600 tracking-wide uppercase mb-2">Vocabulary Courses</p>
                <h1 class="text-3xl font-bold text-zinc-900 tracking-tight sm:text-4xl">精选课程</h1>
                <p class="mt-3 text-zinc-500 text-sm max-w-md mx-auto">一次购买，长期有效 · 覆盖高考、考研、四六级、托福雅思等</p>
            </header>
            <el-tabs type="card" v-model="currentTab" @tab-change="getList">
                <el-tab-pane name="list" label="精选课程"></el-tab-pane>
                <el-tab-pane v-if="userStore.user?.id" name="my" label="我的课程"></el-tab-pane>

            </el-tabs>
            <el-skeleton v-if="isLoading" :rows="8" animated />
            <el-alert v-else-if="errorMessage" class="mb-6" :title="errorMessage" type="error" show-icon :closable="false" />
            <!-- 课程卡片 3 列 -->
            <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                <article v-for="item in list" :key="item.id"
                    class="group bg-white rounded-2xl overflow-hidden border border-zinc-100 shadow-sm hover:shadow-lg hover:shadow-indigo-500/5 hover:border-indigo-100 transition-all duration-300 flex flex-col">
                    <div class="relative aspect-4/3 bg-zinc-100 overflow-hidden">
                        <img :src="imageSrc(item.url)" :alt="item.name"
                            loading="lazy" decoding="async"
                            class="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out" />
                        <div
                            class="absolute top-3 left-3 px-2.5 py-1 rounded-lg bg-white/90 backdrop-blur text-xs font-medium text-zinc-600 shadow-sm">
                            词汇</div>
                    </div>
                    <div class="p-5 flex-1 flex flex-col">
                        <h2 class="text-base font-semibold text-zinc-900 line-clamp-1">{{ item.name }}</h2>
                        <p class="mt-2 text-sm text-zinc-500 line-clamp-2 leading-relaxed flex-1">{{ item.description }}
                        </p>
                        <div class="mt-4 pt-4 border-t border-zinc-100 flex items-center justify-between gap-3">
                            <span class="text-xs text-zinc-400 truncate">讲师 {{ item.teacher }}</span>
                            <span class="text-lg font-bold text-indigo-600 shrink-0">¥{{ item.price }}</span>
                        </div>
                        <button type="button" @click="openPay(item)"
                            class="mt-4 w-full py-2.5 rounded-xl text-sm font-medium text-indigo-600 border border-indigo-200 bg-white hover:bg-indigo-50 transition-colors cursor-pointer">
                            {{ currentTab === 'list' ? '购买课程' : '学习课程'}}
                        </button>
                    </div>
                </article>
            </div>
            <el-empty v-if="!isLoading && !errorMessage && list.length === 0" description="暂无课程"></el-empty>
        </div>
        <CoursePay v-model="payVisible" :course="selectedCourse" @confirmed="onPaymentConfirmed"></CoursePay>
    </div>
</template>
<script setup lang="ts">
import { uploadUrl } from '@/apis';
import { getCourseList, getMyCourse } from '@/apis/course';
import type { Course, CourseList } from '@en/common/course';
import { onMounted, ref } from 'vue';
import CoursePay from './components/Pay.vue';
import { useLogin } from '@/hooks/useLogin';
import { useUserStore } from '@/stores/user';
import router from '@/router';
import { apiErrorMessage } from '@/apis/errors';

const currentTab = ref('list')
const { login } = useLogin()
const payVisible = ref(false)//控制弹框显示隐藏
const selectedCourse = ref<Course | null>(null)//选中的课程
const list = ref<CourseList>([]) 
const isLoading = ref(false)
const errorMessage = ref('')
const userStore =  useUserStore()
const getList = async () => {
    isLoading.value = true
    errorMessage.value = ''
    try {
        if(currentTab.value === 'list') {
            const res = await getCourseList()
            list.value = res.data
        }
        else{
            const res = await getMyCourse()
            list.value = res.data
        }
    } catch (error) {
        list.value = []
        errorMessage.value = apiErrorMessage(error, '课程加载失败')
    } finally {
        isLoading.value = false
    }
}
//打开支付弹窗
const openPay = async (course: Course) => {
    const authenticated = await login()
    if (!authenticated) return
    if(currentTab.value === 'list'){
        payVisible.value = true
        selectedCourse.value = course
    }else{
        router.push(`/courses/learn/${course.id}/${course.name}`)
    }
}
const imageSrc = (url: string) => { 
    return uploadUrl + url
}
const onPaymentConfirmed = async () => {
    currentTab.value = 'my'
    await getList()
}
onMounted(() => {
    getList()
})
</script>

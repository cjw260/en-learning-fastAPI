<template>
    <Teleport to="body">
        <Transition name="pay-fade">
            <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center p-4">
                <!-- 遮罩 -->
                <div class="absolute inset-0 bg-zinc-900/50 backdrop-blur-sm" aria-hidden="true" />

                <!-- 弹框 -->
                <div class="relative w-full max-w-md rounded-2xl bg-white shadow-xl shadow-indigo-500/10 border border-zinc-100 overflow-hidden"
                    role="dialog" aria-modal="true" aria-labelledby="pay-dialog-title">
                    <!-- 标题 -->
                    <div class="px-6 pt-6 pb-4 border-b border-zinc-100">
                        <h2 id="pay-dialog-title" class="text-lg font-semibold text-zinc-900">确认支付</h2>
                        <p class="mt-1 text-sm text-zinc-500">请核对课程信息后完成支付</p>
                    </div>
                    <!-- 课程信息（有 course 时展示） -->
                    <div v-if="course" class="p-6 space-y-4">
                        <div class="flex gap-4 rounded-xl bg-zinc-50/80 p-4">
                            <div class="w-20 h-20 shrink-0 rounded-lg overflow-hidden bg-zinc-200">
                                <img :src="imageSrc(course.url)" :alt="course.name"
                                    loading="lazy" decoding="async"
                                    class="w-full h-full object-cover" />
                            </div>
                            <div class="min-w-0 flex-1">
                                <h3 class="text-sm font-medium text-zinc-900 line-clamp-2">{{ course.name }}</h3>
                                <p class="mt-1 text-xs text-zinc-500">讲师 {{ course.teacher }}</p>
                            </div>
                        </div>
                        <div
                            class="flex items-center justify-between rounded-xl border border-zinc-100 bg-indigo-50/50 px-4 py-3">
                            <span class="text-sm text-zinc-600">支付金额</span>
                            <span class="text-xl font-bold text-indigo-600">¥{{ course.price }}</span>
                        </div>
                        <!-- 支付剩余时间倒计时（创建订单后显示） -->
                        <div v-if="timeExpire > 0"
                            class="flex flex-col items-center rounded-xl border border-amber-100 bg-amber-50/50 px-4 py-3">
                            <el-countdown title="支付剩余时间" format="HH:mm:ss" :value="timeExpire" @finish="tips" />
                        </div>
                        <el-alert v-if="statusMessage" :title="statusMessage" type="info" show-icon :closable="false" />
                    </div>

                    <!-- 无数据时的占位 -->
                    <div v-else class="p-6 text-center text-sm text-zinc-400">
                        暂无课程信息
                    </div>

                    <!-- 底部按钮 -->
                    <div class="flex gap-3 px-6 pb-6 pt-2">
                        <button type="button"
                            class="flex-1 py-2.5 rounded-xl text-sm font-medium text-zinc-600 border border-zinc-200 bg-white hover:bg-zinc-50 transition-colors"
                            @click="close">
                            取消
                        </button>
                        <button type="button"
                            class="flex-1 py-2.5 rounded-xl text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                            :disabled="isCreating || isChecking" @click="isPay ? verifyPayment('manual') : onConfirm()">
                            {{ isCreating ? '创建订单中...' : isPay ? (isChecking ? '查询中...' : '刷新支付状态') : '确认支付' }}
                        </button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>


<script setup lang="ts">
import { uploadUrl } from '@/apis';
import type { Course } from '@en/common/course';
import { ElMessage } from 'element-plus';
import { onBeforeUnmount, ref, watch } from 'vue';
import type {CreatePayDto} from '@en/common/pay';
const { getSocket } =  useSocket();
import {createPay, getPaymentStatus} from '@/apis/pay';
import { useSocket } from '@/hooks/userSocket';
import { apiErrorMessage } from '@/apis/errors';
import { PaymentStatusPoller, paymentOrderNumber } from '@/payments/status';
import { useUserStore } from '@/stores/user';
const modelValue = defineModel<boolean>('modelValue',{required: true});
const emits = defineEmits<{ confirmed: [] }>()
const props = defineProps<{
    course: Course | null,
}>()
const isPay = ref(false);//是否支付中
const isCreating = ref(false)
const isChecking = ref(false)
const timeExpire = ref(0);//支付剩余时间
const statusMessage = ref('')
const userStore = useUserStore()
let statusPoller: PaymentStatusPoller | null = null
let confirmed = false

const stopConfirmation = () => {
    statusPoller?.stop()
    statusPoller = null
}

const finishPayment = () => {
    if (confirmed) return
    confirmed = true
    ElMessage.success({
        message: '支付成功',
        duration: 1000,
    })
    emits('confirmed')
    close()
}

const responseStatus = (error: unknown) =>
    (error as { response?: { status?: number } })?.response?.status

const onPollingError = (error: unknown) => {
    if (responseStatus(error) === 404) {
        statusMessage.value = '当前后端不支持主动查询，将等待支付通知'
        return
    }
    statusMessage.value = `${apiErrorMessage(error, '暂时无法确认支付结果')}，将自动重试`
}

const verifyPayment = async (source: 'manual' | 'socket' | 'reconnect' | 'poll') => {
    if (!statusPoller) {
        if (source === 'socket') finishPayment()
        return
    }
    isChecking.value = source !== 'poll'
    try {
        const status = await statusPoller.check()
        if (!status.isPurchased) statusMessage.value = '订单尚未支付，正在持续确认…'
    } catch (error) {
        // The legacy NestJS rollback target has no status endpoint. Only a
        // payment event whose payload matches the current user may fall back.
        if (source === 'socket' && responseStatus(error) === 404) {
            finishPayment()
        } else {
            onPollingError(error)
        }
    } finally {
        isChecking.value = false
    }
}

const onPaymentSuccess = (eventUserId: unknown) => {
    if (eventUserId !== userStore.user?.id) return
    void verifyPayment('socket')
}

const onSocketConnect = () => {
    if (isPay.value) void verifyPayment('reconnect')
}

const unbindSocket = () => {
    const socket = getSocket()
    socket?.off('paymentSuccess', onPaymentSuccess)
    socket?.off('connect', onSocketConnect)
}

const bindSocket = () => {
    const socket = getSocket()
    socket?.off('paymentSuccess', onPaymentSuccess)
    socket?.off('connect', onSocketConnect)
    socket?.on('paymentSuccess', onPaymentSuccess)
    socket?.on('connect', onSocketConnect)
}

watch(modelValue, (newVal) => {
    if(newVal){
        confirmed = false
        statusMessage.value = ''
        bindSocket()
    } else {
        unbindSocket()
        stopConfirmation()
    }
})

//图片地址
const imageSrc = (url: string) => {
    return uploadUrl + url;
}
//支付超时
const tips = () => {
    stopConfirmation()
    ElMessage.error('支付超时');
    timeExpire.value = 0;
    isPay.value = false;
}
//关闭弹框
const close = () => {
    unbindSocket()
    stopConfirmation()
    modelValue.value = false;//关闭弹框
    timeExpire.value = 0;//重置支付剩余时间
    isPay.value = false;//重置支付状态
    isCreating.value = false
    isChecking.value = false
    statusMessage.value = ''
}

//点击确认支付  
const onConfirm = async () => {
    const body: CreatePayDto = {
        subject: props.course?.name || '',
        body: props.course?.description || '',
        total_amount: props.course?.price || '',
        courseId: props.course?.id || ''
    }
    isCreating.value = true
    try {
        const res = await createPay(body);
        const outTradeNo = paymentOrderNumber(res.data)
        isPay.value = true;//设置支付中
        statusMessage.value = '等待支付完成，页面会自动确认最终状态…'
        timeExpire.value = res.data.timeExpire;
        if (outTradeNo) {
            statusPoller = new PaymentStatusPoller(
                async () => (await getPaymentStatus(outTradeNo)).data,
                finishPayment,
            )
            statusPoller.start(2000, onPollingError)
        }
        window.open(res.data.payUrl, '_blank', 'noopener,noreferrer')
    } catch (error) {
        ElMessage.error(apiErrorMessage(error, '创建支付订单失败'))
        isPay.value = false
    } finally {
        isCreating.value = false
    }
}

onBeforeUnmount(() => {
    unbindSocket()
    stopConfirmation()
})
</script>

<style scoped>
.pay-fade-enter-active,
.pay-fade-leave-active {
    transition: opacity 0.2s ease;
}

.pay-fade-enter-from,
.pay-fade-leave-to {
    opacity: 0;
}
</style>

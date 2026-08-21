import { ref } from "vue";

export interface Options {
    lang?: string;//语言
    continuous?: boolean;//是否连续识别 默认false 说完一句话或者没有声音了就会自动停止识别 true会一直识别需要手动停止
    interimResults?: boolean;//是否显示中间结果
    maxAlternatives?: number;//最多返回几个候选结果
}


let instance: SpeechRecognition | null = null;

const getInstance = (options: Options): SpeechRecognition => {
    const speechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition; //兼容苹果浏览器
    if(!speechRecognition) {
        throw new Error('SpeechRecognition is not supported in this browser');//浏览器不支持
    }
    //第一次创建
    if(!instance) {
        const { lang = 'zh-CN', continuous = false, interimResults = false, maxAlternatives = 1 } = options;
        instance = new speechRecognition();
        instance.lang = lang;
        instance.continuous = continuous;
        instance.interimResults = interimResults;
        instance.maxAlternatives = maxAlternatives;
    }
    //其他次数直接返回（单例模式）
    return instance;
}

export const useVoiceToText = (options: Options) => {
    const recognition = getInstance(options);
    const isRecording = ref(false);//是否正在录音
    recognition.onend = () => {
        isRecording.value = false;
    }
    //开启语音转文字
    const start = (callback: (result: string) => void) => {
        isRecording.value = true;
        recognition.start();
        recognition.onresult = (event) => {
            let fullText = ''
            for (let i = 0; i < event.results.length; i++) {
                fullText += event.results[i]![0]!.transcript;
            }
            callback?.(fullText);
        }
    }
    //停止语音转文字
    const stop = () => {
        isRecording.value = false;
        recognition.stop();
    }
    return {
        isRecording,
        start,
        stop
    }
}

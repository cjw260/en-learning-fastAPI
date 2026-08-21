<template>
    <div class="relative w-[800px] h-full bg-linear-to-br from-gray-800 to-gray-900">
        <canvas class="w-full h-full" ref="canvasRef"></canvas>
        <div class="absolute top-6 left-6">
            <div class="flex items-center gap-2">
                <div
                    class="w-10 h-10 bg-linear-to-br from-indigo-500 to-purple-600 rounded-[10px] flex items-center justify-center">
                    <span class="text-white font-bold text-xl">E</span>
                </div>
                <span class="text-white text-xl font-bold">English App</span>
            </div>
        </div>
        <!-- 登录/注册切换按钮 -->
        <div class="absolute top-6 right-6">
            <div class="flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-lg p-1">
                <button @click="() => loadModel('login')" :class="loginClass">
                    登录
                </button>
                <button @click="() => loadModel('register')" :class="registerClass">
                    注册
                </button>
            </div>
        </div>
    </div>    
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, onMounted, useTemplateRef } from 'vue'
import type { LoginType } from '@/components/Login/type'
// Three.js 动态导入，只在组件挂载时加载（减少主包体积 ~500KB+）
const canvasRef = useTemplateRef<HTMLCanvasElement>('canvasRef')
const type = ref<LoginType>('login')
const loginClass = computed(() => {
    return type.value === 'login' ? 'bg-indigo-500 text-white shadow-lg px-4 py-2 rounded-md text-sm font-medium transition-all' : 'text-white/70 hover:text-white hover:bg-white/10 px-4 py-2 rounded-md text-sm font-medium transition-all'
})
const registerClass = computed(() => {
    return type.value === 'register' ? 'bg-indigo-500 text-white shadow-lg px-4 py-2 rounded-md text-sm font-medium transition-all' : 'text-white/70 hover:text-white hover:bg-white/10 px-4 py-2 rounded-md text-sm font-medium transition-all'
})
const emits = defineEmits(['changeType'])

// Three.js 模块级变量（由 initThree 动态赋值）
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let THREE: any = null
let GLTFLoader: any = null
let OrbitControls: any = null
let scene: any = null
let currentModel: any = null
let mixer: any = null
let clock: any = null
let renderer: any = null
let controls: any = null
let animationFrame = 0
let disposed = false

const disposeModel = (model: any) => {
    model?.traverse?.((node: any) => {
        node.geometry?.dispose?.()
        const materials = Array.isArray(node.material) ? node.material : [node.material]
        materials.filter(Boolean).forEach((material: any) => material.dispose?.())
    })
}

const loadModel = (url: 'login' | 'register') => {
    if (!GLTFLoader || !scene || disposed) return
    if (currentModel) {
        scene.remove(currentModel)//如果已经有模型，先移除
        disposeModel(currentModel)
        currentModel = null
    }
    const loader = new GLTFLoader()//创建模型加载器
    type.value = url
    loader.load(`${import.meta.env.BASE_URL}models/${url}/scene.gltf`, (gltf: any) => {
        if (disposed) {
            disposeModel(gltf.scene)
            return
        }
        currentModel = gltf.scene//保存当前加载的模型
        scene.add(currentModel)//将加载的模型添加到场景中
        scene.position.y = -0.8//调整模型位置
        gltf.scene.scale.set(0.8, 0.8, 0.8)//缩放模型
        if(gltf.animations && gltf.animations.length > 0) {
            mixer = new THREE.AnimationMixer(currentModel)//创建动画混合器
            gltf.animations.forEach((clip: any) => {
                mixer!.clipAction(clip).play()//播放动画
            })
        }
    }, undefined, () => undefined)
    emits('changeType', url)//向父组件发送事件，通知类型改变
}

const initThree = async () => {
	    // 动态导入 Three.js（首次加载 login 弹窗时才下载）
	    const [THREE_MODULE, GLTF_MODULE, CTRL_MODULE] = await Promise.all([
	        import('three'),
	        import('three/examples/jsm/loaders/GLTFLoader.js'),
	        import('three/examples/jsm/controls/OrbitControls.js'),
	    ])
	    THREE = THREE_MODULE
	    GLTFLoader = GLTF_MODULE.GLTFLoader
	    OrbitControls = CTRL_MODULE.OrbitControls
	    scene = new THREE.Scene()
        clock = new THREE.Timer()
    if (disposed || !canvasRef.value) return
    const width = canvasRef.value?.clientWidth//获取画布宽度
    const height = canvasRef.value?.clientHeight//获取画布高度
    const camera = new THREE.PerspectiveCamera(60, width! / height!, 0.1, 1000)//创建透视相机
    camera.position.set(1, 0.5, 1)//设置相机位置
    renderer = new THREE.WebGLRenderer({ //创建渲染器
        canvas: canvasRef.value!,//指定渲染器使用的画布
        antialias: true,//启用抗锯齿
        alpha: true,//启用透明背景
        powerPreference: 'high-performance',//性能优先
        precision: 'highp',//高精度渲染
    })
    loadModel(type.value)//加载模型
    renderer.setSize(width!, height!)//设置渲染器大小
    renderer.render(scene, camera)//渲染场景
    controls = new OrbitControls(camera, renderer.domElement)//创建轨道控制器
    const animate = () => {
        animationFrame = requestAnimationFrame(animate)//请求下一帧动画
        if(mixer) {
            mixer.update(clock.getDelta())//更新动画混合器
        }
        scene.rotation.y += 0.002//旋转场景
        controls.update()//更新控制器
        renderer.render(scene, camera)//渲染场景
    }
    animate()//开始动画循环 
}
onMounted(() => {
    void initThree().catch(() => undefined)
})
onBeforeUnmount(() => {
    disposed = true
    cancelAnimationFrame(animationFrame)
    controls?.dispose?.()
    renderer?.dispose?.()
    disposeModel(currentModel)
    currentModel = null
})

</script>

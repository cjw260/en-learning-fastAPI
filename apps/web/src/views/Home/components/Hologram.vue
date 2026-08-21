<template>
    <canvas ref="hologramRef">
    </canvas>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, useTemplateRef } from 'vue';

const hologramRef = useTemplateRef<HTMLCanvasElement>('hologramRef');
let disposeThree: (() => void) | null = null
let disposed = false

const disposeModel = (model: any) => {
    model?.traverse?.((node: any) => {
        node.geometry?.dispose?.()
        const materials = Array.isArray(node.material) ? node.material : [node.material]
        materials.filter(Boolean).forEach((material: any) => material.dispose?.())
    })
}

const initThree = async () => {
    // 动态导入 Three.js（首次加载 Home 页时才下载，不阻塞首屏）
    const [THREE, GLTF, CTRL] = await Promise.all([
        import('three'),
        import('three/examples/jsm/loaders/GLTFLoader.js'),
        import('three/examples/jsm/controls/OrbitControls.js'),
    ])
    if (disposed || !hologramRef.value) return
    // 创建场景
    const scene = new THREE.Scene();
    //动画混合器
    let mixer: any = null;
    let currentModel: any = null;
    const clock = new THREE.Timer();//创建时钟
    // 创建相机
    const camera = new THREE.PerspectiveCamera(75, 500 / 250, 0.1, 1000);
    camera.position.set(0, 0, 10);
    const loader = new GLTF.GLTFLoader();// 创建 GLTF 加载器
    loader.load(`${import.meta.env.BASE_URL}models/hologram/scene.gltf`, (gltf: any) => {
        if (disposed) {
            disposeModel(gltf.scene)
            return
        }
        currentModel = gltf.scene
        scene.add(currentModel);// 将加载的模型添加到场景中
        currentModel.scale.set(4, 4, 4);// 调整模型大小
        if (gltf.animations && gltf.animations.length > 0) {
            mixer = new THREE.AnimationMixer(currentModel);
            gltf.animations.forEach((clip: any) => {
                mixer!.clipAction(clip).play();
            })
        }
    }, undefined, () => undefined)
    //环境光
    const ambientLight = new THREE.AmbientLight(0xffffff, 1);
    scene.add(ambientLight);
    //平行光
    const directionalLight = new THREE.DirectionalLight(0xffffff, 2);
    directionalLight.position.set(5, 10, 7.5);
    scene.add(directionalLight);
    // 创建渲染器
    const renderer = new THREE.WebGLRenderer({ canvas: hologramRef.value!,
        alpha: true,// 开启透明背景
        antialias: true,// 开启抗锯齿
        precision: 'highp',// 高精度渲染
        powerPreference: 'high-performance'//高性能
    });
    renderer.setSize(500, 250);// 设置渲染器大小
    const controls = new CTRL.OrbitControls(camera, renderer.domElement);// 创建轨道控制器
    let animationFrame = 0
    const animate = () => {
        animationFrame = requestAnimationFrame(animate);//请求动画帧
        const delta = clock.getDelta();//获取时间增量
        if (mixer) {
            mixer.update(delta);//更新动画混合器
        }
        scene.rotation.y += 0.002;// 旋转场景
        controls.update();  // 更新控制器
        renderer.render(scene, camera);// 渲染场景和相机
    };
    animate(); // 启动动画循环
    disposeThree = () => {
        cancelAnimationFrame(animationFrame)
        controls.dispose()
        renderer.dispose()
        disposeModel(currentModel)
        currentModel = null
    }
}
onMounted(() => {
    void initThree().catch(() => undefined)
})
onBeforeUnmount(() => {
    disposed = true
    disposeThree?.()
})
</script>

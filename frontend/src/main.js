import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { vWatermark } from './directives/watermark'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus, { locale: zhCn })

// V5.3安全特性: 全局注册隐形水印指令
app.directive('watermark', vWatermark)

app.mount('#app')
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import 'element-plus/dist/index.css'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import './styles.css'

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app')

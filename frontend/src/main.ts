import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import { pinia } from './stores'
import { useAuthStore } from './stores/auth'
import { configureAuthTransport } from './api/http'
import 'element-plus/dist/index.css'
import './styles/base.css'
const auth = useAuthStore(pinia)
function exitToLogin() {
  if (router.currentRoute.value.name !== 'login') void router.replace({ name: 'login' })
}
configureAuthTransport({
  getToken: () => { if (auth.expire()) exitToLogin(); return auth.token },
  onUnauthorized: (token) => {
    if (token === auth.token) { auth.invalidate(token); exitToLogin() }
  },
})
setInterval(() => { if (auth.expire()) exitToLogin() }, 1000)
createApp(App).use(pinia).use(router).mount('#app')

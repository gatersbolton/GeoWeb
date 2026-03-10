import { createRouter, createWebHistory } from 'vue-router'
import User from './views/User.vue'
import CsvSum from './views/CsvSum.vue'
import Login from './views/Login.vue'
import Register from './views/Register.vue'
import MapData from './views/MapData.vue'
import BoreholeEllipticity from './views/BoreholeEllipticity.vue'
import StressInversion from './views/StressInversion.vue'
import DataAugmentation from './views/DataAugmentation.vue'
import Profile from './views/Profile.vue'
import AgentAssistant from './views/AgentAssistant.vue'
import DlisWorkbench from './views/DlisWorkbench.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/map', component: MapData },
  { path: '/user', component: User },
  { path: '/profile', component: Profile },
  { path: '/csv', component: CsvSum },
  { path: '/dlis', component: DlisWorkbench },
  { path: '/borehole', component: BoreholeEllipticity },
  { path: '/stressinv', component: StressInversion },
  { path: '/augmentation', component: DataAugmentation },
  { path: '/agent', component: AgentAssistant },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫，未登录时跳转到 /login
router.beforeEach((to, from, next) => {
  const publicPages = ['/login', '/register']
  const loggedIn = localStorage.getItem('loggedIn') === 'true'
  if (!loggedIn && !publicPages.includes(to.path)) {
    return next('/login')
  }
  next()
})

export default router 

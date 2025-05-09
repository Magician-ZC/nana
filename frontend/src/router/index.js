import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

// Create new components for login and register
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { requiresAuth: true }
  },
  // Fallback route
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const isAuthenticated = userStore.checkAuth()

  if (requiresAuth && !isAuthenticated) {
    next('/login')
  } else if (!requiresAuth && isAuthenticated && (to.path === '/login' || to.path === '/register')) {
    next('/')
  } else {
    next()
  }
})

export default router 
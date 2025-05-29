import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

// Create new components for login and register
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false, autoLogin: true }
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
    meta: { requiresAuth: true, autoLogin: true }
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

// 执行自动登录
const performAutoLogin = async (userStore) => {
  if (!userStore.isLoggedIn) {
    console.log('执行自动登录...');
    try {
      await userStore.loginWithCredentials('admin', '123456');
      console.log('自动登录成功');
      return true;
    } catch (error) {
      console.error('自动登录失败:', error);
      return false;
    }
  }
  return true; // 已经登录
}

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const autoLogin = to.matched.some(record => record.meta.autoLogin)
  const isAuthenticated = userStore.checkAuth()

  // 对于需要自动登录的路由
  if (autoLogin) {
    const loginSuccess = await performAutoLogin(userStore);
    if (loginSuccess) {
      // 如果是登录页面且自动登录成功，则重定向到主页
      if (to.path === '/login') {
        next('/');
        return;
      } else {
        next();
        return;
      }
    }
  }

  // 常规路由守卫逻辑
  if (requiresAuth && !isAuthenticated) {
    next('/login');
  } else if (!requiresAuth && isAuthenticated && (to.path === '/login' || to.path === '/register')) {
    next('/');
  } else {
    next();
  }
})

export default router 
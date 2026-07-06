import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('./views/Login.vue') },
  {
    path: '/',
    component: () => import('./views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: () => import('./views/Dashboard.vue'), meta: { title: '概览' } },
      { path: 'products', component: () => import('./views/Products.vue'), meta: { title: '商品管理' } },
      { path: 'orders', component: () => import('./views/Orders.vue'), meta: { title: '订单管理' } },
      { path: 'wholesale', component: () => import('./views/Wholesale.vue'), meta: { title: '批发审核' } },
      { path: 'banners', component: () => import('./views/Banners.vue'), meta: { title: '首页轮播' } },
      { path: 'coupons', component: () => import('./views/Coupons.vue'), meta: { title: '优惠券' } },
      { path: 'users', component: () => import('./views/Users.vue'), meta: { title: '用户' } }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to) => {
  if (to.path !== '/login' && !localStorage.getItem('admin_token')) return '/login'
})

export default router

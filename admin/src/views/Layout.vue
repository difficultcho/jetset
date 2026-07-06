<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo">JETSET</div>
      <el-menu :default-active="$route.path" router background-color="#211e1a" text-color="#b8b0a4" active-text-color="#d6be94">
        <el-menu-item index="/dashboard">概览</el-menu-item>
        <el-menu-item index="/products">商品管理</el-menu-item>
        <el-menu-item index="/orders">订单管理</el-menu-item>
        <el-menu-item index="/wholesale">批发审核</el-menu-item>
        <el-menu-item index="/banners">首页轮播</el-menu-item>
        <el-menu-item index="/users">用户</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="title">{{ $route.meta.title }}</span>
        <span class="user">
          {{ adminName }}
          <el-button link @click="pwDialog = true">改密码</el-button>
          <el-button link type="primary" @click="logout">退出</el-button>
        </span>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="pwDialog" title="修改密码" width="380px">
    <el-form label-width="70px">
      <el-form-item label="原密码"><el-input v-model="pw.old_password" type="password" show-password /></el-form-item>
      <el-form-item label="新密码"><el-input v-model="pw.new_password" type="password" show-password placeholder="至少 8 位" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="pwDialog = false">取消</el-button>
      <el-button type="primary" @click="changePw">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api.js'

const router = useRouter()
const adminName = localStorage.getItem('admin_name') || 'admin'
const pwDialog = ref(false)
const pw = ref({ old_password: '', new_password: '' })

async function changePw() {
  if ((pw.value.new_password || '').length < 8) return ElMessage.warning('新密码至少 8 位')
  await http.post('/api/admin/auth/password', pw.value)
  ElMessage.success('密码已修改，请重新登录')
  pwDialog.value = false
  logout()
}

function logout() {
  localStorage.removeItem('admin_token')
  router.push('/login')
}
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #211e1a; }
.aside :deep(.el-menu) { border-right: none; }
.logo {
  color: #ece6dc;
  font-weight: 900;
  letter-spacing: 4px;
  font-size: 18px;
  padding: 20px;
  text-align: center;
}
.header {
  background: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title { font-weight: 600; }
.user { color: #666; font-size: 14px; }
</style>

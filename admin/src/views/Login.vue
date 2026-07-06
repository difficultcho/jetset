<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <div class="brand">JETSET 管理后台</div>
      <el-form @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">登 录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api.js'

const router = useRouter()
const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function submit() {
  if (!form.username || !form.password) return
  loading.value = true
  try {
    const data = await http.post('/api/admin/auth/login', form)
    localStorage.setItem('admin_token', data.token)
    localStorage.setItem('admin_name', data.username)
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(140deg, #3a352e 0%, #2b2823 55%, #211e1a 100%);
}
.login-card { width: 360px; padding: 12px 8px; }
.brand {
  text-align: center;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 4px;
  margin-bottom: 24px;
}
</style>

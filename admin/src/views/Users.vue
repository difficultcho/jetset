<template>
  <el-card>
    <div class="toolbar">
      <el-input v-model="q" placeholder="搜索昵称/手机号" clearable style="width: 240px" @change="fetch" />
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="昵称" min-width="140">
        <template #default="{ row }">{{ row.name || '（未设置）' }}</template>
      </el-table-column>
      <el-table-column label="手机号" width="140">
        <template #default="{ row }">{{ row.phone || '-' }}</template>
      </el-table-column>
      <el-table-column prop="openid" label="openid" width="140" />
      <el-table-column prop="points" label="积分" width="80" />
      <el-table-column label="注册时间" width="170">
        <template #default="{ row }">{{ fmt(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-switch :model-value="row.status === 1" @change="(v) => toggle(row, v)" />
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
      :page-size="pageSize" :current-page="page" @current-change="(p) => { page = p; fetch() }" />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api.js'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const q = ref('')
const loading = ref(false)

const fmt = (s) => (s ? String(s).replace('T', ' ').slice(0, 19) : '')

async function fetch() {
  loading.value = true
  try {
    const data = await http.get('/api/admin/users', {
      params: { q: q.value || undefined, page: page.value, page_size: pageSize }
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function toggle(row, on) {
  await http.put(`/api/admin/users/${row.id}/status`, { status: on ? 1 : 0 })
  row.status = on ? 1 : 0
  ElMessage.success(on ? '已启用' : '已禁用')
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.pager { margin-top: 16px; justify-content: flex-end; }
</style>

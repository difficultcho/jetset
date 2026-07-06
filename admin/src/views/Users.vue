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
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openAdjust(row)">调积分</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="adjustDialog" title="调整积分" width="400px">
      <p class="adjust-user">用户 #{{ adjust.userId }}（当前 {{ adjust.current }} 分）</p>
      <el-form label-width="80px">
        <el-form-item label="调整值">
          <el-input-number v-model="adjust.change" :step="10" style="width: 180px" />
          <span class="hint">正加负减</span>
        </el-form-item>
        <el-form-item label="备注" required>
          <el-input v-model="adjust.remark" placeholder="如：活动补偿" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustDialog = false">取消</el-button>
        <el-button type="primary" @click="doAdjust">确定</el-button>
      </template>
    </el-dialog>
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

const adjustDialog = ref(false)
const adjust = ref({ userId: null, current: 0, change: 0, remark: '' })

function openAdjust(row) {
  adjust.value = { userId: row.id, current: row.points, change: 0, remark: '' }
  adjustDialog.value = true
}

async function doAdjust() {
  const a = adjust.value
  if (!a.change) return ElMessage.warning('调整值不能为 0')
  if (!a.remark) return ElMessage.warning('请填写备注')
  const data = await http.post(`/api/admin/users/${a.userId}/points`,
                               { change: a.change, remark: a.remark })
  ElMessage.success('已调整，当前 ' + data.points + ' 分')
  adjustDialog.value = false
  fetch()
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.pager { margin-top: 16px; justify-content: flex-end; }
.adjust-user { color: #666; margin-bottom: 16px; }
.hint { color: #999; font-size: 12px; margin-left: 8px; }
</style>

<template>
  <el-card>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">+ 新增系列</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="系列" min-width="200">
        <template #default="{ row }">
          <div>{{ row.en || row.name }}</div>
          <div class="sub">{{ row.name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="product_count" label="商品数" width="90" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.status === 1" @change="(v) => toggle(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialog" :title="form.id ? '编辑系列' : '新增系列'" width="520px">
    <div class="tip">系列在商城里的展示图请到「商城配置」设置——那里支持多图并可各自配跳转。</div>
    <el-form label-width="80px">
      <el-form-item label="名称" required><el-input v-model="form.name" placeholder="如：2026夏日胶囊系列" /></el-form-item>
      <el-form-item label="英文名"><el-input v-model="form.en" placeholder="如：HIGH SUMMER" /></el-form-item>
      <el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" /></el-form-item>
      <el-form-item label="启用"><el-switch v-model="form.on" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api.js'

const list = ref([])
const loading = ref(false)
const dialog = ref(false)
const form = ref(empty())

function empty() {
  return { id: null, name: '', en: '', sort: 0, on: true }
}

async function fetch() {
  loading.value = true
  try {
    list.value = await http.get('/api/admin/series')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = empty()
  form.value.sort = list.value.length
  dialog.value = true
}

function openEdit(row) {
  form.value = { id: row.id, name: row.name, en: row.en,
                 sort: row.sort, on: row.status === 1 }
  dialog.value = true
}

function payload(f) {
  return { name: f.name, en: f.en, sort: f.sort, status: f.on ? 1 : 0 }
}

async function save() {
  if (!form.value.name) return ElMessage.warning('请填写名称')
  if (form.value.id) await http.put('/api/admin/series/' + form.value.id, payload(form.value))
  else await http.post('/api/admin/series', payload(form.value))
  ElMessage.success('已保存')
  dialog.value = false
  fetch()
}

async function toggle(row, on) {
  await http.put('/api/admin/series/' + row.id,
                 payload({ ...row, on }))
  row.status = on ? 1 : 0
}

async function del(row) {
  await ElMessageBox.confirm(`删除系列「${row.en || row.name}」？`, '确认', { type: 'warning' })
  await http.delete('/api/admin/series/' + row.id)
  ElMessage.success('已删除')
  fetch()
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.sub { color: #999; font-size: 12px; }
.tip { color: #999; font-size: 12px; margin-bottom: 12px; }
</style>

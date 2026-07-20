<template>
  <el-card>
    <div class="toolbar">
      <el-button type="primary" @click="createDialog = true">+ 新建内容页</el-button>
      <span class="sub">首页 / 关于品牌是固定挂载页（不可删）；其余为内容页，可被其他页面用链接块跳转</span>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">
          {{ row.title || '（未命名）' }}
          <el-tag v-if="row.fixed" size="small" type="warning" style="margin-left: 6px">固定</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="key" label="标识" width="120" />
      <el-table-column label="封面" width="90">
        <template #default="{ row }">
          <el-image v-if="row.cover" :src="imgUrl(row.cover)" fit="cover" class="thumb"
            :preview-src-list="[imgUrl(row.cover)]" />
          <span v-else class="sub">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click="edit(row)">编辑</el-button>
          <el-button link type="danger" :disabled="row.fixed" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="createDialog" title="新建内容页" width="420px">
    <el-form label-width="60px">
      <el-form-item label="标题"><el-input v-model="newTitle" placeholder="如：品牌故事 / 2026 大片" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createDialog = false">取消</el-button>
      <el-button type="primary" @click="create">创建并编辑</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http, { imgUrl } from '../api.js'

const router = useRouter()
const list = ref([])
const loading = ref(false)
const createDialog = ref(false)
const newTitle = ref('')

async function fetch() {
  loading.value = true
  try {
    list.value = await http.get('/api/admin/pages')
  } finally {
    loading.value = false
  }
}

function edit(row) { router.push('/pages/' + row.key) }

async function create() {
  if (!newTitle.value.trim()) return ElMessage.warning('请填写标题')
  const p = await http.post('/api/admin/pages', { title: newTitle.value, blocks: [] })
  createDialog.value = false
  newTitle.value = ''
  router.push('/pages/' + p.key)
}

async function del(row) {
  await ElMessageBox.confirm(`删除页面「${row.title || row.key}」？引用它的链接将失效。`, '确认', { type: 'warning' })
  await http.delete('/api/admin/pages/' + row.key)
  ElMessage.success('已删除')
  fetch()
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; display: flex; align-items: center; gap: 16px; }
.sub { color: #999; font-size: 12px; }
.thumb { width: 48px; height: 38px; border-radius: 4px; border: 1px solid #eee; }
</style>

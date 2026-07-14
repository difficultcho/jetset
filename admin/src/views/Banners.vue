<template>
  <el-card>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">+ 新增首图</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="图片" width="110">
        <template #default="{ row }">
          <el-image v-if="row.image" :src="imgUrl(row.image)" fit="cover" class="thumb"
            :preview-src-list="[imgUrl(row.image)]" />
          <span v-else class="sub">无图</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="主标题" min-width="180" />
      <el-table-column prop="sub_title" label="副标题" min-width="180" />
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

  <el-dialog v-model="dialog" :title="form.id ? '编辑首图' : '新增首图'" width="480px">
    <el-form label-width="70px">
      <el-form-item label="主标题"><el-input v-model="form.title" placeholder="如：MID SEASON SALE" /></el-form-item>
      <el-form-item label="副标题"><el-input v-model="form.sub_title" placeholder="如：EXPLORE WITHOUT LIMITS" /></el-form-item>
      <el-form-item label="图片">
        <div>
          <ImgUpload v-model="form.image" />
          <div class="sub" style="margin-top: 4px">首页首图（撑满首屏）：只展示「排序最前的启用项」，可存多条按季节切换启用；建议竖版大图</div>
        </div>
      </el-form-item>
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
import http, { imgUrl } from '../api.js'
import ImgUpload from '../components/ImgUpload.vue'

const list = ref([])
const loading = ref(false)
const dialog = ref(false)
const form = ref({ id: null, title: '', sub_title: '', image: '', sort: 0, on: true })

async function fetch() {
  loading.value = true
  try {
    list.value = await http.get('/api/admin/banners')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = { id: null, title: '', sub_title: '', image: '', sort: list.value.length, on: true }
  dialog.value = true
}

function openEdit(row) {
  form.value = { id: row.id, title: row.title, sub_title: row.sub_title, image: row.image || '',
                 sort: row.sort, on: row.status === 1 }
  dialog.value = true
}

function payload() {
  const f = form.value
  return { title: f.title, sub_title: f.sub_title, image: f.image, link: '', sort: f.sort, status: f.on ? 1 : 0 }
}

async function save() {
  if (!form.value.title) return ElMessage.warning('请填写主标题')
  if (form.value.id) await http.put('/api/admin/banners/' + form.value.id, payload())
  else await http.post('/api/admin/banners', payload())
  ElMessage.success('已保存')
  dialog.value = false
  fetch()
}

async function toggle(row, on) {
  await http.put('/api/admin/banners/' + row.id, {
    title: row.title, sub_title: row.sub_title, image: row.image || '',
    link: row.link || '', sort: row.sort, status: on ? 1 : 0
  })
  row.status = on ? 1 : 0
}

async function del(row) {
  await ElMessageBox.confirm(`删除首图「${row.title}」？`, '确认', { type: 'warning' })
  await http.delete('/api/admin/banners/' + row.id)
  ElMessage.success('已删除')
  fetch()
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.thumb { width: 72px; height: 56px; border-radius: 6px; border: 1px solid #eee; }
.sub { color: #999; font-size: 12px; }
</style>

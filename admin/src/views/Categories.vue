<template>
  <el-card>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate(null)">+ 新增一级品类</el-button>
      <span class="hint">商品挂在二级品类（或没有子级的一级）下；隐藏≠删除，商品仍保留归属</span>
    </div>
    <el-table :data="rows" v-loading="loading">
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="品类" min-width="200">
        <template #default="{ row }">
          <span v-if="row.parent_id" class="indent">└</span>
          {{ row.name }}
          <span class="sub" v-if="row.en">{{ row.en }}</span>
        </template>
      </el-table-column>
      <el-table-column label="级别" width="90">
        <template #default="{ row }">
          <el-tag size="small" :effect="row.parent_id ? 'plain' : 'dark'" type="info">
            {{ row.parent_id ? '二级' : '一级' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.status === 1" @change="(v) => toggle(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="!row.parent_id" link @click="openCreate(row.id)">+ 子品类</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialog" :title="form.id ? '编辑品类' : '新增品类'" width="460px">
    <el-form label-width="80px">
      <el-form-item label="名称" required><el-input v-model="form.name" placeholder="如：滑雪镜" /></el-form-item>
      <el-form-item label="英文名"><el-input v-model="form.en" placeholder="如：GOGGLES" /></el-form-item>
      <el-form-item label="父级">
        <el-select v-model="form.parent_id" clearable placeholder="无（作为一级品类）" style="width: 100%"
          :disabled="hasChildren(form.id)">
          <el-option v-for="t in tops" :key="t.id" :label="t.name" :value="t.id"
            :disabled="t.id === form.id" />
        </el-select>
        <div v-if="hasChildren(form.id)" class="sub">该品类下有子级，不能改为二级</div>
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
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api.js'

const cats = ref([])
const loading = ref(false)
const dialog = ref(false)
const form = ref(empty())

const tops = computed(() => cats.value.filter((c) => !c.parent_id))

// 树形排列：一级后面紧跟它的二级
const rows = computed(() => {
  const out = []
  tops.value.forEach((t) => {
    out.push(t)
    cats.value.filter((c) => c.parent_id === t.id).forEach((c) => out.push(c))
  })
  return out
})

function hasChildren(id) {
  return id != null && cats.value.some((c) => c.parent_id === id)
}

function empty() {
  return { id: null, name: '', en: '', parent_id: null, sort: 0, on: true }
}

async function fetch() {
  loading.value = true
  try {
    cats.value = await http.get('/api/admin/categories')
  } finally {
    loading.value = false
  }
}

function openCreate(parentId) {
  form.value = empty()
  form.value.parent_id = parentId
  form.value.sort = cats.value.filter((c) => c.parent_id === parentId).length
  dialog.value = true
}

function openEdit(row) {
  form.value = { id: row.id, name: row.name, en: row.en, parent_id: row.parent_id,
                 sort: row.sort, on: row.status === 1 }
  dialog.value = true
}

function payload(f) {
  return { name: f.name, en: f.en, parent_id: f.parent_id || null, sort: f.sort, status: f.on ? 1 : 0 }
}

async function save() {
  if (!form.value.name) return ElMessage.warning('请填写名称')
  if (form.value.id) await http.put('/api/admin/categories/' + form.value.id, payload(form.value))
  else await http.post('/api/admin/categories', payload(form.value))
  ElMessage.success('已保存')
  dialog.value = false
  fetch()
}

async function toggle(row, on) {
  await http.put('/api/admin/categories/' + row.id, {
    name: row.name, en: row.en, parent_id: row.parent_id, sort: row.sort, status: on ? 1 : 0
  })
  row.status = on ? 1 : 0
  ElMessage.success(on ? '已启用' : '已隐藏（该品类及其子级不再出现在小程序）')
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.hint { color: #999; font-size: 12px; }
.sub { color: #999; font-size: 12px; margin-left: 8px; }
.indent { color: #bbb; margin-right: 6px; }
</style>

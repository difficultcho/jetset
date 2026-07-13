<template>
  <el-card>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">+ 新增门店</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="门店图" width="90">
        <template #default="{ row }">
          <el-image v-if="row.images[0]" :src="imgUrl(row.images[0])" fit="cover" class="thumb"
            :preview-src-list="row.images.map(imgUrl)" />
        </template>
      </el-table-column>
      <el-table-column label="门店" min-width="200">
        <template #default="{ row }">
          <div>{{ row.name }}</div>
          <div class="sub">{{ row.province }} {{ row.city }} · {{ row.address }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="tel" label="电话" width="130" />
      <el-table-column prop="business_hours" label="营业时间" width="120" />
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

  <el-dialog v-model="dialog" :title="form.id ? '编辑门店' : '新增门店'" width="640px" top="5vh">
    <el-form label-width="90px">
      <el-row :gutter="12">
        <el-col :span="12"><el-form-item label="名称" required><el-input v-model="form.name" placeholder="如：北京三里屯精品店" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="短名"><el-input v-model="form.short_name" placeholder="导航栏标题，如：北京三里屯" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="省份"><el-input v-model="form.province" placeholder="如：北京市" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="城市"><el-input v-model="form.city" placeholder="如：北京市" /></el-form-item></el-col>
      </el-row>
      <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
      <el-row :gutter="12">
        <el-col :span="12"><el-form-item label="电话"><el-input v-model="form.tel" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="营业时间"><el-input v-model="form.business_hours" placeholder="如：10:00 - 22:00" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="纬度 lat"><el-input-number v-model="form.lat" :precision="6" :controls="false" style="width: 100%" placeholder="用于距离计算" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="经度 lng"><el-input-number v-model="form.lng" :precision="6" :controls="false" style="width: 100%" /></el-form-item></el-col>
      </el-row>
      <el-form-item label="门店图">
        <div>
          <ImgListUpload v-model="form.images" />
          <div class="hint">第一张为主图（门店列表/详情头图），其余为店内陈列</div>
        </div>
      </el-form-item>
      <el-form-item label="导购二维码"><ImgUpload v-model="form.consultant_qr" /></el-form-item>
      <el-row :gutter="12">
        <el-col :span="12"><el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="启用"><el-switch v-model="form.on" /></el-form-item></el-col>
      </el-row>
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
import ImgListUpload from '../components/ImgListUpload.vue'

const list = ref([])
const loading = ref(false)
const dialog = ref(false)
const form = ref(empty())

function empty() {
  return { id: null, name: '', short_name: '', province: '', city: '', address: '',
           tel: '', business_hours: '', images: [], consultant_qr: '',
           lat: null, lng: null, sort: 0, on: true }
}

async function fetch() {
  loading.value = true
  try {
    list.value = await http.get('/api/admin/stores')
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
  form.value = { id: row.id, name: row.name, short_name: row.short_name,
                 province: row.province, city: row.city, address: row.address,
                 tel: row.tel, business_hours: row.business_hours,
                 images: [...(row.images || [])], consultant_qr: row.consultant_qr,
                 lat: row.lat, lng: row.lng, sort: row.sort, on: row.status === 1 }
  dialog.value = true
}

function payload(f) {
  return { name: f.name, short_name: f.short_name, province: f.province, city: f.city,
           address: f.address, tel: f.tel, business_hours: f.business_hours,
           images: f.images, consultant_qr: f.consultant_qr,
           lat: f.lat, lng: f.lng, sort: f.sort, status: f.on ? 1 : 0 }
}

async function save() {
  if (!form.value.name) return ElMessage.warning('请填写名称')
  if (form.value.id) await http.put('/api/admin/stores/' + form.value.id, payload(form.value))
  else await http.post('/api/admin/stores', payload(form.value))
  ElMessage.success('已保存')
  dialog.value = false
  fetch()
}

async function toggle(row, on) {
  await http.put('/api/admin/stores/' + row.id, payload({ ...row, on }))
  row.status = on ? 1 : 0
}

async function del(row) {
  await ElMessageBox.confirm(`删除门店「${row.name}」？`, '确认', { type: 'warning' })
  await http.delete('/api/admin/stores/' + row.id)
  ElMessage.success('已删除')
  fetch()
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.sub { color: #999; font-size: 12px; }
.thumb { width: 56px; height: 56px; border-radius: 6px; border: 1px solid #eee; }
.hint { color: #999; font-size: 12px; margin-top: 4px; }
</style>

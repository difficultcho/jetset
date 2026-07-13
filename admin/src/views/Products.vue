<template>
  <el-card>
    <div class="toolbar">
      <el-input v-model="q" placeholder="搜索商品名/款号" clearable style="width: 240px" @change="fetch" />
      <el-select v-model="status" placeholder="状态" clearable style="width: 120px" @change="fetch">
        <el-option label="在售" :value="1" />
        <el-option label="下架" :value="0" />
      </el-select>
      <el-button type="primary" @click="openCreate">+ 新增商品</el-button>
    </div>

    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="商品" min-width="180">
        <template #default="{ row }">
          <div>{{ row.name }}</div>
          <div class="sub">{{ row.code || '—' }} · {{ row.category_name }}</div>
        </template>
      </el-table-column>
      <el-table-column label="系列" width="130">
        <template #default="{ row }">
          <el-tag v-if="row.series_id" size="small" effect="plain">{{ seriesName(row.series_id) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="价格" width="100">
        <template #default="{ row }">¥{{ (row.price / 100).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="stock_total" label="库存" width="80" />
      <el-table-column prop="sales" label="销量" width="80" />
      <el-table-column label="标签" width="110">
        <template #default="{ row }">
          <el-tag v-if="row.badge" type="danger" size="small">{{ row.badge }}</el-tag>
          <el-tag v-if="row.featured" type="warning" size="small">精选</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上架" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.status === 1" @change="(v) => toggle(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row.id)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
      :page-size="pageSize" :current-page="page" @current-change="(p) => { page = p; fetch() }" />
  </el-card>

  <!-- 编辑/新增 -->
  <el-dialog v-model="dialog" :title="form.id ? '编辑商品' : '新增商品'" width="880px" top="4vh">
    <el-form label-width="80px">
      <el-row :gutter="12">
        <el-col :span="12"><el-form-item label="名称" required><el-input v-model="form.name" placeholder="完整名，如：SOLEIL 挂脖牛仔连衣裙" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="短名"><el-input v-model="form.sub" placeholder="卡片/走马灯展示名，空则用名称" /></el-form-item></el-col>
        <el-col :span="8">
          <el-form-item label="分类" required>
            <el-select v-model="form.category_id" style="width: 100%">
              <el-option-group v-for="g in catGroups" :key="g.id" :label="g.name">
                <el-option v-for="c in g.children" :key="c.id" :label="c.name" :value="c.id" />
              </el-option-group>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="系列">
            <el-select v-model="form.series_id" clearable placeholder="不归属" style="width: 100%">
              <el-option v-for="s in seriesList" :key="s.id" :label="s.en ? s.en + '｜' + s.name : s.name" :value="s.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8"><el-form-item label="款号"><el-input v-model="form.code" placeholder="如：AU433DSS266" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="角标"><el-input v-model="form.badge" placeholder="如：SALE" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="划线价"><el-input-number v-model="form.originalYuan" :min="0.01" :precision="2" :controls="false" placeholder="元，可空" style="width: 100%" /></el-form-item></el-col>
        <el-col :span="4"><el-form-item label="精选"><el-switch v-model="form.featured" /></el-form-item></el-col>
        <el-col :span="4"><el-form-item label="视频"><el-switch v-model="form.has_video" /></el-form-item></el-col>
        <el-col :span="4"><el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" :controls="false" style="width: 100%" /></el-form-item></el-col>
      </el-row>
      <el-form-item label="简介"><el-input v-model="form.brief" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="详情"><el-input v-model="form.detail" type="textarea" :rows="3" /></el-form-item>
      <el-form-item label="卖点">
        <el-input v-model="form.bulletsText" type="textarea" :rows="3"
          placeholder="商品细节条目，每行一条，如：
意大利制造
鞋跟高度 8.5cm" />
      </el-form-item>

      <el-form-item label="SKU" required>
        <el-table :data="form.skus" size="small" border style="width: 100%">
          <el-table-column label="色序" width="70">
            <template #default="{ row }"><el-input-number v-model="row.color_index" :min="0" :controls="false" style="width: 100%" /></template>
          </el-table-column>
          <el-table-column label="颜色名" min-width="120">
            <template #default="{ row }"><el-input v-model="row.color_name" /></template>
          </el-table-column>
          <el-table-column label="色值" width="70">
            <template #default="{ row }"><el-color-picker v-model="row.color_hex" /></template>
          </el-table-column>
          <el-table-column label="尺码" width="90">
            <template #default="{ row }"><el-input v-model="row.size" /></template>
          </el-table-column>
          <el-table-column label="价格(元)" width="110">
            <template #default="{ row }"><el-input-number v-model="row.priceYuan" :min="0.01" :precision="2" :controls="false" style="width: 100%" /></template>
          </el-table-column>
          <el-table-column label="库存" width="90">
            <template #default="{ row }"><el-input-number v-model="row.stock" :min="0" :controls="false" style="width: 100%" /></template>
          </el-table-column>
          <el-table-column label="在售" width="60">
            <template #default="{ row }"><el-switch v-model="row.on" /></template>
          </el-table-column>
          <el-table-column width="50">
            <template #default="{ $index }">
              <el-button link type="danger" @click="form.skus.splice($index, 1)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button size="small" style="margin-top: 8px" @click="addSku">+ 加一行</el-button>
      </el-form-item>

      <el-form-item label="图片">
        <div class="imgs">
          <div v-for="(img, i) in form.images" :key="i" class="img-item">
            <el-image :src="imgUrl(img.url)" fit="cover" class="img" :preview-src-list="[imgUrl(img.url)]" />
            <div class="img-meta">
              色序 <el-input-number v-model="img.color_index" :min="0" :controls="false" style="width: 48px" />
              <el-button link type="danger" @click="form.images.splice(i, 1)">删</el-button>
            </div>
          </div>
          <el-upload :show-file-list="false" :http-request="doUpload" accept="image/*">
            <div class="upload-box">+ 上传</div>
          </el-upload>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http, { imgUrl } from '../api.js'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const q = ref('')
const status = ref()
const loading = ref(false)
const cats = ref([])
const seriesList = ref([])
const dialog = ref(false)
const saving = ref(false)
const form = ref(emptyForm())

// 一级作分组、二级作选项；没有子级的一级自身可选
const catGroups = computed(() => {
  const tops = cats.value.filter((c) => !c.parent_id)
  return tops.map((t) => {
    const children = cats.value.filter((c) => c.parent_id === t.id)
    return { id: t.id, name: t.name, children: children.length ? children : [t] }
  })
})

function seriesName(id) {
  const s = seriesList.value.find((x) => x.id === id)
  return s ? (s.en || s.name) : id
}

function emptyForm() {
  return { id: null, category_id: null, series_id: null, name: '', sub: '', code: '',
           en_model: '', brief: '', detail: '', bulletsText: '', badge: '',
           featured: false, has_video: false, originalYuan: null,
           sort: 0, status: 1, skus: [], images: [] }
}

async function fetch() {
  loading.value = true
  try {
    const data = await http.get('/api/admin/products', {
      params: { q: q.value || undefined, status: status.value, page: page.value, page_size: pageSize }
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function addSku() {
  form.value.skus.push({ color_index: 0, color_name: '', color_hex: '#1a1a1a', size: '均码', priceYuan: 0, stock: 0, on: true })
}

function openCreate() {
  form.value = emptyForm()
  addSku()
  dialog.value = true
}

async function openEdit(id) {
  const d = await http.get('/api/admin/products/' + id)
  form.value = {
    id: d.id, category_id: d.category_id, series_id: d.series_id,
    name: d.name, sub: d.sub || '', code: d.code || '', en_model: d.en_model,
    brief: d.brief, detail: d.detail, bulletsText: (d.bullets || []).join('\n'),
    badge: d.badge || '', featured: d.featured, has_video: !!d.has_video,
    originalYuan: d.original_price ? d.original_price / 100 : null,
    sort: d.sort, status: d.status,
    skus: d.skus.map((s) => ({ color_index: s.color_index, color_name: s.color_name, color_hex: s.color_hex,
                               size: s.size, priceYuan: s.price / 100, stock: s.stock, on: s.status === 1 })),
    images: d.images.map((i) => ({ color_index: i.color_index, url: i.url, sort: i.sort || 0 }))
  }
  dialog.value = true
}

async function doUpload({ file }) {
  const fd = new FormData()
  fd.append('file', file)
  const data = await http.post('/api/v1/uploads', fd)
  form.value.images.push({ color_index: 0, url: data.url, sort: form.value.images.length })
}

async function save() {
  const f = form.value
  if (!f.name || !f.category_id) return ElMessage.warning('请填写名称和分类')
  if (!f.skus.length) return ElMessage.warning('至少一个 SKU')
  for (const s of f.skus) {
    if (!s.color_name || !s.size || !s.priceYuan) return ElMessage.warning('SKU 的颜色/尺码/价格必填')
  }
  const payload = {
    category_id: f.category_id, series_id: f.series_id || null,
    name: f.name, sub: f.sub, code: f.code, en_model: f.en_model, brief: f.brief,
    detail: f.detail,
    bullets: f.bulletsText.split('\n').map((s) => s.trim()).filter(Boolean),
    badge: f.badge || null, featured: f.featured, has_video: f.has_video,
    original_price: f.originalYuan ? Math.round(f.originalYuan * 100) : null,
    sort: f.sort, status: f.status,
    skus: f.skus.map((s) => ({ color_index: s.color_index, color_name: s.color_name, color_hex: s.color_hex || '#888888',
                               size: s.size, price: Math.round(s.priceYuan * 100), stock: s.stock, status: s.on ? 1 : 0 })),
    images: f.images.map((i, idx) => ({ color_index: i.color_index, url: i.url, sort: idx }))
  }
  saving.value = true
  try {
    if (f.id) await http.put('/api/admin/products/' + f.id, payload)
    else await http.post('/api/admin/products', payload)
    ElMessage.success('已保存')
    dialog.value = false
    fetch()
  } finally {
    saving.value = false
  }
}

async function toggle(row, on) {
  await http.post(`/api/admin/products/${row.id}/status`, { status: on ? 1 : 0 })
  row.status = on ? 1 : 0
  ElMessage.success(on ? '已上架' : '已下架')
}

onMounted(async () => {
  fetch()
  ;[cats.value, seriesList.value] = await Promise.all([
    http.get('/api/admin/categories'),
    http.get('/api/admin/series')
  ])
})
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.sub { color: #999; font-size: 12px; }
.pager { margin-top: 16px; justify-content: flex-end; }
.imgs { display: flex; gap: 12px; flex-wrap: wrap; }
.img-item { width: 96px; }
.img { width: 96px; height: 96px; border-radius: 6px; border: 1px solid #eee; }
.img-meta { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #666; margin-top: 4px; }
.upload-box {
  width: 96px; height: 96px; border: 1px dashed #ccc; border-radius: 6px;
  display: flex; align-items: center; justify-content: center; color: #999; cursor: pointer;
}
</style>

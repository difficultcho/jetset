<template>
  <el-card>
    <div class="toolbar">
      <el-radio-group v-model="type" @change="fetch">
        <el-radio-button :value="''">全部</el-radio-button>
        <el-radio-button v-for="(label, t) in TYPES" :key="t" :value="t">{{ label }}</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="openCreate">+ 新增内容</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="类型" width="110">
        <template #default="{ row }"><el-tag size="small" effect="plain">{{ TYPES[row.type] || row.type }}</el-tag></template>
      </el-table-column>
      <el-table-column label="封面" width="90">
        <template #default="{ row }">
          <el-image v-if="row.cover" :src="imgUrl(row.cover)" fit="cover" class="thumb"
            :preview-src-list="[imgUrl(row.cover)]" />
          <div v-else class="thumb tint" :style="{ background: row.cover_tint }" />
        </template>
      </el-table-column>
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">
          <div>
            {{ row.title }}
            <el-tag v-if="row.parent_id" size="small" type="info" effect="plain">子项目</el-tag>
            <el-tag v-if="row.series_id" size="small" effect="plain">{{ seriesName(row.series_id) }}</el-tag>
          </div>
          <div class="sub">{{ row.subtitle }}</div>
        </template>
      </el-table-column>
      <el-table-column label="图文块" width="80">
        <template #default="{ row }">{{ row.body.length || '—' }}</template>
      </el-table-column>
      <el-table-column label="发布" width="80">
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

  <el-dialog v-model="dialog" :title="form.id ? '编辑内容' : '新增内容'" width="720px" top="4vh">
    <el-form label-width="80px">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="类型" required>
            <el-select v-model="form.type" style="width: 100%">
              <el-option v-for="(label, t) in TYPES" :key="t" :label="label" :value="t" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="16"><el-form-item label="标题" required><el-input v-model="form.title" placeholder="如：MID SEASON SALE" /></el-form-item></el-col>
      </el-row>
      <el-form-item label="副标题"><el-input v-model="form.subtitle" /></el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="关联系列">
            <el-select v-model="form.series_id" clearable placeholder="无（详情页尾部不出导购条）" style="width: 100%">
              <el-option v-for="s in seriesList" :key="s.id" :label="s.en ? s.en + '｜' + s.name : s.name" :value="s.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12" v-if="form.type === 'project'">
          <el-form-item label="父项目">
            <el-select v-model="form.parent_id" clearable placeholder="无（本身是顶级项目）" style="width: 100%">
              <el-option v-for="p in parentOptions" :key="p.id" :label="p.title" :value="p.id" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="10">
          <el-form-item label="封面图"><ImgUpload v-model="form.cover" :size="80" /></el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="占位色"><el-color-picker v-model="form.cover_tint" /></el-form-item>
        </el-col>
        <el-col :span="4"><el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" :controls="false" style="width: 100%" /></el-form-item></el-col>
        <el-col :span="4"><el-form-item label="发布"><el-switch v-model="form.on" /></el-form-item></el-col>
      </el-row>

      <el-form-item label="图文块">
        <div class="blocks">
          <div v-for="(b, i) in form.body" :key="i" class="block">
            <div class="block-head">
              <el-select v-model="b.kind" style="width: 100px" size="small">
                <el-option label="图片" value="image" />
                <el-option label="视频" value="video" />
                <el-option label="正文" value="text" />
                <el-option label="引言" value="quote" />
              </el-select>
              <span class="grow" />
              <el-button link size="small" :disabled="i === 0" @click="move(i, -1)">上移</el-button>
              <el-button link size="small" :disabled="i === form.body.length - 1" @click="move(i, 1)">下移</el-button>
              <el-button link type="danger" size="small" @click="form.body.splice(i, 1)">删除</el-button>
            </div>
            <div v-if="b.kind === 'image'" class="block-img">
              <ImgUpload v-model="b.img" :size="72" />
              <div class="block-opts">
                <span>宽高比 <el-input v-model="b.ratio" size="small" style="width: 80px" placeholder="3/3.3" /></span>
                <span>两侧留白 <el-switch v-model="b.inset" size="small" /></span>
                <span>占位色 <el-color-picker v-model="b.tint" size="small" /></span>
                <el-input v-model="b.ph" size="small" style="width: 200px" placeholder="占位标签（未传图时展示）" />
              </div>
            </div>
            <div v-else-if="b.kind === 'video'" class="block-img">
              <div>
                <el-upload :show-file-list="false" :http-request="(o) => doVideo(o, b)" accept="video/mp4">
                  <el-button size="small">{{ b.src ? '重新上传视频' : '上传视频（mp4 ≤50MB）' }}</el-button>
                </el-upload>
                <div v-if="vPct" class="v-hint">上传中 {{ vPct }}%</div>
                <div v-else-if="b.src" class="v-hint">✓ {{ b.src }}</div>
              </div>
              <div class="block-opts">
                <span>封面图 <ImgUpload v-model="b.poster" :size="72" /></span>
                <span>宽高比 <el-input v-model="b.ratio" size="small" style="width: 80px" placeholder="16/9" /></span>
                <span>两侧留白 <el-switch v-model="b.inset" size="small" /></span>
              </div>
            </div>
            <el-input v-else v-model="b.value" type="textarea" :rows="2"
              :placeholder="b.kind === 'quote' ? '引言（居中大字）' : '正文段落'" />
          </div>
          <el-button size="small" @click="addBlock">+ 加一块</el-button>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http, { imgUrl, uploadImage } from '../api.js'
import ImgUpload from '../components/ImgUpload.vue'

const TYPES = { project: 'A.PROJECTS', moment: 'A.MOMENTS', campaign: '广告大片', story: '品牌故事' }

const list = ref([])
const type = ref('')
const loading = ref(false)
const dialog = ref(false)
const form = ref(empty())
const seriesList = ref([])
const allPosts = ref([])
const vPct = ref(0)

// 父项目候选：顶级 project，排除自己
const parentOptions = computed(() =>
  allPosts.value.filter((p) => p.type === 'project' && !p.parent_id && p.id !== form.value.id))

function empty() {
  return { id: null, type: 'project', title: '', subtitle: '', cover: '',
           cover_tint: '#e6ddce', link: '', body: [], series_id: null, parent_id: null,
           sort: 0, on: true }
}

async function doVideo({ file }, b) {
  vPct.value = 1
  try {
    const data = await uploadImage(file, (p) => { vPct.value = p })
    b.src = data.url
  } finally {
    vPct.value = 0
  }
}

async function fetch() {
  loading.value = true
  try {
    list.value = await http.get('/api/admin/brand/posts', { params: { type: type.value || undefined } })
    if (!type.value) allPosts.value = list.value
    else allPosts.value = await http.get('/api/admin/brand/posts')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = empty()
  if (type.value) form.value.type = type.value
  form.value.sort = list.value.length
  dialog.value = true
}

function openEdit(row) {
  form.value = {
    id: row.id, type: row.type, title: row.title, subtitle: row.subtitle,
    cover: row.cover, cover_tint: row.cover_tint, link: row.link || '',
    series_id: row.series_id, parent_id: row.parent_id,
    sort: row.sort, on: row.status === 1,
    body: (row.body || []).map((b) => ({
      kind: b.kind || 'text', img: b.img || '', value: b.value || '',
      src: b.src || '', poster: b.poster || '',
      ratio: b.ratio || '3/3.3', inset: !!b.inset, ph: b.ph || '', tint: b.tint || '#e6ddce'
    }))
  }
  dialog.value = true
}

function addBlock() {
  form.value.body.push({ kind: 'image', img: '', value: '', src: '', poster: '',
                         ratio: '3/3.3', inset: false, ph: '', tint: '#e6ddce' })
}

function move(i, delta) {
  const arr = form.value.body
  const [x] = arr.splice(i, 1)
  arr.splice(i + delta, 0, x)
}

// 各类块只带各自需要的键（与小程序 toBrand 的契约一致）
function blockOut(b) {
  if (b.kind === 'image') {
    return { kind: 'image', img: b.img, ratio: b.ratio || '3/3.3', inset: !!b.inset,
             ph: b.ph, tint: b.tint || '#e6ddce' }
  }
  if (b.kind === 'video') {
    return { kind: 'video', src: b.src, poster: b.poster,
             ratio: b.ratio || '16/9', inset: !!b.inset }
  }
  return { kind: b.kind, value: b.value }
}

function payload(f) {
  return { type: f.type, title: f.title, subtitle: f.subtitle, cover: f.cover,
           cover_tint: f.cover_tint || '#e6ddce', link: f.link,
           series_id: f.series_id || null,
           parent_id: f.type === 'project' ? (f.parent_id || null) : null,
           body: f.body.map(blockOut), sort: f.sort, status: f.on ? 1 : 0 }
}

async function save() {
  if (!form.value.title) return ElMessage.warning('请填写标题')
  if (form.value.id) await http.put('/api/admin/brand/posts/' + form.value.id, payload(form.value))
  else await http.post('/api/admin/brand/posts', payload(form.value))
  ElMessage.success('已保存')
  dialog.value = false
  fetch()
}

async function toggle(row, on) {
  await http.put('/api/admin/brand/posts/' + row.id, {
    type: row.type, title: row.title, subtitle: row.subtitle, cover: row.cover,
    cover_tint: row.cover_tint, link: row.link || '', body: row.body,
    series_id: row.series_id, parent_id: row.parent_id,
    sort: row.sort, status: on ? 1 : 0
  })
  row.status = on ? 1 : 0
}

async function del(row) {
  await ElMessageBox.confirm(`删除「${row.title}」？`, '确认', { type: 'warning' })
  await http.delete('/api/admin/brand/posts/' + row.id)
  ElMessage.success('已删除')
  fetch()
}

function seriesName(id) {
  const s = seriesList.value.find((x) => x.id === id)
  return s ? (s.en || s.name) : '系列'
}

onMounted(async () => {
  fetch()
  seriesList.value = await http.get('/api/admin/series')
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
.sub { color: #999; font-size: 12px; }
.thumb { width: 56px; height: 56px; border-radius: 6px; border: 1px solid #eee; }
.tint { display: inline-block; }
.blocks { width: 100%; display: flex; flex-direction: column; gap: 10px; }
.block { border: 1px solid #ebebeb; border-radius: 6px; padding: 10px; }
.block-head { display: flex; align-items: center; gap: 4px; margin-bottom: 8px; }
.grow { flex: 1; }
.block-img { display: flex; gap: 16px; align-items: flex-start; }
.v-hint { color: #67a23a; font-size: 12px; margin-top: 6px; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.block-opts { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; color: #666; font-size: 13px; }
</style>

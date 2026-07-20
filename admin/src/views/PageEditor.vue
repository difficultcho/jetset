<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="head-row">
        <div class="head-left">
          <el-button link @click="back">← 页面管理</el-button>
          <el-input v-model="title" placeholder="页面标题" style="width: 220px" :disabled="fixed" />
          <el-tag v-if="fixed" size="small" type="warning">固定挂载页</el-tag>
        </div>
        <div class="head-ops">
          <span class="sub">封面</span>
          <ImgUpload v-model="cover" :size="40" />
          <span class="sub">启用</span>
          <el-switch v-model="on" />
          <el-button type="primary" @click="save">保存</el-button>
        </div>
      </div>
    </template>

    <div class="blocks">
      <div v-for="(b, i) in blocks" :key="b._id" class="block">
        <div class="block-head">
          <el-tag size="small" :type="TAG[b.kind]">{{ KINDS[b.kind] }}</el-tag>
          <span class="grow" />
          <el-button link size="small" :disabled="i === 0" @click="move(i, -1)">上移</el-button>
          <el-button link size="small" :disabled="i === blocks.length - 1" @click="move(i, 1)">下移</el-button>
          <el-button link type="danger" size="small" @click="blocks.splice(i, 1)">删除</el-button>
        </div>

        <!-- 图片块 -->
        <div v-if="b.kind === 'image'" class="block-body">
          <ImgUpload v-model="b.img" :size="72" />
          <div class="opts">
            <span>画幅
              <el-select v-model="b.ratio" size="small" style="width: 130px">
                <el-option label="撑满首屏" value="hero" />
                <el-option v-for="r in RATIOS" :key="r" :label="r" :value="r" />
              </el-select>
            </span>
            <span>两侧留白 <el-switch v-model="b.inset" size="small" /></span>
          </div>
        </div>

        <!-- 视频块 -->
        <div v-else-if="b.kind === 'video'" class="block-body">
          <div>
            <el-upload :show-file-list="false" :http-request="(o) => doVideo(o, b)" accept="video/mp4">
              <el-button size="small">{{ b.src ? '重新上传视频' : '上传视频（mp4 ≤50MB）' }}</el-button>
            </el-upload>
            <div v-if="b._pct" class="v-hint">上传中 {{ b._pct }}%</div>
            <div v-else-if="b.src" class="v-hint">✓ {{ b.src }}</div>
          </div>
          <div class="opts">
            <span>封面图 <ImgUpload v-model="b.poster" :size="72" /></span>
            <span>画幅
              <el-select v-model="b.ratio" size="small" style="width: 110px">
                <el-option v-for="r in RATIOS" :key="r" :label="r" :value="r" />
              </el-select>
            </span>
            <span>两侧留白 <el-switch v-model="b.inset" size="small" /></span>
          </div>
        </div>

        <!-- 文本块 -->
        <div v-else-if="b.kind === 'text'" class="block-body-col">
          <div class="opts">
            <span>排版
              <el-select v-model="b.preset" size="small" style="width: 150px">
                <el-option label="正文段落" value="para" />
                <el-option label="居中引文" value="quote" />
                <el-option label="小字距标题" value="eyebrow" />
                <el-option label="下划线链接" value="link" />
              </el-select>
            </span>
            <span>对齐
              <el-select v-model="b.align" size="small" style="width: 100px">
                <el-option label="居左" value="left" />
                <el-option label="居中" value="center" />
                <el-option label="居右" value="right" />
              </el-select>
            </span>
          </div>
          <el-input v-model="b.text" type="textarea" :rows="2" placeholder="文本内容" />
        </div>

        <!-- 链接行块：左右两栏 -->
        <div v-else-if="b.kind === 'linkrow'" class="block-body-col">
          <div v-for="side in ['left', 'right']" :key="side" class="opts linkrow-side">
            <el-tag size="small" type="info">{{ side === 'left' ? '左' : '右' }}</el-tag>
            <el-input v-model="b[side].text" size="small" style="width: 200px" placeholder="链接文字（留空=该侧不显示）" />
            <LinkTarget v-model="b[side].link" :pages="pages" :cats="catList" :series="seriesList" :prods="prodList" />
          </div>
        </div>

        <!-- 走马灯块 -->
        <div v-else-if="b.kind === 'carousel'" class="block-body-col">
          <div class="opts">
            <span>数据源
              <el-select v-model="b.source" size="small" style="width: 120px">
                <el-option label="精选商品" value="featured" />
                <el-option label="某系列" value="series" />
                <el-option label="某品类" value="category" />
                <el-option label="手动选品" value="manual" />
              </el-select>
            </span>
            <span v-if="b.source === 'series'">系列
              <el-select v-model="b.series_id" size="small" filterable style="width: 200px">
                <el-option v-for="s in seriesList" :key="s.id"
                  :label="s.en ? s.en + '｜' + s.name : s.name" :value="s.id" :disabled="s.status !== 1" />
              </el-select>
            </span>
            <span v-if="b.source === 'category'">品类
              <el-select v-model="b.category_id" size="small" filterable style="width: 200px">
                <el-option v-for="c in catList" :key="c.id" :label="catLabel(c)" :value="c.id"
                  :disabled="c.status !== 1" />
              </el-select>
            </span>
            <span>展示数量 <el-input-number v-model="b.count" :min="1" :max="10" size="small" style="width: 100px" /></span>
          </div>
          <div v-if="b.source === 'manual'" class="opts">
            <span class="picker-label">选品（按选择顺序展示）</span>
            <el-select v-model="b.spu_ids" multiple filterable size="small" style="flex: 1; min-width: 320px"
              placeholder="搜索并选择商品">
              <el-option v-for="p in prodList" :key="p.id" :label="prodLabel(p)" :value="p.id"
                :disabled="p.status !== 1" />
            </el-select>
          </div>
        </div>

        <!-- 跳转配置（图片/文本；视频不支持、走马灯与链接行自带） -->
        <div v-if="b.kind === 'image' || b.kind === 'text'" class="opts link-row">
          <LinkTarget v-model="b.link" :pages="pages" :cats="catList" :series="seriesList" :prods="prodList" />
        </div>
      </div>

      <div class="add-row">
        <el-button size="small" @click="add('image')">+ 图片</el-button>
        <el-button size="small" @click="add('video')">+ 视频</el-button>
        <el-button size="small" @click="add('text')">+ 文本</el-button>
        <el-button size="small" @click="add('linkrow')">+ 链接行</el-button>
        <el-button size="small" @click="add('carousel')">+ 走马灯</el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http, { uploadImage } from '../api.js'
import ImgUpload from '../components/ImgUpload.vue'
import LinkTarget from '../components/LinkTarget.vue'

const KINDS = { image: '图片', video: '视频', text: '文本', linkrow: '链接行', carousel: '走马灯' }
const TAG = { image: '', video: 'warning', text: 'info', linkrow: 'info', carousel: 'success' }
const RATIOS = ['3/3.9', '3/3.6', '3/3.4', '3/3.2', '1/1', '16/9']

const route = useRoute()
const router = useRouter()
const pageKey = route.params.key

const loading = ref(false)
const title = ref('')
const cover = ref('')
const coverTint = ref('#e6ddce')
const sort = ref(0)
const on = ref(true)
const fixed = ref(false)
const blocks = ref([])
const pages = ref([])
const seriesList = ref([])
const catList = ref([])
const prodList = ref([])
let seq = 0

const catLabel = (c) => (c.parent_name ? c.parent_name + ' / ' : '') + c.name
const prodLabel = (p) => p.name + (p.code ? '｜' + p.code : '')

function blank(kind) {
  const b = { _id: ++seq, _pct: 0, kind, img: '', src: '', poster: '',
              ratio: kind === 'image' ? 'hero' : '3/3.4', inset: false,
              preset: 'para', text: '', align: 'left',
              source: 'featured', series_id: null, category_id: null, spu_ids: [], count: 6,
              link: null }
  if (kind === 'linkrow') { b.left = { text: '', link: null }; b.right = { text: '', link: null } }
  return b
}

function add(kind) { blocks.value.push(blank(kind)) }

function move(i, d) {
  const [x] = blocks.value.splice(i, 1)
  blocks.value.splice(i + d, 0, x)
}

async function doVideo({ file }, b) {
  b._pct = 1
  try {
    const data = await uploadImage(file, (p) => { b._pct = p })
    b.src = data.url
  } finally {
    b._pct = 0
  }
}

// 存储态 → 编辑态（link 结构直接沿用，交给 LinkTarget 组件维护）
function toEdit(b) {
  const e = { ...blank(b.kind), ...b, _id: ++seq, _pct: 0 }
  if (b.kind === 'linkrow') {
    e.left = { text: (b.left && b.left.text) || '', link: (b.left && b.left.link) || null }
    e.right = { text: (b.right && b.right.text) || '', link: (b.right && b.right.link) || null }
  } else {
    e.link = b.link || null
  }
  return e
}

// 编辑态 → 存储态（各块只带自己的键）
function toOut(b) {
  if (b.kind === 'image') return { kind: 'image', img: b.img, ratio: b.ratio, inset: !!b.inset, link: b.link || null }
  if (b.kind === 'video') return { kind: 'video', src: b.src, poster: b.poster, ratio: b.ratio, inset: !!b.inset }
  if (b.kind === 'text') return { kind: 'text', preset: b.preset, text: b.text, align: b.align, link: b.link || null }
  if (b.kind === 'linkrow') {
    return { kind: 'linkrow',
             left: { text: b.left.text, link: b.left.link || null },
             right: { text: b.right.text, link: b.right.link || null } }
  }
  return { kind: 'carousel', source: b.source, series_id: b.series_id, category_id: b.category_id,
           spu_ids: b.spu_ids, count: b.count }
}

async function load() {
  loading.value = true
  try {
    const [page, allPages, ss, cs, ps] = await Promise.all([
      http.get('/api/admin/pages/' + pageKey),
      http.get('/api/admin/pages'),
      http.get('/api/admin/series'),
      http.get('/api/admin/categories'),
      http.get('/api/admin/products', { params: { page_size: 100 } })
    ])
    title.value = page.title
    cover.value = page.cover
    coverTint.value = page.cover_tint
    sort.value = page.sort
    on.value = page.status === 1
    fixed.value = page.fixed
    blocks.value = (page.blocks || []).map(toEdit)
    pages.value = allPages.filter((p) => p.key !== pageKey)  // 排除自身，避免自引用
    seriesList.value = ss
    catList.value = cs.filter((c) => c.parent_id !== null)  // 商品挂叶子品类
    prodList.value = ps.items
  } finally {
    loading.value = false
  }
}

async function save() {
  try {
    await http.put('/api/admin/pages/' + pageKey, {
      title: title.value, cover: cover.value, cover_tint: coverTint.value,
      sort: sort.value, status: on.value ? 1 : 0, blocks: blocks.value.map(toOut)
    })
    ElMessage.success('已保存')
  } catch (e) { /* 校验失败：拦截器已提示第几块的问题 */ }
}

function back() { router.push('/pages') }

onMounted(load)
</script>

<style scoped>
.head-row { display: flex; justify-content: space-between; align-items: center; }
.head-left { display: flex; align-items: center; gap: 12px; }
.head-ops { display: flex; align-items: center; gap: 12px; }
.sub { color: #999; font-size: 12px; }
.blocks { display: flex; flex-direction: column; gap: 12px; }
.block { border: 1px solid #e8e4dc; border-radius: 8px; padding: 10px 12px; }
.block-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.grow { flex: 1; }
.block-body { display: flex; gap: 16px; align-items: flex-start; }
.block-body-col { display: flex; flex-direction: column; gap: 8px; }
.opts { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; font-size: 12px; color: #666; }
.link-row { margin-top: 8px; padding-top: 8px; border-top: 1px dashed #eee; }
.linkrow-side { padding: 4px 0; }
.picker-label { flex-shrink: 0; }
.v-hint { margin-top: 6px; font-size: 12px; color: #67c23a; }
.add-row { display: flex; gap: 8px; }
</style>

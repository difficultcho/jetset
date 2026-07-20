<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="head-row">
        <div>
          <span>首页编排</span>
          <span class="sub" style="margin-left: 12px">
            自由编排首页区块；关闭开关或没有区块时，小程序显示内置默认排版
          </span>
        </div>
        <div class="head-ops">
          <span class="sub">启用配置化首页</span>
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

        <!-- 跳转配置（视频块不支持） -->
        <div v-if="b.kind !== 'video' && b.kind !== 'carousel'" class="opts link-row">
          <span>点击跳转
            <el-select v-model="b.lkind" size="small" style="width: 130px">
              <el-option label="不跳转" value="none" />
              <el-option label="内容页" value="post" />
              <el-option label="广告大片" value="campaign" />
              <el-option label="商品列表" value="list" />
              <el-option label="商品详情" value="pdp" />
            </el-select>
          </span>
          <span v-if="b.lkind === 'post'">内容帖
            <el-select v-model="b.lpost" size="small" filterable style="width: 240px" placeholder="选择帖子">
              <el-option v-for="p in postList" :key="p.id" :label="POST_TYPES[p.type] + '｜' + p.title" :value="p.id" />
            </el-select>
          </span>
          <template v-if="b.lkind === 'list'">
            <span>品类
              <el-select v-model="b.lcat" size="small" clearable filterable style="width: 170px" placeholder="（可选）">
                <el-option v-for="c in catList" :key="c.id" :label="catLabel(c)" :value="c.id" :disabled="c.status !== 1" />
              </el-select>
            </span>
            <span>系列
              <el-select v-model="b.lseries" size="small" clearable filterable style="width: 170px" placeholder="（可选）">
                <el-option v-for="s in seriesList" :key="s.id" :label="s.en ? s.en + '｜' + s.name : s.name"
                  :value="s.id" :disabled="s.status !== 1" />
              </el-select>
            </span>
            <span class="sub">优先品类；都不选 = 全部商品</span>
          </template>
          <span v-if="b.lkind === 'pdp'">商品
            <el-select v-model="b.lspu" size="small" filterable style="width: 240px" placeholder="选择商品">
              <el-option v-for="p in prodList" :key="p.id" :label="prodLabel(p)" :value="p.id" :disabled="p.status !== 1" />
            </el-select>
          </span>
        </div>
      </div>

      <div class="add-row">
        <el-button size="small" @click="add('image')">+ 图片</el-button>
        <el-button size="small" @click="add('video')">+ 视频</el-button>
        <el-button size="small" @click="add('text')">+ 文本</el-button>
        <el-button size="small" @click="add('carousel')">+ 走马灯</el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http, { uploadImage } from '../api.js'
import ImgUpload from '../components/ImgUpload.vue'

const KINDS = { image: '图片', video: '视频', text: '文本', carousel: '走马灯' }
const TAG = { image: '', video: 'warning', text: 'info', carousel: 'success' }
const POST_TYPES = { project: '项目', moment: '瞬间', campaign: '大片', story: '故事' }
const RATIOS = ['3/3.9', '3/3.6', '3/3.4', '3/3.2', '1/1', '16/9']

const loading = ref(false)
const on = ref(true)
const blocks = ref([])
const seriesList = ref([])
const catList = ref([])
const prodList = ref([])
const postList = ref([])
let seq = 0

const catLabel = (c) => (c.parent_name ? c.parent_name + ' / ' : '') + c.name
const prodLabel = (p) => p.name + (p.code ? '｜' + p.code : '')

function blank(kind) {
  return { _id: ++seq, _pct: 0, kind, img: '', src: '', poster: '',
           ratio: kind === 'image' ? 'hero' : '3/3.4', inset: false,
           preset: 'para', text: '', align: 'left',
           source: 'featured', series_id: null, category_id: null, spu_ids: [], count: 6,
           lkind: 'none', lpost: null, lcat: null, lseries: null, lspu: null }
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

// 存储态 → 编辑态
function toEdit(b) {
  const e = { ...blank(b.kind), ...b, _id: ++seq, _pct: 0 }
  const l = b.link
  e.lkind = (l && l.kind) || 'none'
  e.lpost = (l && l.post_id) || null
  e.lcat = (l && l.category_id) || null
  e.lseries = (l && l.series_id) || null
  e.lspu = (l && l.spu_id) || null
  delete e.link
  return e
}

// 编辑态 → 存储态（各块只带自己的键）
function toOut(b) {
  let link = null
  if (b.lkind === 'campaign') link = { kind: 'campaign' }
  if (b.lkind === 'post' && b.lpost) link = { kind: 'post', post_id: b.lpost }
  if (b.lkind === 'pdp' && b.lspu) link = { kind: 'pdp', spu_id: b.lspu }
  if (b.lkind === 'list') link = { kind: 'list', category_id: b.lcat || null, series_id: b.lseries || null }
  if (b.kind === 'image') return { kind: 'image', img: b.img, ratio: b.ratio, inset: !!b.inset, link }
  if (b.kind === 'video') return { kind: 'video', src: b.src, poster: b.poster, ratio: b.ratio, inset: !!b.inset }
  if (b.kind === 'text') return { kind: 'text', preset: b.preset, text: b.text, align: b.align, link }
  return { kind: 'carousel', source: b.source, series_id: b.series_id, category_id: b.category_id,
           spu_ids: b.spu_ids, count: b.count }
}

async function load() {
  loading.value = true
  try {
    const [page, ss, cs, ps, bp] = await Promise.all([
      http.get('/api/admin/pages/home'),
      http.get('/api/admin/series'),
      http.get('/api/admin/categories'),
      http.get('/api/admin/products', { params: { page_size: 100 } }),
      http.get('/api/admin/brand/posts')
    ])
    on.value = page.status === 1
    blocks.value = (page.blocks || []).map(toEdit)
    seriesList.value = ss
    catList.value = cs.filter((c) => c.parent_id !== null)  // 商品挂叶子品类
    prodList.value = ps.items
    postList.value = bp.filter((p) => p.status === 1 && !p.parent_id)
  } finally {
    loading.value = false
  }
}

async function save() {
  try {
    await http.put('/api/admin/pages/home', { blocks: blocks.value.map(toOut), status: on.value ? 1 : 0 })
    ElMessage.success(on.value ? '已保存并启用' : '已保存（未启用，小程序走默认排版）')
  } catch (e) { /* 校验失败：拦截器已提示第几块的问题 */ }
}

onMounted(load)
</script>

<style scoped>
.head-row { display: flex; justify-content: space-between; align-items: center; }
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
.picker-label { flex-shrink: 0; }
.v-hint { margin-top: 6px; font-size: 12px; color: #67c23a; }
.add-row { display: flex; gap: 8px; }
</style>

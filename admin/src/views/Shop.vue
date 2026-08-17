<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="head-row">
        <span>商城左菜单</span>
        <span class="sub">选中某项时，右侧上部展示它的图片跳链，下部自动展示下钻入口</span>
      </div>
    </template>

    <div class="grp-head">
      <b>上部 · 自定义项</b>
      <span class="sub">通常是系列，排在一级类目之前</span>
      <span class="grow" />
      <el-button type="primary" size="small" @click="openAdd">+ 添加系列</el-button>
    </div>
    <el-table :data="tops" size="small">
      <el-table-column label="显示名" min-width="180">
        <template #default="{ row }">
          {{ row.title || nameOf(row) }}
          <span v-if="row.en || enOf(row)" class="sub">｜{{ row.en || enOf(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="指向" min-width="140">
        <template #default="{ row }"><el-tag size="small" type="success">系列 · {{ nameOf(row) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="图片跳链" width="100">
        <template #default="{ row }">{{ (row.banners || []).length }} 张</template>
      </el-table-column>
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '显示' : '隐藏' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button link type="primary" @click="edit(row)">配置</el-button>
          <el-button link type="danger" @click="del(row)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="!tops.length" class="empty">还没有自定义项，左菜单只会显示一级类目</div>

    <div class="grp-head second">
      <b>下部 · 一级类目</b>
      <span class="sub">名称、排序、上下架以「品类管理」为准；这里只配它的图片跳链</span>
    </div>
    <el-table :data="cats" size="small">
      <el-table-column label="类目" min-width="180">
        <template #default="{ row }">
          {{ nameOf(row) }}<span v-if="row.title" class="sub">（显示为 {{ row.title }}）</span>
        </template>
      </el-table-column>
      <el-table-column label="二级类目" min-width="220">
        <template #default="{ row }"><span class="sub">{{ subsOf(row) || '—' }}</span></template>
      </el-table-column>
      <el-table-column label="图片跳链" width="100">
        <template #default="{ row }">{{ (row.banners || []).length }} 张</template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }"><el-button link type="primary" @click="edit(row)">配置</el-button></template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="addDialog" title="添加自定义项" width="420px">
    <el-form label-width="60px">
      <el-form-item label="系列">
        <el-select v-model="addId" filterable placeholder="选择系列" style="width: 100%">
          <el-option v-for="s in addable" :key="s.id" :label="(s.en ? s.en + '｜' : '') + s.name" :value="s.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="addDialog = false">取消</el-button>
      <el-button type="primary" :disabled="!addId" @click="doAdd">添加并配置</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="editDialog" :title="'配置 · ' + (cur.title || nameOf(cur))" width="760px">
    <el-form label-width="80px">
      <el-form-item label="显示名"><el-input v-model="cur.title" :placeholder="nameOf(cur)" style="width: 220px" /></el-form-item>
      <el-form-item label="英文小字"><el-input v-model="cur.en" :placeholder="enOf(cur)" style="width: 220px" /></el-form-item>
      <template v-if="cur.kind === 'series'">
        <el-form-item label="排序"><el-input-number v-model="cur.sort" :min="0" size="small" /></el-form-item>
        <el-form-item label="显示"><el-switch v-model="curOn" /></el-form-item>
      </template>
    </el-form>

    <div class="grp-head"><b>图片跳链</b><span class="sub">图片等宽依次排列；文字标题显示在图片下方左对齐；不选目标则不可点</span>
      <span class="grow" /><el-button size="small" @click="cur.banners.push({ img: '', title: '', link: null })">+ 添加图片</el-button>
    </div>
    <div v-for="(b, i) in cur.banners" :key="i" class="bn">
      <ImgUpload v-model="b.img" :size="72" />
      <div class="bn-right">
        <el-input v-model="b.title" size="small" maxlength="60" show-word-limit
          placeholder="图片下方的文字标题（留空则不显示）" />
        <LinkTarget v-model="b.link" :pages="pages" :cats="catList" :series="seriesList" :prods="prodList" />
      </div>
      <div class="bn-ops">
        <el-button link size="small" :disabled="i === 0" @click="move(i, -1)">上移</el-button>
        <el-button link size="small" :disabled="i === cur.banners.length - 1" @click="move(i, 1)">下移</el-button>
        <el-button link type="danger" size="small" @click="cur.banners.splice(i, 1)">删除</el-button>
      </div>
    </div>
    <div v-if="!cur.banners.length" class="empty">未配置图片，右侧上部留空</div>

    <template #footer>
      <el-button @click="editDialog = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api.js'
import ImgUpload from '../components/ImgUpload.vue'
import LinkTarget from '../components/LinkTarget.vue'

const LINK_KINDS = ['page', 'list', 'pdp']   // 与后端 services/pages.py 保持一致

const loading = ref(false)
const menus = ref([])
const seriesList = ref([])
const catList = ref([])
const catTree = ref([])
const pages = ref([])
const prodList = ref([])

const addDialog = ref(false)
const addId = ref(null)
const editDialog = ref(false)
const cur = ref({ kind: 'series', ref_id: 0, title: '', en: '', banners: [], sort: 0, status: 1 })
const curOn = computed({
  get: () => cur.value.status === 1,
  set: (v) => { cur.value.status = v ? 1 : 0 }
})

const tops = computed(() => menus.value.filter((m) => m.kind === 'series'))
const cats = computed(() => menus.value.filter((m) => m.kind === 'category'))
const addable = computed(() => {
  const used = new Set(tops.value.map((m) => m.ref_id))
  return seriesList.value.filter((s) => !used.has(s.id))
})

function nameOf(m) {
  const src = m.kind === 'series' ? seriesList.value : catTree.value
  const hit = src.find((x) => x.id === m.ref_id)
  return hit ? hit.name : '（已删除）'
}
function enOf(m) {
  const src = m.kind === 'series' ? seriesList.value : catTree.value
  const hit = src.find((x) => x.id === m.ref_id)
  return hit ? hit.en : ''
}
function subsOf(m) {
  return catList.value.filter((c) => c.parent_id === m.ref_id).map((c) => c.name).join('、')
}
function move(i, d) {
  const b = cur.value.banners
  const [x] = b.splice(i, 1)
  b.splice(i + d, 0, x)
}

async function load() {
  loading.value = true
  try {
    const [ms, ss, cs, ps, prods] = await Promise.all([
      http.get('/api/admin/shop/menus'),
      http.get('/api/admin/series'),
      http.get('/api/admin/categories'),
      http.get('/api/admin/pages'),
      http.get('/api/admin/products', { params: { page_size: 100 } })
    ])
    menus.value = ms
    seriesList.value = ss
    catTree.value = cs.filter((c) => c.parent_id === null)
    // 跳转目标可以是任意类目：后端按名字匹配时，有子类目的连子类目一起筛，
    // 叶子则只筛自身。过滤掉一级类目会让「没建二级的一级类目」根本没法做跳转目标。
    catList.value = cs
    pages.value = ps
    prodList.value = prods.items
  } finally {
    loading.value = false
  }
}

function openAdd() { addId.value = null; addDialog.value = true }

function doAdd() {
  const s = seriesList.value.find((x) => x.id === addId.value)
  addDialog.value = false
  cur.value = { kind: 'series', ref_id: s.id, title: '', en: '', banners: [],
                sort: (tops.value.length + 1) * 10, status: 1 }
  editDialog.value = true
}

function edit(row) {
  // 旧模型留下的跳转在新规则下非法，打开时降级为「不跳转」，避免原样回传被后端拒
  let stale = 0
  const banners = (row.banners || []).map((b) => {
    const ok = b.link && LINK_KINDS.includes(b.link.kind)
    if (b.link && !ok) stale++
    return { img: b.img, title: b.title || '', link: ok ? b.link : null }
  })
  if (stale) ElMessage.warning(`${stale} 处旧版跳转配置已失效，已重置为「不跳转」`)
  cur.value = { ...row, banners }
  editDialog.value = true
}

async function save() {
  const c = cur.value
  if (c.banners.some((b) => !b.img)) return ElMessage.warning('有图片未上传')
  await http.put('/api/admin/shop/menus', {
    kind: c.kind, ref_id: c.ref_id, title: c.title || '', en: c.en || '',
    banners: c.banners, sort: c.sort || 0, status: c.status
  })
  ElMessage.success('已保存')
  editDialog.value = false
  load()
}

async function del(row) {
  await ElMessageBox.confirm(`把「${row.title || nameOf(row)}」从左菜单移除？`, '确认', { type: 'warning' })
  await http.delete('/api/admin/shop/menus/' + row.id)
  ElMessage.success('已移除')
  load()
}

onMounted(load)
</script>

<style scoped>
.head-row { display: flex; align-items: baseline; gap: 16px; }
.grp-head { display: flex; align-items: baseline; gap: 12px; margin: 8px 0 12px; }
.grp-head.second { margin-top: 32px; }
.grow { flex: 1; }
.sub { color: #999; font-size: 12px; }
.empty { color: #bbb; font-size: 13px; padding: 16px 0; text-align: center; }
.bn { display: flex; align-items: center; gap: 16px; padding: 12px 0; border-bottom: 1px solid #f0f0f0; }
.bn-right { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.bn-ops { display: flex; gap: 4px; }
</style>

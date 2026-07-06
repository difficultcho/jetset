<template>
  <el-card>
    <div class="toolbar">
      <el-radio-group v-model="status" @change="fetch">
        <el-radio-button label="pending">待审核</el-radio-button>
        <el-radio-button label="approved">已通过</el-radio-button>
        <el-radio-button label="rejected">已驳回</el-radio-button>
        <el-radio-button label="">全部</el-radio-button>
      </el-radio-group>
    </div>

    <el-table :data="list" v-loading="loading">
      <el-table-column prop="company" label="公司" min-width="160" />
      <el-table-column prop="type" label="类型" width="90" />
      <el-table-column prop="phone" label="联系方式" width="130" />
      <el-table-column prop="region" label="地区" width="150" />
      <el-table-column label="资质" width="150">
        <template #default="{ row }">
          <el-image :src="imgUrl(row.license_img)" class="thumb" fit="cover" :preview-src-list="[imgUrl(row.license_img), imgUrl(row.store_img)]" />
          <el-image :src="imgUrl(row.store_img)" class="thumb" fit="cover" :preview-src-list="[imgUrl(row.store_img), imgUrl(row.license_img)]" />
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'pending' ? 'warning' : row.status === 'approved' ? 'success' : 'info'" size="small">
            {{ { pending: '待审核', approved: '已通过', rejected: '已驳回' }[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="review_note" label="备注" min-width="120" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button link type="success" @click="review(row, 'approve')">通过</el-button>
            <el-button link type="danger" @click="review(row, 'reject')">驳回</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
      :page-size="pageSize" :current-page="page" @current-change="(p) => { page = p; fetch() }" />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http, { imgUrl } from '../api.js'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const status = ref('pending')
const loading = ref(false)

async function fetch() {
  loading.value = true
  try {
    const data = await http.get('/api/admin/wholesale', {
      params: { status: status.value || undefined, page: page.value, page_size: pageSize }
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function review(row, action) {
  const { value: note } = await ElMessageBox.prompt(
    action === 'approve' ? '通过备注（可空）' : '驳回原因（可空）',
    action === 'approve' ? '通过申请' : '驳回申请',
    { confirmButtonText: '确定', cancelButtonText: '取消', inputValue: '' }
  ).catch(() => ({}))
  if (note === undefined) return
  await http.post(`/api/admin/wholesale/${row.id}/review`, { action, note: note || '' })
  ElMessage.success('已处理')
  fetch()
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.thumb { width: 56px; height: 56px; border-radius: 4px; margin-right: 6px; border: 1px solid #eee; }
.pager { margin-top: 16px; justify-content: flex-end; }
</style>

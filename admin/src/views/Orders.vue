<template>
  <el-card>
    <div class="toolbar">
      <el-radio-group v-model="status" @change="() => { page = 1; fetch() }">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button v-for="(v, k) in STATUS" :key="k" :label="k">{{ v }}</el-radio-button>
      </el-radio-group>
      <el-input v-model="q" placeholder="搜索订单号" clearable style="width: 220px" @change="fetch" />
    </div>

    <el-table :data="list" v-loading="loading">
      <el-table-column prop="order_no" label="订单号" width="180" />
      <el-table-column label="商品" min-width="200">
        <template #default="{ row }">
          <div v-for="it in row.items" :key="it.sku_id" class="line">
            {{ it.name }}（{{ it.color_name }}/{{ it.size }}）×{{ it.qty }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="金额" width="100">
        <template #default="{ row }">¥{{ (row.pay_amount / 100).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="收货人" width="120">
        <template #default="{ row }">{{ row.address && row.address.name }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="TAG[row.status] || 'info'" size="small">{{ row.status_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="下单时间" width="170">
        <template #default="{ row }">{{ fmt(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending_shipment'" link type="primary" @click="openShip(row)">发货</el-button>
          <el-button v-if="row.status === 'pending_receipt' || row.status === 'pending_review'" link type="primary" @click="markDone(row)">完成</el-button>
          <el-button v-if="showRefund(row)" link type="primary" @click="refundOrder(row)">{{ refundLabel(row) }}</el-button>
          <el-button link @click="detail = row">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
      :page-size="pageSize" :current-page="page" @current-change="(p) => { page = p; fetch() }" />
  </el-card>

  <!-- 发货 -->
  <el-dialog v-model="shipDialog" title="订单发货" width="420px">
    <el-form label-width="80px">
      <el-form-item label="物流公司">
        <el-select v-model="ship.express_code" placeholder="请选择" style="width: 100%">
          <el-option v-for="c in CARRIERS" :key="c.code" :label="c.name" :value="c.code" />
        </el-select>
      </el-form-item>
      <el-form-item label="运单号"><el-input v-model="ship.tracking_no" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="shipDialog = false">取消</el-button>
      <el-button type="primary" :loading="shipping" @click="doShip">确认发货</el-button>
    </template>
  </el-dialog>

  <!-- 详情 -->
  <el-drawer :model-value="!!detail" title="订单详情" size="420px" @close="detail = null">
    <template v-if="detail">
      <p><b>订单号：</b>{{ detail.order_no }}</p>
      <p><b>状态：</b>{{ detail.status_label }}</p>
      <p><b>收货：</b>{{ detail.address.name }} {{ detail.address.phone }}</p>
      <p style="color: #666">{{ detail.address.region }} {{ detail.address.detail }}</p>
      <p v-if="detail.note"><b>备注：</b>{{ detail.note }}</p>
      <p v-if="detail.shipment"><b>物流：</b>{{ detail.shipment.company }} {{ detail.shipment.tracking_no }}</p>
      <p v-if="detail.refund"><b>退款：</b>{{ detail.refund.status_label }}　{{ detail.refund.reason }}</p>
      <p v-if="detail.refund && detail.refund.reject_reason"><b>拒绝原因：</b>{{ detail.refund.reject_reason }}</p>
      <el-divider />
      <div v-for="it in detail.items" :key="it.sku_id" class="d-item">
        <div>{{ it.name }}</div>
        <div class="sub">{{ it.color_name }} / {{ it.size }} × {{ it.qty }} — ¥{{ (it.price / 100).toFixed(2) }}</div>
      </div>
      <el-divider />
      <p><b>应付：</b>¥{{ (detail.pay_amount / 100).toFixed(2) }}</p>
    </template>
  </el-drawer>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api.js'

const STATUS = {
  pending_payment: '待付款', pending_shipment: '待发货', pending_receipt: '待收货',
  completed: '已完成', cancelled: '已取消', refund_pending: '退款中', refunded: '已退款'
}
const TAG = { pending_payment: 'warning', pending_shipment: 'danger', pending_receipt: 'primary',
              completed: 'success', cancelled: 'info', refund_pending: 'warning', refunded: 'info' }

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const status = ref('')
const q = ref('')
const loading = ref(false)
const detail = ref(null)
const shipDialog = ref(false)
const shipping = ref(false)
const CARRIERS = [
  { code: 'SF', name: '顺丰速运' },
  { code: 'YTO', name: '圆通速递' },
  { code: 'ZTO', name: '中通快递' },
  { code: 'STO', name: '申通快递' },
  { code: 'YD', name: '韵达速递' },
  { code: 'JTSD', name: '极兔速递' },
  { code: 'JD', name: '京东物流' },
  { code: 'EMS', name: 'EMS' },
  { code: 'DBL', name: '德邦快递' }
]
const ship = ref({ id: null, express_code: '', tracking_no: '' })

const fmt = (s) => (s ? String(s).replace('T', ' ').slice(0, 19) : '')

async function fetch() {
  loading.value = true
  try {
    const data = await http.get('/api/admin/orders', {
      params: { status: status.value || undefined, q: q.value || undefined, page: page.value, page_size: pageSize }
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openShip(row) {
  ship.value = { id: row.id, express_code: '', tracking_no: '' }
  shipDialog.value = true
}

function showRefund(row) {
  if (row.status === 'pending_shipment' || row.status === 'pending_receipt' || row.status === 'completed') return true
  return row.status === 'refund_pending' && row.refund && (row.refund.status === 'failed' || row.refund.status === 'pending')
}

function refundLabel(row) {
  return row.status === 'refund_pending' ? '重试退款' : '退款'
}

async function markDone(row) {
  try {
    await ElMessageBox.confirm(`将订单 ${row.order_no} 标为已完成？`, '确认', { type: 'warning' })
  } catch {
    return
  }
  await http.post(`/api/admin/orders/${row.id}/complete`)
  ElMessage.success('已标为已完成')
  if (detail.value && detail.value.id === row.id) detail.value = null
  fetch()
}

async function refundOrder(row) {
  try {
    await ElMessageBox.confirm(
      '确认已完成客服核验，对该订单全额原路退款？已发货订单须已由买家自费退回并完成污损检查。',
      '确认退款',
      { type: 'warning' }
    )
  } catch {
    return
  }
  const data = await http.post(`/api/admin/orders/${row.id}/refund`, {})
  ElMessage.success(data.status === 'refunded' ? '已退款' : '已提交微信退款')
  if (detail.value && detail.value.id === row.id) detail.value = null
  fetch()
}

async function doShip() {
  const carrier = CARRIERS.find((c) => c.code === ship.value.express_code)
  if (!carrier || !ship.value.tracking_no) return ElMessage.warning('请选择快递公司并填写运单号')
  shipping.value = true
  try {
    await http.post(`/api/admin/orders/${ship.value.id}/ship`, {
      company: carrier.name,
      express_code: carrier.code,
      tracking_no: ship.value.tracking_no
    })
    ElMessage.success('已发货')
    shipDialog.value = false
    fetch()
  } finally {
    shipping.value = false
  }
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; justify-content: space-between; }
.line { font-size: 13px; }
.sub { color: #999; font-size: 12px; }
.pager { margin-top: 16px; justify-content: flex-end; }
.d-item { margin-bottom: 8px; }
</style>

<template>
  <el-card>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">+ 新建优惠券</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="name" label="名称" min-width="150" />
      <el-table-column label="规则" width="180">
        <template #default="{ row }">
          {{ row.threshold ? `满 ${yuan(row.threshold)}` : '无门槛' }} 减 {{ yuan(row.amount) }}
        </template>
      </el-table-column>
      <el-table-column label="有效期" width="170">
        <template #default="{ row }">
          {{ row.valid_days ? `领取后 ${row.valid_days} 天` : '' }}
          {{ row.valid_until ? `至 ${String(row.valid_until).slice(0, 10)}` : '' }}
        </template>
      </el-table-column>
      <el-table-column label="发行/领取/已用" width="140">
        <template #default="{ row }">
          {{ row.total || '不限' }} / {{ row.taken }} / {{ row.used }}
        </template>
      </el-table-column>
      <el-table-column prop="per_user_limit" label="限领" width="70" />
      <el-table-column label="可领取" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.status === 1" @change="(v) => toggle(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialog" :title="form.id ? '编辑优惠券' : '新建优惠券'" width="520px">
    <el-form label-width="110px">
      <el-form-item label="名称" required>
        <el-input v-model="form.name" placeholder="如：满 2000 减 200" />
      </el-form-item>
      <el-form-item label="使用门槛(元)">
        <el-input-number v-model="form.thresholdYuan" :min="0" :precision="2" style="width: 180px" />
        <span class="hint">0 = 无门槛</span>
      </el-form-item>
      <el-form-item label="减免金额(元)" required>
        <el-input-number v-model="form.amountYuan" :min="0.01" :precision="2" style="width: 180px" />
      </el-form-item>
      <el-form-item label="发行量">
        <el-input-number v-model="form.total" :min="0" style="width: 180px" />
        <span class="hint">0 = 不限量</span>
      </el-form-item>
      <el-form-item label="每人限领">
        <el-input-number v-model="form.per_user_limit" :min="1" style="width: 180px" />
      </el-form-item>
      <el-form-item label="有效期">
        <el-radio-group v-model="form.validType">
          <el-radio value="days">领取后 N 天</el-radio>
          <el-radio value="until">固定截止日</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.validType === 'days'" label="有效天数">
        <el-input-number v-model="form.valid_days" :min="1" style="width: 180px" />
      </el-form-item>
      <el-form-item v-else label="截止日期">
        <el-date-picker v-model="form.valid_until" type="date" style="width: 180px" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api.js'

const list = ref([])
const loading = ref(false)
const dialog = ref(false)
const saving = ref(false)
const form = ref(emptyForm())

const yuan = (cents) => '¥' + (cents / 100).toFixed(2).replace(/\.00$/, '')

function emptyForm() {
  return { id: null, name: '', thresholdYuan: 0, amountYuan: 0, total: 0,
           per_user_limit: 1, validType: 'days', valid_days: 30, valid_until: null, status: 1 }
}

async function fetch() {
  loading.value = true
  try {
    list.value = await http.get('/api/admin/coupons')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = emptyForm()
  dialog.value = true
}

function openEdit(row) {
  form.value = {
    id: row.id, name: row.name, thresholdYuan: row.threshold / 100, amountYuan: row.amount / 100,
    total: row.total, per_user_limit: row.per_user_limit,
    validType: row.valid_days ? 'days' : 'until',
    valid_days: row.valid_days || 30, valid_until: row.valid_until, status: row.status
  }
  dialog.value = true
}

async function save() {
  const f = form.value
  if (!f.name) return ElMessage.warning('请填写名称')
  if (!f.amountYuan) return ElMessage.warning('请填写减免金额')
  if (f.validType === 'until' && !f.valid_until) return ElMessage.warning('请选择截止日期')
  const payload = {
    name: f.name,
    threshold: Math.round(f.thresholdYuan * 100),
    amount: Math.round(f.amountYuan * 100),
    total: f.total, per_user_limit: f.per_user_limit,
    valid_days: f.validType === 'days' ? f.valid_days : null,
    valid_until: f.validType === 'until' ? f.valid_until : null,
    status: f.status
  }
  saving.value = true
  try {
    if (f.id) await http.put('/api/admin/coupons/' + f.id, payload)
    else await http.post('/api/admin/coupons', payload)
    ElMessage.success('已保存')
    dialog.value = false
    fetch()
  } finally {
    saving.value = false
  }
}

async function toggle(row, on) {
  await http.post(`/api/admin/coupons/${row.id}/status`, { status: on ? 1 : 0 })
  row.status = on ? 1 : 0
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.hint { color: #999; font-size: 12px; margin-left: 8px; }
</style>

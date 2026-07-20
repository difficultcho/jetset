<template>
  <el-row :gutter="16">
    <el-col :span="8" v-for="c in cards" :key="c.label">
      <el-card class="stat-card">
        <div class="stat-value">{{ c.value }}</div>
        <div class="stat-label">{{ c.label }}</div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api.js'

const stats = ref(null)

const cards = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    { label: '近24h 订单数', value: s.orders_24h },
    { label: '近24h 支付额（元）', value: (s.gmv_24h / 100).toFixed(2) },
    { label: '待发货订单', value: s.pending_shipment },
    { label: '待审核门店申请', value: s.pending_wholesale },
    { label: '注册用户', value: s.users },
    { label: '在售商品', value: s.products_on }
  ]
})

onMounted(async () => {
  stats.value = await http.get('/api/admin/stats')
})
</script>

<style scoped>
.stat-card { margin-bottom: 16px; text-align: center; }
.stat-value { font-size: 32px; font-weight: 700; }
.stat-label { color: #888; margin-top: 8px; font-size: 13px; }
</style>

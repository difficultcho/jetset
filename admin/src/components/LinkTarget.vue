<template>
  <span class="lt">
    <span>点击跳转
      <el-select :model-value="kind" size="small" style="width: 120px" @change="onKind">
        <el-option label="不跳转" value="none" />
        <el-option label="内容页" value="page" />
        <el-option label="商品列表" value="list" />
        <el-option label="商品详情" value="pdp" />
      </el-select>
    </span>
    <span v-if="kind === 'page'">页面
      <el-select :model-value="v.key" size="small" filterable style="width: 220px" placeholder="选择页面"
        @change="(x) => set({ key: x })">
        <el-option v-for="p in pages" :key="p.key" :label="pageLabel(p)" :value="p.key"
          :disabled="p.status !== 1" />
      </el-select>
    </span>
    <template v-else-if="kind === 'list'">
      <span>品类
        <el-select :model-value="v.category_id" clearable filterable size="small" style="width: 150px"
          placeholder="（可选）" @change="(x) => set({ category_id: x })">
          <el-option v-for="c in cats" :key="c.id" :label="catLabel(c)" :value="c.id" :disabled="c.status !== 1" />
        </el-select>
      </span>
      <span>系列
        <el-select :model-value="v.series_id" clearable filterable size="small" style="width: 150px"
          placeholder="（可选）" @change="(x) => set({ series_id: x })">
          <el-option v-for="s in series" :key="s.id" :label="s.en ? s.en + '｜' + s.name : s.name"
            :value="s.id" :disabled="s.status !== 1" />
        </el-select>
      </span>
      <span class="sub">优先品类；都不选 = 全部商品</span>
    </template>
    <span v-else-if="kind === 'pdp'">商品
      <el-select :model-value="v.spu_id" size="small" filterable style="width: 220px" placeholder="选择商品"
        @change="(x) => set({ spu_id: x })">
        <el-option v-for="p in prods" :key="p.id" :label="prodLabel(p)" :value="p.id" :disabled="p.status !== 1" />
      </el-select>
    </span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: null },
  pages: { type: Array, default: () => [] },
  cats: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  prods: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue'])

const pageLabel = (p) => (p.title || '（未命名）') + (p.fixed ? '｜固定挂载' : '')
const catLabel = (c) => (c.parent_name ? c.parent_name + ' / ' : '') + c.name
const prodLabel = (p) => p.name + (p.code ? '｜' + p.code : '')

const v = computed(() => props.modelValue || {})
const kind = computed(() => v.value.kind || 'none')

// 切换目标类型：none→清空；其余先落 kind，等选具体对象补 key/id
function onKind(k) {
  if (k === 'none') emit('update:modelValue', null)
  else emit('update:modelValue', { kind: k })
}
function set(patch) {
  emit('update:modelValue', { ...v.value, ...patch })
}
</script>

<style scoped>
.lt { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
.sub { color: #999; }
</style>

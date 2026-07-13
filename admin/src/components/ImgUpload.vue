<template>
  <div v-if="modelValue" class="iu-item" :style="box">
    <el-image :src="imgUrl(modelValue)" fit="cover" class="iu-img" :preview-src-list="[imgUrl(modelValue)]" />
    <el-button class="iu-del" link type="danger" size="small"
      @click="$emit('update:modelValue', '')">删除</el-button>
  </div>
  <el-upload v-else :show-file-list="false" :http-request="doUpload" accept="image/*">
    <div class="iu-box" :style="box">{{ pct ? pct + '%' : '+ 上传' }}</div>
  </el-upload>
</template>

<script setup>
import { computed, ref } from 'vue'
import { imgUrl, uploadImage } from '../api.js'

const props = defineProps({ modelValue: { type: String, default: '' }, size: { type: Number, default: 96 } })
const emit = defineEmits(['update:modelValue'])
const box = computed(() => ({ width: props.size + 'px', height: props.size + 'px' }))
const pct = ref(0)

async function doUpload({ file }) {
  pct.value = 1
  try {
    const data = await uploadImage(file, (p) => { pct.value = p })
    emit('update:modelValue', data.url)
  } finally {
    pct.value = 0
  }
}
</script>

<style scoped>
.iu-item { position: relative; }
.iu-img { width: 100%; height: 100%; border-radius: 6px; border: 1px solid #eee; display: block; }
.iu-del { position: absolute; right: 0; bottom: -24px; }
.iu-box {
  border: 1px dashed #ccc; border-radius: 6px; box-sizing: border-box;
  display: flex; align-items: center; justify-content: center; color: #999; cursor: pointer;
}
</style>

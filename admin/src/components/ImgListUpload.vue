<template>
  <div class="il">
    <div v-for="(url, i) in modelValue" :key="url + i" class="il-item">
      <el-image :src="imgUrl(url)" fit="cover" class="il-img" :preview-src-list="[imgUrl(url)]" />
      <div class="il-ops">
        <el-button link size="small" :disabled="i === 0" @click="move(i, -1)">←</el-button>
        <el-button link type="danger" size="small" @click="remove(i)">删</el-button>
        <el-button link size="small" :disabled="i === modelValue.length - 1" @click="move(i, 1)">→</el-button>
      </div>
    </div>
    <el-upload :show-file-list="false" :http-request="doUpload" accept="image/*">
      <div class="il-box">{{ pct ? pct + '%' : '+ 上传' }}</div>
    </el-upload>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { imgUrl, uploadImage } from '../api.js'

const props = defineProps({ modelValue: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue'])
const pct = ref(0)

async function doUpload({ file }) {
  pct.value = 1
  try {
    const data = await uploadImage(file, (p) => { pct.value = p })
    emit('update:modelValue', [...props.modelValue, data.url])
  } finally {
    pct.value = 0
  }
}

function remove(i) {
  const next = [...props.modelValue]
  next.splice(i, 1)
  emit('update:modelValue', next)
}

function move(i, delta) {
  const next = [...props.modelValue]
  const [x] = next.splice(i, 1)
  next.splice(i + delta, 0, x)
  emit('update:modelValue', next)
}
</script>

<style scoped>
.il { display: flex; gap: 12px; flex-wrap: wrap; }
.il-item { width: 96px; }
.il-img { width: 96px; height: 96px; border-radius: 6px; border: 1px solid #eee; display: block; }
.il-ops { display: flex; justify-content: center; gap: 2px; }
.il-box {
  width: 96px; height: 96px; border: 1px dashed #ccc; border-radius: 6px;
  display: flex; align-items: center; justify-content: center; color: #999; cursor: pointer;
}
</style>

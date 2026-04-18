<template>
  <!-- V5.3标记已采购弹窗 - 科长级专属
      FIXED in V5.3: 必须输入新主标题，触发原标题降级为副标题 -->
  <el-dialog
    title="标记为已采购"
    :model-value="visible"
    width="480px"
    @close="$emit('close')"
  >
    <div v-if="project" class="purchased-tip">
      <p>项目 #{{ project.id }} 当前状态: <el-tag size="small">{{ project.status }}</el-tag></p>
      <p class="warn-text">
        确认后将触发标题降级：
        原主标题 <strong>"{{ project.main_title }}"</strong> 将降级为副标题，
        请输入采购后的新主标题（采购物品名称）。
      </p>
    </div>

    <el-form label-width="100px">
      <el-form-item label="新主标题">
        <el-input
          v-model="newMainTitle"
          placeholder="如：手术室LED无影灯-明视医疗(已签约)"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="$emit('close')">取消</el-button>
      <el-button type="success" :loading="submitting" @click="submit">确认已采购</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage } from 'element-plus'

const store = useAppStore()
const emit = defineEmits(['close', 'confirmed'])

const props = defineProps({
  visible: Boolean,
  project: { type: Object, default: null },
})

const newMainTitle = ref('')
const submitting = ref(false)

async function submit() {
  if (!newMainTitle.value.trim()) {
    ElMessage.warning('请输入采购后的新主标题')
    return
  }
  submitting.value = true
  try {
    await store.request('PUT', `/projects/${props.project.id}/status`, {
      status: '已采购',
      new_main_title: newMainTitle.value.trim(),
    })
    ElMessage.success('已标记为已采购，标题已降级')
    newMainTitle.value = ''
    emit('confirmed')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.purchased-tip {
  background: #fdf6ec;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 16px;
}
.warn-text {
  color: #e6a23c;
  font-size: 13px;
  margin-top: 8px;
}
</style>
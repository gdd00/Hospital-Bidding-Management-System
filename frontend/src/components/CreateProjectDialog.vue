<template>
  <!-- V5.3创建需求弹窗 - 仅科长级可见 -->
  <el-dialog title="新建需求项目" :model-value="visible" width="460px" @close="$emit('close')">
    <el-form :model="form" label-width="90px">
      <el-form-item label="需求名称">
        <el-input
          v-model="form.main_title"
          placeholder="例如：ICU监护仪需求申报"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('close')">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确认创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage } from 'element-plus'

const store = useAppStore()
const emit = defineEmits(['close', 'created'])

defineProps({ visible: Boolean })

const form = reactive({ main_title: '' })
const submitting = ref(false)

async function submit() {
  if (!form.main_title.trim()) {
    ElMessage.warning('请输入需求名称')
    return
  }
  submitting.value = true
  try {
    await store.request('POST', '/projects', { main_title: form.main_title.trim() })
    ElMessage.success('需求已创建')
    form.main_title = ''
    emit('created')
  } finally {
    submitting.value = false
  }
}
</script>
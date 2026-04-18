<template>
  <!-- V5.3补充采购数据弹窗 - 采购科专属，动态表单设计
      FIXED in V5.3: 新增"添加自定义字段"按钮，JSON可自由拓展 -->
  <el-dialog
    title="补充采购数据"
    :model-value="visible"
    width="640px"
    @close="$emit('close')"
  >
    <div v-if="project" class="procurement-header">
      <span>项目 #{{ project.id }}: {{ project.main_title }}</span>
      <el-tag size="small">{{ project.status }}</el-tag>
      <el-tag v-if="existingRecords.length" type="warning" size="small">
        已有{{ existingRecords.length }}条报价
      </el-tag>
    </div>

    <!-- ── 已有供应商记录摘要 ────────────────────────────────── -->
    <div v-if="existingRecords.length" class="existing-records">
      <el-divider content-position="left">已有供应商记录</el-divider>
      <el-table :data="existingRecords" stripe size="small" max-height="180">
        <el-table-column prop="supplier_name" label="供应商" width="120" />
        <el-table-column prop="quotation" label="报价" width="120" />
        <el-table-column prop="contact_person" label="联系人" width="80" />
      </el-table>
    </div>

    <el-divider content-position="left">新增一条供应商记录</el-divider>

    <!-- ── 固定字段 ──────────────────────────────────────────── -->
    <el-form label-width="100px" size="default">
      <el-form-item label="供应商名称">
        <el-input v-model="fields.supplier_name" placeholder="供应商全称" />
      </el-form-item>
      <el-form-item label="联系人">
        <el-input v-model="fields.contact_person" placeholder="对接人姓名" />
      </el-form-item>
      <el-form-item label="联系电话">
        <el-input v-model="fields.contact_phone" placeholder="手机或座机" />
      </el-form-item>
      <el-form-item label="报价">
        <el-input v-model="fields.quotation" placeholder="如：¥85,000/台" />
      </el-form-item>
      <el-form-item label="资质文件说明">
        <el-input v-model="fields.qualification_desc" type="textarea" :rows="2" placeholder="许可证、认证等" />
      </el-form-item>

      <!-- ── 扩展字段(V5.3新增) ──────────────────────────────── -->
      <el-form-item label="交付日期">
        <el-input v-model="fields.delivery_date" placeholder="预计交付日期" />
      </el-form-item>
      <el-form-item label="合同编号">
        <el-input v-model="fields.contract_no" placeholder="如: HT-2026-xxxx" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="fields.notes" type="textarea" :rows="2" />
      </el-form-item>

      <!-- ── 自定义字段区 ────────────────────────────────────── -->
      <el-divider content-position="left">自定义字段</el-divider>

      <div v-for="(cf, idx) in customFields" :key="idx" class="custom-field-row">
        <el-form-item :label="cf.key" label-width="100px">
          <div class="custom-field-inputs">
            <el-input v-model="cf.key" placeholder="字段名" style="width: 140px" />
            <el-input v-model="cf.value" placeholder="字段值" style="width: 260px; margin-left: 8px" />
            <el-button type="danger" size="small" circle @click="removeCustomField(idx)">
              ✕
            </el-button>
          </div>
        </el-form-item>
      </div>

      <el-form-item label="">
        <el-button type="primary" size="small" plain @click="addCustomField">
          + 添加自定义字段
        </el-button>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="$emit('close')">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存采购数据</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage } from 'element-plus'

const store = useAppStore()
const emit = defineEmits(['close', 'saved'])

const props = defineProps({
  visible: Boolean,
  project: { type: Object, default: null },
})

// ── 已有记录 ──────────────────────────────────────────────────
const existingRecords = computed(() => {
  if (!props.project?.procurement_data) return []
  // V5.2遗留逻辑兼容: 旧数据可能是单个dict
  const pd = props.project.procurement_data
  return Array.isArray(pd) ? pd : (pd && pd.supplier_name ? [pd] : [])
})

// ── 固定字段(每次新增一条) ──────────────────────────────────
const fields = reactive({
  supplier_name: '',
  contact_person: '',
  contact_phone: '',
  quotation: '',
  qualification_desc: '',
  delivery_date: '',
  contract_no: '',
  notes: '',
})

const customFields = ref([])

function addCustomField() { customFields.value.push({ key: '', value: '' }) }
function removeCustomField(idx) { customFields.value.splice(idx, 1) }

// ── 每次打开弹窗清空表单(追加新记录，不回填旧数据) ──────────
watch(() => props.visible, (v) => {
  if (v) {
    for (const k of Object.keys(fields)) fields[k] = ''
    customFields.value = []
  }
})

const submitting = ref(false)

async function submit() {
  if (!fields.supplier_name.trim()) {
    ElMessage.warning('请填写供应商名称')
    return
  }
  submitting.value = true
  try {
    const data = { ...fields }
    for (const cf of customFields.value) {
      if (cf.key.trim()) data[cf.key.trim()] = cf.value
    }

    await store.request('PUT', `/projects/${props.project.id}/procurement`, { data })
    ElMessage.success('供应商记录已追加')
    emit('saved')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.procurement-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.custom-field-row {
  margin-bottom: 4px;
}
.custom-field-inputs {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
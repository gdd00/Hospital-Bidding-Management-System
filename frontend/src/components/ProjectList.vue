<template>
  <!-- V5.3项目列表 - 时间倒序 + 按钮逻辑改造 -->
  <el-table :data="projects" v-loading="loading" stripe border style="width: 100%">
    <el-table-column label="主标题" min-width="220">
      <template #default="{ row }">
        <span class="title-link" :class="{ purchased: isPostPurchased(row) }" @click="$emit('open-detail', row)">
          {{ row.main_title }}
        </span>
        <div v-if="row.sub_title" class="sub-title">(原需求: {{ row.sub_title }})</div>
      </template>
    </el-table-column>

    <el-table-column prop="status" label="状态" width="110">
      <template #default="{ row }">
        <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
      </template>
    </el-table-column>

    <el-table-column prop="creator_name" label="创建人" width="90" />

    <el-table-column label="供应商" width="140">
      <template #default="{ row }">
        <template v-if="row.procurement_data && row.procurement_data.length">
          {{ row.procurement_data.length }}条报价
        </template>
        <span v-else class="no-data">--</span>
      </template>
    </el-table-column>

    <el-table-column label="创建时间" width="170">
      <template #default="{ row }">
        {{ formatTime(row.created_at) }}
      </template>
    </el-table-column>

    <el-table-column label="操作" width="260" fixed="right">
      <template #default="{ row }">
        <!-- 补充采购数据: 需求填报/寻找供应商阶段均可，但已报废不可 -->
        <el-button
          v-if="store.canWriteProcurement && row.status !== '已报废'"
          type="warning"
          size="small"
          @click="$emit('open-procurement', row)"
        >
          补充采购数据
        </el-button>

        <!-- 推进寻源: 至少有一条采购记录后才出现 -->
        <el-button
          v-if="store.canAdvanceToSupplier && row.status === '需求填报' && row.has_records"
          type="primary"
          size="small"
          @click="advanceStatus(row, '寻找供应商')"
        >
          推进寻源
        </el-button>

        <!-- 标记已采购: 至少有一条采购记录 -->
        <el-button
          v-if="store.canAdvanceStatus && row.status === '寻找供应商' && row.has_records"
          type="success"
          size="small"
          @click="$emit('open-purchased', row)"
        >
          标记已采购
        </el-button>

        <!-- 计划报废/确认报废 -->
        <el-button
          v-if="store.canAdvanceStatus && row.status === '已采购'"
          type="danger"
          size="small"
          @click="advanceStatus(row, '计划报废')"
        >
          计划报废
        </el-button>
        <el-button
          v-if="store.canAdvanceStatus && row.status === '计划报废'"
          type="danger"
          size="small"
          plain
          @click="advanceStatus(row, '已报废')"
        >
          确认报废
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { useAppStore } from '../stores/app'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useAppStore()
const emit = defineEmits(['refresh', 'open-procurement', 'open-purchased', 'open-detail'])

defineProps({
  projects: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

function isPostPurchased(row) {
  return ['已采购', '计划报废', '已报废'].includes(row.status)
}

function statusTagType(status) {
  const map = { '需求填报': 'info', '寻找供应商': 'warning', '已采购': 'success', '计划报废': 'danger', '已报废': '' }
  return map[status] || 'info'
}

function formatTime(ts) {
  if (!ts) return '--'
  return new Date(ts).toLocaleString('zh-CN')
}

async function advanceStatus(project, targetStatus) {
  const labels = { '寻找供应商': '推进到寻找供应商', '计划报废': '标记为计划报废', '已报废': '确认报废' }
  try {
    await ElMessageBox.confirm(
      `确认将项目 #${project.id} "${project.main_title}" ${labels[targetStatus]}？`,
      '状态流转确认',
      { type: 'warning' },
    )
    await store.request('PUT', `/projects/${project.id}/status`, { status: targetStatus })
    ElMessage.success('状态已更新')
    emit('refresh')
  } catch { /* 取消或报错 */ }
}
</script>

<style scoped>
.title-link {
  cursor: pointer;
  color: #409eff;
  transition: color 0.2s;
}
.title-link:hover { color: #66b1ff; }
.title-link.purchased { color: #67c23a; font-weight: 600; }
.title-link.purchased:hover { color: #85ce61; }
.sub-title { font-size: 12px; color: #909399; margin-top: 2px; }
.no-data { color: #c0c4cc; }
</style>
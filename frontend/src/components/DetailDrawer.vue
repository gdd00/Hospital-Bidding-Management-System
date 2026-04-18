<template>
  <!-- V5.3项目详情抽屉 - 供应商对比图表 + 多条记录表格 -->
  <el-drawer
    :model-value="visible"
    size="580px"
    @close="$emit('close')"
  >
    <template #header>
      <div class="drawer-header">
        <span>项目详情</span>
        <el-tag v-if="project" :type="statusTagType(project.status)" size="small">
          {{ project.status }}
        </el-tag>
      </div>
    </template>

    <template v-if="project">
      <!-- ── 标题 ──────────────────────────────────────────────── -->
      <h3 class="detail-title">{{ project.main_title }}</h3>
      <div v-if="project.sub_title" class="detail-sub-title">
        原需求名称: {{ project.sub_title }}
      </div>

      <el-descriptions :column="2" border size="default" style="margin-top: 12px">
        <el-descriptions-item label="项目ID">{{ project.id }}</el-descriptions-item>
        <el-descriptions-item label="创建人">{{ project.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(project.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatTime(project.updated_at) }}</el-descriptions-item>
      </el-descriptions>

      <!-- ── 供应商报价对比图表 ──────────────────────────────────── -->
      <template v-if="records.length >= 2">
        <el-divider content-position="left">供应商报价对比</el-divider>
        <v-chart :option="barChartOption" autoresize style="height: 240px" />
      </template>

      <!-- ── 供应商记录列表 ──────────────────────────────────────── -->
      <template v-if="records.length">
        <el-divider content-position="left">
          供应商记录 ({{ records.length }}条)
        </el-divider>

        <el-collapse>
          <el-collapse-item
            v-for="(rec, idx) in records"
            :key="idx"
            :title="rec.supplier_name || `供应商#${idx+1}`"
            :name="idx"
          >
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="供应商">{{ rec.supplier_name || '--' }}</el-descriptions-item>
              <el-descriptions-item label="联系人">{{ rec.contact_person || '--' }}</el-descriptions-item>
              <el-descriptions-item label="联系电话">{{ rec.contact_phone || '--' }}</el-descriptions-item>
              <el-descriptions-item label="报价">
                <span class="price">{{ rec.quotation || '--' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="资质说明">{{ rec.qualification_desc || '--' }}</el-descriptions-item>
              <el-descriptions-item label="交付日期">{{ rec.delivery_date || '--' }}</el-descriptions-item>
              <el-descriptions-item label="合同编号">{{ rec.contract_no || '--' }}</el-descriptions-item>
              <el-descriptions-item label="备注">{{ rec.notes || '--' }}</el-descriptions-item>
              <!-- 自定义字段 -->
              <template v-for="(val, key) in extraFields(rec)" :key="key">
                <el-descriptions-item :label="key">{{ val }}</el-descriptions-item>
              </template>
            </el-descriptions>
          </el-collapse-item>
        </el-collapse>
      </template>

      <template v-else>
        <el-divider content-position="left">采购数据</el-divider>
        <el-empty description="暂无采购数据" :image-size="80" />
      </template>
    </template>
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([BarChart, TitleComponent, TooltipComponent, GridComponent, CanvasRenderer])

const FIXED_KEYS = [
  'supplier_name', 'contact_person', 'contact_phone',
  'quotation', 'qualification_desc', 'delivery_date', 'contract_no', 'notes',
]

const props = defineProps({
  visible: Boolean,
  project: { type: Object, default: null },
})

defineEmits(['close'])

// ── 采购记录列表(兼容V5.2旧版单个dict格式) ──────────────────
const records = computed(() => {
  if (!props.project?.procurement_data) return []
  const pd = props.project.procurement_data
  if (Array.isArray(pd)) return pd
  if (pd && pd.supplier_name) return [pd]
  return []
})

// ── 报价数值解析 ────────────────────────────────────────────
function parseQuotation(q) {
  if (!q) return 0
  let s = q.replace(/[¥￥,\s]/g, '')
  if (s.includes('万')) return (parseFloat(s.replace('万', '')) || 0) * 10000
  s = s.split('/')[0]
  return parseFloat(s) || 0
}

// ── 供应商报价对比柱状图 ────────────────────────────────────
const barChartOption = computed(() => {
  if (records.value.length < 2) return {}

  const names = records.value.map(r => r.supplier_name || `未知#${records.value.indexOf(r)+1}`)
  const prices = records.value.map(r => parseQuotation(r.quotation))
  const maxPrice = Math.max(...prices)

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        const val = p.value >= 10000 ? `${(p.value/10000).toFixed(1)}万` : `${p.value}`
        return `${p.name}: ¥${val}`
      },
    },
    grid: { left: 80, right: 20, bottom: 30, top: 10 },
    xAxis: { type: 'category', data: names },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (v) => v >= 10000 ? `${v/10000}万` : v,
      },
    },
    series: [{
      type: 'bar',
      data: prices.map((v, i) => ({
        value: v,
        itemStyle: {
          color: v === maxPrice ? '#f56c6c' : '#409eff',
        },
      })),
      barWidth: '40%',
      label: { show: true, position: 'top', fontSize: 12 },
    }],
  }
})

function statusTagType(status) {
  const map = { '需求填报': 'info', '寻找供应商': 'warning', '已采购': 'success', '计划报废': 'danger', '已报废': '' }
  return map[status] || 'info'
}

function extraFields(rec) {
  const extra = {}
  for (const [k, v] of Object.entries(rec)) {
    if (!FIXED_KEYS.includes(k) && v) extra[k] = v
  }
  return extra
}

function formatTime(ts) {
  if (!ts) return '--'
  return new Date(ts).toLocaleString('zh-CN')
}
</script>

<style scoped>
.drawer-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.detail-title {
  margin: 0;
  font-size: 18px;
}
.detail-sub-title {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
.price {
  color: #e6a23c;
  font-weight: 600;
}
</style>
<template>
  <!-- V5.3数据看板 - 科长级专属(领导大屏)
      FIXED in V5.3: 旧版看板数据硬编码，现从后端实时拉取 -->
  <div class="dashboard-container">
    <div class="dashboard-header">
      <h2>数据看板</h2>
      <el-button size="small" @click="fetchData" :loading="loading">刷新数据</el-button>
    </div>

    <el-row :gutter="24">
      <!-- ── 左: 状态统计柱状图 ──────────────────────────────── -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>项目状态分布</span>
          </template>
          <v-chart :option="barOption" autoresize style="height: 360px" />
        </el-card>
      </el-col>

      <!-- ── 右: 供应商采购金额占比饼图 ──────────────────────── -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>供应商采购金额占比</span>
          </template>
          <v-chart :option="pieOption" autoresize style="height: 360px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ── 底部: 快速统计卡片 ──────────────────────────────────── -->
    <el-row :gutter="24" style="margin-top: 24px">
      <el-col :span="6" v-for="card in summaryCards" :key="card.label">
        <el-card shadow="hover" class="summary-card" :body-style="{ padding: '20px' }">
          <div class="card-value" :style="{ color: card.color }">{{ card.value }}</div>
          <div class="card-label">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { use } from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { useAppStore } from '../stores/app'

// ── ECharts按需注册 ──────────────────────────────────────────
use([
  BarChart, PieChart,
  TitleComponent, TooltipComponent, LegendComponent, GridComponent,
  CanvasRenderer,
])

const store = useAppStore()
const projects = ref([])
const loading = ref(false)

// ── 状态常量(与后端一致) ──────────────────────────────────────
const STATUS_LIST = ['需求填报', '寻找供应商', '已采购', '计划报废', '已报废']
const STATUS_COLORS = {
  '需求填报': '#909399',
  '寻找供应商': '#e6a23c',
  '已采购': '#67c23a',
  '计划报废': '#f56c6c',
  '已报废': '#303133',
}

// ── 从报价字符串提取数值 ──────────────────────────────────────
// V5.2遗留逻辑兼容: 报价格式不统一(¥85,000/台 / ¥320,000 / 120万)
// FIXED in V5.3: 增强解析逻辑，兼容"万"单位和"/台"后缀
function parseQuotation(q) {
  if (!q) return 0
  let s = q.replace(/[¥￥,\s]/g, '')
  // 处理"万"单位: 如"120万" → 1200000
  if (s.includes('万')) {
    const num = parseFloat(s.replace('万', '')) || 0
    return num * 10000
  }
  // 处理"/台"等后缀: 如"85000/台" → 85000
  s = s.split('/')[0]
  return parseFloat(s) || 0
}

// ── 统计数据 ──────────────────────────────────────────────────

/** 柱状图数据: 各状态项目数 */
const statusCounts = computed(() => {
  const counts = {}
  STATUS_LIST.forEach(s => counts[s] = 0)
  projects.value.forEach(p => {
    if (counts[p.status] !== undefined) counts[p.status]++
  })
  return counts
})

/** 饼图数据: 各供应商采购金额 */
const supplierAmounts = computed(() => {
  const amounts = {}
  projects.value.forEach(p => {
    const pd = p.procurement_data
    if (!pd || !pd.supplier_name) return
    const name = pd.supplier_name
    const val = parseQuotation(pd.quotation)
    amounts[name] = (amounts[name] || 0) + val
  })
  // 转为ECharts数据格式
  return Object.entries(amounts).map(([name, value]) => ({ name, value }))
})

/** 快速统计卡片 */
const summaryCards = computed(() => {
  const total = projects.value.length
  const active = projects.value.filter(p =>
    ['需求填报', '寻找供应商', '已采购'].includes(p.status)
  ).length
  const purchased = projects.value.filter(p => p.status === '已采购').length
  const scrapped = projects.value.filter(p =>
    ['计划报废', '已报废'].includes(p.status)
  ).length
  return [
    { label: '项目总数', value: total, color: '#409eff' },
    { label: '进行中', value: active, color: '#e6a23c' },
    { label: '已采购', value: purchased, color: '#67c23a' },
    { label: '已/将报废', value: scrapped, color: '#f56c6c' },
  ]
})

// ── ECharts配置 ──────────────────────────────────────────────

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 30, bottom: 40, top: 20 },
  xAxis: {
    type: 'category',
    data: STATUS_LIST,
    axisLabel: { fontSize: 12 },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    axisLabel: { fontSize: 12 },
  },
  series: [{
    type: 'bar',
    data: STATUS_LIST.map(s => ({
      value: statusCounts.value[s],
      itemStyle: { color: STATUS_COLORS[s] },
    })),
    barWidth: '45%',
    label: {
      show: true,
      position: 'top',
      fontSize: 14,
      fontWeight: 'bold',
    },
  }],
}))

const pieOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: (params) => {
      // FIXED in V5.3: 饼图tooltip显示金额而非百分比
      const val = params.value >= 10000
        ? `${(params.value / 10000).toFixed(1)}万`
        : `${params.value}`
      return `${params.name}: ¥${val} (${params.percent}%)`
    },
  },
  legend: {
    orient: 'vertical',
    right: 10,
    top: 'center',
    textStyle: { fontSize: 12 },
  },
  series: [{
    type: 'pie',
    radius: ['35%', '65%'],
    center: ['40%', '50%'],
    avoidLabelOverlap: true,
    itemStyle: {
      borderRadius: 6,
      borderColor: '#fff',
      borderWidth: 2,
    },
    label: {
      show: true,
      formatter: '{b}\n{d}%',
      fontSize: 11,
    },
    data: supplierAmounts.value,
  }],
}))

// ── 数据获取 ──────────────────────────────────────────────────
async function fetchData() {
  loading.value = true
  try {
    projects.value = await store.request('GET', '/projects')
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.dashboard-container {
  padding: 0 0 24px 0;
}
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.dashboard-header h2 {
  margin: 0;
  font-size: 20px;
}
.summary-card {
  text-align: center;
}
.card-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}
.card-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
</style>
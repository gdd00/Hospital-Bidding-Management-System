<template>
  <div class="app-container">
    <!-- ── 顶部栏：系统标题 + 模拟登录切换 ── -->
    <el-header class="top-bar">
      <span class="sys-title">医院招投标管理系统 V5.3</span>
      <div class="user-switch">
        <span class="role-tag">{{ name }} ({{ role }})</span>
        <el-select
          v-model="selectedEmpId"
          placeholder="切换登录身份"
          size="small"
          style="width: 180px"
          @change="onSwitchUser"
        >
          <el-option
            v-for="u in store.mockUsers"
            :key="u.emp_id"
            :label="`${u.name} (${u.role})`"
            :value="u.emp_id"
          />
        </el-select>
      </div>
    </el-header>

    <!-- ── 主体：项目列表 ── -->
    <el-main>
      <!-- 科长级: 创建需求按钮 -->
      <div v-if="store.isChief" style="margin-bottom: 16px">
        <el-button type="primary" @click="showCreateDialog = true">
          + 新建需求
        </el-button>
      </div>

      <ProjectList
        :projects="projects"
        :loading="loading"
        @refresh="fetchProjects"
        @open-procurement="openProcurementDialog"
        @open-purchased="openPurchasedDialog"
        @open-detail="openDetailDrawer"
      />
    </el-main>

    <!-- ── 弹窗: 创建需求 ── -->
    <CreateProjectDialog
      v-if="store.isChief"
      :visible="showCreateDialog"
      @close="showCreateDialog = false"
      @created="onCreated"
    />

    <!-- ── 弹窗: 补充采购数据(动态表单) ── -->
    <ProcurementDialog
      v-if="store.isPurchase"
      :visible="showProcurementDialog"
      :project="procurementTarget"
      @close="showProcurementDialog = false"
      @saved="onProcurementSaved"
    />

    <!-- ── 弹窗: 标记已采购(输入新主标题) ── -->
    <PurchasedDialog
      :visible="showPurchasedDialog"
      :project="purchasedTarget"
      @close="showPurchasedDialog = false"
      @confirmed="onPurchasedConfirmed"
    />

    <!-- ── 抽屉: 项目详情 ── -->
    <DetailDrawer
      :visible="showDetailDrawer"
      :project="detailTarget"
      @close="showDetailDrawer = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAppStore } from './stores/app'
import ProjectList from './components/ProjectList.vue'
import CreateProjectDialog from './components/CreateProjectDialog.vue'
import ProcurementDialog from './components/ProcurementDialog.vue'
import PurchasedDialog from './components/PurchasedDialog.vue'
import DetailDrawer from './components/DetailDrawer.vue'

const store = useAppStore()

// ── 数据 ──────────────────────────────────────────────────────
const projects = ref([])
const loading = ref(false)
const selectedEmpId = ref('')

// ── 弹窗状态 ──────────────────────────────────────────────────
const showCreateDialog = ref(false)
const showProcurementDialog = ref(false)
const showPurchasedDialog = ref(false)
const showDetailDrawer = ref(false)
const procurementTarget = ref(null)
const purchasedTarget = ref(null)
const detailTarget = ref(null)

// ── 初始化 ────────────────────────────────────────────────────
onMounted(() => {
  // 默认选科长
  store.switchUser('EMP001')
  selectedEmpId.value = 'EMP001'
  fetchProjects()
})

function onSwitchUser(empId) {
  store.switchUser(empId)
  fetchProjects()
}

async function fetchProjects() {
  loading.value = true
  try {
    projects.value = await store.request('GET', '/projects')
  } finally {
    loading.value = false
  }
}

// ── 创建需求回调 ──────────────────────────────────────────────
async function onCreated() {
  showCreateDialog.value = false
  await fetchProjects()
}

// ── 采购数据弹窗 ──────────────────────────────────────────────
function openProcurementDialog(project) {
  procurementTarget.value = project
  showProcurementDialog.value = true
}
async function onProcurementSaved() {
  showProcurementDialog.value = false
  await fetchProjects()
}

// ── 标记已采购弹窗 ────────────────────────────────────────────
function openPurchasedDialog(project) {
  purchasedTarget.value = project
  showPurchasedDialog.value = true
}
async function onPurchasedConfirmed() {
  showPurchasedDialog.value = false
  await fetchProjects()
}

// ── 详情抽屉 ──────────────────────────────────────────────────
function openDetailDrawer(project) {
  detailTarget.value = project
  showDetailDrawer.value = true
}
</script>

<style>
.app-container {
  min-height: 100vh;
  background: #f0f2f5;
}
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #001529;
  color: #fff;
  padding: 0 24px;
  height: 56px;
}
.sys-title {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 2px;
}
.user-switch {
  display: flex;
  align-items: center;
  gap: 12px;
}
.role-tag {
  font-size: 13px;
  opacity: 0.85;
}
</style>
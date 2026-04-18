<template>
  <!-- V5.3主页面 - 登录认证 + 分组权限 + 隐形水印 -->
  <div class="app-container" v-watermark="store.empId">

    <!-- ── 未登录: 显示登录页 ── -->
    <LoginPage v-if="!store.isLoggedIn" @login-success="onLoginSuccess" />

    <!-- ── 已登录: 主界面 ── -->
    <template v-else>
      <!-- 顶部栏 -->
      <el-header class="top-bar">
        <span class="sys-title">医院招投标管理系统 V5.3</span>
        <div class="top-bar-right">
          <span class="user-info">{{ store.name }} ({{ store.groupName }})</span>
          <el-button
            v-if="store.canManageAccounts"
            size="small"
            type="warning"
            plain
            @click="showAccountManager = true"
          >
            账号管理
          </el-button>
          <el-button size="small" type="info" plain @click="onLogout">退出</el-button>
        </div>
      </el-header>

      <!-- 主体: Tab切换 -->
      <el-main>
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="项目列表" name="list">
            <div v-if="store.canCreateProject" style="margin-bottom: 16px">
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
          </el-tab-pane>

          <el-tab-pane label="数据看板" name="dashboard">
            <Dashboard v-if="store.canViewDashboard" />
            <el-result v-else icon="warning" title="权限不足" sub-title="数据看板需要 view_dashboard 权限" />
          </el-tab-pane>
        </el-tabs>
      </el-main>

      <!-- 弹窗 -->
      <CreateProjectDialog
        v-if="store.canCreateProject"
        :visible="showCreateDialog"
        @close="showCreateDialog = false"
        @created="onCreated"
      />
      <ProcurementDialog
        v-if="store.canWriteProcurement"
        :visible="showProcurementDialog"
        :project="procurementTarget"
        @close="showProcurementDialog = false"
        @saved="onProcurementSaved"
      />
      <PurchasedDialog
        :visible="showPurchasedDialog"
        :project="purchasedTarget"
        @close="showPurchasedDialog = false"
        @confirmed="onPurchasedConfirmed"
      />
      <DetailDrawer
        :visible="showDetailDrawer"
        :project="detailTarget"
        @close="showDetailDrawer = false"
      />
      <AccountManager
        v-if="store.canManageAccounts"
        :visible="showAccountManager"
        @close="showAccountManager = false"
        @changed="onAccountChanged"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAppStore } from './stores/app'
import { updateWatermark } from './directives/watermark'
import { ElMessage } from 'element-plus'
import LoginPage from './components/LoginPage.vue'
import ProjectList from './components/ProjectList.vue'
import CreateProjectDialog from './components/CreateProjectDialog.vue'
import ProcurementDialog from './components/ProcurementDialog.vue'
import PurchasedDialog from './components/PurchasedDialog.vue'
import DetailDrawer from './components/DetailDrawer.vue'
import Dashboard from './components/Dashboard.vue'
import AccountManager from './components/AccountManager.vue'

const store = useAppStore()

const projects = ref([])
const loading = ref(false)
const activeTab = ref('list')

const showCreateDialog = ref(false)
const showProcurementDialog = ref(false)
const showPurchasedDialog = ref(false)
const showDetailDrawer = ref(false)
const showAccountManager = ref(false)
const procurementTarget = ref(null)
const purchasedTarget = ref(null)
const detailTarget = ref(null)

// ── 初始化: 恢复登录态 ────────────────────────────────────
onMounted(async () => {
  if (store.token) {
    await store.fetchMe()
    if (store.isLoggedIn) {
      await fetchProjects()
    }
  }
})

// ── 登录后 ────────────────────────────────────────────────
async function onLoginSuccess() {
  await fetchProjects()
}

async function onLogout() {
  await store.logout()
  projects.value = []
  ElMessage.info('已退出登录')
}

// ── 水印同步 ──────────────────────────────────────────────
watch(() => store.empId, (newId) => {
  if (newId) updateWatermark(newId)
})

async function fetchProjects() {
  loading.value = true
  try {
    projects.value = await store.request('GET', '/projects')
  } catch {
    projects.value = []
  } finally {
    loading.value = false
  }
}

async function onCreated() { showCreateDialog.value = false; await fetchProjects() }
function openProcurementDialog(p) { procurementTarget.value = p; showProcurementDialog.value = true }
async function onProcurementSaved() { showProcurementDialog.value = false; await fetchProjects() }
function openPurchasedDialog(p) { purchasedTarget.value = p; showPurchasedDialog.value = true }
async function onPurchasedConfirmed() { showPurchasedDialog.value = false; await fetchProjects() }
function openDetailDrawer(p) { detailTarget.value = p; showDetailDrawer.value = true }
async function onAccountChanged() { await store.fetchMe(); await fetchProjects() }
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
.top-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-info {
  font-size: 13px;
  opacity: 0.85;
}
</style>
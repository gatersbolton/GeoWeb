<template>
  <div v-if="isAuthPage">
    <router-view />
  </div>
  <div v-else class="ant-layout vben-default-layout">
    <!-- 顶部导航栏 -->
    <header class="ant-layout-header vben-layout-header">
      <div class="header-left">
        <div class="header-trigger" @click="toggleCollapsed">
          <el-icon :size="16">
            <Fold v-if="!collapsed" />
            <Expand v-else />
          </el-icon>
        </div>
      </div>
      <div class="header-right">
        <div class="header-action">
          <el-dropdown @command="handleCommand">
            <div class="user-dropdown">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ displayName }}</span>
              <el-icon class="el-icon--right">
                <arrow-down />
              </el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人资料</el-dropdown-item>
                <el-dropdown-item command="settings">设置</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </header>

    <!-- 侧边栏 -->
    <aside class="ant-layout-sider vben-layout-sidebar" :class="{'collapsed': collapsed}">
      <div class="ant-layout-sider-children">
        <div class="sidebar-logo">
          <div class="logo-img">
            <el-icon :size="28" color="#1890ff">
              <Location />
            </el-icon>
          </div>
          <div class="logo-text" v-show="!collapsed">GeoWeb</div>
        </div>
        
        <div class="scrollbar scroll-container">
          <el-menu
            class="vben-menu"
            mode="vertical"
            :default-active="$route.path"
            :collapse="collapsed"
            router
            background-color="#ffffff"
            text-color="#4a5568"
            active-text-color="#1890ff"
          >
            <el-menu-item index="/map" class="vben-menu-item">
              <el-icon><Location /></el-icon>
              <span>地图数据</span>
            </el-menu-item>
            
            <el-sub-menu index="file" class="vben-menu-submenu">
              <template #title>
                <el-icon><Document /></el-icon>
                <span>文件管理</span>
              </template>
              <el-menu-item index="/csv" class="vben-menu-item-sub">
                <span>CSV处理</span>
              </el-menu-item>
            </el-sub-menu>
            
            <el-sub-menu index="analysis" class="vben-menu-submenu">
              <template #title>
                <el-icon><DataAnalysis /></el-icon>
                <span>数据分析</span>
              </template>
              <el-menu-item index="/borehole" class="vben-menu-item-sub">
                <span>钻孔椭圆度项目</span>
              </el-menu-item>
              <el-menu-item index="/stressinv" class="vben-menu-item-sub">
                <span>地应力反演项目</span>
              </el-menu-item>
              <el-menu-item index="/augmentation" class="vben-menu-item-sub">
                <span>数据增强项目</span>
              </el-menu-item>
            </el-sub-menu>
            
            <el-sub-menu index="system" class="vben-menu-submenu">
              <template #title>
                <el-icon><Setting /></el-icon>
                <span>系统管理</span>
              </template>
              <el-menu-item index="/user" class="vben-menu-item-sub">
                <span>用户信息</span>
              </el-menu-item>
            </el-sub-menu>
          </el-menu>
        </div>
      </div>
    </aside>

    <!-- 主内容区域 -->
    <main class="ant-layout-content vben-layout-content" :class="{'content-collapsed': collapsed}">
      <div class="content-wrapper">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  Location, 
  Document, 
  DataAnalysis, 
  Fold, 
  Expand, 
  Setting,
  UserFilled,
  ArrowDown
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { clearUser, useUserStore } from '@/utils/userStore'

const route = useRoute()
const router = useRouter()
const isAuthPage = computed(() => ['/login', '/register'].includes(route.path))
const collapsed = ref(false)
const { username } = useUserStore()
const displayName = computed(() => username.value || '管理员')

function toggleCollapsed() {
  collapsed.value = !collapsed.value
}

function handleCommand(command) {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      ElMessage.info('设置功能开发中')
      break
    case 'logout':
      logout()
      break
  }
}

function logout() {
  localStorage.removeItem('loggedIn')
  clearUser()
  router.push('/login')
}
</script>

<style scoped>
/* 全局布局样式 */
.ant-layout {
  min-height: 100vh;
  background: #f0f2f5;
}

.vben-default-layout {
  display: flex;
  flex-direction: column;
}

/* 顶部导航栏样式 */
.ant-layout-header {
  height: 48px;
  line-height: 48px;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1001;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 4px;
}

.header-trigger:hover {
  background: #f5f5f5;
}

.header-right {
  display: flex;
  align-items: center;
}

.header-action {
  display: flex;
  align-items: center;
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 0 12px;
  height: 48px;
  transition: all 0.2s;
}

.user-dropdown:hover {
  background: #f5f5f5;
}

.username {
  margin: 0 8px;
  font-size: 14px;
  color: #333;
}

/* 侧边栏样式 */
.ant-layout-sider {
  width: 210px;
  min-width: 210px;
  max-width: 210px;
  background: #ffffff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  position: fixed;
  top: 48px;
  left: 0;
  bottom: 0;
  z-index: 1000;
  transition: all 0.2s;
}

.ant-layout-sider.collapsed {
  width: 64px;
  min-width: 64px;
  max-width: 64px;
}

.ant-layout-sider-children {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  border-bottom: 1px solid #f0f0f0;
}

.collapsed .sidebar-logo {
  padding: 0 20px;
}

.logo-img {
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  margin-left: 12px;
  font-size: 18px;
  font-weight: 600;
  color: #1890ff;
  transition: all 0.2s;
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

/* 菜单样式 */
:deep(.vben-menu) {
  border-right: none;
  background: transparent !important;
}

:deep(.vben-menu .el-menu-item) {
  height: 40px;
  line-height: 40px;
  margin: 2px 8px;
  border-radius: 6px;
  color: #4a5568;
  font-size: 14px;
}

:deep(.vben-menu .el-menu-item:hover) {
  background: #e6f7ff;
  color: #1890ff;
}

:deep(.vben-menu .el-menu-item.is-active) {
  background: #1890ff;
  color: #ffffff;
}

:deep(.vben-menu .el-sub-menu) {
  margin: 2px 8px;
}

:deep(.vben-menu .el-sub-menu > .el-sub-menu__title) {
  height: 40px;
  line-height: 40px;
  border-radius: 6px;
  color: #4a5568;
  font-size: 14px;
}

:deep(.vben-menu .el-sub-menu > .el-sub-menu__title:hover) {
  background: #e6f7ff;
  color: #1890ff;
}

:deep(.vben-menu .el-sub-menu.is-opened > .el-sub-menu__title) {
  background: #e6f7ff;
  color: #1890ff;
}

:deep(.vben-menu .el-menu-item-sub) {
  height: 36px;
  line-height: 36px;
  margin: 2px 16px;
  border-radius: 4px;
  color: #4a5568;
  font-size: 13px;
}

:deep(.vben-menu .el-menu-item-sub:hover) {
  background: #f0f8ff;
  color: #1890ff;
}

:deep(.vben-menu .el-menu-item-sub.is-active) {
  background: #1890ff;
  color: #ffffff;
}

/* 收缩状态下的菜单样式 */
:deep(.collapsed .vben-menu .el-menu-item),
:deep(.collapsed .vben-menu .el-sub-menu > .el-sub-menu__title) {
  margin: 2px 16px;
  padding: 0 !important;
  text-align: center;
}

:deep(.collapsed .vben-menu .el-menu-item span),
:deep(.collapsed .vben-menu .el-sub-menu > .el-sub-menu__title span) {
  display: none;
}

/* 主内容区域样式 */
.ant-layout-content {
  margin-left: 210px;
  margin-top: 48px;
  min-height: calc(100vh - 48px);
  background: #f0f2f5;
  transition: all 0.2s;
}

.ant-layout-content.content-collapsed {
  margin-left: 64px;
}

.content-wrapper {
  padding: 24px;
  min-height: 100%;
}

/* 滚动条样式 */
.scroll-container::-webkit-scrollbar {
  width: 4px;
}

.scroll-container::-webkit-scrollbar-track {
  background: transparent;
}

.scroll-container::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 2px;
}

.scroll-container::-webkit-scrollbar-thumb:hover {
  background: #bfbfbf;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .ant-layout-sider {
    width: 64px;
    min-width: 64px;
    max-width: 64px;
  }
  
  .ant-layout-content {
    margin-left: 64px;
  }
  
  .logo-text {
    display: none;
  }
}
</style> 

<template>
  <n-config-provider>
    <n-dialog-provider>
      <n-message-provider>
        <n-layout has-sider>
          <!-- 左侧导航栏 -->
          <n-layout-sider
            bordered
            collapse-mode="width"
            :collapsed-width="64"
            :width="240"
            show-trigger
            @collapse="collapsed = true"
            @expand="collapsed = false"
          >
            <!-- 添加标题 -->
            <div
              class="platform-title"
              :style="{ width: collapsed ? '64px' : '240px' }"
            >
              <img
                v-if="collapsed"
                src="./assets/logo.png"
                alt="Logo"
                class="platform-logo-small"
              />
              <h1 v-if="!collapsed">自动化测试平台</h1>
            </div>

            <n-menu
              v-model:value="activeKey"
              :collapsed="collapsed"
              :collapsed-width="64"
              :options="menuOptions"
              @update:value="handleMenuUpdate"
              :indent="50"
              class="custom-menu"
            />
          </n-layout-sider>

          <!-- 右侧内容区 -->
          <n-layout>
            <n-layout-content content-style="padding: 24px;">
              <router-view v-slot="{ Component }">
                <transition name="fade" mode="out-in">
                  <component :is="Component" />
                </transition>
              </router-view>
            </n-layout-content>
          </n-layout>
        </n-layout>
      </n-message-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>

<script lang="ts">
import { defineComponent, ref, h, onMounted, watch, Component } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  NConfigProvider,
  NMessageProvider,
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NMenu,
  NDialogProvider,
} from "naive-ui";
import {
  BookOutline,
  DocumentTextOutline,
  FolderOpenOutline,
  HomeOutline, // 添加首页图标
  ListOutline, // 添加元素列表图标
  CodeSlashOutline, // 添加变量管理图标
  DocumentAttachOutline, // 添加日志图标
  AppsOutline, // 添加项目管理图标
  ServerOutline, // 添加环境管理图标
  FileTrayStackedOutline, // 添加数据管理图标
} from "@vicons/ionicons5";
import DataTableComponent from "./components/DataTableComponent.vue";

export default defineComponent({
  name: "App",
  components: {
    NConfigProvider,
    NMessageProvider,
    NLayout,
    NLayoutSider,
    NLayoutContent,
    NMenu,
    DataTableComponent,
    NDialogProvider,
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const collapsed = ref(false);
    const activeKey = ref("dashboard"); // 默认选中首页

    const menuOptions = [
      {
        label: "首页",
        key: "dashboard",
        icon: renderIcon(HomeOutline),
      },
      {
        label: "项目管理",
        key: "project-management",
        icon: renderIcon(AppsOutline),
      },
      {
        label: "环境管理",
        key: "env-management",
        icon: renderIcon(ServerOutline),
      },
      {
        label: "用例列表",
        key: "test-cases",
        icon: renderIcon(BookOutline),
      },
      {
        label: "元素列表",
        key: "elements",
        icon: renderIcon(ListOutline),
      },
      {
        label: "报告列表",
        key: "reports",
        icon: renderIcon(DocumentTextOutline),
      },
      {
        label: "任务列表",
        key: "projects",
        icon: renderIcon(FolderOpenOutline),
      },
      {
        label: "变量管理",
        key: "variables",
        icon: renderIcon(CodeSlashOutline),
      },
      {
        label: "数据管理",
        key: "database-management",
        icon: renderIcon(FileTrayStackedOutline),
      },
      {
        label: "日志查询",
        key: "logs",
        icon: renderIcon(DocumentAttachOutline),
      },
    ];

    function renderIcon(icon: Component) {
      return () => h(icon);
    }

    function handleMenuUpdate(key: string) {
      router.push(`/${key}`);
    }

    // 根据当前路由路径设置菜单激活状态
    function updateActiveKeyFromRoute() {
      const path = route.path;
      if (path === "/" || path === "/dashboard") {
        activeKey.value = "dashboard";
      } else if (path.startsWith("/test-cases")) {
        activeKey.value = "test-cases";
      } else if (path.startsWith("/elements")) {
        activeKey.value = "elements";
      } else if (path.startsWith("/reports")) {
        activeKey.value = "reports";
      } else if (path.startsWith("/projects")) {
        activeKey.value = "projects";
      } else if (path.startsWith("/variables")) {
        activeKey.value = "variables";
      } else if (path.startsWith("/logs")) {
        activeKey.value = "logs";
      } else if (path.startsWith("/project-management")) {
        activeKey.value = "project-management";
      } else if (path.startsWith("/env-management")) {
        activeKey.value = "env-management";
      } else if (path.startsWith("/database-management")) {
        activeKey.value = "database-management";
      }
    }

    // 监听路由变化
    watch(
      () => route.path,
      () => {
        updateActiveKeyFromRoute();
      }
    );

    // 组件挂载时设置初始状态
    onMounted(() => {
      updateActiveKeyFromRoute();
    });

    return {
      collapsed,
      activeKey,
      menuOptions,
      handleMenuUpdate,
    };
  },
});
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.platform-title {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
  transition: all 0.3s ease;
  background: linear-gradient(135deg, #eaf8f1 0%, #d3f0e1 55%, #b7e8cd 100%);
  box-shadow: 0 4px 12px rgba(24, 160, 88, 0.15);
  overflow: hidden;
}

.platform-title::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    120deg,
    rgba(255, 255, 255, 0.5) 0%,
    rgba(255, 255, 255, 0) 60%
  );
  pointer-events: none;
}

.platform-title::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  background: #18a058;
  box-shadow: 0 0 8px rgba(24, 160, 88, 0.6);
}

.platform-logo-small {
  position: relative;
  z-index: 1;
  width: 40px;
  height: 40px;
  object-fit: contain;
  filter: drop-shadow(0 2px 4px rgba(24, 160, 88, 0.25));
}

.platform-title h1 {
  position: relative;
  z-index: 1;
  font-size: 20px;
  font-weight: bold;
  letter-spacing: 1.5px;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background: linear-gradient(135deg, #0d3b2e 0%, #18a058 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* 自定义菜单样式 */
.custom-menu :deep(.n-menu-item-content) {
  justify-content: center;
}

.custom-menu :deep(.n-menu-item-content-header) {
  flex: none;
}

/* 展开状态下的菜单样式 */
.custom-menu:not(:deep(.n-menu--collapsed)) .n-menu-item-content {
  justify-content: flex-start;
  padding-left: 24px;
}

/* 收起状态下的菜单图标居中 */
.custom-menu:deep(.n-menu--collapsed) .n-menu-item-content {
  padding: 0;
  justify-content: center;
}

/* 全局表格内容居中展示 */
.n-data-table-th {
  text-align: center !important;
}

.n-data-table-td {
  text-align: center !important;
}

.n-data-table-td .n-space {
  justify-content: center !important;
}
</style>
import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
import DataTableComponent from "../components/DataTableComponent.vue";
import Dashboard from "../components/Dashboard.vue";
import ReportView from "../components/ReportView.vue";

// 扩展路由meta类型
declare module "vue-router" {
  interface RouteMeta {
    title?: string;
  }
}

const routes: Array<RouteRecordRaw> = [
  {
    path: "/",
    redirect: "/dashboard", // 修改默认路由为 dashboard
  },
  {
    path: "/dashboard", // 添加 dashboard 路由
    name: "Dashboard",
    component: Dashboard,
    meta: { title: "自动化测试平台 - 仪表盘" },
  },
  {
    path: "/test-cases",
    name: "TestCases",
    component: DataTableComponent,
    meta: { title: "自动化测试平台 - 测试用例" },
  },
  {
    path: "/test-cases/new",
    name: "TestCaseNew",
    component: () => import("../components/TestCaseForm.vue"),
    meta: { title: "自动化测试平台 - 新建用例" },
  },
  {
    path: "/test-cases/:id/edit",
    name: "TestCaseEdit",
    component: () => import("../components/TestCaseForm.vue"),
    meta: { title: "自动化测试平台 - 编辑用例" },
  },
  {
    path: "/elements",
    name: "Elements",
    component: () => import("../components/ElementList.vue"),
    meta: { title: "自动化测试平台 - 元素管理" },
  },
  {
    path: "/reports",
    name: "Reports",
    component: () => import("../components/ReportList.vue"),
    meta: { title: "自动化测试平台 - 测试报告" },
  },
  {
    path: "/reports/:id", // 添加报告详情路由
    name: "ReportDetail",
    component: ReportView,
    meta: { title: "自动化测试平台 - 报告详情" },
  },
  {
    path: "/projects",
    name: "Projects",
    component: () => import("../components/ProjectList.vue"),
    meta: { title: "自动化测试平台 - 项目管理" },
  },
  {
    path: "/variables",
    name: "Variables",
    component: () => import("../components/VariableList.vue"),
    meta: { title: "自动化测试平台 - 变量管理" },
  },
  {
    path: "/logs",
    name: "Logs",
    component: () => import("../components/LogViewer.vue"),
    meta: { title: "自动化测试平台 - 日志查询" },
  },
  {
    path: "/project-management",
    name: "ProjectManagement",
    component: () => import("../components/ProjectManage.vue"),
    meta: { title: "自动化测试平台 - 项目管理" },
  },
  {
    path: "/env-management",
    name: "EnvManagement",
    component: () => import("../components/EnvironmentManage.vue"),
    meta: { title: "自动化测试平台 - 环境管理" },
  },
  {
    path: "/database-management",
    name: "DatabaseManagement",
    component: () => import("../components/DatabaseManage.vue"),
    meta: { title: "自动化测试平台 - 数据管理" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 添加全局前置守卫，用于设置页面标题
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = (to.meta?.title as string) || "自动化测试平台";
  next();
});

export default router;

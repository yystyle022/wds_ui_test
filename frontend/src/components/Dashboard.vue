<template>
  <div class="dashboard-container">
    <div class="dashboard-title">
      <div class="title-content">
        <h3>您好，欢迎使用自动化管理平台！</h3>
        <n-button
          size="small"
          @click="fetchDashboardData"
          :loading="loading"
          type="primary"
          class="refresh-btn"
        >
          刷新数据
        </n-button>
      </div>
    </div>

    <!-- 统计卡片区域 -->
    <div class="stats-container">
      <n-card class="stat-card total-card clickable" @click="navigateToList()">
        <template #header>
          <div class="card-header">
            <div class="card-title">总用例数</div>
          </div>
        </template>
        <div class="stat-number-centered">{{ totalTestCases }}</div>
      </n-card>
    </div>

    <!-- 项目用例统计 -->
    <div class="project-stats-section">
      <div class="section-header">
        <h4>项目概览</h4>
        <div class="more-link" @click="navigateToProjectManagement">
          更多 <n-icon><ChevronForwardOutline /></n-icon>
        </div>
      </div>
      <div class="project-stats-row">
        <n-card
          v-for="(project, index) in projectStats.slice(0, 3)"
          :key="project.id"
          :class="['project-card', `project-card-${(index % 3) + 1}`, 'clickable']"
          @click="navigateToProjectManagement"
        >
          <template #header>
            <div class="card-header">
              <div class="card-title">{{ project.name }}</div>
            </div>
          </template>
          <div class="project-card-body">
            <div class="project-card-number">{{ project.count }}</div>
          </div>
        </n-card>

        <n-empty
          v-if="projectStats.length === 0"
          description="暂无项目"
          style="flex: 1"
        />
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="chart-container">
      <n-card title="用例类型分布" class="chart-card">
        <div ref="pieChartRef" class="chart"></div>
      </n-card>

      <n-card title="用例功能分布" class="chart-card">
        <div ref="pageChartRef" class="chart"></div>
      </n-card>
    </div>

    <!-- 最近执行记录 -->
    <n-card title="最近执行记录" class="recent-reports">
      <n-data-table
        :columns="reportColumns"
        :data="recentReports"
        :pagination="false"
        :bordered="false"
      />
    </n-card>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, h } from "vue";
import { useRouter } from "vue-router"; // 添加 router 导入
import axios from "axios";
import { NCard, NDataTable, NIcon, NTag, NButton, NEmpty, useMessage } from "naive-ui";
import {
  BookOutline,
  DesktopOutline,
  TimeOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  ChevronForwardOutline,
} from "@vicons/ionicons5";
import * as echarts from "echarts";

interface ProjectStat {
  id: number;
  name: string;
  count: number;
}

interface ReportRecord {
  id: number;
  name: string;
  time: string;
  status: "success" | "fail";
  pass_rate: number;
  duration: string;
}

interface ChartDataItem {
  name: string;
  value: number;
}

export default defineComponent({
  name: "Dashboard",
  components: {
    NCard,
    NDataTable,
    NIcon,
    NButton, // 添加按钮组件
    NEmpty,
  },
  setup() {
    const router = useRouter();
    const message = useMessage();
    const loading = ref(false); // 添加加载状态
    const totalTestCases = ref(0);
    const projectStats = ref<ProjectStat[]>([]);
    const recentReports = ref<ReportRecord[]>([]);
    const pieChartRef = ref<HTMLElement | null>(null);
    const pageChartRef = ref<HTMLElement | null>(null);

    // 获取统计数据
    const fetchDashboardData = async () => {
      loading.value = true; // 开始加载
      try {
        console.log("正在获取仪表盘数据...");
        const response = await axios.get("/api/dashboard");
        const data = response.data;

        console.log("获取到的仪表盘数据:", data);

        // 更新基本数据
        totalTestCases.value = data.total_cases;
        projectStats.value = data.project_stats || [];
        recentReports.value = data.recent_reports;

        // 确保类型分布数据格式正确
        const typeData = data.type_distribution.map((item: any) => ({
          name: item.name || "未分类",
          value:
            typeof item.value === "number"
              ? item.value
              : parseInt(item.value, 10) || 0,
        }));

        // 确保模块分布数据格式正确
        const pageData = data.module_distribution.map((item: any) => ({
          name: item.name || "未分类",
          value:
            typeof item.value === "number"
              ? item.value
              : parseInt(item.value, 10) || 0,
        }));

        // 初始化图表
        initPieChart(typeData);
        initPageChart(pageData);

        message.success("数据刷新成功");
      } catch (error: any) {
        console.error("获取仪表盘数据失败:", error);
        console.error("错误详情:", error.response?.data);
        console.error("状态码:", error.response?.status);
        console.error("完整错误对象:", JSON.stringify(error, null, 2));
        message.error(
          `获取数据失败: ${
            error.response?.data?.error || error.message || "未知错误"
          }`
        );

        // 使用模拟数据以便展示
        useMockData();
      } finally {
        loading.value = false; // 结束加载
      }
    };

    // 模拟数据（以防API未实现）
    const useMockData = () => {
      totalTestCases.value = 256;
      projectStats.value = [];
      recentReports.value = [
        {
          id: 3,
          name: "官网登录流程测试",
          time: "2025-07-01 09:30:15",
          status: "success",
          pass_rate: 100,
          duration: "00:02:15",
        },
        {
          id: 2,
          name: "管理端批量操作测试",
          time: "2025-06-30 16:45:22",
          status: "fail",
          pass_rate: 85,
          duration: "00:04:30",
        },
        {
          id: 1,
          name: "吉利私有化部署测试",
          time: "2025-06-29 14:20:18",
          status: "success",
          pass_rate: 95,
          duration: "00:03:45",
        },
      ];

      // 初始化图表（使用模拟数据）
      initPieChart([
        { name: "主流程", value: 120 },
        { name: "分流程", value: 60 },
        { name: "异常流程", value: 45 },
        { name: "UI验证", value: 31 },
      ]);

      // 修改为模块分布的饼图数据格式
      initPageChart([
        { name: "首页", value: 35 },
        { name: "登录页", value: 42 },
        { name: "产品列表", value: 28 },
        { name: "用户中心", value: 19 },
        { name: "订单管理", value: 15 },
        { name: "设置页", value: 12 },
      ]);
    };

    // 跳转到用例列表页面
    const navigateToList = () => {
      router.push("/test-cases");
    };

    // 跳转到项目管理页面
    const navigateToProjectManagement = () => {
      router.push("/project-management");
    };

    // 初始化饼图
    const initPieChart = (data: ChartDataItem[]) => {
      if (!pieChartRef.value) return;

      // 确保数据非空
      if (!data || data.length === 0) {
        console.warn("用例类型分布数据为空");
        return;
      }

      console.log("初始化用例类型图表:", data);

      const chart = echarts.init(pieChartRef.value);
      const option = {
        tooltip: {
          trigger: "item",
          formatter: "{a} <br/>{b}: {c} ({d}%)",
        },
        color: [
          "#5470c6",
          "#91cc75",
          "#fac858",
          "#ee6666",
          "#73c0de",
          "#3ba272",
          "#fc8452",
          "#9a60b4",
        ],
        legend: {
          type: "scroll",
          orient: "horizontal",
          bottom: 10,
          left: "center",
          data: data.map((item) => item.name),
          pageButtonItemGap: 5,
          pageButtonGap: 20,
          pageIconSize: 12,
          pageTextStyle: {
            fontSize: 12,
          },
        },
        grid: {
          bottom: 80,
        },
        series: [
          {
            name: "用例类型",
            type: "pie",
            radius: ["35%", "65%"],
            center: ["50%", "40%"],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: "#fff",
              borderWidth: 2,
            },
            label: {
              show: false,
              position: "center",
            },
            emphasis: {
              label: {
                show: true,
                fontSize: "18",
                fontWeight: "bold",
              },
            },
            labelLine: {
              show: false,
            },
            data: data,
          },
        ],
      };
      chart.setOption(option);

      // 延迟重新渲染确保图表显示正常
      setTimeout(() => {
        chart.resize();
      }, 100);

      // 窗口大小变化时重新渲染
      window.addEventListener("resize", () => {
        chart.resize();
      });
    };

    // 初始化模块分布饼图
    const initPageChart = (data: ChartDataItem[]) => {
      if (!pageChartRef.value) return;

      // 确保数据非空
      if (!data || data.length === 0) {
        console.warn("模块分布数据为空");
        return;
      }

      console.log("初始化模块分布图表:", data);

      const chart = echarts.init(pageChartRef.value);
      const option = {
        tooltip: {
          trigger: "item",
          formatter: "{a} <br/>{b}: {c} ({d}%)",
        },
        color: [
          "#5470c6",
          "#91cc75",
          "#fac858",
          "#ee6666",
          "#73c0de",
          "#3ba272",
          "#fc8452",
          "#9a60b4",
        ],
        legend: {
          type: "scroll",
          orient: "horizontal",
          bottom: 10,
          left: "center",
          data: data.map((item) => item.name),
          pageButtonItemGap: 5,
          pageButtonGap: 20,
          pageIconSize: 12,
          pageTextStyle: {
            fontSize: 12,
          },
        },
        grid: {
          bottom: 80,
        },
        series: [
          {
            name: "模块分布",
            type: "pie",
            radius: ["35%", "65%"],
            center: ["50%", "40%"],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: "#fff",
              borderWidth: 2,
            },
            label: {
              show: false,
              position: "center",
            },
            emphasis: {
              label: {
                show: true,
                fontSize: "18",
                fontWeight: "bold",
              },
            },
            labelLine: {
              show: false,
            },
            data: data,
          },
        ],
      };
      chart.setOption(option);

      // 延迟重新渲染确保图表显示正常
      setTimeout(() => {
        chart.resize();
      }, 100);

      // 窗口大小变化时重新渲染
      window.addEventListener("resize", () => {
        chart.resize();
      });
    };

    // 报告表格列配置
    const reportColumns = [
      {
        title: "报告ID",
        key: "id",
        width: 120,
      },
      {
        title: "测试名称",
        key: "name",
        width: 440,
      },
      {
        title: "执行时间",
        key: "time",
        width: 220,
        render(row: ReportRecord) {
          return h("div", {}, [
            h(
              NIcon,
              { size: 14, style: "margin-right: 5px" },
              {
                default: () => h(TimeOutline),
              }
            ),
            row.time,
          ]);
        },
      },
      {
        title: "状态",
        key: "status",
        width: 100,
        render(row: ReportRecord) {
          return h(
            NTag,
            {
              type: row.status === "success" ? "success" : "error",
              size: "small",
            },
            {
              default: () => (row.status === "success" ? "通过" : "失败"),
              icon: () =>
                h(
                  NIcon,
                  { size: 14 },
                  {
                    default: () =>
                      h(
                        row.status === "success"
                          ? CheckmarkCircleOutline
                          : CloseCircleOutline
                      ),
                  }
                ),
            }
          );
        },
      },
      {
        title: "通过率",
        key: "pass_rate",
        width: 100,
        render(row: ReportRecord) {
          return `${row.pass_rate}%`;
        },
      },
      {
        title: "耗时",
        key: "duration",
        width: 100,
      },
      {
        title: "操作",
        key: "actions",
        render(row: ReportRecord) {
          return h(
            NButton,
            {
              size: "small",
              onClick: () => viewReport(row.id),
            },
            { default: () => "查看详情" }
          );
        },
      },
    ];

    // 查看报告详情
    const viewReport = (id: number) => {
      router.push(`/reports/${id}`);
    };

    onMounted(() => {
      fetchDashboardData();
    });

    return {
      loading,
      totalTestCases,
      projectStats,
      recentReports,
      reportColumns,
      pieChartRef,
      pageChartRef,
      fetchDashboardData,
      BookOutline,
      DesktopOutline,
      navigateToList, // 确保此方法被导出
      navigateToProjectManagement,
    };
  },
});
</script>

<style scoped>
.dashboard-container {
  padding: 0 12px;
}

.title-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.refresh-btn {
  margin-left: auto;
}

.stats-container {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  flex: 1;
  min-width: 200px;
  transition: all 0.3s ease;
  height: 150px; /* 保持卡片高度 */
  color: #000000;
}

.clickable {
  cursor: pointer;
  transition: all 0.3s ease;
}

.clickable:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.15);
}

.stat-card {
  position: relative;
  overflow: hidden;
  border-radius: 12px;
}

.stat-card::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 0;
  background: rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.stat-card:hover::after {
  height: 100%;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
}

/* 总用例数卡片 */
.total-card {
  background: linear-gradient(135deg, #134e5e 0%, #71b280 100%);
}

.total-card :deep(.n-card-header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.25);
  color: #ffffff;
  padding: 12px 20px;
}

.total-card .card-title,
.total-card .stat-number-centered {
  color: #ffffff;
}

.card-header {
  display: flex;
  align-items: center;
}

.card-title {
  font-weight: bold;
  font-size: 16px;
  color: #000000;
  display: flex;
  align-items: center;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  color: #000000;
  margin-left: 8px;
}

/* 新增居中数字的样式 */
.stat-number-centered {
  font-size: 32px;
  font-weight: bold;
  color: #000000;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.stat-desc {
  font-size: 14px;
  color: #000000;
  opacity: 0.8;
  text-align: left;
  padding: 10px 20px;
}

.project-stats-section {
  margin-bottom: 24px;
}

.section-header {
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #2d3436;
}

.project-stats-row {
  display: flex;
  flex-wrap: nowrap;
  align-items: stretch;
  gap: 16px;
  overflow-x: auto;
  padding: 10px 4px 14px;
  margin: -10px -4px -14px;
}

.project-card {
  flex: 1;
  min-width: 200px;
  height: 150px;
  color: #000000;
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.project-card :deep(.n-card__content) {
  height: calc(100% - 45px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 20px;
}

.project-card-body {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.project-card-number {
  font-size: 40px;
  font-weight: bold;
  color: #ffffff;
  line-height: 1;
}

.project-card-1 {
  background: linear-gradient(135deg, #0ba360 0%, #3cba92 100%);
}

.project-card-2 {
  background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
}

.project-card-3 {
  background: linear-gradient(135deg, #134e5e 0%, #4ca1af 100%);
}

.project-card-1 :deep(.n-card-header),
.project-card-2 :deep(.n-card-header),
.project-card-3 :deep(.n-card-header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.25);
  color: #ffffff;
  padding: 12px 20px;
}

.project-card-1 .card-title,
.project-card-2 .card-title,
.project-card-3 .card-title {
  color: #ffffff;
}

.more-link {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 2px;
  color: #606266;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
}

.more-link:hover {
  color: #18a058;
}

.chart-container {
  display: flex;
  flex-wrap: nowrap;
  gap: 16px;
  margin-bottom: 24px;
}

.chart-card {
  flex: 1;
  min-width: 300px;
  border-radius: 12px;
  overflow: hidden;
}

.chart {
  height: 240px;
  width: 100%;
  background-color: #ffffff;
}

.recent-reports {
  margin-bottom: 24px;
  border-radius: 12px;
  overflow: hidden;
}

@media (max-width: 1200px) {
  .chart-container {
    flex-wrap: wrap;
  }
  .chart-card {
    min-width: 45%;
  }
}

@media (max-width: 768px) {
  .stat-card,
  .chart-card {
    flex: 1 0 100%;
  }
  .chart-container {
    flex-direction: column;
  }
}
</style>
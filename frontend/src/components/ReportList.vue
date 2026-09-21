<template>
  <div>
    <!-- 按钮区域 -->
    <NSpace style="margin-bottom: 16px">
      <NButton
        type="primary"
        :disabled="selectedRowKeys.length === 0"
        @click="batchDeleteReports"
      >
        批量删除 ({{ selectedRowKeys.length }})
      </NButton>
      <NButton type="default" @click="fetchReports" :loading="loading">
        刷新列表
      </NButton>
    </NSpace>

    <!-- 表格 -->
    <NDataTable
      :columns="columns"
      :data="pagedData"
      :loading="loading"
      :row-key="(row) => row.id"
      v-model:checked-row-keys="selectedRowKeys"
    />

    <!-- 自定义分页区域：共 X 条 + 分页控件 -->
    <div
      style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;
      "
    >
      <div style="color: #666; font-size: 14px">
        共 {{ data.length }} 条报告
        <span v-if="selectedRowKeys.length > 0">
          ，已选择 {{ selectedRowKeys.length }} 条
        </span>
      </div>

      <NPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :page-count="Math.ceil(data.length / pageSize)"
        :page-sizes="[10, 20, 50]"
        show-size-picker
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </div>
  </div>
</template>

<script lang="ts">
import {
  ref,
  onMounted,
  onUnmounted,
  watch,
  h,
  defineComponent,
  computed,
} from "vue";
import {
  NDataTable,
  NButton,
  NSpace,
  NPagination,
  useMessage,
  type DataTableColumns,
} from "naive-ui";
import axios from "axios";
import { useRouter } from "vue-router";

interface ExecutedCase {
  id: number;
  name: string;
  client?: string;
  page?: string;
}

interface ReportRecord {
  id: number;
  test_id: number;
  name: string;
  status: string;
  start_time: string;
  end_time: string;
  duration: string;
  pass_rate: number;
  executed_cases?: ExecutedCase[];
  time?: string;
}

interface TestStep {
  step: number;
  action: string;
  description: string;
  status: "success" | "failed" | "skipped";
  screenshot?: string;
  screenshotBase64?: string;
  duration: string;
  failureReason?: string;
}

interface TestCase {
  id: number;
  name: string;
  status: string;
  duration: string;
  description: string;
  steps: TestStep[];
  client?: string;
  page?: string;
}

interface DetailedReportData extends ReportRecord {
  testCases?: TestCase[];
}

export default defineComponent({
  name: "ReportList",
  components: {
    NDataTable,
    NButton,
    NSpace,
    NPagination,
  },

  setup() {
    const router = useRouter();
    const message = useMessage();
    const loading = ref(false);
    const data = ref<ReportRecord[]>([]);
    const selectedRowKeys = ref<number[]>([]);

    // 分页相关
    const page = ref(1);
    const pageSize = ref(10);

    // 轮询定时器
    let pollingTimer: number | null = null;

    // 是否有执行中的报告
    const hasExecutingReport = computed(() => {
      return data.value.some((r) => r.status === "executing");
    });

    // 当前页数据
    const pagedData = computed(() => {
      const start = (page.value - 1) * pageSize.value;
      const end = start + pageSize.value;
      return data.value.slice(start, end);
    });

    const handlePageChange = (p: number) => {
      page.value = p;
    };

    const handlePageSizeChange = (size: number) => {
      pageSize.value = size;
      // 如果当前页超出范围，重置到第一页
      const maxPage = Math.ceil(data.value.length / size);
      if (page.value > maxPage) {
        page.value = 1;
      }
    };

    const pagination = computed(() => ({
      page: page.value,
      pageSize: pageSize.value,
      showSizePicker: true,
      pageSizes: [10, 20, 50],
      itemCount: data.value.length,
      pageCount: Math.ceil(data.value.length / pageSize.value),
      onUpdatePage: (p: number) => {
        page.value = p;
      },
      onUpdatePageSize: (s: number) => {
        pageSize.value = s;
        // 当前页超过新的总页数时，重置到第一页
        const maxPage = Math.ceil(data.value.length / s);
        if (page.value > maxPage) {
          page.value = 1;
        }
      },
    }));

    // 获取报告列表
    const fetchReports = async () => {
      try {
        loading.value = true;
        const response = await axios.get("/api/reports");
        console.log("获取到的报告数据:", response.data);
        data.value = response.data;
      } catch (error) {
        console.error("获取报告列表失败:", error);
        message.error("获取报告列表失败");
      } finally {
        loading.value = false;
      }
    };

    // 删除报告
    const deleteReport = async (id: number) => {
      try {
        await axios.delete(`/api/reports/${id}`);
        message.success("删除成功");
        await fetchReports(); // 重新获取列表
      } catch (error) {
        console.error("删除报告失败:", error);
        message.error("删除报告失败");
      }
    };

    // 批量删除报告
    const batchDeleteReports = async () => {
      if (selectedRowKeys.value.length === 0) {
        message.warning("请选择要删除的报告");
        return;
      }

      const deleteCount = selectedRowKeys.value.length;
      const idsToDelete = [...selectedRowKeys.value]; // 复制一份ID列表

      try {
        // 依次删除选中的报告
        let successCount = 0;
        let failCount = 0;

        for (const id of idsToDelete) {
          try {
            await axios.delete(`/api/reports/${id}`);
            successCount++;
          } catch (error) {
            console.error(`删除报告 ${id} 失败:`, error);
            failCount++;
          }
        }

        // 清空选中状态（无论成功还是失败都清空）
        selectedRowKeys.value = [];

        // 重新获取列表
        await fetchReports();

        // 显示结果消息
        if (failCount === 0) {
          message.success(`成功删除 ${successCount} 个报告`);
        } else if (successCount === 0) {
          message.error(`删除失败，共 ${failCount} 个报告删除失败`);
        } else {
          message.warning(
            `成功删除 ${successCount} 个报告，${failCount} 个报告删除失败`
          );
        }
      } catch (error) {
        console.error("批量删除报告失败:", error);
        message.error("批量删除报告失败");
        // 即使出错也要清空选中状态
        selectedRowKeys.value = [];
        await fetchReports();
      }
    };

    // 查看报告详情
    const viewReportDetail = (id: number) => {
      console.log("点击查看报告详情 - ID:", id);
      router.push(`/reports/${id}`);
    };

    // 处理选择
    const handleCheck = (rowKeys: Array<string | number>) => {
      selectedRowKeys.value = rowKeys as number[];
    };

    // 获取详细的报告数据（包含用例详情和步骤）
    const fetchDetailedReportData = async (
      reportData: ReportRecord
    ): Promise<DetailedReportData> => {
      try {
        console.log("正在获取报告详细数据:", reportData.id);

        // 调用后端API获取详细的报告数据
        const response = await axios.get(
          `/api/reports/${reportData.id}`
        );

        const detailedReport = response.data;
        console.log("后端返回的详细报告数据:", detailedReport);

        // 如果是任务执行报告（包含多个用例）
        if (
          detailedReport.executed_cases &&
          detailedReport.executed_cases.length > 0
        ) {
          console.log(
            "处理任务报告，包含",
            detailedReport.executed_cases.length,
            "个用例"
          );

          // 将steps按照executed_cases分组
          const stepsByCase = new Map<number, any[]>();

          // 初始化每个用例的步骤数组
          detailedReport.executed_cases.forEach((execCase: ExecutedCase) => {
            stepsByCase.set(execCase.id, []);
          });

          // 将步骤分配给对应的用例
          if (detailedReport.steps && detailedReport.steps.length > 0) {
            console.log("开始分配步骤到各个用例...");
            console.log("第一个步骤的完整数据:", detailedReport.steps[0]);

            detailedReport.steps.forEach((step: any, index: number) => {
              // 优先使用步骤中的 case_id 字段
              let caseId = step.case_id;

              // 如果步骤没有 case_id，尝试通过其他方式确定
              if (!caseId) {
                console.warn(`步骤 ${index} 缺少 case_id，尝试平均分配`);
                // 后备方案：平均分配
                const stepsPerCase = Math.ceil(
                  detailedReport.steps.length /
                    detailedReport.executed_cases.length
                );
                const caseIndex = Math.floor(index / stepsPerCase);
                caseId = detailedReport.executed_cases[caseIndex]?.id;
              }

              if (caseId && stepsByCase.has(caseId)) {
                const caseSteps = stepsByCase.get(caseId)!;
                caseSteps.push({
                  step: caseSteps.length + 1,
                  action: step.action || step.operate || "执行操作",
                  description:
                    step.describe || step.description || "执行测试步骤",
                  status:
                    step.result === "success"
                      ? "success"
                      : step.result === "failed" ||
                        step.result === "fail" ||
                        step.result === "error"
                      ? "failed"
                      : step.result === "skipped" || step.result === "skip"
                      ? "skipped"
                      : "success",
                  screenshot: step.details?.screenshot || step.screenshot,
                  duration: step.duration || "1.0s",
                  failureReason:
                    step.result === "failed" ||
                    step.result === "fail" ||
                    step.result === "error"
                      ? step.error_message ||
                        step.failure_reason ||
                        "步骤执行失败"
                      : undefined,
                });
                console.log(`步骤 ${index} 分配给用例 ${caseId}`);
              } else {
                console.warn(`步骤 ${index} 无法分配，caseId=${caseId}`);
              }
            });

            // 输出每个用例的步骤数量
            stepsByCase.forEach((steps, caseId) => {
              console.log(`用例 ${caseId} 包含 ${steps.length} 个步骤`);
            });
          }

          // 生成用例列表
          const testCases: TestCase[] = detailedReport.executed_cases.map(
            (execCase: ExecutedCase) => {
              const caseSteps = stepsByCase.get(execCase.id) || [];

              // 根据步骤结果确定用例状态
              let caseStatus = "success";
              if (caseSteps.some((step) => step.status === "failed")) {
                caseStatus = "failed";
              }

              // 计算用例持续时间
              const totalDuration = caseSteps.reduce((total, step) => {
                const duration =
                  parseFloat(step.duration.replace("s", "")) || 1;
                return total + duration;
              }, 0);

              return {
                id: execCase.id,
                name: execCase.name,
                status: caseStatus,
                duration: `${totalDuration.toFixed(1)}s`,
                description: `${execCase.name}的自动化测试，验证功能正确性`,
                steps: caseSteps,
                client: execCase.client || "未知客户端",
                page: execCase.page || "未知页面",
              };
            }
          );

          console.log("生成的测试用例:", testCases);

          return {
            ...detailedReport,
            testCases: testCases,
          };
        } else {
          // 单个用例报告
          console.log("处理单个用例报告");

          const steps: TestStep[] = (detailedReport.steps || []).map(
            (step: any, index: number) => ({
              step: index + 1,
              action: step.action || step.operate || "执行操作",
              description: step.describe || step.description || "执行测试步骤",
              status:
                step.result === "success"
                  ? "success"
                  : step.result === "failed"
                  ? "failed"
                  : step.result === "error"
                  ? "failed"
                  : "success",
              screenshot: step.details?.screenshot || step.screenshot,
              duration: step.duration || "1.0s",
              failureReason:
                step.result === "failed" || step.result === "error"
                  ? step.error_message || step.failure_reason || "步骤执行失败"
                  : undefined,
            })
          );

          const testCase: TestCase = {
            id: detailedReport.test_id || detailedReport.id,
            name: detailedReport.name,
            status: detailedReport.status,
            duration: detailedReport.duration || "0s",
            description: `${detailedReport.name}的自动化测试`,
            steps: steps,
          };

          return {
            ...detailedReport,
            testCases: [testCase],
          };
        }
      } catch (error) {
        console.error("获取详细报告数据失败:", error);
        // 返回基本的报告数据，添加空的testCases
        return { ...reportData, testCases: [] };
      }
    };

    // 将截图转换为base64的函数
    const convertImageToBase64 = async (imageName: string): Promise<string> => {
      try {
        // 如果路径包含 screenshots/ 前缀，则去掉它
        const fileName = imageName.replace(/^screenshots\//, "");
        console.log(
          `[截图转换] 原始路径: "${imageName}", 处理后: "${fileName}"`
        );

        // 尝试从后端获取截图的base64编码（注意：后端路由是 /api/screenshot 单数）
        const apiUrl = `/api/screenshot/${fileName}`;
        console.log(`[截图转换] 请求URL: ${apiUrl}`);

        const response = await axios.get(apiUrl, { responseType: "blob" });

        return new Promise((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => {
            const result = reader.result as string;
            resolve(result);
          };
          reader.readAsDataURL(response.data);
        });
      } catch (error) {
        console.error(`获取截图失败: ${imageName}`, error);
        // 返回一个1x1像素的透明PNG作为占位符
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";
      }
    };

    // 导出详细报告
    const exportReport = async (reportData: ReportRecord) => {
      try {
        message.info("正在生成详细报告，请稍候...");

        // 获取详细报告数据
        const detailedReportData = await fetchDetailedReportData(reportData);

        // 为每个步骤的截图生成base64编码
        if (detailedReportData.testCases) {
          for (const testCase of detailedReportData.testCases) {
            for (const step of testCase.steps) {
              if (step.screenshot) {
                console.log("正在转换截图:", step.screenshot);
                step.screenshotBase64 = await convertImageToBase64(
                  step.screenshot
                );
                console.log(
                  "截图转换完成，长度:",
                  step.screenshotBase64.length,
                  "前50个字符:",
                  step.screenshotBase64.substring(0, 50)
                );
              } else {
                console.log("步骤没有截图:", step.action);
              }
            }
          }
        }

        // 生成HTML报告
        const htmlContent = generateReportHTML(detailedReportData);

        // 创建并下载文件
        const blob = new Blob([htmlContent], { type: "text/html" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `测试报告_${reportData.name}_${new Date()
          .toLocaleString()
          .replace(/[\/\s:]/g, "_")}.html`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        message.success("详细报告导出成功！");
      } catch (error) {
        console.error("导出报告失败:", error);
        message.error("导出报告失败，请重试");
      }
    };

    // 获取完全模仿报告详情页的CSS样式
    const getAllureCSS = (): string => {
      return `
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8f9fa;
            color: #333;
            margin: 0;
            padding: 20px;
        }

        .report-container {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
        }

    /* 页面头部样式 */
    .page-header {
      background: #f0f9f0; /* 浅绿色背景，区分详情栏 */
      border: 1px solid #e8f5e8;
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 20px;
    }

    .header-title-section {
            flex: 1;
        }

        .header-title {
            font-size: 24px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }

        .header-subtitle {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .status-tag {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-success {
            background-color: #f0f9ff;
            color: #0ea5e9;
            border: 1px solid #e0f2fe;
        }
        
        .status-partial {
            background-color: #fefce8;
            color: #eab308;
            border: 1px solid #fef08a;
        }
        
        .status-executing {
            background-color: #f0f9ff;
            color: #3b82f6;
            border: 1px solid #bfdbfe;
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        
        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.5;
            }
        }

        .status-error {
            background-color: #fef2f2;
            color: #ef4444;
            border: 1px solid #fecaca;
        }

        .report-time {
            color: #666;
            font-size: 14px;
        }

        .header-stats {
            display: flex;
            gap: 24px;
        }

        .stat-item {
            text-align: center;
        }

        .stat-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
        }

        .stat-value {
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }

    /* 报告卡片样式 */
    .report-card {
      background: #f7fdf7; /* 使基本信息卡与页面头部绿色配色协调 */
      border-left: 4px solid #e8f5e8;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .card-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e9ecef;
        }

        .basic-info-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }

        .info-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .info-label {
            font-size: 14px;
            color: #666;
            font-weight: 500;
            min-width: fit-content;
        }

        .info-value {
            font-size: 14px;
            color: #333;
            font-weight: 500;
        }

        /* 主内容区域 */
        .report-main-content {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .case-list-header {
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid #e9ecef;
        }

        .case-list-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin: 0;
        }

        .collapse-container {
            border: 1px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }

        /* 分类样式 */
        .category-section {
            margin-bottom: 20px;
        }

        .category-section:last-child {
            margin-bottom: 0;
        }

        .category-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 8px 8px 0 0;
            margin-bottom: 0;
        }

        .category-title {
            font-size: 16px;
            font-weight: 600;
            margin: 0;
        }

        .category-count {
            font-size: 12px;
            background: rgba(255, 255, 255, 0.2);
            padding: 4px 8px;
            border-radius: 12px;
        }

        .category-content {
            border: 1px solid #e9ecef;
            border-top: none;
            border-radius: 0 0 8px 8px;
            overflow: hidden;
        }

        .category-content .collapse-item {
            border-bottom: 1px solid #e9ecef;
        }

        .category-content .collapse-item:last-child {
            border-bottom: none;
        }

        .collapse-item {
            border-bottom: 1px solid #e9ecef;
        }

        .collapse-item:last-child {
            border-bottom: none;
        }

        .collapse-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            background: #fafbfc;
            transition: background-color 0.2s;
        }

        .collapse-header:hover {
            background: #f0f2f5;
        }

        .case-header-content {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
        }

        .case-name {
            font-weight: 500;
            font-size: 14px;
            color: #303133;
        }

        .case-status-tag {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }

        .case-status-tag.success {
            background: #67c23a;
            color: white;
        }

        .case-status-tag.failed {
            background: #f56c6c;
            color: white;
        }

        .case-step-count {
            color: #909399;
            font-size: 12px;
        }

        .collapse-icon {
            transition: transform 0.3s;
            color: #909399;
        }

        .collapse-item.active .collapse-icon {
            transform: rotate(0deg);
        }

        .collapse-item:not(.active) .collapse-icon {
            transform: rotate(-90deg);
        }

        .collapse-content {
            border-top: 1px solid #e9ecef;
            background: white;
        }

        .steps-list {
            padding: 0;
        }

        .step-item {
            padding: 8px 16px;
            border-bottom: 1px solid #f0f2f5;
        }

        .step-item:last-child {
            border-bottom: none;
        }

        .step-row {
            width: 100%;
            display: flex;
            flex-direction: row;
            align-items: flex-start;
            gap: 20px;
        }

        .step-header-inline {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-shrink: 0;
            min-width: 150px;
        }

        .step-tag {
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }

        .step-tag.tag-success {
            background: #67c23a;
            color: white;
        }

        .step-tag.tag-error {
            background: #f56c6c;
            color: white;
        }

        .step-tag.tag-info {
            background: #909399;
            color: white;
        }
        
        .step-tag.tag-skipped {
            background: #409eff;
            color: white;
        }

        .step-title {
            font-weight: 500;
            color: #303133;
            font-size: 13px;
        }

        .step-details-inline {
            flex: 1;
            min-width: 0;
        }

        .step-info-row {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            align-items: center;
        }

        .step-info-item {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 13px;
        }

        .info-label {
            font-weight: 500;
            color: #606266;
        }

        .info-value {
            color: #303133;
        }

        .screenshot-link {
            color: #409eff;
            cursor: pointer;
            text-decoration: none;
        }

        .screenshot-link:hover {
            text-decoration: underline;
        }

        .step-error-row {
            margin-top: 8px;
            padding: 8px 12px;
            background: #fef0f0;
            border-left: 3px solid #f56c6c;
            border-radius: 4px;
        }

        .error-text {
            color: #f56c6c;
            font-size: 13px;
            word-break: break-word;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #909399;
        }

        .empty-state h3 {
            margin-bottom: 10px;
            color: #606266;
        }

        /* 响应式设计 */
        @media (max-width: 768px) {
            .page-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 16px;
            }
            
            .header-stats {
                width: 100%;
                justify-content: space-between;
            }
            
            .basic-info-row {
                grid-template-columns: 1fr;
                gap: 12px;
            }
            
            .step-row {
                flex-direction: column;
                gap: 10px;
            }
            
            .step-header-inline {
                min-width: auto;
            }
            
            .step-info-row {
                flex-direction: column;
                gap: 8px;
                align-items: flex-start;
            }
        }
      `;
    };

    // 生成侧边栏HTML
    const generateSidebarHTML = (
      testCases: TestCase[],
      reportName: string,
      stats: { total: number; passed: number; failed: number; passRate: string }
    ): string => {
      const casesHTML = testCases
        .map(
          (testCase, index) => `
            <div class="case-item" onclick="showCase(${index})">
                <div class="case-status ${testCase.status}"></div>
                <div class="case-info">
                    <div class="case-name" title="${testCase.name}">${testCase.name}</div>
                    <div class="case-duration">${testCase.duration}</div>
                </div>
            </div>
        `
        )
        .join("");

      return `
        <div class="sidebar-header">
            <div class="report-title">${reportName}</div>
            <div class="report-stats">
                <div class="stat-item">
                    <span class="stat-value">${stats.total}</span>
                    <div class="stat-label">总用例</div>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${stats.passed}</span>
                    <div class="stat-label">通过</div>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${stats.failed}</span>
                    <div class="stat-label">失败</div>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${stats.passRate}%</span>
                    <div class="stat-label">通过率</div>
                </div>
            </div>
        </div>
        <div class="test-cases">
            ${casesHTML}
        </div>
      `;
    };

    // 生成主内容HTML - 与报告详情页完全一致的布局
    const generateMainContentHTML = (
      testCases: TestCase[],
      reportData: DetailedReportData
    ): string => {
      if (testCases.length === 0) {
        return `
          <div class="empty-state">
              <h3>暂无测试用例</h3>
              <p>该报告中没有找到测试用例数据</p>
          </div>
        `;
      }

      // 计算统计信息
      const totalCases = testCases.length;
      const passedCases = testCases.filter(
        (c) => c.status === "success"
      ).length;
      const passRate =
        totalCases > 0 ? Math.round((passedCases / totalCases) * 100) : 0;

      // 生成页面头部统计信息
      const headerHTML = `
        <div class="page-header">
            <div class="header-title-section">
                <h1 class="header-title">测试报告详情</h1>
                <div class="header-subtitle">
                    <span class="status-tag ${
                      reportData.status === "success"
                        ? "status-success"
                        : reportData.status === "partial"
                        ? "status-partial"
                        : reportData.status === "executing"
                        ? "status-executing"
                        : "status-error"
                    }">
                        ${
                          reportData.status === "success"
                            ? "通过"
                            : reportData.status === "partial"
                            ? "部分成功"
                            : reportData.status === "executing"
                            ? "执行中..."
                            : "失败"
                        }
                    </span>
                    <span class="report-time">${reportData.time}</span>
                </div>
            </div>
            <div class="header-stats">
                <div class="stat-item">
                    <div class="stat-label">${
                      totalCases > 1 ? "批量执行" : "用例ID"
                    }</div>
                    <div class="stat-value">${
                      totalCases > 1
                        ? totalCases + "个用例"
                        : reportData.test_id || "N/A"
                    }</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">通过率</div>
                    <div class="stat-value">${passRate}%</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">耗时</div>
                    <div class="stat-value">${
                      reportData.duration || "N/A"
                    }</div>
                </div>
            </div>
        </div>
        
        <div class="report-card">
            <div class="card-title">测试基本信息</div>
            <div class="basic-info-row">
                <div class="info-item">
                    <span class="info-label">报告ID：</span>
                    <span class="info-value">${reportData.id}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">测试名称：</span>
                    <span class="info-value">${reportData.name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">执行时间：</span>
                    <span class="info-value">${reportData.time}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">状态：</span>
                    <span class="status-tag ${
                      reportData.status === "success"
                        ? "status-success"
                        : reportData.status === "partial"
                        ? "status-partial"
                        : reportData.status === "executing"
                        ? "status-executing"
                        : "status-error"
                    }">
                        ${
                          reportData.status === "success"
                            ? "通过"
                            : reportData.status === "partial"
                            ? "部分成功"
                            : reportData.status === "executing"
                            ? "执行中..."
                            : "失败"
                        }
                    </span>
                </div>
                <div class="info-item">
                    <span class="info-label">通过率：</span>
                    <span class="info-value">${passRate}%</span>
                </div>
                <div class="info-item">
                    <span class="info-label">执行耗时：</span>
                    <span class="info-value">${
                      reportData.duration || "N/A"
                    }</span>
                </div>
                <div class="info-item">
                    <span class="info-label">执行用例数：</span>
                    <span class="info-value">${totalCases}</span>
                </div>
            </div>
        </div>
      `;

      // 调试：检查步骤是否有截图
      testCases.forEach((testCase, caseIndex) => {
        console.log(`用例 ${caseIndex}: ${testCase.name}`);
        testCase.steps.forEach((step, stepIndex) => {
          console.log(
            `  步骤 ${stepIndex}: screenshot=${
              step.screenshot
            }, screenshotBase64=${step.screenshotBase64 ? "已转换" : "未转换"}`
          );
        });
      });

      // 收集所有截图数据到一个数组中
      const screenshotData: string[] = [];
      testCases.forEach((testCase) => {
        testCase.steps.forEach((step) => {
          if (step.screenshotBase64) {
            screenshotData.push(step.screenshotBase64);
          }
        });
      });

      // 为每个用例生成折叠面板
      let screenshotIndex = 0;
      const casesHTML = testCases
        .map((testCase, caseIndex) => {
          return `
                    <div class="collapse-item" id="case-${caseIndex}">
                        <div class="collapse-header" onclick="toggleCase(${caseIndex})">
                            <div class="case-header-content">
                                <span class="case-name">${testCase.name}</span>
                                <span class="case-status-tag ${
                                  testCase.status === "success"
                                    ? "success"
                                    : testCase.status === "failed"
                                    ? "failed"
                                    : "failed"
                                }">
                                    ${
                                      testCase.status === "success"
                                        ? "通过"
                                        : "失败"
                                    }
                                </span>
                                <span class="case-step-count">${
                                  testCase.steps.length
                                } 个步骤</span>
                            </div>
                            <span class="collapse-icon">▼</span>
                        </div>
                        <div class="collapse-content" style="display: none;">
                            <div class="steps-list">
                                ${testCase.steps
                                  .map((step, stepIndex) => {
                                    const currentScreenshotIndex =
                                      step.screenshotBase64
                                        ? screenshotIndex++
                                        : -1;
                                    return `
                                    <div class="step-item">
                                        <div class="step-row">
                                            <!-- 步骤标签 -->
                                            <div class="step-header-inline">
                                                <span class="step-tag ${
                                                  step.status === "success"
                                                    ? "tag-success"
                                                    : step.status === "failed"
                                                    ? "tag-error"
                                                    : step.status === "skipped"
                                                    ? "tag-skipped"
                                                    : "tag-info"
                                                }">
                                                    步骤 ${stepIndex + 1}
                                                </span>
                                                ${
                                                  step.description &&
                                                  step.description !==
                                                    step.action
                                                    ? `<span class="step-title">${step.description}</span>`
                                                    : ""
                                                }
                                            </div>
                                            
                                            <!-- 步骤详情 -->
                                            <div class="step-details-inline">
                                                <div class="step-info-row">
                                                    <div class="step-info-item">
                                                        <span class="info-label">操作：</span>
                                                        <span class="info-value">${
                                                          step.action
                                                        }</span>
                                                    </div>
                                                    <div class="step-info-item">
                                                        <span class="info-label">目标：</span>
                                                        <span class="info-value">${
                                                          step.description
                                                        }</span>
                                                    </div>
                                                    ${
                                                      currentScreenshotIndex >=
                                                      0
                                                        ? `
                                                    <div class="step-info-item">
                                                        <span class="info-label">截图：</span>
                                                        <a href="javascript:void(0)" 
                                                           class="screenshot-link" 
                                                           onclick="showFullScreenImage(event, ${currentScreenshotIndex})">
                                                            查看截图
                                                        </a>
                                                    </div>
                                                    `
                                                        : ""
                                                    }
                                                </div>
                                                
                                                ${
                                                  step.failureReason
                                                    ? `
                                                    <div class="step-error-row">
                                                        <span class="info-label">错误信息：</span>
                                                        <span class="info-value error-text">${step.failureReason}</span>
                                                    </div>
                                                `
                                                    : ""
                                                }
                                            </div>
                                        </div>
                                    </div>
                                `;
                                  })
                                  .join("")}
                            </div>
                        </div>
                    </div>
                `;
        })
        .join("");

      return `
        ${headerHTML}
        <div class="report-main-content">
            <div class="case-list-header">
                <h3 class="case-list-title">用例列表</h3>
            </div>
            <div class="collapse-container">
                ${casesHTML}
            </div>
        </div>
      `;
    };

    // 生成JavaScript代码
    const generateJavaScript = (screenshotData: string[]): string => {
      return `
        // 全局截图数据数组
        const SCREENSHOT_DATA = ${JSON.stringify(screenshotData)};
        console.log('截图数据数组长度:', SCREENSHOT_DATA.length);
        console.log('前3个截图数据长度:', SCREENSHOT_DATA.slice(0, 3).map(s => s.length));
        
        // 切换用例折叠面板
        function toggleCase(caseIndex) {
            const collapseItem = document.getElementById('case-' + caseIndex);
            if (!collapseItem) return;
            
            const content = collapseItem.querySelector('.collapse-content');
            const icon = collapseItem.querySelector('.collapse-icon');
            
            if (collapseItem.classList.contains('active')) {
                collapseItem.classList.remove('active');
                content.style.display = 'none';
                icon.style.transform = 'rotate(-90deg)';
            } else {
                collapseItem.classList.add('active');
                content.style.display = 'block';
                icon.style.transform = 'rotate(0deg)';
            }
        }

        // 全屏显示图片
        function showFullScreenImage(event, screenshotIndex) {
            event.preventDefault();
            event.stopPropagation();
            
            const imgSrc = SCREENSHOT_DATA[screenshotIndex];
            console.log('截图索引:', screenshotIndex, '数据长度:', imgSrc ? imgSrc.length : 0);
            if (!imgSrc) {
                console.error('未找到截图数据');
                return;
            }
            
            const overlay = document.createElement('div');
            overlay.style.cssText = \`
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.9);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                cursor: zoom-out;
            \`;
            
            const fullImg = document.createElement('img');
            fullImg.src = imgSrc;
            fullImg.style.cssText = \`
                max-width: 95%;
                max-height: 95%;
                object-fit: contain;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            \`;
            
            overlay.appendChild(fullImg);
            overlay.onclick = function() {
                document.body.removeChild(overlay);
            };
            
            document.body.appendChild(overlay);
        }

        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            // 所有用例默认折叠状态，用户可以手动展开
            console.log('报告页面初始化完成');
        });
      `;
    };

    // 生成HTML报告内容
    const generateReportHTML = (reportData: DetailedReportData): string => {
      const testCases = reportData.testCases || [];

      // 计算统计信息
      const totalCases = testCases.length;
      const passedCases = testCases.filter(
        (tc) => tc.status === "success"
      ).length;
      const failedCases = testCases.filter(
        (tc) => tc.status === "failed"
      ).length;
      const passRate =
        totalCases > 0 ? ((passedCases / totalCases) * 100).toFixed(1) : "0.0";

      // 获取CSS样式
      const css = getAllureCSS();

      // 生成主内容HTML
      const mainContent = generateMainContentHTML(testCases, reportData);

      // 收集所有截图数据
      const screenshotData: string[] = [];
      testCases.forEach((testCase) => {
        testCase.steps.forEach((step) => {
          if (step.screenshotBase64) {
            screenshotData.push(step.screenshotBase64);
          }
        });
      });

      // 生成JavaScript代码
      const javascript = generateJavaScript(screenshotData);

      // 构建HTML内容
      const LT = "<"; // 小于号
      const GT = ">"; // 大于号

      return `<!DOCTYPE html>
                ${LT}html lang="zh-CN"${GT}
                ${LT}head${GT}
                    ${LT}meta charset="UTF-8"${GT}
                    ${LT}meta name="viewport" content="width=device-width, initial-scale=1.0"${GT}
                    ${LT}title${GT}测试报告 - ${reportData.name}${LT}/title${GT}
                    ${LT}style${GT}${css}${LT}/style${GT}
                ${LT}/head${GT}
                ${LT}body${GT}
                    ${LT}div class="report-container"${GT}
                        ${mainContent}
                    ${LT}/div${GT}
                    ${LT}script${GT}${javascript}${LT}/script${GT}
                ${LT}/body${GT}
                ${LT}/html${GT}`;
    };

    // 表格列定义
    const columns: DataTableColumns<ReportRecord> = [
      {
        type: "selection",
      },
      {
        title: "报告ID",
        key: "id",
        width: 120,
        titleAlign: "center",
        align: "center",
      },
      {
        title: "测试名称",
        key: "name",
        titleAlign: "center",
        align: "center",
        ellipsis: {
          tooltip: true,
        },
      },
      {
        title: "状态",
        key: "status",
        width: 100,
        titleAlign: "center",
        align: "center",
        render(row) {
          const statusMap: { [key: string]: { text: string; type: string } } = {
            success: { text: "成功", type: "success" },
            partial: { text: "部分成功", type: "warning" },
            executing: { text: "执行中...", type: "info" },
            failed: { text: "失败", type: "error" },
            fail: { text: "失败", type: "error" },
            error: { text: "失败", type: "error" },
            running: { text: "运行中", type: "info" },
          };

          const status = statusMap[row.status] || {
            text: row.status,
            type: "default",
          };

          return h(
            "span",
            {
              style: {
                color:
                  status.type === "success"
                    ? "#52c41a"
                    : status.type === "warning"
                    ? "#faad14"
                    : status.type === "error"
                    ? "#ff4d4f"
                    : status.type === "info"
                    ? "#1890ff"
                    : "#666",
              },
            },
            status.text
          );
        },
      },
      {
        title: "执行时间",
        key: "time",
        width: 180,
        titleAlign: "center",
        align: "center",
        render(row) {
          return row.time || "-";
        },
      },
      {
        title: "持续时间",
        key: "duration",
        width: 100,
        titleAlign: "center",
        align: "center",
      },
      {
        title: "通过率",
        key: "pass_rate",
        width: 100,
        titleAlign: "center",
        align: "center",
        render(row) {
          return `${row.pass_rate}%`;
        },
      },
      {
        title: "操作",
        key: "actions",
        width: 300,
        titleAlign: "center",
        align: "center",
        render(row) {
          return h(
            NSpace,
            { size: "small" },
            {
              default: () => [
                h(
                  NButton,
                  {
                    size: "small",
                    type: "info",
                    style: { width: "80px" },
                    disabled: row.status === "executing",
                    onClick: () => viewReportDetail(row.id),
                  },
                  {
                    default: () => "查看详情",
                  }
                ),
                h(
                  NButton,
                  {
                    size: "small",
                    type: "primary",
                    style: { width: "80px" },
                    disabled: row.status === "executing",
                    onClick: () => exportReport(row),
                  },
                  { default: () => "导出报告" }
                ),
                h(
                  NButton,
                  {
                    size: "small",
                    type: "error",
                    style: { width: "80px" },
                    disabled: row.status === "executing",
                    onClick: () => deleteReport(row.id),
                  },
                  { default: () => "删除" }
                ),
              ],
            }
          );
        },
      },
    ];

    // 组件挂载时获取数据
    onMounted(() => {
      fetchReports();
    });

    // 监听executing状态，启动或停止轮询
    watch(hasExecutingReport, (hasExecuting) => {
      if (hasExecuting) {
        // 如果有执行中的报告，启动轮询
        if (!pollingTimer) {
          console.log("启动报告轮询...");
          pollingTimer = window.setInterval(() => {
            fetchReports();
          }, 2000); // 每2秒刷新一次
        }
      } else {
        // 如果没有执行中的报告，停止轮询
        if (pollingTimer) {
          console.log("停止报告轮询");
          clearInterval(pollingTimer);
          pollingTimer = null;
        }
      }
    });

    // 组件卸载时清除定时器
    onUnmounted(() => {
      if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
      }
    });

    return {
      loading,
      data,
      pagedData,
      columns,
      selectedRowKeys,
      fetchReports,
      deleteReport,
      batchDeleteReports,
      handleCheck,
      exportReport,
      viewReportDetail,
      pagination,
      page,
      pageSize,
      handlePageChange,
      handlePageSizeChange,
    };
  },
});
</script>
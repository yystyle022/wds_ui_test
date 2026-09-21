<template>
  <div class="report-container">
    <div class="page-header">
      <n-page-header @back="goBack">
        <template #title>
          <div class="header-title">测试报告详情</div>
        </template>
        <template #subtitle>
          <n-tag
            :type="
              report.status === 'success'
                ? 'success'
                : report.status === 'partial'
                ? 'warning'
                : 'error'
            "
            size="small"
          >
            {{
              report.status === "success"
                ? "通过"
                : report.status === "partial"
                ? "部分通过"
                : "失败"
            }}
          </n-tag>
          <span class="report-time">{{ report.time }}</span>
        </template>
        <template #extra>
          <n-space>
            <n-statistic
              :label="isBatchReport ? '批量执行' : '用例ID'"
              :value="
                isBatchReport
                  ? `${getExecutedCasesCount()}个用例`
                  : report.test_id
              "
            />
            <n-statistic label="通过率" :value="`${report.pass_rate}%`" />
            <n-statistic label="耗时" :value="report.duration" />
          </n-space>
        </template>
      </n-page-header>
    </div>

    <n-card title="测试基本信息" class="report-card">
      <!-- 基本信息一行显示 -->
      <div class="basic-info-row">
        <div class="info-item">
          <span class="info-label">报告ID：</span>
          <span class="info-value">{{ report.id }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">测试名称：</span>
          <span class="info-value" :title="report.name">{{ report.name }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">执行时间：</span>
          <span class="info-value">{{ report.time }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">状态：</span>
          <n-tag
            :type="
              report.status === 'success'
                ? 'success'
                : report.status === 'partial'
                ? 'warning'
                : 'error'
            "
            size="small"
          >
            {{
              report.status === "success"
                ? "通过"
                : report.status === "partial"
                ? "部分通过"
                : "失败"
            }}
          </n-tag>
        </div>
        <div class="info-item">
          <span class="info-label">通过率：</span>
          <span class="info-value">{{ report.pass_rate }}%</span>
        </div>
        <div class="info-item">
          <span class="info-label">执行耗时：</span>
          <span class="info-value">{{ report.duration }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">执行用例数：</span>
          <span class="info-value">{{ getExecutedCasesCount() }}</span>
        </div>
      </div>

      <!-- 用例列表单独显示 -->
      <div v-if="hasExecutedCases" class="case-list-section">
        <div class="case-list-header">
          <span class="info-label">用例列表：</span>
        </div>
        <div class="case-list-content">
          <!-- 新数据格式 - executed_cases -->
          <n-space
            v-if="report.executed_cases && report.executed_cases.length > 0"
          >
            <n-tag
              v-for="caseInfo in report.executed_cases"
              :key="caseInfo.id"
              size="small"
              type="info"
            >
              {{ `${caseInfo.id} - ${caseInfo.name}` }}
            </n-tag>
          </n-space>

          <!-- 兼容旧数据格式 - batch_info -->
          <n-space v-else-if="isBatchReport && report.batch_info?.case_names">
            <n-tag
              v-for="(name, index) in report.batch_info?.case_names"
              :key="index"
              size="small"
              type="info"
            >
              {{
                `${report.batch_info?.case_ids?.[index] || "Unknown"} - ${name}`
              }}
            </n-tag>
          </n-space>
        </div>
      </div>
    </n-card>

    <!-- 执行配置信息 -->
    <n-card v-if="report.config" title="执行配置" class="report-card">
      <div class="config-info-row">
        <div class="info-item">
          <span class="info-label">浏览器：</span>
          <span class="info-value">{{
            getBrowserLabel(report.config.browser)
          }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">运行模式：</span>
          <span class="info-value">{{
            report.config.headless ? "无头模式" : "显示界面"
          }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">步骤截图：</span>
          <span class="info-value">{{
            report.config.saveScreenshots ? "启用" : "禁用"
          }}</span>
        </div>
        <div v-if="isBatchReport" class="info-item">
          <span class="info-label">执行模式：</span>
          <span class="info-value">{{
            getExecutionModeText(report.batch_info?.execution_mode)
          }}</span>
        </div>
        <div v-if="report.description" class="info-item description-item">
          <span class="info-label">执行说明：</span>
          <span class="info-value" :title="report.description">{{
            report.description
          }}</span>
        </div>
      </div>
    </n-card>

    <!-- 测试用例详情 - 统一按用例分组展示 -->
    <n-card title="测试用例详情" class="report-card steps-card">
      <n-collapse
        :default-expanded-names="
          groupedSteps.length === 1 ? [`case-${groupedSteps[0]?.caseId}`] : []
        "
      >
        <n-collapse-item
          v-for="caseGroup in groupedSteps"
          :key="caseGroup.caseId"
          :name="`case-${caseGroup.caseId}`"
        >
          <template #header>
            <div class="case-header">
              <div class="case-info">
                <span class="case-name">{{ caseGroup.caseName }}</span>
                <n-tag
                  :type="caseGroup.status === 'success' ? 'success' : 'error'"
                  size="small"
                  class="case-status-tag"
                >
                  {{ caseGroup.status === "success" ? "通过" : "失败" }}
                </n-tag>
                <span class="case-step-count"
                  >{{ caseGroup.steps.length }} 个步骤</span
                >
              </div>
            </div>
          </template>
          <n-list bordered>
            <n-list-item v-for="(step, index) in caseGroup.steps" :key="index">
              <div class="step-row">
                <!-- 步骤标签 -->
                <div class="step-header">
                  <n-tag
                    :type="
                      step.result === 'success'
                        ? 'success'
                        : step.result === 'fail' || step.result === 'error'
                        ? 'error'
                        : step.result === 'skipped' || step.result === 'skip'
                        ? 'info'
                        : 'default'
                    "
                    class="step-tag"
                  >
                    步骤 {{ step.step_number || index + 1 }}
                  </n-tag>

                  <div class="step-title" v-if="step.describe">
                    <n-tooltip trigger="hover" placement="top">
                      <template #trigger>
                        <span class="step-title-text">{{ step.describe }}</span>
                      </template>
                      <span>{{ step.describe }}</span>
                    </n-tooltip>
                  </div>
                </div>

                <!-- 步骤详情 -->
                <div class="step-details">
                  <div class="step-info-row">
                    <div class="step-info-item">
                      <span class="info-label">操作：</span>
                      <n-tooltip trigger="hover" placement="top">
                        <template #trigger>
                          <span class="info-value">{{ step.action }}</span>
                        </template>
                        <span>{{ step.action }}</span>
                      </n-tooltip>
                    </div>
                    <div class="step-info-item">
                      <span class="info-label">目标：</span>
                      <n-tooltip trigger="hover" placement="top">
                        <template #trigger>
                          <span class="info-value">{{ step.value }}</span>
                        </template>
                        <span>{{ step.value }}</span>
                      </n-tooltip>
                    </div>
                    <div class="step-info-item" v-if="step.details?.screenshot">
                      <span class="info-label">截图：</span>
                      <n-button
                        text
                        type="primary"
                        @click="showImagePreview(step.details.screenshot)"
                        class="screenshot-link"
                      >
                        查看截图
                      </n-button>
                    </div>
                  </div>

                  <!-- 错误信息单独一行 -->
                  <div v-if="step.details?.error" class="step-error-row">
                    <span class="info-label">错误信息：</span>
                    <span
                      class="info-value error-text"
                      :title="step.details.error"
                      >{{ step.details.error }}</span
                    >
                  </div>

                  <!-- 消息单独一行 -->
                  <div v-if="step.details?.message" class="step-message-row">
                    <span class="info-label">消息：</span>
                    <n-tooltip trigger="hover" placement="top">
                      <template #trigger>
                        <span class="info-value">{{
                          step.details.message
                        }}</span>
                      </template>
                      <span>{{ step.details.message }}</span>
                    </n-tooltip>
                  </div>
                </div>
              </div>
            </n-list-item>
          </n-list>
        </n-collapse-item>
      </n-collapse>

      <!-- 如果没有步骤数据，显示提示信息 -->
      <div v-if="groupedSteps.length === 0" class="no-steps-message">
        <n-empty description="暂无步骤数据" />
      </div>
    </n-card>

    <!-- 图片预览弹窗保持不变 -->
    <n-modal
      v-model:show="showPreview"
      preset="dialog"
      :title="'截图预览'"
      :style="{
        width: 'auto',
        maxWidth: '90%',
        maxHeight: '90vh',
        overflow: 'hidden',
      }"
    >
      <div class="modal-content">
        <img
          :src="previewImage"
          class="preview-image"
          @error="handleImageError"
        />
      </div>
    </n-modal>
  </div>
</template>

<script lang="ts">
// script 部分保持不变，只添加一个计算属性
import { defineComponent, ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import axios from "axios";
import {
  NCard,
  NPageHeader,
  NDescriptions,
  NDescriptionsItem,
  NTag,
  NSpace,
  NStatistic,
  NImage,
  NButton,
  NModal,
  NList,
  NListItem,
  NCollapse,
  NCollapseItem,
  NEmpty,
  NTooltip,
  useMessage,
} from "naive-ui";

// 接口定义保持不变...
interface StepDetail {
  title?: string;
  error?: string;
  message?: string;
  screenshot?: string;
  success?: boolean;
  [key: string]: any;
}

interface TestStep {
  case_id?: number;
  case_name?: string;
  step_number?: number;
  action: string;
  value: string;
  describe?: string;
  result: "success" | "fail" | "skip" | string;
  details?: StepDetail;
}

interface BatchInfo {
  total_cases: number;
  case_ids: number[];
  case_names: string[];
  execution_mode?: string;
}

interface ExecutedCase {
  id: number;
  name: string;
}

interface TestReport {
  id: number;
  test_id: number | string;
  name: string;
  time: string;
  status: string;
  pass_rate: number;
  duration: string;
  config?: {
    browser: string;
    headless: boolean;
    saveScreenshots: boolean;
  };
  batch_info?: BatchInfo;
  steps: TestStep[];
  executed_cases?: ExecutedCase[];
  description?: string; // 添加描述字段
}

export default defineComponent({
  name: "ReportView",
  components: {
    NCard,
    NPageHeader,
    NTag,
    NSpace,
    NStatistic,
    NButton,
    NModal,
    NList,
    NListItem,
    NCollapse,
    NCollapseItem,
    NEmpty,
    NTooltip,
  },
  setup() {
    const route = useRoute();
    const router = useRouter();
    const message = useMessage();

    const report = ref<TestReport>({
      id: 0,
      test_id: 0,
      name: "",
      time: "",
      status: "",
      pass_rate: 0,
      duration: "",
      steps: [],
    });

    const showPreview = ref(false);
    const previewImage = ref("");

    // 获取执行的用例数量
    const getExecutedCasesCount = (): number => {
      if (report.value.executed_cases) {
        return report.value.executed_cases.length;
      }
      // 兼容旧数据格式
      return report.value.batch_info?.total_cases || 1;
    };

    // 判断是否为批量执行报告
    const isBatchReport = computed(() => {
      if (
        report.value.executed_cases &&
        report.value.executed_cases.length > 1
      ) {
        return true;
      }
      return report.value.batch_info != null;
    });

    // 判断是否有执行用例信息需要显示
    const hasExecutedCases = computed(() => {
      return (
        (report.value.executed_cases &&
          report.value.executed_cases.length > 0) ||
        (isBatchReport.value && report.value.batch_info?.case_names)
      );
    });

    // 按用例分组步骤
    const groupedSteps = computed(() => {
      console.log("计算 groupedSteps:");
      console.log("  - isBatchReport:", isBatchReport.value);
      console.log("  - report.value.batch_info:", report.value.batch_info);
      console.log(
        "  - report.value.executed_cases:",
        report.value.executed_cases
      );
      console.log("  - report.value.steps:", report.value.steps);

      const groups = new Map();

      // 如果是批量报告，按用例ID分组
      if (isBatchReport.value) {
        console.log("处理批量报告...");

        // 先检查是否所有步骤都有case_id
        const stepsWithCaseId = report.value.steps.filter(
          (step) => step.case_id
        );
        const stepsWithoutCaseId = report.value.steps.filter(
          (step) => !step.case_id
        );

        console.log(`  - 有case_id的步骤: ${stepsWithCaseId.length}个`);
        console.log(`  - 缺少case_id的步骤: ${stepsWithoutCaseId.length}个`);

        if (stepsWithCaseId.length > 0) {
          // 如果有步骤包含case_id，按case_id分组
          stepsWithCaseId.forEach((step, stepIndex) => {
            const caseId = step.case_id;
            console.log(
              `  - 步骤 ${stepIndex}: case_id=${caseId}, case_name=${step.case_name}`
            );

            if (!groups.has(caseId)) {
              // 获取用例名称
              let caseName = step.case_name || `用例 ${caseId}`;

              // 如果有executed_cases信息，优先使用
              if (report.value.executed_cases) {
                const caseInfo = report.value.executed_cases.find(
                  (c) => c.id === caseId
                );
                if (caseInfo) {
                  caseName = caseInfo.name;
                }
              }
              // 兼容旧格式
              else if (
                report.value.batch_info?.case_names &&
                caseId !== undefined
              ) {
                const caseIndex =
                  report.value.batch_info.case_ids?.indexOf(caseId);
                if (caseIndex !== -1 && caseIndex !== undefined) {
                  caseName = report.value.batch_info.case_names[caseIndex];
                }
              }

              console.log(`    创建新用例组: ${caseId} - ${caseName}`);
              groups.set(caseId, {
                caseId,
                caseName,
                steps: [],
                status: "success", // 默认成功，有失败步骤时会更新
                hasFailedSteps: false,
                hasSuccessSteps: false,
              });
            }

            const group = groups.get(caseId);
            group.steps.push(step);

            // 统计成功和失败步骤
            if (step.result === "fail" || step.result === "error") {
              group.hasFailedSteps = true;
            } else if (step.result === "success") {
              group.hasSuccessSteps = true;
            }

            // 更新用例状态：同时有成功和失败步骤则为partial，有失败步骤则为fail，否则为success
            if (group.hasFailedSteps && group.hasSuccessSteps) {
              group.status = "partial";
            } else if (group.hasFailedSteps) {
              group.status = "fail";
            } else {
              group.status = "success";
            }
          });
        }

        // 如果有缺少case_id的步骤，创建一个默认组来放置它们
        if (stepsWithoutCaseId.length > 0) {
          console.log("发现缺少case_id的步骤，创建默认组");
          const defaultCaseId = "unknown";
          const defaultCaseName = "未分组步骤";

          groups.set(defaultCaseId, {
            caseId: defaultCaseId,
            caseName: defaultCaseName,
            steps: stepsWithoutCaseId,
            status: stepsWithoutCaseId.some(
              (s) => s.result === "fail" || s.result === "error"
            )
              ? "fail"
              : "success",
          });
        }

        // 如果完全没有case_id信息，但有batch_info，尝试根据batch_info分组
        if (
          stepsWithCaseId.length === 0 &&
          report.value.batch_info &&
          report.value.batch_info.case_ids
        ) {
          console.log("尝试根据batch_info重建分组...");
          const caseIds = report.value.batch_info.case_ids;
          const caseNames = report.value.batch_info.case_names || [];

          // 假设步骤是按用例顺序排列的，尝试平均分配
          const stepsPerCase = Math.ceil(
            report.value.steps.length / caseIds.length
          );

          caseIds.forEach((caseId, index) => {
            const startIndex = index * stepsPerCase;
            const endIndex = Math.min(
              (index + 1) * stepsPerCase,
              report.value.steps.length
            );
            const caseSteps = report.value.steps.slice(startIndex, endIndex);

            if (caseSteps.length > 0) {
              const caseName = caseNames[index] || `用例 ${caseId}`;
              console.log(
                `    重建用例组: ${caseId} - ${caseName} (${caseSteps.length}个步骤)`
              );

              groups.set(caseId, {
                caseId,
                caseName,
                steps: caseSteps,
                status: caseSteps.some(
                  (s) => s.result === "fail" || s.result === "error"
                )
                  ? "fail"
                  : "success",
              });
            }
          });
        }
      } else {
        console.log("处理单个用例报告...");
        // 单个用例报告，创建一个用例组
        if (report.value.steps.length > 0) {
          const caseId = report.value.test_id || 1;
          const caseName = report.value.name || "测试用例";

          // 计算用例状态
          let hasFailedSteps = false;
          let hasSuccessSteps = false;
          for (const step of report.value.steps) {
            if (step.result === "fail" || step.result === "error") {
              hasFailedSteps = true;
            } else if (step.result === "success") {
              hasSuccessSteps = true;
            }
          }

          let status = "success";
          if (hasFailedSteps && hasSuccessSteps) {
            status = "partial";
          } else if (hasFailedSteps) {
            status = "fail";
          }

          console.log(`    创建单用例组: ${caseId} - ${caseName}`);
          groups.set(caseId, {
            caseId,
            caseName,
            steps: report.value.steps,
            status,
          });
        }
      }

      const result = Array.from(groups.values()).sort((a, b) => {
        // 确保caseId是数字类型进行比较
        const aId =
          typeof a.caseId === "number"
            ? a.caseId
            : parseInt(String(a.caseId)) || 0;
        const bId =
          typeof b.caseId === "number"
            ? b.caseId
            : parseInt(String(b.caseId)) || 0;
        return aId - bId;
      });

      console.log("最终分组结果:", result);
      console.log("  - 用例组数量:", result.length);
      result.forEach((group, index) => {
        console.log(
          `  - 用例组 ${index}: ID=${group.caseId}, 名称=${group.caseName}, 步骤数=${group.steps.length}`
        );
      });

      return result;
    });

    const getExecutionModeText = (mode?: string): string => {
      const modeMap: Record<string, string> = {
        parallel: "并行执行",
        sequential: "顺序执行",
      };
      return modeMap[mode || "sequential"] || "顺序执行";
    };

    const getBrowserLabel = (browserValue: string): string => {
      const browserMap: Record<string, string> = {
        chrome: "Chrome",
        firefox: "Firefox",
        chromium: "Chromium",
        msedge: "Edge",
      };
      return browserMap[browserValue] || browserValue;
    };

    const getReportDetails = async () => {
      try {
        const reportId = route.params.id;
        if (!reportId) {
          message.error("报告ID不存在");
          return;
        }

        const response = await axios.get(`/api/reports/${reportId}`);
        report.value = response.data as TestReport;

        // 调试日志：查看获取到的报告数据
        console.log("获取到的报告数据:", report.value);
        console.log("报告步骤数据:", report.value.steps);
        console.log("步骤数量:", report.value.steps?.length || 0);

        // 分析步骤结果分布
        if (report.value.steps) {
          const resultCounts: Record<string, number> = {};
          report.value.steps.forEach((step) => {
            const result = step.result;
            resultCounts[result] = (resultCounts[result] || 0) + 1;
          });
          console.log("步骤结果分布:", resultCounts);
        }
      } catch (error) {
        console.error("获取报告详情失败:", error);
        message.error("获取报告详情失败，请检查网络或服务器状态");
      }
    };

    const goBack = () => {
      router.push("/reports");
    };

    const getScreenshotUrl = (path?: string) => {
      if (!path) return "";
      if (path.startsWith("http")) return path;
      return `/screenshots/${path.split("/").pop()}`;
    };

    const showImagePreview = (path?: string) => {
      if (!path) return;
      previewImage.value = getScreenshotUrl(path);
      showPreview.value = true;
    };

    const handleImageError = () => {
      message.error("图片加载失败，请检查网络或图片路径");
    };

    onMounted(() => {
      getReportDetails();
    });

    return {
      report,
      goBack,
      getScreenshotUrl,
      showPreview,
      previewImage,
      showImagePreview,
      handleImageError,
      isBatchReport,
      hasExecutedCases,
      groupedSteps,
      getBrowserLabel,
      getExecutionModeText,
      getExecutedCasesCount,
    };
  },
});
</script>

<style scoped>
.report-container {
  padding: 20px;
  max-width: 100%;
  box-sizing: border-box;
  overflow-x: hidden;
}

.page-header {
  margin-bottom: 10px;
  background: white;
  padding: 10px;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.header-title {
  font-size: 24px;
  font-weight: bold;
}

.report-time {
  margin-left: 12px;
  color: #606266;
}

.report-card {
  margin-bottom: 20px;
  width: 100%;
}

/* 基本信息一行布局 - 进一步减小间隔 */
.basic-info-row,
.config-info-row {
  display: flex;
  flex-wrap: wrap;
  gap: 15px; /* 从 20px 减小到 15px */
  align-items: center;
  padding: 4px 0; /* 从 8px 减小到 4px */
}

.info-item {
  display: flex;
  align-items: center;
  min-width: 0;
  flex-shrink: 0;
  padding: 4px 8px; /* 从 6px 12px 减小到 4px 8px */
  background-color: #fafbfc;
  border-radius: 4px; /* 从 6px 减小到 4px */
  border: 1px solid #e4e7ed;
  transition: all 0.2s ease;
}

.info-item:hover {
  background-color: #f0f2f5;
  border-color: #d9dce0;
}

.info-label {
  font-weight: 500;
  color: #606266;
  margin-right: 4px; /* 从 6px 减小到 4px */
  white-space: nowrap;
  font-size: 12px; /* 稍微减小字体 */
}

.info-value {
  color: #303133;
  word-break: break-word;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px; /* 稍微减小字体 */
}

/* 用例列表单独区域 */
.case-list-section {
  margin-top: 8px; /* 从 16px 减小到 12px */
  padding-top: 8px; /* 从 16px 减小到 12px */
  border-top: 1px solid #ebeef5;
}

.case-list-header {
  margin-bottom: 8px; /* 从 10px 减小到 8px */
}

.case-list-content {
  margin-left: 0;
}

/* 配置信息中的描述项特殊处理 */
.description-item .info-value {
  max-width: 300px;
}

/* 步骤详情样式保持不变 */
.steps-card {
  overflow: hidden;
}

/* 用例头部样式 */
.case-header {
  width: 100%;
  padding: 1px 0; /* 从 8px 减小到 6px */
}

.case-info {
  display: flex;
  align-items: center;
  gap: 12px; /* 从 12px 减小到 10px */
}

.case-name {
  font-weight: 500;
  font-size: 13px; /* 从 16px 减小到 14px */
  color: #303133;
}

.case-status-tag {
  flex-shrink: 0;
}

.case-step-count {
  color: #909399;
  font-size: 11px; /* 从 12px 减小到 11px */
}

/* 折叠面板样式调整 */
:deep(.n-collapse-item__header) {
  padding: 10px 14px; /* 从 12px 16px 减小到 10px 14px */
  border-bottom: none; /* 移除分割线 */
}

:deep(.n-collapse-item__content-wrapper) {
  border-bottom: none;
}

:deep(.n-collapse-item__content-inner) {
  padding: 0;
}

/* 进一步减少列表的间距 */
:deep(.n-list) {
  padding: 0;
  margin: 0;
}

:deep(.n-list-item) {
  padding: 2px 8px; /* 进一步减小到 2px 8px */
  margin: 0;
  border-bottom: none;
}

/* 空状态样式 */
.no-steps-message {
  padding: 40px 20px;
  text-align: center;
}

.step-row {
  width: 100%;
  display: flex;
  flex-direction: row; /* 改为水平布局 */
  align-items: center; /* 垂直居中对齐 */
  gap: 30px; /* 从 12px 增加到 20px */
  padding: 1px 0; /* 进一步减小到 1px */
}

.step-header {
  display: flex;
  align-items: center;
  gap: 12px; /* 从 8px 增加到 12px */
  flex-shrink: 0; /* 不允许收缩 */
  padding-bottom: 0; /* 移除底部内边距 */
  border-bottom: none; /* 移除底部边框 */
}

.step-tag {
  min-width: 80px;
  text-align: center;
}

.case-name-tag {
  flex-shrink: 0;
}

.step-title {
  font-weight: 500;
  color: #303133;
  flex-shrink: 0; /* 不允许收缩 */
  white-space: nowrap; /* 防止换行 */
  max-width: 200px; /* 限制最大宽度 */
  overflow: hidden; /* 隐藏溢出 */
  text-overflow: ellipsis; /* 显示省略号 */
}

.step-details {
  width: 100%;
  display: flex;
  flex-direction: row; /* 改为水平布局 */
  flex-wrap: wrap; /* 允许换行 */
  align-items: center; /* 垂直居中 */
  gap: 20px; /* 从 12px 增加到 20px */
}

.step-info-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px; /* 从 16px 增加到 24px */
  padding: 0; /* 移除垂直内边距 */
  align-items: center;
}

.step-info-item {
  display: flex;
  align-items: center;
  white-space: nowrap;
  flex-wrap: wrap;
}

.step-error-row,
.step-message-row {
  padding: 0; /* 移除内边距 */
  display: flex;
  align-items: flex-start; /* 改为顶部对齐 */
  flex-wrap: wrap; /* 允许换行 */
  word-break: break-word; /* 单词换行 */
  /* 移除以下限制，允许完整显示错误信息 */
  /* white-space: nowrap; */
  /* overflow: hidden; */
  /* text-overflow: ellipsis; */
}

.error-text {
  color: #f56c6c;
  white-space: pre-wrap; /* 保留换行和空格 */
  word-break: break-word; /* 长单词换行 */
  max-width: 100%; /* 确保不超出容器 */
}

.screenshot-link {
  font-weight: normal;
  margin-left: 0;
  padding: 0 6px; /* 从 8px 减小到 6px */
}

.modal-content {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  padding: 10px;
  box-sizing: border-box;
}

.preview-image {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 4px;
}

:deep(.n-modal) {
  max-width: 90vw;
  max-height: 90vh;
}

:deep(.n-dialog__content) {
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 响应式布局 - 调整间隔 */
@media (max-width: 1200px) {
  .basic-info-row,
  .config-info-row {
    gap: 10px; /* 从 16px 减小到 10px */
  }

  .info-value {
    max-width: 150px;
  }
}

@media (max-width: 768px) {
  .report-container {
    padding: 12px;
  }

  .basic-info-row,
  .config-info-row {
    flex-direction: column;
    gap: 8px; /* 从 12px 减小到 8px */
    align-items: flex-start;
  }

  .info-item {
    width: 100%;
    padding: 3px 6px; /* 从 4px 8px 减小到 3px 6px */
  }

  .info-value {
    max-width: none;
  }

  .step-info-row {
    flex-direction: column;
    gap: 6px; /* 从 8px 减小到 6px */
    align-items: flex-start;
  }

  .step-info-item {
    width: 100%;
  }

  .preview-image {
    max-height: 70vh;
  }

  .step-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px; /* 从 8px 减小到 6px */
  }
}
</style>
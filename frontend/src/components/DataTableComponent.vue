<template>
  <div>
    <!-- 搜索区域 -->
    <div class="search-area">
      <div class="search-title">查询条件</div>
      <n-form
        inline
        :label-width="80"
        :label-placement="'left'"
        class="search-form"
      >
        <!-- 搜索条件行 -->
        <div class="search-items-wrapper">
          <n-form-item label="所属项目" :show-label="true">
            <n-select
              v-model:value="searchForm.project"
              :options="projectOptions"
              placeholder="请选择所属项目"
              clearable
            />
          </n-form-item>
          <n-form-item label="所属模块" :show-label="true">
            <n-input
              v-model:value="searchForm.module"
              placeholder="请输入模块"
            />
          </n-form-item>
          <n-form-item label="页面" :show-label="true">
            <n-input v-model:value="searchForm.page" placeholder="请输入页面" />
          </n-form-item>
          <n-form-item label="用例概述" :show-label="true">
            <n-input
              v-model:value="searchForm.name"
              placeholder="请输入用例名称"
            />
          </n-form-item>
          <n-form-item label="用例类型" :show-label="true">
            <n-select
              v-model:value="searchForm.type"
              :options="typeOptions"
              placeholder="请选择用例类型"
              clearable
            />
          </n-form-item>
        </div>

        <!-- 按钮行 -->
        <div class="search-buttons-wrapper">
          <n-button type="primary" @click="handleSearch">搜索</n-button>
          <n-button @click="handleReset">重置</n-button>
        </div>
      </n-form>
    </div>

    <!-- 批量执行区域 -->
    <div class="operation-area">
      <div class="operation-left">
        <n-p>已选中 {{ checkedRowKeys.length }} 行</n-p>
      </div>
      <div class="operation-right">
        <!-- 修改设置按钮样式 -->
        <n-button
          type="primary"
          @click="handleSettings"
          style="margin-right: 8px"
        >
          设置
        </n-button>
        <n-button
          type="info"
          @click="handleVariables"
          style="margin-right: 8px"
        >
          变量查看
        </n-button>
        <n-button type="primary" @click="handleAdd" style="margin-right: 8px">
          添加用例
        </n-button>
        <n-button @click="batchExecute" type="primary">批量执行</n-button>
      </div>
    </div>

    <!-- 设置弹窗：复用共享的设置弹窗组件（scope="case" 对应 /api/settings） -->
    <SettingsModal scope="case" />

    <!-- 变量管理弹窗 -->
    <n-modal
      v-model:show="showVariablesModal"
      preset="dialog"
      title="变量查看"
      style="width: 600px"
    >
      <div class="variables-container">
        <div class="variables-header">
          <span>当前存储的变量:</span>
        </div>

        <div class="variables-content">
          <n-empty
            v-if="Object.keys(variables).length === 0"
            description="暂无存储的变量"
          />
          <n-descriptions
            v-else
            bordered
            :column="1"
            label-placement="left"
            label-style="width: 200px; font-weight: 500;"
          >
            <n-descriptions-item
              v-for="(value, key) in variables"
              :key="key"
              :label="key"
            >
              <n-text>{{ value }}</n-text>
            </n-descriptions-item>
          </n-descriptions>
        </div>

        <div class="variables-usage">
          <n-alert type="info" title="使用方法">
            在后续步骤的xpath或输入内容中，使用以下格式引用变量：<br />
            格式1: <n-text code>$&#123;变量名&#125;</n-text><br />
            格式2: <n-text code>&#123;&#123;变量名&#125;&#125;</n-text>
          </n-alert>
        </div>
      </div>

      <template #action>
        <n-button @click="closeVariablesModal">关闭</n-button>
      </template>
    </n-modal>

    <!-- 查看用例详情弹窗 -->
    <n-modal
      v-model:show="showViewModal"
      preset="dialog"
      title="查看用例详情"
      style="width: 80%"
    >
      <n-descriptions bordered :column="3">
        <n-descriptions-item label="所属项目">
          {{ viewData.project }}
        </n-descriptions-item>
        <n-descriptions-item label="所属模块">
          {{ viewData.module }}
        </n-descriptions-item>
        <n-descriptions-item label="页面">
          {{ viewData.page }}
        </n-descriptions-item>
        <n-descriptions-item label="用例概述">
          {{ viewData.name }}
        </n-descriptions-item>
        <n-descriptions-item label="用例类型">
          {{ viewData.type }}
        </n-descriptions-item>
      </n-descriptions>

      <n-divider>测试步骤</n-divider>

      <n-table striped class="case-detail-table">
        <thead>
          <tr>
            <th style="width: 60px">步骤</th>
            <th style="width: 150px">操作</th>
            <th style="width: 250px">元素</th>
            <th style="width: 150px">输入内容</th>
            <th style="width: 150px">变量名</th>
            <th style="width: 230px">描述</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="step in viewData.testcase_step" :key="step.step">
            <td>{{ step.step }}</td>
            <td class="operate-cell">
              <n-tooltip trigger="hover" placement="top">
                <template #trigger>
                  <div class="operate-content">{{ step.operate }}</div>
                </template>
                <span>{{ step.operate }}</span>
              </n-tooltip>
            </td>
            <td class="xpath-cell">
              <n-tooltip trigger="hover" placement="top">
                <template #trigger>
                  <div
                    class="xpath-content"
                    v-html="highlightVariables(step.xpath)"
                  ></div>
                </template>
                <span>{{ step.xpath }}</span>
              </n-tooltip>
            </td>
            <td class="input-cell">
              <n-tooltip trigger="hover" placement="top">
                <template #trigger>
                  <div class="input-content">
                    {{ getDisplayInputValue(step) }}
                  </div>
                </template>
                <span>{{ getDisplayInputValue(step) }}</span>
              </n-tooltip>
            </td>
            <td class="var-name-cell">
              <n-tooltip trigger="hover" placement="top">
                <template #trigger>
                  <div class="var-name-content">
                    {{ getDisplayVarName(step) }}
                  </div>
                </template>
                <span>{{ getDisplayVarName(step) }}</span>
              </n-tooltip>
            </td>
            <td class="desc-cell">
              <n-tooltip trigger="hover" placement="top">
                <template #trigger>
                  <div
                    class="desc-content"
                    v-html="highlightVariables(step.describe)"
                  ></div>
                </template>
                <span>{{ step.describe }}</span>
              </n-tooltip>
            </td>
          </tr>
        </tbody>
      </n-table>

      <template #action>
        <n-button @click="closeViewModal">关闭</n-button>
      </template>
    </n-modal>

    <!-- 添加报告名称设置弹窗 -->
    <n-modal
      v-model:show="showReportNameModal"
      preset="dialog"
      title="设置报告名称"
      style="width: 500px"
    >
      <n-form
        ref="reportNameFormRef"
        :model="reportNameForm"
        :rules="reportNameRules"
        label-placement="left"
        label-width="100"
      >
        <n-form-item label="报告名称" path="reportName">
          <n-input
            v-model:value="reportNameForm.reportName"
            placeholder="请输入报告名称"
            maxlength="100"
            show-count
          />
        </n-form-item>
        <n-form-item label="执行说明" path="description">
          <n-input
            v-model:value="reportNameForm.description"
            type="textarea"
            placeholder="请输入执行说明（可选）"
            :autosize="{ minRows: 2, maxRows: 4 }"
            maxlength="200"
            show-count
          />
        </n-form-item>
      </n-form>

      <template #action>
        <n-space>
          <n-button @click="closeReportNameModal">取消</n-button>
          <n-button
            type="primary"
            @click="confirmExecute"
            :loading="executeLoading"
          >
            开始执行
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 数据表格 -->
    <n-data-table
      :columns="columns"
      :data="data"
      :pagination="pagination"
      :row-key="rowKey"
      @update:checked-row-keys="handleCheck"
    />

    <!-- 总数显示 -->
    <div class="total-count">
      <n-text>共计 {{ data.length }} 条用例</n-text>
    </div>
  </div>
</template>

<script lang="ts">
import type { DataTableColumns, DataTableRowKey } from "naive-ui";
import { defineComponent, ref, onMounted, h, Fragment, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import axios from "axios";
import { useSettings } from "../composables/useSettings";
import {
  NButton,
  NP,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NText,
  NModal,
  NSpace,
  NSelect,
  NDescriptions,
  NDescriptionsItem,
  NDivider,
  NTable,
  NTooltip,
  useDialog,
  useMessage,
} from "naive-ui";

interface RowData {
  id: number;
  project: string;
  module: string;
  page: string;
  name: string;
  type: string;
}

interface StepItem {
  stepNo: number;
  action: string;
  xpath: string;
  inputValue?: string;
  description: string;
  // 定位方式：xpath | css | text，配合需要定位元素的操作类型使用
  locateType?: string;
  // 元素选择相关字段
  selectedElement?: string | null;
  elementName?: string; // 保存选中的元素名称
  element_id?: number; // 保存选中的元素ID，用于同步更新（与后端字段名保持一致）
  // 验证元素值专用字段
  expectedValue?: string;
  // 变量名字段（用于获取元素文案时存储变量）
  varName?: string;
  // 引用其他用例专用字段
  referencedCaseId?: number | null;
}

interface ElementData {
  id: number;
  project: string;
  module: string;
  page: string;
  elementName: string;
  xpath: string;
  description?: string;
}

interface ReportNameForm {
  reportName: string;
  description: string;
}

export default defineComponent({
  components: {
    NButton,
    NP,
    NDataTable,
    NForm,
    NFormItem,
    NInput,
    NText,
    NModal,
    NSelect,
    NSpace,
    NDescriptions,
    NDescriptionsItem,
    NDivider,
    NTable,
    NTooltip,
    VariableHighlightInput: () => import("./VariableHighlightInput.vue"),
    SettingsModal: () => import("./SettingsModal.vue"),
  },

  setup() {
    const route = useRoute();
    const router = useRouter();
    const dialog = useDialog();
    const message = useMessage();
    const checkedRowKeysRef = ref<DataTableRowKey[]>([]);
    const data = ref<RowData[]>([]);
    const searchForm = ref<{
      project: string | null;
      module: string;
      page: string;
      name: string;
      type: string | null;
    }>({
      project: null,
      module: "",
      page: "",
      name: "",
      type: null,
    });

    // 报告名称设置相关
    const showReportNameModal = ref(false);
    const executeLoading = ref(false);
    const reportNameFormRef = ref();
    const currentExecuteType = ref<"single" | "batch">("single");
    const currentExecuteData = ref<any>(null);

    // 执行状态控制
    const isExecuting = ref(false);
    const currentExecutingReportId = ref<number | null>(null);

    const reportNameForm = ref<ReportNameForm>({
      reportName: "",
      description: "",
    });

    const reportNameRules = {
      reportName: [
        {
          required: true,
          message: "请输入报告名称",
          trigger: ["input", "blur"],
        },
      ],
    };

    // 添加查看相关的响应式数据
    const showViewModal = ref(false);
    const viewData = ref({
      project: "",
      module: "",
      page: "",
      name: "",
      type: "",
      testcase_step: [] as any[],
    });

    // 修改单个执行方法
    const singleExecute = async (id: number) => {
      try {
        // 获取当前用例信息
        const testCase = data.value.find((item) => item.id === id);
        if (!testCase) {
          message.error("找不到指定的测试用例");
          return;
        }

        // 设置默认报告名称为用例名称
        reportNameForm.value = {
          reportName: testCase.name,
          description: `单个执行测试用例: ${testCase.name}`,
        };

        // 记录执行类型和数据
        currentExecuteType.value = "single";
        currentExecuteData.value = { id, testCase };

        // 显示报告名称设置弹窗
        showReportNameModal.value = true;
      } catch (error) {
        console.error("准备单个执行失败:", error);
        message.error("准备执行失败");
      }
    };

    // 确认执行
    const confirmExecute = async () => {
      try {
        // 检查是否有任务正在执行
        if (isExecuting.value) {
          message.warning("当前有任务正在执行中，请等待任务完成后再执行");
          return;
        }

        // 验证表单
        await reportNameFormRef.value?.validate();

        const config = await getExecuteConfig();

        // 添加报告名称到配置中
        const executeConfig = {
          ...config,
          reportName: reportNameForm.value.reportName,
          description: reportNameForm.value.description,
        };

        // 调试日志：查看执行配置
        console.log("执行配置 executeConfig:", executeConfig);

        // 保存执行类型和数据的副本（在关闭弹窗前）
        const executeType = currentExecuteType.value;
        const executeData = { ...currentExecuteData.value };
        const reportName = reportNameForm.value.reportName;

        // 设置执行状态
        isExecuting.value = true;

        // 立即关闭弹窗
        closeReportNameModal();

        // 创建一个"执行中"状态的临时报告ID
        const tempReportId = Date.now();
        currentExecutingReportId.value = tempReportId;

        // 显示开始执行的提示
        if (executeType === "single") {
          message.info(`开始执行测试用例: ${reportName}`);

          // 单个执行
          axios
            .post(
              "/api/execute",
              {
                id: executeData.id,
                config: executeConfig,
              },
              {
                timeout: 600000, // 10分钟超时
              }
            )
            .then((response) => {
              console.log("单个执行操作成功:", response.data);
              message.success(`测试用例执行完成！报告名称: ${reportName}`);
            })
            .catch((error) => {
              console.error("执行失败:", error);
              if (error.code === "ECONNABORTED") {
                message.error("执行超时，请检查测试用例是否过于复杂");
              } else if (error.response) {
                message.error(
                  `执行失败: ${error.response.data?.error || error.message}`
                );
              } else {
                message.error("执行失败: 网络错误或服务器无响应");
              }
            })
            .finally(() => {
              // 执行完成，重置状态
              isExecuting.value = false;
              currentExecutingReportId.value = null;
            });
        } else if (executeType === "batch") {
          message.info(`开始批量执行 ${executeData.ids.length} 个测试用例...`);

          // 批量执行
          axios
            .post(
              "/api/batch_execute",
              {
                ids: executeData.ids,
                config: executeConfig,
              },
              {
                timeout: 1800000, // 30分钟超时（批量执行需要更长时间）
              }
            )
            .then((response) => {
              console.log("批量执行操作成功:", response.data);
              const report = response.data.report;
              if (report) {
                message.success(
                  `批量执行完成！报告: ${reportName}，共 ${
                    report.batch_info?.total_cases || executeData.ids.length
                  } 个测试用例，总通过率: ${report.pass_rate}%`
                );
              } else {
                message.success(`批量执行完成！报告: ${reportName}`);
              }
            })
            .catch((error) => {
              console.error("执行失败:", error);
              if (error.code === "ECONNABORTED") {
                message.error("批量执行超时，请减少用例数量或检查用例复杂度");
              } else if (error.response) {
                message.error(
                  `执行失败: ${error.response.data?.error || error.message}`
                );
              } else {
                message.error("执行失败: 网络错误或服务器无响应");
              }
            })
            .finally(() => {
              // 执行完成，重置状态
              isExecuting.value = false;
              currentExecutingReportId.value = null;
            });
        }
      } catch (error) {
        console.error("表单验证失败:", error);
        message.error("请填写报告名称");
      }
    };

    // 关闭报告名称弹窗
    const closeReportNameModal = () => {
      showReportNameModal.value = false;
      executeLoading.value = false;
      reportNameForm.value = {
        reportName: "",
        description: "",
      };
      currentExecuteType.value = "single";
      currentExecuteData.value = null;
    };

    // 设置弹窗逻辑（复用共享composable，scope="case" 对应 /api/settings）
    const { handleSettings } = useSettings("case", message);

    // 变量查看相关的响应式数据
    const showVariablesModal = ref(false);
    const variables = ref<Record<string, string>>({});

    // ==================== 元素管理相关 ====================
    // 元素列表数据
    const elementsData = ref<ElementData[]>([]);

    // 获取元素列表
    const fetchElements = async () => {
      try {
        const response = await axios.get("/api/elements");
        elementsData.value = response.data;
      } catch (error) {
        console.error("获取元素列表失败:", error);
      }
    };

    // 高亮显示变量的方法
    const highlightVariables = (text: string): string => {
      if (!text) return text;

      // 匹配 {{variable}} 和 ${variable} 格式的变量
      const variableRegex = /(\{\{[^}]+\}\}|\$\{[^}]+\})/g;

      return text.replace(
        variableRegex,
        '<span style="color: #ff8800; font-weight: bold;">$1</span>'
      );
    };

    // 变量配置列表（用于将查看详情里"输入内容"引用的变量解析为实际值）
    const variableConfigs = ref<any[]>([]);

    const fetchVariableConfigs = async () => {
      try {
        const response = await axios.get("/api/variables/list");
        variableConfigs.value = response.data.variables || response.data || [];
      } catch (error) {
        console.error("获取变量配置失败:", error);
      }
    };

    // 如果整个输入内容就是一个变量引用（{{name}} 或 ${name}），返回变量名，否则返回null
    const getReferencedVarName = (text: string | undefined): string | null => {
      if (!text) return null;
      const match = text.trim().match(/^(?:\{\{([^}]+)\}\}|\$\{([^}]+)\})$/);
      if (!match) return null;
      return (match[1] || match[2]).trim();
    };

    // 根据变量名查找配置，优先匹配当前用例所属项目，找不到就取第一个匹配项
    const resolveVariableValue = (varName: string): string | null => {
      const candidates = variableConfigs.value.filter(
        (v) => v.name === varName
      );
      if (candidates.length === 0) return null;

      const matched =
        candidates.find((v) => v.project === viewData.value.project) ||
        candidates[0];

      if (matched.type === "fixed") return matched.value ?? "";
      if (matched.type === "database") return "(数据库查询结果，执行时生成)";
      if (matched.type === "random") return "(随机数，执行时生成)";
      if (matched.type === "auth") return "(Authorization，执行时注入)";
      return matched.value ?? "";
    };

    // 输入内容展示：引用变量时显示实际值，普通输入原样显示
    const getDisplayInputValue = (step: any): string => {
      const varName = getReferencedVarName(step.input_value);
      if (!varName) return step.input_value || "-";
      const resolved = resolveVariableValue(varName);
      return resolved !== null ? resolved : step.input_value || "-";
    };

    // 变量名展示：优先显示步骤自身的var_name（如获取文案存储的变量），
    // 否则显示输入内容引用的变量名，都没有则为空
    const getDisplayVarName = (step: any): string => {
      if (step.var_name) return step.var_name;
      return getReferencedVarName(step.input_value) || "-";
    };

    // 获取执行配置
    const getExecuteConfig = async () => {
      let config = {
        browser: "chrome",
        headless: false,
        saveScreenshots: false,
        enableMultiThread: false, // 新增
        clientAuthToken: "",
        adminAuthToken: "",
        privateAuthToken: "",
        executeEnvironment: "",
      };

      try {
        const settingsResponse = await axios.get("/api/settings");
        if (settingsResponse.data) {
          config = {
            browser: settingsResponse.data.defaultBrowser || "chrome",
            headless: settingsResponse.data.defaultHeadless || false,
            saveScreenshots: settingsResponse.data.saveScreenshots || false,
            enableMultiThread: settingsResponse.data.enableMultiThread || false, // 新增
            clientAuthToken: settingsResponse.data.clientAuthToken || "",
            adminAuthToken: settingsResponse.data.adminAuthToken || "",
            privateAuthToken: settingsResponse.data.privateAuthToken || "",
            executeEnvironment: settingsResponse.data.defaultEnvironment || "",
          };
        }
      } catch (settingsError) {
        console.log("获取设置失败，使用默认配置:", settingsError);
      }

      return config;
    };

    // 变量查看相关方法
    const handleVariables = async () => {
      await fetchVariables();
      showVariablesModal.value = true;
    };

    const closeVariablesModal = () => {
      showVariablesModal.value = false;
    };

    const fetchVariables = async () => {
      try {
        const response = await axios.get("/api/variables");
        if (response.data.success) {
          variables.value = response.data.variables;
        }
      } catch (error) {
        console.error("获取变量失败:", error);
        message.error("获取变量失败");
      }
    };

    // 编辑用例：跳转到独立的编辑用例页面
    const handleEdit = (id: number) => {
      router.push(`/test-cases/${id}/edit`);
    };

    // 新建用例：跳转到独立的新建用例页面
    const handleAdd = () => {
      router.push("/test-cases/new");
    };

    const fetchData = async () => {
      try {
        const params = {
          project: searchForm.value.project,
          module: searchForm.value.module,
          name: searchForm.value.name,
          type: searchForm.value.type,
        };
        const response = await axios.get("/api/data", {
          params,
        });
        // 倒序排列用例列表
        data.value = response.data.reverse();

        // 初始化elementName字段
        initializeElementNames();
      } catch (error) {
        console.error("Error fetching data:", error);
        message.error("获取数据失败，请检查网络或服务器状态");
      }
    };

    // 初始化elementName字段的函数
    const initializeElementNames = () => {
      if (data.value && Array.isArray(data.value)) {
        data.value.forEach((item: any) => {
          if (item.testCase && Array.isArray(item.testCase)) {
            item.testCase.forEach((step: StepItem) => {
              if (!step.elementName) {
                let matchingElement = null;

                // 优先通过element_id查找元素
                if (step.element_id) {
                  matchingElement = elementsData.value.find(
                    (element: any) => element.id === step.element_id
                  );
                }
                // 兼容旧数据：如果没有element_id，通过xpath查找
                else if (step.xpath) {
                  matchingElement = elementsData.value.find(
                    (element: any) => element.xpath === step.xpath
                  );
                }

                if (matchingElement) {
                  step.elementName = `${matchingElement.elementName} (${matchingElement.page})`;
                  step.selectedElement = matchingElement.id.toString();
                }
              }
            });
          }
        });
      }
    };

    // 获取步骤选中元素的显示名称
    const getStepElementDisplayName = (step: StepItem) => {
      if (step.elementName) {
        return step.elementName;
      }
      if (step.selectedElement) {
        const matchingElement = elementsData.value.find(
          (element: any) => element.id.toString() === step.selectedElement
        );
        if (matchingElement) {
          return `${matchingElement.elementName} (${matchingElement.page})`;
        }
        // 如果找不到匹配的元素，返回一个提示而不是ID
        return `未找到元素 (ID: ${step.selectedElement})`;
      }
      return step.xpath || "未设置";
    };

    const handleSearch = () => {
      fetchData();
    };

    const handleReset = () => {
      searchForm.value = {
        project: null,
        module: "",
        page: "",
        name: "",
        type: null,
      };
      fetchData();
    };

    const typeOptions = [
      { label: "主流程", value: "主流程" },
      { label: "分流程", value: "分流程" },
      { label: "异常流程", value: "异常流程" },
      { label: "UI验证", value: "UI验证" },
    ];

    const projectOptions = ref<{ label: string; value: string }[]>([]);

    // 获取项目列表
    const fetchProjects = async () => {
      try {
        const response = await axios.get("/api/projects");
        const projects = response.data.projects || response.data || [];
        projectOptions.value = projects.map((p: any) => ({
          label: p.name,
          value: p.name,
        }));
      } catch (error) {
        console.error("加载项目列表失败:", error);
      }
    };

    onMounted(async () => {
      // 先获取项目列表
      await fetchProjects();

      const projectParam = route.query.project as string | undefined;

      if (projectParam) {
        const isValidProject = projectOptions.value.some(
          (option) => option.value === projectParam
        );

        if (isValidProject) {
          searchForm.value.project = projectParam;
        } else {
          message.warning(`无效的项目参数: ${projectParam}`);
        }
        fetchData();
      } else {
        fetchData();
      }

      // 获取元素列表
      fetchElements();
    });

    const handleCheck = (rowKeys: DataTableRowKey[]) => {
      checkedRowKeysRef.value = rowKeys;
    };

    const handleView = async (id: number) => {
      try {
        const response = await axios.get(`/api/testcase/${id}`);
        viewData.value = response.data;

        // 加载变量配置，用于将输入内容中引用的变量解析为实际值
        await fetchVariableConfigs();

        // 初始化viewData中的elementName字段
        if (
          viewData.value?.testcase_step &&
          Array.isArray(viewData.value.testcase_step)
        ) {
          viewData.value.testcase_step.forEach((step: StepItem) => {
            if (!step.elementName) {
              let matchingElement = null;

              // 优先通过element_id查找元素
              if (step.element_id) {
                matchingElement = elementsData.value.find(
                  (element: any) => element.id === step.element_id
                );
              }
              // 兼容旧数据：如果没有element_id，通过xpath查找
              else if (step.xpath) {
                matchingElement = elementsData.value.find(
                  (element: any) => element.xpath === step.xpath
                );
              }

              if (matchingElement) {
                step.elementName = `${matchingElement.elementName} (${matchingElement.page})`;
                step.selectedElement = matchingElement.id.toString();
              }
            }
          });
        }

        showViewModal.value = true;
      } catch (error) {
        console.error("获取用例详情失败:", error);
        message.error("获取用例详情失败");
      }
    };

    // 执行用例时使用设置中的配置
    const handleExecute = async (id: number) => {
      try {
        message.loading("正在启动执行...", { duration: 2000 });

        const config = await getExecuteConfig();

        const response = await axios.post("/api/execute", {
          id,
          config,
        });
        console.log("执行操作成功:", response.data);
        message.success(
          `执行操作成功！通过率: ${response.data.report?.pass_rate || 0}%`
        );
      } catch (error) {
        console.error("执行操作失败:", error);
        message.error("执行操作失败");
      }
    };

    // 复制用例功能
    const handleCopy = async (id: number) => {
      try {
        console.log("开始复制用例，ID:", id);

        // 获取原用例详细信息
        const response = await axios.get(`/api/testcase/${id}`);
        const originalCase = response.data;

        console.log("获取到原用例数据:", originalCase);

        // 创建复制的用例数据
        const copiedCaseData = {
          project: originalCase.project,
          module: originalCase.module,
          page: originalCase.page,
          name: `${originalCase.name}-复制`, // 添加-复制后缀
          type: originalCase.type,
          testcase_step: originalCase.testcase_step || [], // 复制所有步骤
        };

        console.log("准备提交的复制数据:", copiedCaseData);

        // 发送到后端保存
        const copyResponse = await axios.post("/api/add_case", copiedCaseData);

        if (copyResponse.data.message) {
          message.success("用例复制成功");
          // 刷新用例列表
          fetchData();
        } else {
          message.error(copyResponse.data.error || "复制用例失败");
        }
      } catch (error) {
        console.error("复制用例失败:", error);
        message.error("复制用例失败，请检查网络连接");
      }
    };

    const handleDelete = (id: number) => {
      dialog.warning({
        title: "确认删除",
        content: "确定要删除这条测试用例吗？",
        positiveText: "确定",
        negativeText: "取消",
        onPositiveClick: async () => {
          try {
            const response = await axios.delete(`/api/testcase/${id}`);
            if (response.data.message) {
              message.success("删除成功");
              fetchData();
            } else {
              message.error(response.data.error || "删除失败");
            }
          } catch (error) {
            console.error("删除失败:", error);
            message.error("删除失败");
          }
        },
        onNegativeClick: () => {
          // 用户点击取消，不执行任何操作
        },
      });
    };

    function createColumns(): DataTableColumns<RowData> {
      return [
        { type: "selection" },
        { title: "用例ID", key: "id", align: "center", width: 80 },
        { title: "所属项目", key: "project", align: "center", width: 100 },
        { title: "所属模块", key: "module", align: "center", width: 120 },
        { title: "用例概述", key: "name", align: "center", width: 300 },
        { title: "用例类型", key: "type", align: "center", width: 100 },
        {
          title: "操作",
          key: "action",
          align: "center",
          width: 200,
          render(row) {
            return h("div", { style: { textAlign: "center" } }, [
              h(
                NButton,
                {
                  size: "small",
                  onClick: () => handleView(row.id),
                  style: { marginRight: "8px" },
                },
                "查看"
              ),
              h(
                NButton,
                {
                  size: "small",
                  type: "primary",
                  onClick: () => handleExecute(row.id),
                  style: { marginRight: "8px" },
                },
                "执行"
              ),
              h(
                NButton,
                {
                  size: "small",
                  type: "info",
                  onClick: () => handleEdit(row.id),
                  style: { marginRight: "8px" },
                },
                "编辑"
              ),
              h(
                NButton,
                {
                  size: "small",
                  type: "warning",
                  onClick: () => handleCopy(row.id),
                  style: { marginRight: "8px" },
                },
                "复制"
              ),
              h(
                NButton,
                {
                  size: "small",
                  type: "error",
                  onClick: () => handleDelete(row.id),
                },
                "删除"
              ),
            ]);
          },
        },
      ];
    }

    // 批量执行时使用设置中的配置
    const batchExecute = async () => {
      if (checkedRowKeysRef.value.length === 0) {
        message.warning("请先勾选测试用例");
        return;
      }

      try {
        // 获取选中的用例名称
        const selectedCases = data.value.filter((item) =>
          checkedRowKeysRef.value.includes(item.id)
        );

        const caseNames = selectedCases.map((item) => item.name);
        const defaultName =
          selectedCases.length === 1
            ? caseNames[0]
            : `批量执行${selectedCases.length}个用例`;

        // 设置默认报告名称
        reportNameForm.value = {
          reportName: defaultName,
          description: `批量执行测试用例: ${caseNames.join(", ")}`,
        };

        // 记录执行类型和数据
        currentExecuteType.value = "batch";
        currentExecuteData.value = {
          ids: [...checkedRowKeysRef.value],
          cases: selectedCases,
        };

        // 显示报告名称设置弹窗
        showReportNameModal.value = true;
      } catch (error) {
        console.error("准备批量执行失败:", error);
        message.error("准备执行失败");
      }
    };

    const closeViewModal = () => {
      showViewModal.value = false;
      viewData.value = {
        project: "",
        module: "",
        page: "",
        name: "",
        type: "",
        testcase_step: [],
      };
    };

    // 元素同步更新功能
    const syncTestCasesAfterElementUpdate = async (
      elementId: number,
      newXPath: string,
      newElementName: string
    ) => {
      try {
        console.log(
          `开始同步更新 - 元素ID: ${elementId}, 新XPath: "${newXPath}", 新元素名称: "${newElementName}"`
        );

        // 获取所有用例数据
        const response = await axios.get("/api/data");
        const allTestCases = response.data || [];

        const updatedCases: any[] = [];

        // 遍历所有用例，查找使用了该元素的步骤
        for (const testCase of allTestCases) {
          let hasUpdates = false;
          const updatedSteps = (testCase.testcase_step || []).map(
            (step: any) => {
              // 通过元素ID匹配（新的正确逻辑）
              if (step.element_id === elementId) {
                console.log(
                  `找到匹配步骤 - 用例: ${testCase.name}, 步骤: ${step.step}, 元素ID: ${step.element_id}`
                );
                hasUpdates = true;
                return {
                  ...step,
                  xpath: newXPath,
                  elementName: newElementName,
                };
              }
              return step;
            }
          );

          if (hasUpdates) {
            // 如果该用例有更新，准备提交
            updatedCases.push({
              ...testCase,
              testcase_step: updatedSteps, // 使用正确的字段名
            });
          }
        }

        // 批量更新用例
        if (updatedCases.length > 0) {
          console.log(`准备更新 ${updatedCases.length} 个用例`);
          await Promise.all(
            updatedCases.map((testCase: any) =>
              axios.put(`/api/testcase/${testCase.id}`, {
                project: testCase.project,
                module: testCase.module,
                page: testCase.page,
                name: testCase.name,
                type: testCase.type,
                testcase_step: testCase.testcase_step, // 直接使用更新后的步骤数据
              })
            )
          );

          message.success(`已同步更新 ${updatedCases.length} 个相关用例`);

          // 刷新用例列表数据
          fetchData();
        } else {
          console.log(`没有找到使用元素ID ${elementId} 的用例步骤`);
          message.info("没有找到使用该元素的用例");
        }
      } catch (error) {
        console.error("同步更新用例失败:", error);
        message.error("同步更新用例失败");
      }
    };

    // 监听元素更新事件的函数（需要在元素管理组件中调用）
    const onElementUpdated = (
      elementId: number,
      newXPath: string,
      newElementName: string
    ) => {
      syncTestCasesAfterElementUpdate(elementId, newXPath, newElementName);
    };

    return {
      data,
      message,
      columns: createColumns(),
      checkedRowKeys: checkedRowKeysRef,
      pagination: { pageSize: 10 },
      rowKey: (row: RowData) => row.id,
      handleCheck,
      handleView,
      handleExecute,
      searchForm,
      handleSearch,
      handleReset,
      typeOptions,
      projectOptions,
      handleAdd,
      showViewModal,
      viewData,
      closeViewModal,
      handleCopy,
      handleDelete,
      dialog,
      handleEdit,
      // 设置相关
      handleSettings,
      getExecuteConfig,
      // 变量查看相关
      showVariablesModal,
      variables,
      handleVariables,
      closeVariablesModal,
      fetchVariables,
      // Cookie相关

      showReportNameModal,
      executeLoading,
      reportNameFormRef,
      reportNameForm,
      reportNameRules,
      confirmExecute,
      closeReportNameModal,
      // 更新后的方法
      singleExecute,
      batchExecute,
      // 元素管理相关
      elementsData,
      fetchElements,
      highlightVariables,
      getDisplayInputValue,
      getDisplayVarName,
      getStepElementDisplayName,
      // 元素同步更新功能
      onElementUpdated,
      syncTestCasesAfterElementUpdate,
    };
  },
});
</script>

<style scoped>
.settings-hint {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: #909399;
}

.search-area {
  position: relative;
  margin-bottom: 30px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 16px;
}

.search-title {
  position: absolute;
  top: -12px;
  left: 10px;
  background-color: #fff;
  padding: 0 8px;
  color: #606266;
  font-size: 14px;
  font-weight: bold;
}

.search-form {
  background-color: #fff;
  padding: 0;
  border-radius: 4px;
}

.search-form :deep(.n-select) {
  width: 180px;
}

.modal-form :deep(.n-select) {
  width: 100%;
}

.search-items-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  width: 100%;
}

.search-buttons-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: 12px;
  flex-shrink: 0;
  flex-basis: auto;
}

@media (max-width: 1150px) {
  .search-items-wrapper {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .search-buttons-wrapper {
    margin-left: 0;
    justify-content: flex-end;
    width: 100%;
    padding-top: 8px;
    border-top: 1px solid #f0f0f0;
  }
}

.search-form :deep(.n-form-item) {
  margin: 0;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  white-space: nowrap;
}

.search-form :deep(.n-form-item-label) {
  height: 34px;
  line-height: 34px;
  padding: 0 8px;
  white-space: nowrap;
  font-size: 14px;
  flex-shrink: 0;
  min-width: max-content;
}

.search-form :deep(.n-input) {
  width: 200px;
  flex-shrink: 0;
}

.search-form :deep(.n-form-item-blank) {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.total-count {
  margin-top: -32px;
  color: #0deca2;
  font-size: 15px;
}

.operation-area {
  background: #fff;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: -3px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.operation-left {
  display: flex;
  align-items: center;
}

.operation-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-form {
  :deep(.n-form-item) {
    margin-bottom: 16px;
  }

  :deep(.n-input) {
    width: 100%;
  }

  :deep(.n-input-textarea) {
    min-height: 80px;
  }
}

/* 设置表单样式 */
.settings-form {
  :deep(.n-form-item) {
    margin-bottom: 16px;
  }

  :deep(.n-select) {
    width: 100%;
  }
}

.settings-preview {
  padding: 12px;
  background-color: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #e9ecef;
}

.settings-preview div {
  margin-bottom: 4px;
}

.settings-preview div:last-child {
  margin-bottom: 0;
}

:deep(.n-modal) {
  min-width: 800px;
  max-width: 80%;
}

/* 步骤滚动容器 */
.steps-scroll-container {
  max-height: 50vh; /* 根据屏幕高度自适应，占50%的视口高度 */
  min-height: 200px; /* 设置最小高度 */
  overflow-y: auto;
  overflow-x: hidden; /* 隐藏水平滚动条 */
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  padding: 4px; /* 减少padding，给内容更多空间 */
  background-color: #fbfbfb;
  width: 100%; /* 与环境选择框等表单项宽度一致 */
  box-sizing: border-box; /* 确保padding不会增加总宽度 */
}

.steps-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  min-width: 0; /* 确保容器能够收缩 */
}

.step-row {
  display: grid;
  grid-template-columns: 60px 0.4fr 2fr 1.5fr 120px;
  gap: 12px;
  padding: 16px;
  border: 1px solid #eee;
  border-radius: 4px;
  background-color: #fafafa;
  width: auto; /* 改为auto，让它适应可用空间 */
  position: relative;
  align-items: center; /* 改为center实现垂直居中 */
  min-width: 0; /* 确保网格项能够收缩 */
  box-sizing: border-box; /* 确保padding和border不会增加总宽度 */
}

.step-row.has-locate {
  grid-template-columns: 60px 0.4fr 0.5fr 2fr 1.5fr 120px;
}

.step-row.has-input {
  grid-template-columns: 60px 0.4fr 0.5fr 2fr 1fr 1fr 120px;
}

.step-row.has-get-text {
  grid-template-columns: 60px 0.4fr 0.5fr 2fr 1fr 1fr 120px;
}

.step-row.has-verify-var {
  grid-template-columns: 60px 0.4fr 1fr 1fr 1fr 120px;
}

.step-row.has-verify {
  grid-template-columns: 60px 0.4fr 0.5fr 1.2fr 0.8fr 1.5fr 120px;
}

.step-number {
  color: #666;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.step-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
  word-wrap: break-word; /* 确保长文本能够换行 */
  align-self: stretch; /* 让表单字段拉伸填充高度 */
  justify-content: center; /* 垂直居中内容 */
}

.step-label {
  font-size: 12px;
  color: #505255;
  font-weight: 500;
}

.step-field :deep(.n-input),
.step-field :deep(.n-select) {
  width: 100%;
  min-width: 0;
}

.step-field :deep(.n-input-wrapper),
.step-field :deep(.n-base-selection) {
  max-width: 100%;
  overflow: hidden;
}

.step-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-row .delete-btn {
  color: #909399;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  width: 32px;
}

.step-row .delete-btn:hover {
  color: #575252;
  background-color: #f4f4f5;
}

.add-step {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

.add-step-btn {
  width: 120px;
}

:deep(.n-descriptions) {
  margin-bottom: 20px;
}

:deep(.n-table-wrapper) {
  margin-top: 16px;
}

@media (max-width: 1500px) {
  .step-row {
    grid-template-columns: 50px 0.4fr 2fr 1.5fr 50px;
  }

  .step-row.has-locate {
    grid-template-columns: 50px 0.4fr 0.5fr 2fr 1.5fr 50px;
  }

  .step-row.has-input {
    grid-template-columns: 50px 0.4fr 0.5fr 1.5fr 1fr 1fr 50px;
  }

  .step-row.has-get-text {
    grid-template-columns: 50px 0.4fr 0.5fr 1.5fr 1fr 1fr 50px;
  }

  .step-row.has-verify-var {
    grid-template-columns: 50px 0.4fr 1fr 1fr 1fr 50px;
  }
}

@media (max-width: 1300px) {
  .step-row {
    grid-template-columns: 50px 0.4fr 2fr 1.5fr 50px;
  }

  .step-row.has-locate {
    grid-template-columns: 50px 0.4fr 0.5fr 2fr 1.5fr 50px;
  }

  .step-row.has-input {
    grid-template-columns: 50px 0.4fr 0.5fr 1.5fr 1fr 1fr 50px;
  }

  .step-row.has-get-text {
    grid-template-columns: 50px 0.4fr 0.5fr 1.5fr 1fr 1fr 50px;
  }

  .step-row.has-verify-var {
    grid-template-columns: 50px 0.4fr 1fr 1fr 1fr 50px;
  }

  .step-row.has-verify {
    grid-template-columns: 50px 0.4fr 0.5fr 1.1fr 0.8fr 1.4fr 50px;
  }
}

@media (max-width: 1200px) {
  .step-row,
  .step-row.has-input,
  .step-row.has-get-text,
  .step-row.has-verify-var,
  .step-row.has-verify,
  .step-row.has-locate {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .step-field {
    width: 100%;
  }

  .step-number {
    align-self: flex-start;
  }

  .step-row .delete-btn {
    position: absolute !important;
    top: 50% !important;
    right: 8px !important;
    transform: translateY(-50%) !important;
  }
}

@media (max-width: 1400px) {
  .search-form :deep(.n-select),
  .search-form :deep(.n-input) {
    width: 140px;
  }

  .search-form :deep(.n-form-item-label) {
    padding: 0 1px;
    font-size: 12px;
  }

  .search-buttons-wrapper {
    gap: 8px;
    margin-left: 8px;
  }
}

@media (max-width: 768px) {
  .search-items-wrapper {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .search-form :deep(.n-form-item) {
    flex-direction: column;
    align-items: flex-start;
  }

  .search-form :deep(.n-form-item-label) {
    margin-bottom: 4px;
    font-size: 14px;
    padding: 0 4px;
  }

  .search-form :deep(.n-select),
  .search-form :deep(.n-input) {
    width: 100%;
  }

  .search-buttons-wrapper {
    justify-content: center;
  }

  .step-field {
    min-width: 100%;
  }
}

/* XPath输入容器样式 */
.xpath-input-container {
  width: 100%;
}

.xpath-selection {
  width: 100%;
}

.xpath-selection :deep(.n-select) {
  width: 100%;
}

/* 滚动条美化 */
.steps-scroll-container::-webkit-scrollbar {
  width: 8px;
}

.steps-scroll-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.steps-scroll-container::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 4px;
}

.steps-scroll-container::-webkit-scrollbar-thumb:hover {
  background: #a6a9ad;
}

@media (max-width: 768px) {
  .steps-scroll-container {
    max-height: 300px;
  }
}

@media (max-width: 480px) {
  .search-buttons-wrapper {
    flex-direction: column;
    gap: 8px;
  }

  .search-buttons-wrapper .n-button {
    width: 100%;
  }

  .steps-scroll-container {
    max-height: 250px;
  }
}

/* 变量管理弹窗样式 */
.variables-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.variables-header {
  padding-bottom: 8px;
  border-bottom: 1px solid #e0e0e6;
}

.variables-content {
  max-height: 300px;
  overflow-y: auto;
}

.variables-usage {
  margin-top: 8px;
}

/* 用例详情表格样式 */
.case-detail-table {
  width: 100%;
  table-layout: fixed;
}

.case-detail-table .operate-cell {
  word-break: break-word;
  font-size: 12px;
  max-width: 150px;
}

.case-detail-table .operate-cell .operate-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.case-detail-table .xpath-cell {
  word-break: break-all;
  font-size: 12px;
  max-width: 250px;
}

.case-detail-table .xpath-cell .xpath-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.case-detail-table .input-cell {
  word-break: break-word;
  font-size: 12px;
  max-width: 150px;
}

.case-detail-table .input-cell .input-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.case-detail-table .var-name-cell {
  word-break: break-word;
  font-size: 12px;
  max-width: 150px;
}

.case-detail-table .var-name-cell .var-name-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.case-detail-table .desc-cell {
  word-break: break-word;
  font-size: 14px;
  max-width: 230px;
}

.case-detail-table .desc-cell .desc-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.case-detail-table th {
  text-align: center;
  font-weight: 600;
  background-color: #fafafa;
}

.case-detail-table td {
  padding: 8px 12px;
  vertical-align: top;
}

/* 变量高亮样式 */
:deep(.n-input__input-el) {
  position: relative;
}

.variable-highlight {
  color: #ff8c00 !important;
  font-weight: 600;
  background-color: rgba(255, 140, 0, 0.1);
  padding: 2px 4px;
  border-radius: 3px;
  cursor: help;
}

.variable-hints {
  margin-top: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.variable-hint-label {
  color: #666;
  margin-right: 4px;
}
</style>
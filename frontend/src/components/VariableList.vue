<template>
  <div class="variable-container">
    <n-space vertical :size="16">
      <!-- 页面标题和操作按钮 -->
      <n-space justify="space-between">
        <h2>变量管理</h2>
        <n-space>
          <n-button type="primary" @click="showAddModal = true">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            添加变量
          </n-button>
          <n-button @click="loadVariables">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </n-space>

      <!-- 查询条件 -->
      <div class="search-area">
        <div class="search-title">查询条件</div>
        <n-form
          inline
          :label-width="80"
          :label-placement="'left'"
          class="search-form"
        >
          <div class="search-items-wrapper">
            <n-form-item label="变量名" :show-label="true">
              <n-input
                v-model:value="searchName"
                placeholder="请输入变量名"
                clearable
              />
            </n-form-item>
            <n-form-item label="变量值" :show-label="true">
              <n-input
                v-model:value="searchValue"
                placeholder="请输入变量值"
                clearable
              />
            </n-form-item>
            <n-form-item label="环境" :show-label="true">
              <n-input
                v-model:value="searchEnvironment"
                placeholder="请输入环境"
                clearable
              />
            </n-form-item>
            <n-form-item label="描述" :show-label="true">
              <n-input
                v-model:value="searchDescription"
                placeholder="请输入描述"
                clearable
              />
            </n-form-item>
          </div>

          <div class="search-buttons-wrapper">
            <n-button type="primary" @click="handleSearch">搜索</n-button>
            <n-button @click="handleReset">重置</n-button>
          </div>
        </n-form>
      </div>

      <!-- 变量列表表格 -->
      <n-data-table
        :columns="columns"
        :data="filteredVariableList"
        :pagination="pagination"
        :bordered="false"
      />
    </n-space>

    <!-- 添加/编辑变量弹窗 -->
    <n-modal
      v-model:show="showAddModal"
      preset="dialog"
      :title="editingVariable ? '编辑变量' : '添加变量'"
      :style="{ width: '600px' }"
    >
      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="left"
        label-width="100px"
      >
        <n-form-item label="变量名" path="name">
          <n-input
            v-model:value="formData.name"
            placeholder="请输入变量名，如: user_id"
            :disabled="!!editingVariable"
          />
        </n-form-item>

        <n-form-item label="所属项目" path="project">
          <n-select
            v-model:value="formData.project"
            :options="projectOptions"
            placeholder="请选择所属项目（不选则不限项目）"
            clearable
          />
        </n-form-item>

        <n-form-item label="所属环境" path="environment">
          <n-select
            v-model:value="formData.environment"
            :options="environmentOptions"
            placeholder="请选择所属环境"
          />
        </n-form-item>

        <n-form-item label="变量类型" path="type">
          <n-radio-group v-model:value="formData.type">
            <n-space>
              <n-radio value="fixed">固定值</n-radio>
              <n-radio value="random">随机数</n-radio>
              <n-radio value="database">数据库查询</n-radio>
              <n-radio value="auth">Authorization</n-radio>
              <n-radio value="cookie">Cookie</n-radio>
              <n-radio value="extracted">提取变量</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>

        <n-form-item
          v-if="formData.type === 'fixed'"
          label="变量值"
          path="value"
        >
          <n-input v-model:value="formData.value" placeholder="请输入固定值" />
        </n-form-item>

        <template v-if="formData.type === 'random'">
          <n-form-item label="最小值" path="minValue">
            <n-input-number
              v-model:value="formData.minValue"
              placeholder="请输入最小值"
              :style="{ width: '100%' }"
            />
          </n-form-item>

          <n-form-item label="最大值" path="maxValue">
            <n-input-number
              v-model:value="formData.maxValue"
              placeholder="请输入最大值"
              :style="{ width: '100%' }"
            />
          </n-form-item>
        </template>

        <template v-if="formData.type === 'database'">
          <n-form-item label="选择数据库" path="database">
            <n-select
              v-model:value="formData.database"
              :options="databaseOptions"
              placeholder="请选择数据库配置"
            />
          </n-form-item>

          <n-form-item label="查询语句" path="query">
            <n-input
              v-model:value="formData.query"
              type="textarea"
              placeholder="请输入 SQL 查询语句，语句中不确定的值可用 ${变量名} 或 {{变量名}} 引用其他变量，用例实际执行时会自动替换为当时的值"
              :rows="4"
            />
          </n-form-item>
        </template>

        <template v-if="isCredentialType">
          <n-form-item label="获取方式" path="sourceType">
            <n-radio-group v-model:value="formData.sourceType">
              <n-space>
                <n-radio value="manual">{{ credentialManualLabel }}</n-radio>
                <n-radio value="testcase">引用登录测试用例</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <n-form-item
            v-if="formData.sourceType === 'manual'"
            :label="credentialValueLabel"
            path="value"
          >
            <n-input
              v-model:value="formData.value"
              :type="formData.type === 'cookie' ? 'textarea' : 'text'"
              :rows="formData.type === 'cookie' ? 4 : undefined"
              :placeholder="credentialValuePlaceholder"
            />
          </n-form-item>

          <template v-if="formData.sourceType === 'testcase'">
            <n-form-item label="登录用例" path="loginTestCaseId">
              <n-select
                v-model:value="formData.loginTestCaseId"
                :options="loginTestCaseOptions"
                placeholder="请选择当前项目下的登录测试用例"
                filterable
                clearable
                @focus="loadLoginTestCases"
              />
            </n-form-item>
          </template>

          <n-form-item label="匹配域名" path="matchDomains">
            <n-select
              v-model:value="formData.matchDomains"
              multiple
              filterable
              tag
              :options="domainCandidateOptions"
              placeholder="输入真实域名，或搜索/选择当前项目+环境下的变量名进行参数化"
            />
          </n-form-item>
        </template>

        <n-form-item label="描述" path="description">
          <n-input
            v-model:value="formData.description"
            type="textarea"
            placeholder="请输入变量描述（可选）"
            :rows="3"
          />
        </n-form-item>
      </n-form>

      <p
        v-if="isCredentialType && formData.sourceType === 'testcase'"
        class="save-hint"
      >
        点击"确定"保存时，会自动执行所选登录测试用例并抓取{{ credentialValueLabel }}
      </p>

      <template #action>
        <n-space justify="end">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button
            type="primary"
            :loading="capturingToken"
            @click="handleSaveVariable"
          >
            确定
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, computed, onMounted } from "vue";
import {
  NSpace,
  NButton,
  NDataTable,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NRadioGroup,
  NRadio,
  NSelect,
  NIcon,
  NTag,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
} from "naive-ui";
import {
  AddOutline,
  RefreshOutline,
  TrashOutline,
  CreateOutline,
} from "@vicons/ionicons5";
import axios from "axios";

interface Variable {
  name: string;
  type: "fixed" | "random" | "database" | "auth" | "cookie" | "extracted";
  value?: string;
  minValue?: number;
  maxValue?: number;
  database?: string;
  query?: string;
  description?: string;
  currentValue?: string;
  environment?: string;
  project?: string;
  matchDomains?: string[];
  sourceType?: "manual" | "testcase";
  loginTestCaseId?: number | null;
}

const message = useMessage();
const showAddModal = ref(false);
const editingVariable = ref<{
  name: string;
  originalEnvironment: string;
  originalProject: string;
} | null>(null);
const formRef = ref<FormInst | null>(null);

const formData = ref<Variable>({
  name: "",
  type: "fixed",
  value: "",
  minValue: 0,
  maxValue: 100,
  database: "",
  query: "",
  description: "",
  environment: "全局",
  project: "",
  matchDomains: [],
  sourceType: "manual",
  loginTestCaseId: null,
});

const variableList = ref<Variable[]>([]);
const capturingToken = ref(false);
const searchName = ref("");
const searchValue = ref("");
const searchEnvironment = ref("");
const searchDescription = ref("");

// 变量值搜索文本（按类型取对应的值字段）
const getVariableSearchValueText = (row: Variable): string => {
  if (
    row.type === "fixed" ||
    row.type === "auth" ||
    row.type === "cookie" ||
    row.type === "extracted"
  ) {
    return row.value || "";
  } else if (row.type === "database") {
    return `${row.database || ""} ${row.query || ""}`;
  } else if (row.type === "random") {
    return `${row.minValue ?? ""} ${row.maxValue ?? ""}`;
  }
  return "";
};

const filteredVariableList = computed(() => {
  const nameKeyword = searchName.value.trim().toLowerCase();
  const valueKeyword = searchValue.value.trim().toLowerCase();
  const environmentKeyword = searchEnvironment.value.trim().toLowerCase();
  const descriptionKeyword = searchDescription.value.trim().toLowerCase();

  return variableList.value.filter((row) => {
    if (nameKeyword && !row.name.toLowerCase().includes(nameKeyword)) {
      return false;
    }
    if (
      valueKeyword &&
      !getVariableSearchValueText(row).toLowerCase().includes(valueKeyword)
    ) {
      return false;
    }
    if (
      environmentKeyword &&
      !(row.environment || "全局").toLowerCase().includes(environmentKeyword)
    ) {
      return false;
    }
    if (
      descriptionKeyword &&
      !(row.description || "").toLowerCase().includes(descriptionKeyword)
    ) {
      return false;
    }
    return true;
  });
});

// 搜索（结果已通过 filteredVariableList 实时过滤，此处仅用于交互一致性）
const handleSearch = () => {};

// 重置查询条件
const handleReset = () => {
  searchName.value = "";
  searchValue.value = "";
  searchEnvironment.value = "";
  searchDescription.value = "";
};

const environmentOptions = ref<{ label: string; value: string }[]>([
  { label: "全局", value: "全局" },
]);
const databaseOptions = ref<{ label: string; value: string }[]>([]);
const projectOptions = ref<{ label: string; value: string }[]>([]);
const loginTestCaseOptions = ref<{ label: string; value: number }[]>([]);

const domainCandidateOptions = computed(() => {
  return variableList.value
    .filter(
      (v) =>
        v.name !== formData.value.name &&
        (v.project || "") === (formData.value.project || "") &&
        (v.environment || "全局") === (formData.value.environment || "全局")
    )
    .map((v) => ({ label: v.name, value: v.name }));
});

// Authorization 和 Cookie 都是"凭证类"变量，获取方式规则完全一致
const isCredentialType = computed(
  () => formData.value.type === "auth" || formData.value.type === "cookie"
);
const credentialManualLabel = computed(() =>
  formData.value.type === "cookie" ? "粘贴Cookie" : "粘贴Token"
);
const credentialValueLabel = computed(() =>
  formData.value.type === "cookie" ? "Cookie值" : "Token值"
);
const credentialValuePlaceholder = computed(() =>
  formData.value.type === "cookie"
    ? "请粘贴Cookie内容（JSON格式的数组），例如: [{\"name\": \"sessionId\", \"value\": \"abc123\", \"domain\": \".example.com\"}]"
    : "请输入 Authorization Token"
);

const pagination = {
  pageSize: 10,
};

const rules: FormRules = {
  name: [
    {
      required: true,
      message: "请输入变量名",
      trigger: "blur",
    },
    {
      pattern: /^[a-zA-Z_][a-zA-Z0-9_]*$/,
      message: "变量名只能包含字母、数字和下划线，且不能以数字开头",
      trigger: "blur",
    },
  ],
  value: [
    {
      validator: (rule, value) => {
        if (formData.value.type === "fixed" && !value) {
          return new Error("请输入变量值");
        }
        if (
          isCredentialType.value &&
          formData.value.sourceType === "manual" &&
          !value
        ) {
          return new Error(`请输入${credentialValueLabel.value}`);
        }
        return true;
      },
      trigger: "blur",
    },
  ],
  loginTestCaseId: [
    {
      validator: (rule, value) => {
        if (
          isCredentialType.value &&
          formData.value.sourceType === "testcase" &&
          !value
        ) {
          return new Error("请选择登录测试用例");
        }
        return true;
      },
      trigger: "change",
    },
  ],
  matchDomains: [
    {
      validator: (rule, value) => {
        if (isCredentialType.value && (!value || value.length === 0)) {
          return new Error("请至少填写一个匹配域名");
        }
        return true;
      },
      trigger: "change",
    },
  ],
  minValue: [
    {
      type: "number",
      required: true,
      message: "请输入最小值",
      trigger: "blur",
    },
  ],
  maxValue: [
    {
      type: "number",
      required: true,
      message: "请输入最大值",
      trigger: "blur",
    },
    {
      validator: (rule, value) => {
        if (value <= formData.value.minValue!) {
          return new Error("最大值必须大于最小值");
        }
        return true;
      },
      trigger: "blur",
    },
  ],
  database: [
    {
      validator: (rule, value) => {
        if (formData.value.type === "database" && !value) {
          return new Error("请选择数据库配置");
        }
        return true;
      },
      trigger: "change",
    },
  ],
  query: [
    {
      validator: (rule, value) => {
        if (formData.value.type === "database" && !value) {
          return new Error("请输入查询语句");
        }
        return true;
      },
      trigger: "blur",
    },
  ],
};

// 加载变量列表
const loadVariables = async () => {
  try {
    const response = await axios.get("/api/variables/list");
    if (response.data.success) {
      variableList.value = response.data.variables;
    }
  } catch (error) {
    console.error("加载变量失败:", error);
    message.error("加载变量失败");
  }
};

// 加载环境列表（用于所属环境联动下拉）
const fetchEnvironments = async () => {
  try {
    const response = await axios.get("/api/environments");
    const envs = response.data.environments || response.data || [];
    environmentOptions.value = [
      { label: "全局", value: "全局" },
      ...envs.map((env: any) => ({ label: env.name, value: env.name })),
    ];
  } catch (error) {
    console.error("加载环境列表失败:", error);
  }
};

// 加载项目列表（用于所属项目联动下拉）
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

// 加载测试用例列表（用于Authorization变量"引用登录测试用例"，按当前所选项目筛选，n-select自带模糊搜索）
const loadLoginTestCases = async () => {
  try {
    const response = await axios.get("/api/testcases");
    if (response.data.success) {
      const currentProject = formData.value.project || "";
      const testcases = currentProject
        ? response.data.testcases.filter((tc: any) => tc.project === currentProject)
        : response.data.testcases;
      loginTestCaseOptions.value = testcases.map((tc: any) => ({
        label: `${tc.name} (ID: ${tc.id})`,
        value: tc.id,
      }));
    }
  } catch (error) {
    console.error("加载测试用例失败:", error);
    message.error("加载测试用例失败");
  }
};

// 加载数据库配置列表（用于数据库查询类型联动下拉）
const fetchDatabases = async () => {
  try {
    const response = await axios.get("/api/databases");
    const databases = response.data.databases || [];
    databaseOptions.value = databases.map((db: any) => ({
      label: db.name,
      value: db.name,
    }));
  } catch (error) {
    console.error("加载数据库配置列表失败:", error);
  }
};

// 环境标签颜色（按环境名称哈希取色，保证同一环境颜色一致，不同环境区分明显）
const ENV_COLOR_PALETTE = [
  { color: "#e6f4ff", textColor: "#1677ff", borderColor: "#91caff" },
  { color: "#f6ffed", textColor: "#52c41a", borderColor: "#b7eb8f" },
  { color: "#fff7e6", textColor: "#fa8c16", borderColor: "#ffd591" },
  { color: "#fff0f6", textColor: "#eb2f96", borderColor: "#ffadd2" },
  { color: "#f9f0ff", textColor: "#722ed1", borderColor: "#d3adf7" },
  { color: "#e6fffb", textColor: "#13c2c2", borderColor: "#87e8de" },
  { color: "#fffbe6", textColor: "#d4b106", borderColor: "#fff566" },
  { color: "#fff1f0", textColor: "#f5222d", borderColor: "#ffa39e" },
];

const getEnvironmentColor = (env: string) => {
  if (!env || env === "全局") {
    return { color: "#f5f5f5", textColor: "#666666", borderColor: "#d9d9d9" };
  }
  let hash = 0;
  for (let i = 0; i < env.length; i++) {
    hash = (hash * 31 + env.charCodeAt(i)) & 0xffffffff;
  }
  const index = Math.abs(hash) % ENV_COLOR_PALETTE.length;
  return ENV_COLOR_PALETTE[index];
};

// 生成随机数（用于预览当前值）
const generateRandomValue = (min: number, max: number): string => {
  return String(Math.floor(Math.random() * (max - min + 1)) + min);
};

// 获取变量当前值
const getVariableCurrentValue = (variable: Variable): string => {
  if (variable.type === "fixed") {
    return variable.value || "";
  } else if (variable.type === "database") {
    return "执行用例时查询";
  } else if (variable.type === "auth" || variable.type === "cookie") {
    return variable.value ? variable.value.slice(0, 6) + "******" : "";
  } else if (variable.type === "extracted") {
    return variable.value || "用例执行后写入";
  } else {
    return generateRandomValue(
      variable.minValue || 0,
      variable.maxValue || 100
    );
  }
};

// 保存变量
const handleSaveVariable = async () => {
  try {
    await formRef.value?.validate();

    // Authorization/Cookie类型且选择"引用登录测试用例"：先执行该用例抓取凭证值
    let resolvedCredentialValue = formData.value.value;
    if (isCredentialType.value && formData.value.sourceType === "testcase") {
      capturingToken.value = true;
      try {
        const captureUrl =
          formData.value.type === "cookie"
            ? "/api/variables/capture-cookie"
            : "/api/variables/capture-auth-token";
        const captureResponse = await axios.post(captureUrl, {
          testCaseId: formData.value.loginTestCaseId,
        });
        if (captureResponse.data.success) {
          resolvedCredentialValue =
            formData.value.type === "cookie"
              ? captureResponse.data.cookies
              : captureResponse.data.token;
          message.success(`已抓取到${credentialValueLabel.value}`);
        } else {
          message.error(captureResponse.data.error || "抓取失败");
          return;
        }
      } catch (error: any) {
        message.error(error.response?.data?.error || "抓取失败");
        return;
      } finally {
        capturingToken.value = false;
      }
    }

    const payload: any = {
      name: formData.value.name,
      type: formData.value.type,
      description: formData.value.description,
      environment: formData.value.environment || "全局",
      project: formData.value.project || "",
    };

    // 如果是编辑模式，需要传递原始的环境和项目信息
    if (editingVariable.value) {
      payload.originalEnvironment = editingVariable.value.originalEnvironment;
      payload.originalProject = editingVariable.value.originalProject;
    }

    if (formData.value.type === "fixed") {
      Object.assign(payload, { value: formData.value.value });
    } else if (formData.value.type === "database") {
      Object.assign(payload, {
        database: formData.value.database,
        query: formData.value.query,
      });
    } else if (isCredentialType.value) {
      Object.assign(payload, {
        sourceType: formData.value.sourceType || "manual",
        value: resolvedCredentialValue,
        matchDomains: formData.value.matchDomains || [],
      });
      if (formData.value.sourceType === "testcase") {
        payload.loginTestCaseId = formData.value.loginTestCaseId;
      }
    } else if (formData.value.type === "extracted") {
      // 提取变量：仅声明变量名，值由用例执行"获取元素文案"步骤写入，此处无需额外字段
      Object.assign(payload, { value: "" });
    } else {
      Object.assign(payload, {
        minValue: formData.value.minValue,
        maxValue: formData.value.maxValue,
      });
    }

    const response = await axios.post("/api/variables/add", payload);

    if (response.data.success) {
      message.success(editingVariable.value ? "变量更新成功" : "变量添加成功");
      showAddModal.value = false;
      resetForm();
      await loadVariables();
    }
  } catch (error: any) {
    if (error?.response?.data?.error) {
      message.error(error.response.data.error);
    } else {
      console.error("保存变量失败:", error);
      message.error("保存变量失败");
    }
  }
};

// 删除变量
const handleDelete = async (variable: Variable) => {
  try {
    const response = await axios.delete(`/api/variables/${variable.name}`, {
      params: {
        environment: variable.environment || "全局",
        project: variable.project || "",
      },
    });
    if (response.data.success) {
      message.success("变量删除成功");
      await loadVariables();
    }
  } catch (error) {
    console.error("删除变量失败:", error);
    message.error("删除变量失败");
  }
};

// 编辑变量
const handleEdit = (variable: Variable) => {
  editingVariable.value = {
    name: variable.name,
    originalEnvironment: variable.environment || "全局",
    originalProject: variable.project || "",
  };
  formData.value = {
    ...variable,
    environment: variable.environment || "全局",
    project: variable.project || "",
    matchDomains: variable.matchDomains || [],
    sourceType: variable.sourceType || "manual",
    loginTestCaseId: variable.loginTestCaseId ?? null,
  };
  if (
    (variable.type === "auth" || variable.type === "cookie") &&
    variable.sourceType === "testcase"
  ) {
    loadLoginTestCases();
  }
  showAddModal.value = true;
};

// 重置表单
const resetForm = () => {
  editingVariable.value = null;
  formData.value = {
    name: "",
    type: "fixed",
    value: "",
    minValue: 0,
    maxValue: 100,
    database: "",
    query: "",
    description: "",
    environment: "全局",
    project: "",
    matchDomains: [],
    sourceType: "manual",
    loginTestCaseId: null,
  };
};

// 表格列定义
const columns: DataTableColumns<Variable> = [
  {
    title: "变量名",
    key: "name",
    width: 250,
  },
  {
    title: "类型",
    key: "type",
    width: 100,
    render(row) {
      const typeMap: Record<string, { label: string; tagType: "success" | "info" | "warning" | "error" }> = {
        fixed: { label: "固定值", tagType: "success" },
        random: { label: "随机数", tagType: "info" },
        database: { label: "数据库查询", tagType: "warning" },
        auth: { label: "Authorization", tagType: "error" },
        cookie: { label: "Cookie", tagType: "error" },
        extracted: { label: "提取变量", tagType: "info" },
      };
      const cfg = typeMap[row.type] || typeMap.fixed;
      return h(NTag, { type: cfg.tagType }, { default: () => cfg.label });
    },
  },
  {
    title: "当前值",
    key: "currentValue",
    width: 300,
    render(row) {
      const value = getVariableCurrentValue(row);
      return h("span", { style: { fontWeight: "500" } }, value);
    },
  },
  {
    title: "配置",
    key: "config",
    render(row) {
      if (row.type === "fixed") {
        return h("span", `固定值: ${row.value}`);
      } else if (row.type === "database") {
        return h("span", `数据库: ${row.database} | 查询: ${row.query}`);
      } else if (row.type === "auth" || row.type === "cookie") {
        const maskedValue = row.value ? row.value.slice(0, 6) + "******" : "";
        const valueLabel = row.type === "cookie" ? "Cookie" : "Token";
        return h(
          "span",
          `域名: ${(row.matchDomains || []).join(", ")} | ${valueLabel}: ${maskedValue}`
        );
      } else if (row.type === "extracted") {
        return h("span", "由用例步骤执行后写入，此处仅为声明");
      } else {
        return h("span", `范围: ${row.minValue} ~ ${row.maxValue}`);
      }
    },
  },
  {
    title: "所属环境",
    key: "environment",
    width: 120,
    render(row) {
      const env = row.environment || "全局";
      return h(
        NTag,
        { color: getEnvironmentColor(env) },
        { default: () => env }
      );
    },
  },
  {
    title: "所属项目",
    key: "project",
    width: 120,
    render(row) {
      return h("span", row.project || "不限");
    },
  },
  {
    title: "描述",
    key: "description",
    ellipsis: {
      tooltip: true,
    },
  },
  {
    title: "操作",
    key: "actions",
    width: 180,
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
                type: "primary",
                onClick: () => handleEdit(row),
              },
              {
                default: () => "编辑",
                icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
              }
            ),
            h(
              NButton,
              {
                size: "small",
                type: "error",
                onClick: () => handleDelete(row),
              },
              {
                default: () => "删除",
                icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
              }
            ),
          ],
        }
      );
    },
  },
];

onMounted(() => {
  loadVariables();
  fetchEnvironments();
  fetchDatabases();
  fetchProjects();
});
</script>

<style scoped>
.variable-container {
  padding: 24px;
}

h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.save-hint {
  margin: 4px 0 0;
  font-size: 12px;
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

  .search-form :deep(.n-input) {
    width: 100%;
  }

  .search-buttons-wrapper {
    justify-content: center;
  }
}
</style>

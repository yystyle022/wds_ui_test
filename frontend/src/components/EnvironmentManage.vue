<template>
  <div class="env-container">
    <n-space vertical :size="16">
      <!-- 页面标题和操作按钮 -->
      <n-space justify="space-between" align="center">
        <n-space align="center" :size="10">
          <h2>环境管理</h2>
          <n-text v-if="!selectedEnv" depth="3" style="font-size: 13px">
            请先选择一个环境以管理它的变量
          </n-text>
        </n-space>
        <n-space>
          <n-button type="primary" @click="openAddEnvModal">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            新建环境
          </n-button>
          <n-button @click="loadEnvironments">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </n-space>

      <!-- 环境列表表格 -->
      <n-data-table
        :columns="envColumns"
        :data="environmentList"
        :pagination="false"
        :bordered="false"
        :row-props="rowProps"
        :row-class-name="rowClassName"
      />

      <!-- 选中环境的变量管理 -->
      <n-card v-if="selectedEnv" :title="`「${selectedEnv.name}」的变量`">
        <template #header-extra>
          <n-button size="small" type="primary" @click="openAddVarModal">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            新增变量
          </n-button>
        </template>
        <n-data-table
          :columns="varColumns"
          :data="selectedEnvVariables"
          :pagination="{ pageSize: 10 }"
          :bordered="false"
        />
      </n-card>
    </n-space>

    <!-- 新建/编辑环境弹窗 -->
    <n-modal
      v-model:show="showEnvModal"
      preset="dialog"
      :title="editingEnvId ? '编辑环境' : '新建环境'"
      :style="{ width: '600px' }"
    >
      <n-form
        ref="envFormRef"
        :model="envFormData"
        :rules="envRules"
        label-placement="left"
        label-width="100px"
      >
        <n-form-item label="环境名称" path="name">
          <n-input v-model:value="envFormData.name" placeholder="如：测试环境" />
        </n-form-item>
        <n-form-item label="关联的项目" path="project">
          <n-select
            v-model:value="envFormData.project"
            :options="projectOptions"
            placeholder="请选择关联的项目（可选）"
            clearable
          />
        </n-form-item>
        <n-form-item label="环境描述" path="description">
          <n-input
            v-model:value="envFormData.description"
            type="textarea"
            placeholder="请输入环境描述（可选）"
            :rows="3"
          />
        </n-form-item>
      </n-form>

      <template #action>
        <n-space justify="end">
          <n-button @click="showEnvModal = false">取消</n-button>
          <n-button type="primary" @click="handleSaveEnv"> 确定 </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 新建/编辑变量弹窗 -->
    <n-modal
      v-model:show="showVarModal"
      preset="dialog"
      :title="editingVarName ? '编辑变量' : '新增变量'"
      :style="{ width: '600px' }"
    >
      <n-form
        ref="varFormRef"
        :model="varFormData"
        :rules="varRules"
        label-placement="left"
        label-width="100px"
      >
        <n-form-item label="变量名" path="name">
          <n-input
            v-model:value="varFormData.name"
            placeholder="请输入变量名，如: user_id"
            :disabled="!!editingVarName"
          />
        </n-form-item>

        <n-form-item label="所属项目" path="project">
          <n-select
            v-model:value="varFormData.project"
            :options="projectOptions"
            placeholder="请选择所属项目（不选则不限项目）"
            clearable
          />
        </n-form-item>

        <n-form-item label="所属环境" path="environment">
          <n-select
            v-model:value="varFormData.environment"
            :options="environmentOptions"
            placeholder="请选择所属环境"
          />
        </n-form-item>

        <n-form-item label="变量类型" path="type">
          <n-radio-group v-model:value="varFormData.type">
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
          v-if="varFormData.type === 'fixed'"
          label="变量值"
          path="value"
        >
          <n-input v-model:value="varFormData.value" placeholder="请输入固定值" />
        </n-form-item>

        <template v-if="varFormData.type === 'random'">
          <n-form-item label="最小值" path="minValue">
            <n-input-number
              v-model:value="varFormData.minValue"
              placeholder="请输入最小值"
              :style="{ width: '100%' }"
            />
          </n-form-item>

          <n-form-item label="最大值" path="maxValue">
            <n-input-number
              v-model:value="varFormData.maxValue"
              placeholder="请输入最大值"
              :style="{ width: '100%' }"
            />
          </n-form-item>
        </template>

        <template v-if="varFormData.type === 'database'">
          <n-form-item label="选择数据库" path="database">
            <n-select
              v-model:value="varFormData.database"
              :options="databaseOptions"
              placeholder="请选择数据库配置"
            />
          </n-form-item>

          <n-form-item label="查询语句" path="query">
            <n-input
              v-model:value="varFormData.query"
              type="textarea"
              placeholder="请输入 SQL 查询语句，语句中不确定的值可用 ${变量名} 或 {{变量名}} 引用其他变量，用例实际执行时会自动替换为当时的值"
              :rows="4"
            />
          </n-form-item>
        </template>

        <template v-if="varFormData.type === 'auth' || varFormData.type === 'cookie'">
          <n-form-item :label="varFormData.type === 'cookie' ? 'Cookie值' : 'Token值'" path="value">
            <n-input
              v-model:value="varFormData.value"
              :type="varFormData.type === 'cookie' ? 'textarea' : 'text'"
              :rows="varFormData.type === 'cookie' ? 4 : undefined"
              :placeholder="varFormData.type === 'cookie' ? '请粘贴Cookie内容（JSON格式的数组）' : '请输入 Authorization Token'"
            />
          </n-form-item>

          <n-form-item label="匹配域名" path="matchDomains">
            <n-select
              v-model:value="varFormData.matchDomains"
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
            v-model:value="varFormData.description"
            type="textarea"
            placeholder="请输入变量描述（可选）"
            :rows="3"
          />
        </n-form-item>
      </n-form>

      <template #action>
        <n-space justify="end">
          <n-button @click="showVarModal = false">取消</n-button>
          <n-button type="primary" @click="handleSaveVar"> 确定 </n-button>
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
  NCard,
  NText,
  NTag,
  NCheckbox,
  NCheckboxGroup,
  useMessage,
  useDialog,
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
  environment?: string;
  project?: string;
  matchDomains?: string[];
  syncToOtherEnvs?: boolean;
  selectedEnvs?: string[];
}

interface Environment {
  id: number;
  name: string;
  description?: string;
  project?: string;
  createTime?: string;
}

const message = useMessage();
const dialog = useDialog();

const environmentList = ref<Environment[]>([]);
const selectedEnv = ref<Environment | null>(null);

// ---------- 环境 增/改 ----------
const showEnvModal = ref(false);
const editingEnvId = ref<number | null>(null);
const envFormRef = ref<FormInst | null>(null);
const envFormData = ref<{
  name: string;
  description: string;
  project: string | null;
}>({ name: "", description: "", project: null });

const envRules: FormRules = {
  name: [{ required: true, message: "请输入环境名称", trigger: "blur" }],
};

const loadEnvironments = async () => {
  try {
    const response = await axios.get("/api/environments");
    if (response.data.success) {
      environmentList.value = response.data.environments;
      if (selectedEnv.value) {
        selectedEnv.value =
          environmentList.value.find((e) => e.id === selectedEnv.value!.id) ||
          null;
      }
    }
  } catch (error) {
    console.error("加载环境失败:", error);
    message.error("加载环境失败");
  }
};

const openAddEnvModal = () => {
  editingEnvId.value = null;
  envFormData.value = { name: "", description: "", project: null };
  showEnvModal.value = true;
};

const handleEditEnv = (env: Environment) => {
  editingEnvId.value = env.id;
  envFormData.value = {
    name: env.name,
    description: env.description || "",
    project: env.project || null,
  };
  showEnvModal.value = true;
};

const handleSaveEnv = async () => {
  try {
    await envFormRef.value?.validate();

    const payload = {
      name: envFormData.value.name,
      description: envFormData.value.description,
      project: envFormData.value.project || "",
    };

    const response = editingEnvId.value
      ? await axios.put(`/api/environments/${editingEnvId.value}`, payload)
      : await axios.post("/api/environments", payload);

    if (response.data.success) {
      message.success(editingEnvId.value ? "环境更新成功" : "环境创建成功");
      showEnvModal.value = false;
      await loadEnvironments();
    }
  } catch (error: any) {
    if (error?.response?.data?.error) {
      message.error(error.response.data.error);
    } else {
      console.error("保存环境失败:", error);
      message.error("保存环境失败");
    }
  }
};

const handleDeleteEnv = (env: Environment) => {
  dialog.warning({
    title: "确认删除",
    content: `确定要删除环境「${env.name}」吗？该环境下的所有变量也会被删除。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        const response = await axios.delete(`/api/environments/${env.id}`);
        if (response.data.success) {
          message.success("环境删除成功");
          if (selectedEnv.value?.id === env.id) {
            selectedEnv.value = null;
          }
          await loadEnvironments();
        }
      } catch (error) {
        console.error("删除环境失败:", error);
        message.error("删除环境失败");
      }
    },
  });
};

const selectEnv = (env: Environment) => {
  selectedEnv.value = env;
};

const rowProps = (row: Environment) => ({
  style: "cursor: pointer;",
  onClick: () => selectEnv(row),
});

const rowClassName = (row: Environment) =>
  selectedEnv.value?.id === row.id ? "env-row-selected" : "";

const envColumns: DataTableColumns<Environment> = [
  { title: "环境名称", key: "name", width: 200 },
  {
    title: "关联的项目",
    key: "project",
    width: 160,
    render(row) {
      return row.project
        ? h(NTag, { type: "success" }, { default: () => row.project })
        : h("span", { style: "color: #c0c4cc" }, "未关联");
    },
  },
  { title: "描述", key: "description", ellipsis: { tooltip: true } },
  {
    title: "变量数",
    key: "variables",
    width: 100,
    render(row) {
      const count = allVariables.value.filter(
        (v) => v.environment === row.name
      ).length;
      return h(NTag, { type: "info" }, { default: () => count });
    },
  },
  { title: "创建时间", key: "createTime", width: 180 },
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
                onClick: (e: MouseEvent) => {
                  e.stopPropagation();
                  handleEditEnv(row);
                },
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
                onClick: (e: MouseEvent) => {
                  e.stopPropagation();
                  handleDeleteEnv(row);
                },
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

// ---------- 变量 增/改/删（与变量管理页面共用同一份全局变量数据，按所属环境过滤）----------
const allVariables = ref<Variable[]>([]);
const databaseOptions = ref<{ label: string; value: string }[]>([]);
const projectOptions = ref<{ label: string; value: string }[]>([]);

const selectedEnvVariables = computed(() =>
  allVariables.value.filter((v) => v.environment === selectedEnv.value?.name)
);

const environmentOptions = computed(() => {
  return environmentList.value.map((env) => ({
    label: env.name,
    value: env.name,
  }));
});

const availableEnvs = computed(() => {
  // 获取当前项目的所有环境（如果有选择项目）
  if (varFormData.value.project) {
    // 这里简化处理，返回所有环境
    return environmentList.value.filter(env => env.name !== selectedEnv.value?.name);
  }
  return environmentList.value.filter(env => env.name !== selectedEnv.value?.name);
});

const domainCandidateOptions = computed(() => {
  return allVariables.value
    .filter(
      (v) =>
        v.name !== varFormData.value.name &&
        (v.project || "") === (varFormData.value.project || "") &&
        v.environment === selectedEnv.value?.name
    )
    .map((v) => ({ label: v.name, value: v.name }));
});

const loadAllVariables = async () => {
  try {
    const response = await axios.get("/api/variables/list");
    if (response.data.success) {
      allVariables.value = response.data.variables;
    }
  } catch (error) {
    console.error("加载变量失败:", error);
  }
};

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

const generateRandomValue = (min: number, max: number): string => {
  return String(Math.floor(Math.random() * (max - min + 1)) + min);
};

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
    return generateRandomValue(variable.minValue || 0, variable.maxValue || 100);
  }
};

const showVarModal = ref(false);
const editingVarName = ref<string | null>(null);
const varFormRef = ref<FormInst | null>(null);
const varFormData = ref<Variable>({
  name: "",
  type: "fixed",
  value: "",
  minValue: 0,
  maxValue: 100,
  database: "",
  query: "",
  description: "",
  environment: "",
  project: "",
  matchDomains: [],
});

const varRules: FormRules = {
  name: [
    { required: true, message: "请输入变量名", trigger: "blur" },
    {
      pattern: /^[a-zA-Z_][a-zA-Z0-9_]*$/,
      message: "变量名只能包含字母、数字和下划线，且不能以数字开头",
      trigger: "blur",
    },
  ],
  value: [
    {
      validator: (rule, value) => {
        if (
          (varFormData.value.type === "fixed" ||
           varFormData.value.type === "auth" ||
           varFormData.value.type === "cookie") &&
          !value
        ) {
          if (varFormData.value.type === "auth") {
            return new Error("请输入Token值");
          } else if (varFormData.value.type === "cookie") {
            return new Error("请输入Cookie值");
          } else {
            return new Error("请输入变量值");
          }
        }
        return true;
      },
      trigger: "blur",
    },
  ],
  matchDomains: [
    {
      validator: (rule, value) => {
        if ((varFormData.value.type === "auth" || varFormData.value.type === "cookie") &&
            (!value || value.length === 0)) {
          return new Error("请至少填写一个匹配域名");
        }
        return true;
      },
      trigger: "change",
    },
  ],
  minValue: [
    { type: "number", required: true, message: "请输入最小值", trigger: "blur" },
  ],
  maxValue: [
    { type: "number", required: true, message: "请输入最大值", trigger: "blur" },
    {
      validator: (rule, value) => {
        if (value <= varFormData.value.minValue!) {
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
        if (varFormData.value.type === "database" && !value) {
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
        if (varFormData.value.type === "database" && !value) {
          return new Error("请输入查询语句");
        }
        return true;
      },
      trigger: "blur",
    },
  ],
};

const openAddVarModal = () => {
  editingVarName.value = null;
  varFormData.value = {
    name: "",
    type: "fixed",
    value: "",
    minValue: 0,
    maxValue: 100,
    database: "",
    query: "",
    description: "",
    environment: selectedEnv.value?.name || "",
    project: "",
    matchDomains: [],
  };
  showVarModal.value = true;
};

const handleEditVar = (variable: Variable) => {
  editingVarName.value = variable.name;

  varFormData.value = {
    ...variable,
    description: variable.description || "",
    project: variable.project || "",
    environment: variable.environment || "",
    matchDomains: variable.matchDomains || [],
  };
  showVarModal.value = true;
};

const handleSaveVar = async () => {
  if (!selectedEnv.value) return;
  try {
    await varFormRef.value?.validate();

    const payload: any = {
      name: varFormData.value.name,
      type: varFormData.value.type,
      description: varFormData.value.description,
      environment: varFormData.value.environment, // 使用表单选择的环境
      project: varFormData.value.project || "",
    };

    if (varFormData.value.type === "fixed") {
      payload.value = varFormData.value.value;
    } else if (varFormData.value.type === "database") {
      payload.database = varFormData.value.database;
      payload.query = varFormData.value.query;
    } else if (varFormData.value.type === "auth" || varFormData.value.type === "cookie") {
      payload.value = varFormData.value.value;
      payload.matchDomains = varFormData.value.matchDomains || [];
    } else if (varFormData.value.type === "extracted") {
      payload.value = "";
    } else {
      payload.minValue = varFormData.value.minValue;
      payload.maxValue = varFormData.value.maxValue;
    }

    const response = await axios.post("/api/variables/add", payload);

    if (response.data.success) {
      message.success(editingVarName.value ? "变量更新成功" : "变量添加成功");
      showVarModal.value = false;
      await loadAllVariables();
    }
  } catch (error: any) {
    if (error?.response?.data?.error) {
      message.error(error.response.data.error);
    } else if (!Array.isArray(error)) {
      console.error("保存变量失败:", error);
      message.error("保存变量失败");
    }
  }
};

const handleDeleteVar = (variable: Variable) => {
  dialog.warning({
    title: "确认删除",
    content: `确定要删除变量「${variable.name}」吗？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        const response = await axios.delete(`/api/variables/${variable.name}`, {
          params: {
            environment: variable.environment || "全局",
            project: variable.project || "",
          },
        });
        if (response.data.success) {
          message.success("变量删除成功");
          await loadAllVariables();
        }
      } catch (error) {
        console.error("删除变量失败:", error);
        message.error("删除变量失败");
      }
    },
  });
};

const varColumns: DataTableColumns<Variable> = [
  { title: "变量名", key: "name", width: 180 },
  {
    title: "类型",
    key: "type",
    width: 110,
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
    title: "环境",
    key: "environment",
    width: 150,
    render(row) {
      return h(
        NTag,
        { type: "info" },
        { default: () => row.environment || "全局" }
      );
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
        const label = row.type === "cookie" ? "Cookie" : "Token";
        return h(
          "span",
          `域名: ${(row.matchDomains || []).join(", ")} | ${label}: ${maskedValue}`
        );
      } else if (row.type === "extracted") {
        return h("span", row.value || "用例执行后写入");
      } else {
        return h("span", `范围: ${row.minValue} ~ ${row.maxValue}`);
      }
    },
  },
  { title: "描述", key: "description", ellipsis: { tooltip: true } },
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
                onClick: () => handleEditVar(row),
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
                onClick: () => handleDeleteVar(row),
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
  loadEnvironments();
  loadAllVariables();
  fetchDatabases();
  fetchProjects();
});
</script>

<style scoped>
.env-container {
  padding: 24px;
}

h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

:deep(.env-row-selected td) {
  background-color: rgba(24, 160, 88, 0.1) !important;
}
</style>

<template>
  <div class="database-container">
    <n-space vertical :size="16">
      <!-- 页面标题和操作按钮 -->
      <n-space justify="space-between">
        <h2>数据管理</h2>
        <n-space>
          <n-button type="primary" @click="openAddModal">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            新建数据库配置
          </n-button>
          <n-button @click="loadDatabases">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </n-space>

      <!-- 数据库配置列表 -->
      <n-data-table
        :columns="columns"
        :data="databaseList"
        :pagination="{ pageSize: 10 }"
        :bordered="false"
      />
    </n-space>

    <!-- 新建/编辑数据库配置弹窗 -->
    <n-modal
      v-model:show="showModal"
      preset="dialog"
      :title="editingId ? '编辑数据库配置' : '新建数据库配置'"
      :style="{ width: '640px' }"
    >
      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="left"
        label-width="100px"
      >
        <n-form-item label="配置名称" path="name">
          <n-input v-model:value="formData.name" placeholder="如：订单库-测试环境" />
        </n-form-item>

        <n-form-item label="数据库类型" path="type">
          <n-select
            v-model:value="formData.type"
            :options="typeOptions"
            @update:value="handleTypeChange"
          />
        </n-form-item>

        <n-form-item label="所属项目" path="project">
          <n-select
            v-model:value="formData.project"
            :options="projectOptions"
            placeholder="请选择所属项目"
          />
        </n-form-item>

        <n-form-item label="所属环境" path="environment">
          <n-select
            v-model:value="formData.environment"
            :options="environmentOptions"
            placeholder="请选择所属环境"
          />
        </n-form-item>

        <n-form-item label="主机地址" path="host">
          <n-input v-model:value="formData.host" placeholder="如：127.0.0.1" />
        </n-form-item>

        <n-form-item label="端口" path="port">
          <n-input-number
            v-model:value="formData.port"
            :style="{ width: '100%' }"
            :min="1"
            :max="65535"
          />
        </n-form-item>

        <n-form-item label="用户名" path="username">
          <n-input v-model:value="formData.username" placeholder="请输入用户名" />
        </n-form-item>

        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="formData.password"
            type="password"
            show-password-on="click"
            placeholder="请输入密码"
          />
        </n-form-item>

        <n-form-item label="数据库名" path="database">
          <n-input v-model:value="formData.database" placeholder="请输入数据库名" />
        </n-form-item>

        <n-form-item label="描述" path="description">
          <n-input
            v-model:value="formData.description"
            type="textarea"
            placeholder="请输入描述（可选）"
            :rows="3"
          />
        </n-form-item>
      </n-form>

      <template #action>
        <n-space justify="end">
          <n-button :loading="testing" @click="handleTestConnection(formData)">
            测试连接
          </n-button>
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="handleSave"> 确定 </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from "vue";
import {
  NSpace,
  NButton,
  NDataTable,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  NIcon,
  NTag,
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
  FlashOutline,
} from "@vicons/ionicons5";
import axios from "axios";

interface DatabaseConfig {
  id: number;
  name: string;
  type: string;
  host: string;
  port: number | string;
  username: string;
  password: string;
  database: string;
  project?: string;
  environment?: string;
  description?: string;
  createTime?: string;
}

const message = useMessage();
const dialog = useDialog();

const databaseList = ref<DatabaseConfig[]>([]);
const projectOptions = ref<{ label: string; value: string }[]>([]);
const environmentOptions = ref<{ label: string; value: string }[]>([]);

const typeOptions = [
  { label: "MySQL", value: "mysql" },
  { label: "PostgreSQL", value: "postgresql" },
];

const defaultPortByType: Record<string, number> = {
  mysql: 3306,
  postgresql: 5432,
};

const showModal = ref(false);
const editingId = ref<number | null>(null);
const testing = ref(false);
const formRef = ref<FormInst | null>(null);

const emptyForm = (): Omit<DatabaseConfig, "id"> => ({
  name: "",
  type: "mysql",
  host: "",
  port: defaultPortByType.mysql,
  username: "",
  password: "",
  database: "",
  project: null as any,
  environment: null as any,
  description: "",
});

const formData = ref<Omit<DatabaseConfig, "id">>(emptyForm());

const rules: FormRules = {
  name: [{ required: true, message: "请输入配置名称", trigger: "blur" }],
  type: [{ required: true, message: "请选择数据库类型", trigger: "change" }],
  host: [{ required: true, message: "请输入主机地址", trigger: "blur" }],
  port: [{ required: true, type: "number", message: "请输入端口", trigger: "blur" }],
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
  database: [{ required: true, message: "请输入数据库名", trigger: "blur" }],
};

const handleTypeChange = (value: string) => {
  formData.value.port = defaultPortByType[value] ?? formData.value.port;
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

const fetchEnvironments = async () => {
  try {
    const response = await axios.get("/api/environments");
    const envs = response.data.environments || response.data || [];
    environmentOptions.value = envs.map((e: any) => ({
      label: e.name,
      value: e.name,
    }));
  } catch (error) {
    console.error("加载环境列表失败:", error);
  }
};

const loadDatabases = async () => {
  try {
    const response = await axios.get("/api/databases");
    if (response.data.success) {
      databaseList.value = response.data.databases;
    }
  } catch (error) {
    console.error("加载数据库配置失败:", error);
    message.error("加载数据库配置失败");
  }
};

const openAddModal = () => {
  editingId.value = null;
  formData.value = emptyForm();
  showModal.value = true;
};

const handleEdit = (row: DatabaseConfig) => {
  editingId.value = row.id;
  formData.value = {
    name: row.name,
    type: row.type,
    host: row.host,
    port: row.port,
    username: row.username,
    password: row.password,
    database: row.database,
    project: row.project || (null as any),
    environment: row.environment || (null as any),
    description: row.description || "",
  };
  showModal.value = true;
};

const handleSave = async () => {
  try {
    await formRef.value?.validate();

    const response = editingId.value
      ? await axios.put(`/api/databases/${editingId.value}`, formData.value)
      : await axios.post("/api/databases", formData.value);

    if (response.data.success) {
      message.success(editingId.value ? "数据库配置更新成功" : "数据库配置创建成功");
      showModal.value = false;
      await loadDatabases();
    }
  } catch (error: any) {
    if (error?.response?.data?.error) {
      message.error(error.response.data.error);
    } else if (!Array.isArray(error)) {
      console.error("保存数据库配置失败:", error);
      message.error("保存数据库配置失败");
    }
  }
};

const handleDelete = (row: DatabaseConfig) => {
  dialog.warning({
    title: "确认删除",
    content: `确定要删除数据库配置「${row.name}」吗？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        const response = await axios.delete(`/api/databases/${row.id}`);
        if (response.data.success) {
          message.success("数据库配置删除成功");
          await loadDatabases();
        }
      } catch (error) {
        console.error("删除数据库配置失败:", error);
        message.error("删除数据库配置失败");
      }
    },
  });
};

const handleTestConnection = async (config: Partial<DatabaseConfig>) => {
  testing.value = true;
  try {
    const response = await axios.post("/api/databases/test", config);
    if (response.data.success) {
      message.success(response.data.message || "连接成功");
    } else {
      message.error(response.data.error || "连接失败");
    }
  } catch (error) {
    console.error("测试数据库连接失败:", error);
    message.error("测试数据库连接失败");
  } finally {
    testing.value = false;
  }
};

const columns: DataTableColumns<DatabaseConfig> = [
  { title: "配置名称", key: "name", width: 180 },
  {
    title: "类型",
    key: "type",
    width: 110,
    render(row) {
      return h(
        NTag,
        { type: row.type === "mysql" ? "success" : "info" },
        { default: () => (row.type === "mysql" ? "MySQL" : "PostgreSQL") }
      );
    },
  },
  {
    title: "主机:端口",
    key: "host",
    width: 180,
    render(row) {
      return `${row.host}:${row.port}`;
    },
  },
  { title: "数据库名", key: "database", width: 150 },
  {
    title: "所属项目",
    key: "project",
    width: 140,
    render(row) {
      return row.project
        ? h(NTag, { type: "success" }, { default: () => row.project })
        : h("span", { style: "color: #c0c4cc" }, "未关联");
    },
  },
  {
    title: "所属环境",
    key: "environment",
    width: 140,
    render(row) {
      return row.environment
        ? h(NTag, { type: "warning" }, { default: () => row.environment })
        : h("span", { style: "color: #c0c4cc" }, "未关联");
    },
  },
  { title: "描述", key: "description", ellipsis: { tooltip: true } },
  { title: "创建时间", key: "createTime", width: 180 },
  {
    title: "操作",
    key: "actions",
    width: 240,
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
                onClick: () => handleTestConnection(row),
              },
              {
                default: () => "测试连接",
                icon: () => h(NIcon, null, { default: () => h(FlashOutline) }),
              }
            ),
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
  loadDatabases();
  fetchProjects();
  fetchEnvironments();
});
</script>

<style scoped>
.database-container {
  padding: 24px;
}

h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
</style>

<template>
  <div class="device-container">
    <n-space vertical :size="16">
      <!-- 页面标题和操作按钮 -->
      <n-space justify="space-between">
        <h2>设备管理</h2>
        <n-space>
          <n-button type="primary" @click="openAddModal">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            新建设备
          </n-button>
          <n-button @click="loadDevices">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </n-space>

      <!-- 设备列表 -->
      <n-data-table
        :columns="columns"
        :data="deviceList"
        :pagination="{ pageSize: 10 }"
        :bordered="false"
      />
    </n-space>

    <!-- 新建/编辑设备弹窗 -->
    <n-modal
      v-model:show="showModal"
      preset="dialog"
      :title="editingId ? '编辑设备' : '新建设备'"
      :style="{ width: '560px' }"
    >
      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="left"
        label-width="120px"
      >
        <n-form-item label="设备名称" path="name">
          <n-input v-model:value="formData.name" placeholder="如：测试机-小米13" />
        </n-form-item>

        <n-form-item label="平台" path="platform">
          <n-select v-model:value="formData.platform" :options="platformOptions" disabled />
        </n-form-item>

        <n-form-item label="设备序列号" path="serial">
          <n-input
            v-model:value="formData.serial"
            placeholder="adb devices 显示的序列号，或 ip:port"
          />
        </n-form-item>

        <n-form-item label="所属项目" path="project">
          <n-select
            v-model:value="formData.project"
            :options="projectOptions"
            placeholder="请选择所属项目（可选）"
            clearable
          />
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
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="handleSave">确定</n-button>
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
  NSelect,
  NIcon,
  NTag,
  useMessage,
  useDialog,
  type DataTableColumns,
  type FormInst,
  type FormRules,
} from "naive-ui";
import { AddOutline, RefreshOutline, TrashOutline, CreateOutline } from "@vicons/ionicons5";
import axios from "axios";

interface DeviceConfig {
  id: number;
  name: string;
  platform: string;
  serial: string;
  project?: string;
  description?: string;
  createTime?: string;
}

const message = useMessage();
const dialog = useDialog();

const deviceList = ref<DeviceConfig[]>([]);
const projectOptions = ref<{ label: string; value: string }[]>([]);

const platformOptions = [{ label: "Android", value: "android" }];

const showModal = ref(false);
const editingId = ref<number | null>(null);
const formRef = ref<FormInst | null>(null);

const emptyForm = (): Omit<DeviceConfig, "id"> => ({
  name: "",
  platform: "android",
  serial: "",
  project: null as any,
  description: "",
});

const formData = ref<Omit<DeviceConfig, "id">>(emptyForm());

const rules: FormRules = {
  name: [{ required: true, message: "请输入设备名称", trigger: "blur" }],
  serial: [{ required: true, message: "请输入设备序列号/连接地址", trigger: "blur" }],
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

const loadDevices = async () => {
  try {
    const response = await axios.get("/api/devices");
    if (response.data.success) {
      deviceList.value = response.data.devices;
    }
  } catch (error) {
    console.error("加载设备列表失败:", error);
    message.error("加载设备列表失败");
  }
};

const openAddModal = () => {
  editingId.value = null;
  formData.value = emptyForm();
  showModal.value = true;
};

const handleEdit = (row: DeviceConfig) => {
  editingId.value = row.id;
  formData.value = {
    name: row.name,
    platform: row.platform,
    serial: row.serial,
    project: row.project || (null as any),
    description: row.description || "",
  };
  showModal.value = true;
};

const handleSave = async () => {
  try {
    await formRef.value?.validate();

    const response = editingId.value
      ? await axios.put(`/api/devices/${editingId.value}`, formData.value)
      : await axios.post("/api/devices", formData.value);

    if (response.data.success) {
      message.success(editingId.value ? "设备更新成功" : "设备创建成功");
      showModal.value = false;
      await loadDevices();
    }
  } catch (error: any) {
    if (error?.response?.data?.error) {
      message.error(error.response.data.error);
    } else if (!Array.isArray(error)) {
      console.error("保存设备失败:", error);
      message.error("保存设备失败");
    }
  }
};

const handleDelete = (row: DeviceConfig) => {
  dialog.warning({
    title: "确认删除",
    content: `确定要删除设备「${row.name}」吗？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        const response = await axios.delete(`/api/devices/${row.id}`);
        if (response.data.success) {
          message.success("设备删除成功");
          await loadDevices();
        }
      } catch (error) {
        console.error("删除设备失败:", error);
        message.error("删除设备失败");
      }
    },
  });
};

const columns: DataTableColumns<DeviceConfig> = [
  { title: "设备名称", key: "name", width: 180 },
  {
    title: "平台",
    key: "platform",
    width: 100,
    render(row) {
      return h(NTag, { type: "success" }, { default: () => "Android" });
    },
  },
  { title: "序列号/连接地址", key: "serial", width: 200 },
  {
    title: "所属项目",
    key: "project",
    width: 140,
    render(row) {
      return row.project
        ? h(NTag, { type: "info" }, { default: () => row.project })
        : h("span", { style: "color: #c0c4cc" }, "未关联");
    },
  },
  { title: "描述", key: "description", ellipsis: { tooltip: true } },
  { title: "创建时间", key: "createTime", width: 180 },
  {
    title: "操作",
    key: "actions",
    width: 160,
    render(row) {
      return h(
        NSpace,
        { size: "small" },
        {
          default: () => [
            h(
              NButton,
              { size: "small", type: "primary", onClick: () => handleEdit(row) },
              {
                default: () => "编辑",
                icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
              }
            ),
            h(
              NButton,
              { size: "small", type: "error", onClick: () => handleDelete(row) },
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
  loadDevices();
  fetchProjects();
});
</script>

<style scoped>
.device-container {
  padding: 24px;
}

h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
</style>

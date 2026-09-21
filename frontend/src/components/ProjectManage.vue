<template>
  <div class="project-container">
    <n-space vertical :size="16">
      <!-- 页面标题和操作按钮 -->
      <n-space justify="space-between">
        <h2>项目管理</h2>
        <n-space>
          <n-button type="primary" @click="openAddModal">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            新建项目
          </n-button>
          <n-button @click="loadProjects">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </n-space>

      <!-- 项目列表表格 -->
      <n-data-table
        :columns="columns"
        :data="projectList"
        :pagination="pagination"
        :bordered="false"
      />
    </n-space>

    <!-- 新建/编辑项目弹窗 -->
    <n-modal
      v-model:show="showModal"
      preset="dialog"
      :title="editingProjectId ? '编辑项目' : '新建项目'"
      :style="{ width: '600px' }"
    >
      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="left"
        label-width="100px"
      >
        <n-form-item label="项目名称" path="name">
          <n-input v-model:value="formData.name" placeholder="请输入项目名称" />
        </n-form-item>

        <n-form-item label="项目描述" path="description">
          <n-input
            v-model:value="formData.description"
            type="textarea"
            placeholder="请输入项目描述（可选）"
            :rows="3"
          />
        </n-form-item>

      </n-form>

      <template #action>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="handleSaveProject"> 确定 </n-button>
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
  NIcon,
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

interface Project {
  id: number;
  name: string;
  description?: string;
  createTime?: string;
}

const message = useMessage();
const dialog = useDialog();
const showModal = ref(false);
const editingProjectId = ref<number | null>(null);
const formRef = ref<FormInst | null>(null);

const formData = ref({
  name: "",
  description: "",
});

const projectList = ref<Project[]>([]);

const pagination = {
  pageSize: 10,
};

const rules: FormRules = {
  name: [
    {
      required: true,
      message: "请输入项目名称",
      trigger: "blur",
    },
  ],
};

// 加载项目列表
const loadProjects = async () => {
  try {
    const response = await axios.get("/api/projects");
    if (response.data.success) {
      projectList.value = response.data.projects;
    }
  } catch (error) {
    console.error("加载项目失败:", error);
    message.error("加载项目失败");
  }
};

// 打开新建弹窗
const openAddModal = () => {
  resetForm();
  showModal.value = true;
};

// 保存项目（新建或编辑）
const handleSaveProject = async () => {
  try {
    await formRef.value?.validate();

    const payload: any = {
      name: formData.value.name,
      description: formData.value.description,
    };

    const response = editingProjectId.value
      ? await axios.put(`/api/projects/${editingProjectId.value}`, payload)
      : await axios.post("/api/projects", payload);

    if (response.data.success) {
      message.success(editingProjectId.value ? "项目更新成功" : "项目创建成功");
      showModal.value = false;
      resetForm();
      await loadProjects();
    }
  } catch (error: any) {
    if (error?.response?.data?.error) {
      message.error(error.response.data.error);
    } else {
      console.error("保存项目失败:", error);
      message.error("保存项目失败");
    }
  }
};

// 编辑项目
const handleEdit = (project: Project) => {
  editingProjectId.value = project.id;
  formData.value = {
    name: project.name,
    description: project.description || "",
  };
  showModal.value = true;
};

// 删除项目
const handleDelete = (project: Project) => {
  dialog.warning({
    title: "确认删除",
    content: `确定要删除项目「${project.name}」吗？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        const response = await axios.delete(`/api/projects/${project.id}`);
        if (response.data.success) {
          message.success("项目删除成功");
          await loadProjects();
        }
      } catch (error) {
        console.error("删除项目失败:", error);
        message.error("删除项目失败");
      }
    },
  });
};

// 重置表单
const resetForm = () => {
  editingProjectId.value = null;
  formData.value = {
    name: "",
    description: "",
  };
};

// 表格列定义
const columns: DataTableColumns<Project> = [
  {
    title: "项目名称",
    key: "name",
    width: 200,
  },
  {
    title: "描述",
    key: "description",
    ellipsis: {
      tooltip: true,
    },
  },
  {
    title: "创建时间",
    key: "createTime",
    width: 180,
  },
  {
    title: "操作",
    key: "actions",
    width: 200,
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
  loadProjects();
});
</script>

<style scoped>
.project-container {
  padding: 24px;
}

h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
</style>

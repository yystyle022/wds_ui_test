<template>
  <div class="task-list-container">
    <!-- 搜索区域 -->
    <div class="search-area">
      <div class="search-title">搜索条件</div>
      <n-form
        ref="searchFormRef"
        :model="searchForm"
        inline
        class="search-form"
      >
        <div class="search-items-wrapper">
          <n-form-item label="任务名称">
            <n-input
              v-model:value="searchForm.name"
              placeholder="请输入任务名称"
              clearable
            />
          </n-form-item>

          <n-form-item label="执行时间">
            <n-input
              v-model:value="searchForm.scheduleTime"
              placeholder="请输入定时执行时间"
              clearable
            />
          </n-form-item>

          <n-form-item label="所属项目">
            <n-select
              v-model:value="searchForm.project"
              placeholder="请选择所属项目"
              :options="projectOptions"
              clearable
            />
          </n-form-item>

          <n-form-item label="执行方式">
            <n-select
              v-model:value="searchForm.executionType"
              placeholder="请选择执行方式"
              :options="executionTypeOptions"
              clearable
            />
          </n-form-item>

          <div class="search-buttons-wrapper">
            <n-button @click="handleSearch" type="primary" size="small">
              搜索
            </n-button>
            <n-button @click="handleReset" size="small"> 重置 </n-button>
          </div>
        </div>
      </n-form>
    </div>

    <!-- 操作区域 -->
    <div class="operation-area">
      <div class="operation-left">
        <span class="total-text">任务列表</span>
      </div>
      <div class="operation-right">
        <n-button
          @click="handleSettings"
          type="primary"
          size="small"
          style="margin-right: 8px"
        >
          设置
        </n-button>
        <n-button @click="handleAddTask" type="primary" size="small">
          + 添加任务
        </n-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <n-data-table
      :columns="columns"
      :data="filteredData"
      :pagination="pagination"
      :bordered="false"
      striped
    />

    <!-- 总数显示 -->
    <div class="total-count">共 {{ filteredData.length }} 条任务</div>

    <!-- 添加任务弹窗 -->
    <n-modal
      v-model:show="showAddModal"
      preset="dialog"
      title="添加任务"
      :style="{ width: '600px' }"
    >
      <n-form
        ref="addFormRef"
        :model="addForm"
        :rules="addRules"
        label-placement="left"
        label-width="100px"
        class="modal-form"
      >
        <n-form-item label="任务名称" path="name">
          <n-input v-model:value="addForm.name" placeholder="请输入任务名称" />
        </n-form-item>

        <n-form-item label="任务描述" path="description">
          <n-input
            v-model:value="addForm.description"
            type="textarea"
            placeholder="请输入任务描述"
            :rows="3"
          />
        </n-form-item>

        <n-form-item label="所属项目" path="project">
          <n-select
            v-model:value="addForm.project"
            placeholder="请选择所属项目"
            :options="projectOptions"
          />
        </n-form-item>

        <n-form-item label="执行方式" path="executionType">
          <n-select
            v-model:value="addForm.executionType"
            placeholder="请选择执行方式"
            :options="executionTypeOptions"
            @update:value="handleExecutionTypeChange"
          />
        </n-form-item>

        <n-form-item
          v-if="addForm.executionType === 'scheduled'"
          label="定时时间"
          path="scheduleTime"
        >
          <n-input
            v-model:value="addForm.scheduleTime"
            placeholder="请输入定时执行时间 (如: 09:00)"
          />
        </n-form-item>

        <n-form-item label="选择用例">
          <n-button @click="handleSelectCases" type="primary" dashed>
            选择用例 (已选 {{ addForm.selectedCases.length }} 个)
          </n-button>
        </n-form-item>
      </n-form>

      <template #action>
        <n-space>
          <n-button @click="closeAddModal">取消</n-button>
          <n-button @click="submitAddForm" type="primary" :loading="addLoading">
            确定
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 选择用例弹窗 -->
    <n-modal
      v-model:show="showCaseSelectModal"
      preset="dialog"
      title="选择用例"
      :style="{ width: '90%', maxWidth: '1200px' }"
    >
      <!-- 用例搜索表单 -->
      <div class="case-search-area">
        <div class="search-title">搜索条件</div>
        <n-form
          ref="caseSearchFormRef"
          :model="caseSearchForm"
          inline
          class="search-form"
        >
          <div class="search-items-wrapper">
            <n-form-item label="用例名称">
              <n-input
                v-model:value="caseSearchForm.name"
                placeholder="请输入用例名称"
                clearable
                style="width: 200px"
              />
            </n-form-item>

            <n-form-item label="所属项目">
              <n-select
                v-model:value="caseSearchForm.project"
                placeholder="请选择所属项目"
                :options="projectOptions"
                clearable
                style="width: 150px"
              />
            </n-form-item>

            <n-form-item label="所属模块">
              <n-input
                v-model:value="caseSearchForm.module"
                placeholder="请输入模块名称"
                clearable
                style="width: 150px"
              />
            </n-form-item>

            <n-form-item label="类型">
              <n-select
                v-model:value="caseSearchForm.type"
                placeholder="请选择类型"
                :options="typeOptions"
                clearable
                style="width: 120px"
              />
            </n-form-item>

            <n-form-item label="环境">
              <n-select
                v-model:value="caseSearchForm.environment"
                placeholder="请选择环境"
                :options="environmentOptions"
                clearable
                style="width: 130px"
              />
            </n-form-item>

            <div class="search-buttons-wrapper">
              <n-button @click="handleCaseSearch" type="primary" size="small">
                搜索
              </n-button>
              <n-button @click="handleCaseSearchReset" size="small">
                重置
              </n-button>
            </div>
          </div>
        </n-form>
      </div>

      <n-divider style="margin: 16px 0" />

      <n-data-table
        :columns="caseColumns"
        :data="filteredCases"
        :row-key="(row) => row.id"
        v-model:checked-row-keys="selectedCaseKeys"
        :pagination="{ pageSize: 10 }"
        :bordered="false"
        striped
      />

      <!-- 总数显示 -->
      <div class="total-count">共 {{ filteredCases.length }} 条用例</div>

      <template #action>
        <n-space>
          <n-button @click="closeCaseSelectModal">取消</n-button>
          <n-button @click="confirmCaseSelection" type="primary">
            确定选择
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 编辑任务弹窗 -->
    <n-modal
      v-model:show="showEditModal"
      preset="dialog"
      title="编辑任务"
      :style="{ width: '600px' }"
    >
      <n-form
        ref="editFormRef"
        :model="editForm"
        :rules="addRules"
        label-placement="left"
        label-width="100px"
        class="modal-form"
      >
        <n-form-item label="任务名称" path="name">
          <n-input v-model:value="editForm.name" placeholder="请输入任务名称" />
        </n-form-item>

        <n-form-item label="任务描述" path="description">
          <n-input
            v-model:value="editForm.description"
            type="textarea"
            placeholder="请输入任务描述"
            :rows="3"
          />
        </n-form-item>

        <n-form-item label="所属项目" path="project">
          <n-select
            v-model:value="editForm.project"
            placeholder="请选择所属项目"
            :options="projectOptions"
          />
        </n-form-item>

        <n-form-item label="执行方式" path="executionType">
          <n-select
            v-model:value="editForm.executionType"
            placeholder="请选择执行方式"
            :options="executionTypeOptions"
            @update:value="handleEditExecutionTypeChange"
          />
        </n-form-item>

        <n-form-item
          v-if="editForm.executionType === 'scheduled'"
          label="定时时间"
          path="scheduleTime"
        >
          <n-input
            v-model:value="editForm.scheduleTime"
            placeholder="请输入定时执行时间 (如: 09:00)"
          />
        </n-form-item>

        <n-form-item label="选择用例">
          <n-button @click="handleEditSelectCases" type="primary" dashed>
            选择用例 (已选 {{ editForm.selectedCases.length }} 个)
          </n-button>
        </n-form-item>
      </n-form>

      <template #action>
        <n-space>
          <n-button @click="closeEditModal">取消</n-button>
          <n-button
            @click="submitEditForm"
            type="primary"
            :loading="editLoading"
          >
            确定
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 使用共享的设置弹窗组件 -->
    <SettingsModal />
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, computed, h } from "vue";
import { DataTableColumns } from "naive-ui";
import {
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NButton,
  NSpace,
  NModal,
  NTag,
  NCard,
  NGrid,
  NGridItem,
  NDivider,
  NCheckbox,
  NSwitch,
  NText,
  useMessage,
  useDialog,
  FormInst,
} from "naive-ui";
import axios from "axios";
import SettingsModal from "./SettingsModal.vue";
import { useSettings } from "../composables/useSettings";

interface TaskData {
  id: number;
  name: string;
  description: string;
  project: string;
  executionType: "manual" | "scheduled";
  scheduleTime?: string;
  selectedCases: number[];
  createTime: string;
  status: "active" | "inactive";
}

interface CaseData {
  id: number;
  name: string;
  project: string;
  module: string;
  type: string;
  environment: string;
}

interface CaseSearchForm {
  name: string;
  project: string | null;
  module: string;
  type: string | null;
  environment: string | null;
}

interface SearchForm {
  name: string;
  scheduleTime: string;
  project: string | null;
  executionType: string | null;
}

interface AddForm {
  name: string;
  description: string;
  project: string | null;
  executionType: "manual" | "scheduled" | null;
  scheduleTime: string;
  selectedCases: number[];
}

export default defineComponent({
  name: "TaskList",
  components: {
    NDataTable,
    NForm,
    NFormItem,
    NInput,
    NSelect,
    NButton,
    NSpace,
    NModal,
    NTag,
    NCard,
    NGrid,
    NGridItem,
    NDivider,
    NCheckbox,
    NSwitch,
    NText,
    SettingsModal,
  },
  setup() {
    const message = useMessage();
    const dialog = useDialog();

    // 使用共享的设置逻辑
    const { handleSettings } = useSettings(message);

    // 添加调试日志
    console.log("ProjectList组件加载完成，handleSettings:", handleSettings);

    // 数据
    const data = ref<TaskData[]>([]);
    const availableCases = ref<CaseData[]>([]);

    // 搜索相关
    const searchFormRef = ref<FormInst | null>(null);
    const searchForm = ref<SearchForm>({
      name: "",
      scheduleTime: "",
      project: null,
      executionType: null,
    });

    // 用例搜索相关
    const caseSearchFormRef = ref<FormInst | null>(null);
    const caseSearchForm = ref<CaseSearchForm>({
      name: "",
      project: null,
      module: "",
      type: null,
      environment: null,
    });

    // 添加任务相关
    const showAddModal = ref(false);
    const addFormRef = ref<FormInst | null>(null);
    const addLoading = ref(false);
    const addForm = ref<AddForm>({
      name: "",
      description: "",
      project: null,
      executionType: null,
      scheduleTime: "",
      selectedCases: [],
    });

    // 编辑任务相关
    const showEditModal = ref(false);
    const editFormRef = ref<FormInst | null>(null);
    const editLoading = ref(false);
    const currentEditId = ref<number | null>(null);
    const editForm = ref<AddForm>({
      name: "",
      description: "",
      project: null,
      executionType: null,
      scheduleTime: "",
      selectedCases: [],
    });

    // 选择用例相关
    const showCaseSelectModal = ref(false);
    const selectedCaseKeys = ref<number[]>([]);
    const isEditingCases = ref(false);

    // 表格列配置
    const columns: DataTableColumns<TaskData> = [
      {
        title: "任务ID",
        key: "id",
        width: 80,
        align: "center",
      },
      {
        title: "任务名称",
        key: "name",
        width: 200,
        ellipsis: {
          tooltip: true,
        },
      },
      {
        title: "描述",
        key: "description",
        width: 250,
        ellipsis: {
          tooltip: true,
        },
      },
      {
        title: "执行方式",
        key: "executionType",
        width: 120,
        align: "center",
        render(row) {
          return h(
            NTag,
            {
              type: row.executionType === "scheduled" ? "info" : "default",
              size: "small",
            },
            {
              default: () =>
                row.executionType === "scheduled" ? "定时执行" : "手动执行",
            }
          );
        },
      },
      {
        title: "定时时间",
        key: "scheduleTime",
        width: 120,
        align: "center",
        render(row) {
          return row.scheduleTime || "-";
        },
      },
      {
        title: "所属项目",
        key: "project",
        width: 120,
        align: "center",
      },
      {
        title: "用例数量",
        key: "caseCount",
        width: 100,
        align: "center",
        render(row) {
          return `${row.selectedCases.length} 个`;
        },
      },
      {
        title: "操作",
        key: "actions",
        width: 200,
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
                    type: "primary",
                    onClick: () => handleEdit(row.id),
                  },
                  { default: () => "编辑" }
                ),
                h(
                  NButton,
                  {
                    size: "small",
                    type: "success",
                    onClick: () => handleExecute(row.id),
                  },
                  { default: () => "执行" }
                ),
                h(
                  NButton,
                  {
                    size: "small",
                    type: "error",
                    onClick: () => handleDelete(row.id),
                  },
                  { default: () => "删除" }
                ),
              ],
            }
          );
        },
      },
    ];

    // 用例选择表格列配置
    const caseColumns: DataTableColumns<CaseData> = [
      {
        type: "selection",
      },
      {
        title: "用例ID",
        key: "id",
        width: 80,
        align: "center",
      },
      {
        title: "用例名称",
        key: "name",
        width: 200,
        ellipsis: {
          tooltip: true,
        },
      },
      {
        title: "所属项目",
        key: "project",
        width: 120,
        align: "center",
      },
      {
        title: "所属模块",
        key: "module",
        width: 150,
        ellipsis: {
          tooltip: true,
        },
      },
      {
        title: "类型",
        key: "type",
        width: 120,
        align: "center",
      },
      {
        title: "环境",
        key: "environment",
        width: 120,
        align: "center",
      },
    ];

    // 选项配置
    const projectOptions = ref<{ label: string; value: string }[]>([]);

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

    const executionTypeOptions = [
      { label: "手动执行", value: "manual" },
      { label: "定时执行", value: "scheduled" },
    ];

    const typeOptions = [
      { label: "主流程", value: "主流程" },
      { label: "分流程", value: "分流程" },
      { label: "异常流程", value: "异常流程" },
      { label: "UI验证", value: "UI验证" },
    ];

    const environmentOptions = [
      { label: "生产环境", value: "生产环境" },
      { label: "测试环境", value: "测试环境" },
      { label: "压测环境", value: "压测环境" },
    ];

    // 表单验证规则
    const addRules = {
      name: {
        required: true,
        message: "请输入任务名称",
        trigger: "blur",
      },
      project: {
        required: true,
        message: "请选择所属项目",
        trigger: "change",
      },
      executionType: {
        required: true,
        message: "请选择执行方式",
        trigger: "change",
      },
      scheduleTime: {
        required: true,
        message: "请输入定时时间",
        trigger: "blur",
      },
    };

    // 计算属性：过滤后的数据
    const filteredData = computed(() => {
      let result = data.value;

      if (searchForm.value.name) {
        result = result.filter((item) =>
          item.name.toLowerCase().includes(searchForm.value.name.toLowerCase())
        );
      }

      if (searchForm.value.scheduleTime) {
        result = result.filter((item) =>
          item.scheduleTime?.includes(searchForm.value.scheduleTime)
        );
      }

      if (searchForm.value.project) {
        result = result.filter(
          (item) => item.project === searchForm.value.project
        );
      }

      if (searchForm.value.executionType) {
        result = result.filter(
          (item) => item.executionType === searchForm.value.executionType
        );
      }

      return result;
    });

    // 计算属性：过滤后的用例数据
    const filteredCases = computed(() => {
      let result = availableCases.value;

      if (caseSearchForm.value.name) {
        result = result.filter((item) =>
          item.name
            .toLowerCase()
            .includes(caseSearchForm.value.name.toLowerCase())
        );
      }

      if (caseSearchForm.value.project) {
        result = result.filter(
          (item) => item.project === caseSearchForm.value.project
        );
      }

      if (caseSearchForm.value.module) {
        result = result.filter((item) =>
          item.module
            .toLowerCase()
            .includes(caseSearchForm.value.module.toLowerCase())
        );
      }

      if (caseSearchForm.value.type) {
        result = result.filter(
          (item) => item.type === caseSearchForm.value.type
        );
      }

      if (caseSearchForm.value.environment) {
        result = result.filter(
          (item) => item.environment === caseSearchForm.value.environment
        );
      }

      return result;
    });

    // 分页配置
    const pagination = {
      pageSize: 10,
    };

    // 获取任务列表
    const fetchTasks = async () => {
      try {
        const response = await axios.get("/api/tasks");
        data.value = response.data;
        console.log("获取到的任务数据:", data.value);
      } catch (error) {
        console.error("获取任务列表失败:", error);
        message.error("获取任务列表失败");
      }
    };

    // 获取可用用例列表
    const fetchAvailableCases = async () => {
      try {
        const response = await axios.get("/api/data");
        availableCases.value = response.data.map((item: any) => ({
          id: item.id,
          name: item.name,
          project: item.project,
          module: item.module,
          type: item.type,
          environment: item.environment || "测试环境", // 默认为测试环境
        }));
      } catch (error) {
        console.error("获取用例列表失败:", error);
        message.error("获取用例列表失败");
      }
    };

    // 搜索处理
    const handleSearch = () => {
      // 过滤逻辑在computed中处理
    };

    // 重置搜索
    const handleReset = () => {
      searchForm.value = {
        name: "",
        scheduleTime: "",
        project: null,
        executionType: null,
      };
    };

    // 用例搜索处理
    const handleCaseSearch = () => {
      // 过滤逻辑在computed中处理
    };

    // 重置用例搜索
    const handleCaseSearchReset = () => {
      caseSearchForm.value = {
        name: "",
        project: null,
        module: "",
        type: null,
        environment: null,
      };
    };

    // 添加任务
    const handleAddTask = () => {
      showAddModal.value = true;
      addForm.value = {
        name: "",
        description: "",
        project: null,
        executionType: null,
        scheduleTime: "",
        selectedCases: [],
      };
    };

    // 执行方式变更处理
    const handleExecutionTypeChange = (value: string) => {
      if (value !== "scheduled") {
        addForm.value.scheduleTime = "";
      }
    };

    // 编辑时执行方式变更处理
    const handleEditExecutionTypeChange = (value: string) => {
      if (value !== "scheduled") {
        editForm.value.scheduleTime = "";
      }
    };

    // 选择用例
    const handleSelectCases = () => {
      selectedCaseKeys.value = [...addForm.value.selectedCases];
      isEditingCases.value = false;
      showCaseSelectModal.value = true;
    };

    // 编辑时选择用例
    const handleEditSelectCases = () => {
      selectedCaseKeys.value = [...editForm.value.selectedCases];
      isEditingCases.value = true;
      showCaseSelectModal.value = true;
    };

    // 确认用例选择
    const confirmCaseSelection = () => {
      if (isEditingCases.value) {
        editForm.value.selectedCases = [...selectedCaseKeys.value];
      } else {
        addForm.value.selectedCases = [...selectedCaseKeys.value];
      }
      showCaseSelectModal.value = false;
    };

    // 关闭用例选择弹窗
    const closeCaseSelectModal = () => {
      showCaseSelectModal.value = false;
      selectedCaseKeys.value = [];
    };

    // 关闭添加弹窗
    const closeAddModal = () => {
      showAddModal.value = false;
      addForm.value = {
        name: "",
        description: "",
        project: null,
        executionType: null,
        scheduleTime: "",
        selectedCases: [],
      };
    };

    // 提交添加表单
    const submitAddForm = async () => {
      try {
        await addFormRef.value?.validate();

        if (
          addForm.value.executionType === "scheduled" &&
          !addForm.value.scheduleTime
        ) {
          message.error("请输入定时执行时间");
          return;
        }

        if (addForm.value.selectedCases.length === 0) {
          message.error("请至少选择一个用例");
          return;
        }

        addLoading.value = true;

        // 调用API保存任务
        const response = await axios.post("/api/tasks", {
          name: addForm.value.name,
          description: addForm.value.description,
          project: addForm.value.project,
          executionType: addForm.value.executionType,
          scheduleTime: addForm.value.scheduleTime,
          selectedCases: addForm.value.selectedCases,
        });

        if (response.data.message) {
          message.success("添加任务成功");
          closeAddModal();
          // 重新获取任务列表
          await fetchTasks();
        } else {
          message.error(response.data.error || "添加任务失败");
        }
      } catch (error) {
        console.error("添加任务失败:", error);
        message.error("添加任务失败");
      } finally {
        addLoading.value = false;
      }
    };

    // 编辑任务
    const handleEdit = (id: number) => {
      const task = data.value.find((t) => t.id === id);
      if (task) {
        currentEditId.value = id;
        editForm.value = {
          name: task.name,
          description: task.description,
          project: task.project,
          executionType: task.executionType,
          scheduleTime: task.scheduleTime || "",
          selectedCases: [...task.selectedCases],
        };
        showEditModal.value = true;
      }
    };

    // 关闭编辑弹窗
    const closeEditModal = () => {
      showEditModal.value = false;
      currentEditId.value = null;
      editForm.value = {
        name: "",
        description: "",
        project: null,
        executionType: null,
        scheduleTime: "",
        selectedCases: [],
      };
    };

    // 提交编辑表单
    const submitEditForm = async () => {
      try {
        await editFormRef.value?.validate();

        if (
          editForm.value.executionType === "scheduled" &&
          !editForm.value.scheduleTime
        ) {
          message.error("请输入定时执行时间");
          return;
        }

        if (editForm.value.selectedCases.length === 0) {
          message.error("请至少选择一个用例");
          return;
        }

        editLoading.value = true;

        // 调用API更新任务
        const response = await axios.put(
          `/api/tasks/${currentEditId.value}`,
          {
            name: editForm.value.name,
            description: editForm.value.description,
            project: editForm.value.project,
            executionType: editForm.value.executionType,
            scheduleTime: editForm.value.scheduleTime,
            selectedCases: editForm.value.selectedCases,
          }
        );

        if (response.data.message) {
          message.success("编辑任务成功");
          closeEditModal();
          // 重新获取任务列表
          await fetchTasks();
        } else {
          message.error(response.data.error || "编辑任务失败");
        }
      } catch (error) {
        console.error("编辑任务失败:", error);
        message.error("编辑任务失败");
      } finally {
        editLoading.value = false;
      }
    };

    // 执行任务
    const handleExecute = (id: number) => {
      const task = data.value.find((t) => t.id === id);
      if (task) {
        dialog.info({
          title: "执行任务",
          content: `确定要执行任务"${task.name}"吗？\n该任务包含 ${task.selectedCases.length} 个用例。`,
          positiveText: "确定",
          negativeText: "取消",
          onPositiveClick: async () => {
            const loadingMessage = message.loading("正在执行任务，请稍候...", {
              duration: 0,
            });
            try {
              console.log(`开始执行任务 ID: ${id}`);

              // 调用API执行任务
              const response = await axios.post(
                `/api/tasks/${id}/execute`
              );

              console.log("任务执行响应:", response.data);

              if (response.data.success || response.data.message) {
                const report = response.data.report;
                if (report && report.pass_rate !== undefined) {
                  message.success(
                    `任务执行完成！共执行 ${
                      response.data.caseCount || task.selectedCases.length
                    } 个用例，通过率: ${report.pass_rate}%`
                  );
                } else {
                  message.success("任务执行成功");
                }
              } else {
                message.error(response.data.error || "任务执行失败");
              }
            } catch (error) {
              console.error("执行任务失败:", error);
              message.error("执行任务失败，请检查网络连接和后端服务");
            } finally {
              loadingMessage.destroy();
            }
          },
        });
      }
    };

    // 删除任务
    const handleDelete = (id: number) => {
      const task = data.value.find((t) => t.id === id);
      if (task) {
        dialog.warning({
          title: "删除任务",
          content: `确定要删除任务"${task.name}"吗？\n删除后将无法恢复。`,
          positiveText: "确定删除",
          negativeText: "取消",
          onPositiveClick: async () => {
            try {
              // 调用API删除任务
              const response = await axios.delete(
                `/api/tasks/${id}`
              );

              if (response.data.message) {
                message.success("任务删除成功");
                // 重新获取任务列表
                await fetchTasks();
              } else {
                message.error(response.data.error || "任务删除失败");
              }
            } catch (error) {
              console.error("删除任务失败:", error);
              message.error("删除任务失败");
            }
          },
        });
      }
    };

    // 组件挂载时获取数据
    onMounted(() => {
      fetchTasks();
      fetchAvailableCases();
      fetchProjects();
    });

    return {
      // 数据
      data,
      filteredData,
      availableCases,
      filteredCases,

      // 搜索
      searchFormRef,
      searchForm,
      handleSearch,
      handleReset,

      // 用例搜索
      caseSearchFormRef,
      caseSearchForm,
      handleCaseSearch,
      handleCaseSearchReset,

      // 表格
      columns,
      caseColumns,
      pagination,

      // 添加任务
      showAddModal,
      addFormRef,
      addForm,
      addRules,
      addLoading,
      handleAddTask,
      closeAddModal,
      submitAddForm,
      handleExecutionTypeChange,

      // 编辑任务
      showEditModal,
      editFormRef,
      editForm,
      editLoading,
      handleEdit,
      closeEditModal,
      submitEditForm,
      handleEditExecutionTypeChange,

      // 用例选择
      showCaseSelectModal,
      selectedCaseKeys,
      handleSelectCases,
      handleEditSelectCases,
      confirmCaseSelection,
      closeCaseSelectModal,

      // 其他
      projectOptions,
      executionTypeOptions,
      typeOptions,
      environmentOptions,
      handleExecute,
      handleDelete,

      // 设置相关 - 使用共享设置
      handleSettings,
    };
  },
});
</script>

<style scoped>
.task-list-container {
  padding: 16px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* 搜索区域样式 */
.search-area,
.case-search-area {
  position: relative;
  margin-bottom: 20px;
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

.search-items-wrapper {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  width: 100%;
}

.search-buttons-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  flex-shrink: 0;
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

/* 操作区域样式 */
.operation-area {
  background: #fff;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #e6e6e6;
}

.operation-left {
  display: flex;
  align-items: center;
}

.total-text {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.operation-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 总数显示 */
.total-count {
  margin-top: 16px;
  color: #909399;
  font-size: 14px;
  text-align: right;
}

/* 弹窗表单样式 */
.modal-form {
  :deep(.n-form-item) {
    margin-bottom: 20px;
  }

  :deep(.n-input) {
    width: 100%;
  }

  :deep(.n-select) {
    width: 100%;
  }

  :deep(.n-input-textarea) {
    width: 100%;
  }
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .search-items-wrapper {
    gap: 12px;
  }

  .search-form :deep(.n-select),
  .search-form :deep(.n-input) {
    width: 160px;
  }
}

@media (max-width: 768px) {
  .search-items-wrapper {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .search-buttons-wrapper {
    margin-left: 0;
    width: 100%;
    justify-content: flex-end;
  }

  .search-form :deep(.n-form-item) {
    width: 100%;
    justify-content: space-between;
  }

  .search-form :deep(.n-form-item-label) {
    min-width: 80px;
  }

  .search-form :deep(.n-select),
  .search-form :deep(.n-input) {
    width: 200px;
  }

  .operation-area {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .operation-left,
  .operation-right {
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .task-list-container {
    padding: 12px;
  }

  .search-area {
    padding: 12px;
  }

  .search-form :deep(.n-select),
  .search-form :deep(.n-input) {
    width: 100%;
  }

  .search-buttons-wrapper {
    gap: 8px;
  }

  .search-buttons-wrapper .n-button {
    flex: 1;
  }
}
</style>
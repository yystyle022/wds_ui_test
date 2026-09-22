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
          <n-form-item label="元素名称" :show-label="true">
            <n-input
              v-model:value="searchForm.elementName"
              placeholder="请输入元素名称"
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

    <!-- 操作区域 -->
    <div class="operation-area">
      <div class="operation-left">
        <n-p>已选中 {{ checkedRowKeys.length }} 行</n-p>
      </div>
      <div class="operation-right">
        <n-button type="primary" @click="handleAdd" style="margin-right: 8px">
          添加元素
        </n-button>
        <n-button @click="batchDelete" type="error">批量删除</n-button>
      </div>
    </div>

    <!-- 添加元素弹窗 -->
    <n-modal
      v-model:show="showAddModal"
      preset="dialog"
      title="添加元素"
      style="width: 600px"
    >
      <n-form
        ref="addFormRef"
        :model="addForm"
        :rules="rules"
        label-placement="left"
        label-width="100"
        class="modal-form"
      >
        <n-form-item label="所属项目" path="project">
          <n-select
            v-model:value="addForm.project"
            :options="projectOptions"
            placeholder="请选择所属项目"
            clearable
          />
        </n-form-item>
        <n-form-item label="所属模块" path="module">
          <n-input
            v-model:value="addForm.module"
            placeholder="请输入模块名称"
          />
        </n-form-item>
        <n-form-item label="页面" path="page">
          <n-input v-model:value="addForm.page" placeholder="请输入页面名称" />
        </n-form-item>
        <n-form-item label="元素名称" path="elementName">
          <n-input
            v-model:value="addForm.elementName"
            placeholder="请输入元素名称"
          />
        </n-form-item>
        <n-form-item label="定位方式" path="locateType">
          <n-select
            v-model:value="addForm.locateType"
            :options="locateTypeOptions"
            placeholder="请选择定位方式"
          />
        </n-form-item>
        <n-form-item :label="getLocateLabel(addForm.locateType)" path="xpath">
          <n-input
            v-model:value="addForm.xpath"
            type="textarea"
            :placeholder="getLocatePlaceholder(addForm.locateType)"
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input
            v-model:value="addForm.description"
            type="textarea"
            placeholder="请输入元素描述（可选）"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="closeAddModal">取消</n-button>
          <n-button type="primary" @click="submitAddForm">确定</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 编辑元素弹窗 -->
    <n-modal
      v-model:show="showEditModal"
      preset="dialog"
      title="编辑元素"
      style="width: 600px"
    >
      <n-form
        ref="editFormRef"
        :model="editForm"
        :rules="rules"
        label-placement="left"
        label-width="100"
        class="modal-form"
      >
        <n-form-item label="所属项目" path="project">
          <n-select
            v-model:value="editForm.project"
            :options="projectOptions"
            placeholder="请选择所属项目"
            clearable
          />
        </n-form-item>
        <n-form-item label="所属模块" path="module">
          <n-input
            v-model:value="editForm.module"
            placeholder="请输入模块名称"
          />
        </n-form-item>
        <n-form-item label="页面" path="page">
          <n-input v-model:value="editForm.page" placeholder="请输入页面名称" />
        </n-form-item>
        <n-form-item label="元素名称" path="elementName">
          <n-input
            v-model:value="editForm.elementName"
            placeholder="请输入元素名称"
          />
        </n-form-item>
        <n-form-item label="定位方式" path="locateType">
          <n-select
            v-model:value="editForm.locateType"
            :options="locateTypeOptions"
            placeholder="请选择定位方式"
          />
        </n-form-item>
        <n-form-item :label="getLocateLabel(editForm.locateType)" path="xpath">
          <n-input
            v-model:value="editForm.xpath"
            type="textarea"
            :placeholder="getLocatePlaceholder(editForm.locateType)"
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input
            v-model:value="editForm.description"
            type="textarea"
            placeholder="请输入元素描述（可选）"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="closeEditModal">取消</n-button>
          <n-button type="primary" @click="submitEditForm">确定</n-button>
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
      <n-text>共计 {{ data.length }} 个元素</n-text>
    </div>
  </div>
</template>

<script lang="ts">
import type { DataTableColumns, DataTableRowKey } from "naive-ui";
import { defineComponent, ref, onMounted, h, Fragment } from "vue";
import axios from "axios";
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
  FormInst,
  useDialog,
  useMessage,
} from "naive-ui";

interface ElementData {
  id: number;
  project: string;
  module: string;
  elementName: string;
  xpath: string;
  locate_type?: string;
  description?: string;
}

interface ElementForm {
  project: string | null;
  module: string;
  page: string;
  elementName: string;
  xpath: string;
  locateType: string;
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
  },

  setup() {
    const dialog = useDialog();
    const message = useMessage();
    const checkedRowKeysRef = ref<DataTableRowKey[]>([]);
    const data = ref<ElementData[]>([]);
    const searchForm = ref<{
      project: string | null;
      module: string;
      page: string;
      elementName: string;
    }>({
      project: null,
      module: "",
      page: "",
      elementName: "",
    });

    // 添加弹窗相关
    const showAddModal = ref(false);
    const addFormRef = ref<FormInst | null>(null);
    const addForm = ref<ElementForm>({
      project: null,
      module: "",
      page: "",
      elementName: "",
      xpath: "",
      locateType: "xpath",
      description: "",
    });

    // 编辑弹窗相关
    const showEditModal = ref(false);
    const editFormRef = ref<FormInst | null>(null);
    const currentEditId = ref<number | null>(null);
    const editForm = ref<ElementForm>({
      project: null,
      module: "",
      page: "",
      elementName: "",
      xpath: "",
      locateType: "xpath",
      description: "",
    });

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

    const rules = {
      project: { required: true, message: "请选择所属项目", trigger: "blur" },
      module: { required: true, message: "请输入模块", trigger: "blur" },
      elementName: {
        required: true,
        message: "请输入元素名称",
        trigger: "blur",
      },
      xpath: { required: true, message: "请输入定位内容", trigger: "blur" },
    };

    // 元素定位方式：XPath 或 CSS，规则一样，仅展示文案区分
    const locateTypeOptions = [
      { label: "XPath", value: "xpath" },
      { label: "CSS", value: "css" },
    ];

    const getLocateLabel = (locateType?: string) =>
      locateType === "css" ? "CSS选择器" : "XPath";

    const getLocatePlaceholder = (locateType?: string) =>
      locateType === "css" ? "请输入元素的CSS选择器" : "请输入元素的XPath";

    const fetchData = async () => {
      try {
        const params = {
          project: searchForm.value.project,
          module: searchForm.value.module,
          elementName: searchForm.value.elementName,
        };
        const response = await axios.get("/api/elements", {
          params,
        });
        // 倒序排列元素列表
        data.value = response.data.reverse();
      } catch (error) {
        console.error("Error fetching elements:", error);
        message.error("获取元素数据失败，请检查网络或服务器状态");
      }
    };

    const handleSearch = () => {
      fetchData();
    };

    const handleReset = () => {
      searchForm.value = {
        project: null,
        module: "",
        page: "",
        elementName: "",
      };
      fetchData();
    };

    const handleCheck = (rowKeys: DataTableRowKey[]) => {
      checkedRowKeysRef.value = rowKeys;
    };

    const handleAdd = () => {
      showAddModal.value = true;
    };

    const closeAddModal = () => {
      showAddModal.value = false;
      addForm.value = {
        project: null,
        module: "",
        elementName: "",
        xpath: "",
        locateType: "xpath",
        description: "",
      };
    };

    const submitAddForm = async () => {
      try {
        await addFormRef.value?.validate();

        const elementData = {
          project: addForm.value.project,
          module: addForm.value.module,
          page: addForm.value.page,
          elementName: addForm.value.elementName,
          xpath: addForm.value.xpath,
          locate_type: addForm.value.locateType,
          description: addForm.value.description,
        };

        const response = await axios.post("/api/elements", elementData);

        if (response.data.message) {
          message.success("元素添加成功");
          closeAddModal();
          fetchData();
        } else {
          message.error(response.data.error || "添加元素失败");
        }
      } catch (error) {
        console.error("添加元素失败:", error);
        message.error("添加元素失败，请检查表单内容");
      }
    };

    const handleEdit = async (id: number) => {
      try {
        const response = await axios.get(`/api/elements/${id}`);
        currentEditId.value = id;

        editForm.value = {
          project: response.data.project || null,
          module: response.data.module || "",
          page: response.data.page || "",
          elementName: response.data.elementName || "",
          xpath: response.data.xpath || "",
          locateType: response.data.locate_type || "xpath",
          description: response.data.description || "",
        };
        showEditModal.value = true;
      } catch (error) {
        console.error("获取元素详情失败:", error);
        message.error("获取元素详情失败");
      }
    };

    const closeEditModal = () => {
      showEditModal.value = false;
      currentEditId.value = null;
      editForm.value = {
        project: null,
        module: "",
        elementName: "",
        xpath: "",
        locateType: "xpath",
        description: "",
      };
    };

    // 元素同步更新功能
    const syncTestCasesAfterElementUpdate = async (
      elementId: number,
      newXPath: string,
      newElementName: string,
      originalXPath?: string // 添加原始xpath参数
    ) => {
      try {
        // 获取所有用例数据
        const response = await axios.get("/api/data");
        const allTestCases = response.data || [];

        // 调试信息：显示所有用例和步骤
        console.log(
          `开始同步 - 元素ID: ${elementId}, 原始XPath: "${originalXPath}", 新XPath: "${newXPath}"`
        );
        console.log(`共找到 ${allTestCases.length} 个用例`);

        allTestCases.forEach((testCase: any, caseIndex: number) => {
          console.log(`用例 ${caseIndex + 1}: ${testCase.name}`);
          (testCase.testcase_step || []).forEach(
            (step: any, stepIndex: number) => {
              console.log(
                `  步骤 ${stepIndex + 1}: ${
                  step.describe || "无描述"
                }, XPath: "${step.xpath || "无XPath"}", element_id: ${
                  step.element_id || "无element_id"
                }`
              );
            }
          );
        });

        const updatedCases: any[] = [];

        // 遍历所有用例，查找使用了该元素的步骤
        for (const testCase of allTestCases) {
          let hasUpdates = false;
          const updatedSteps = (testCase.testcase_step || []).map(
            (step: any) => {
              // 优先通过element_id匹配（与DataTableComponent.vue保持一致）
              if (step.element_id === elementId) {
                hasUpdates = true;
                console.log(
                  `找到匹配的步骤 - 用例: ${testCase.name}, 步骤: ${step.step}, 元素ID: ${step.element_id}`
                );
                return {
                  ...step,
                  xpath: newXPath,
                  elementName: newElementName,
                };
              }
              // 兼容旧数据：通过原始xpath匹配（仅当没有element_id时）
              else if (
                !step.element_id &&
                originalXPath &&
                step.xpath === originalXPath
              ) {
                hasUpdates = true;
                console.log(
                  `找到匹配的步骤（旧数据） - 用例: ${testCase.name}, 步骤: ${step.step}, 原xpath: ${step.xpath}`
                );
                return {
                  ...step,
                  xpath: newXPath,
                  elementName: newElementName,
                  element_id: elementId, // 为旧用例添加element_id，便于后续同步
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
          await Promise.all(
            updatedCases.map((testCase: any) =>
              axios.put(`/api/testcase/${testCase.id}`, {
                project: testCase.project,
                module: testCase.module,
                name: testCase.name,
                type: testCase.type,
                environment: testCase.environment,
                testcase_step: testCase.testcase_step, // 直接使用更新后的步骤数据
              })
            )
          );

          message.success(`已同步更新 ${updatedCases.length} 个相关用例`);
        } else {
          console.log(
            `没有找到使用元素ID ${elementId} 或原始XPath "${originalXPath}" 的用例`
          );
          message.info("没有找到使用该元素的用例");
        }
      } catch (error) {
        console.error("同步更新用例失败:", error);
        message.error("同步更新用例失败");
      }
    };

    const submitEditForm = async () => {
      try {
        await editFormRef.value?.validate();

        // 在更新元素前，先获取原始的xpath用于同步
        let originalXPath = "";
        if (currentEditId.value) {
          try {
            const originalResponse = await axios.get(
              `/api/elements/${currentEditId.value}`
            );
            originalXPath = originalResponse.data.xpath || "";
          } catch (error) {
            console.warn("获取原始xpath失败:", error);
          }
        }

        const elementData = {
          project: editForm.value.project,
          module: editForm.value.module,
          page: editForm.value.page,
          elementName: editForm.value.elementName,
          xpath: editForm.value.xpath,
          locate_type: editForm.value.locateType,
          description: editForm.value.description,
        };

        const response = await axios.put(
          `/api/elements/${currentEditId.value}`,
          elementData
        );

        if (response.data.message) {
          message.success("元素更新成功");

          // 同步更新相关用例，传递原始xpath
          if (currentEditId.value) {
            await syncTestCasesAfterElementUpdate(
              currentEditId.value,
              editForm.value.xpath,
              editForm.value.elementName,
              originalXPath // 传递原始xpath
            );
          }

          closeEditModal();
          fetchData();
        } else {
          message.error(response.data.error || "更新元素失败");
        }
      } catch (error) {
        console.error("更新元素失败:", error);
        message.error("更新元素失败，请检查表单内容");
      }
    };

    const handleDelete = (id: number) => {
      dialog.warning({
        title: "确认删除",
        content: "确定要删除这个元素吗？",
        positiveText: "确定",
        negativeText: "取消",
        onPositiveClick: async () => {
          try {
            const response = await axios.delete(`/api/elements/${id}`);
            if (response.data.message) {
              message.success("删除成功");
              fetchData();
            } else {
              message.error(response.data.error || "删除失败");
            }
          } catch (error) {
            console.error("删除失败:", error);
            // 显示后端返回的具体错误信息
            const errorMsg = error.response?.data?.error || "删除失败";
            message.error(errorMsg);
          }
        },
      });
    };

    const batchDelete = () => {
      if (checkedRowKeysRef.value.length === 0) {
        message.warning("请先勾选要删除的元素");
        return;
      }

      dialog.warning({
        title: "确认删除",
        content: `确定要删除选中的 ${checkedRowKeysRef.value.length} 个元素吗？`,
        positiveText: "确定",
        negativeText: "取消",
        onPositiveClick: async () => {
          try {
            const response = await axios.delete("/api/elements/batch", {
              data: { ids: checkedRowKeysRef.value },
            });
            if (response.data.message) {
              message.success("批量删除成功");
              checkedRowKeysRef.value = [];
              fetchData();
            } else {
              message.error(response.data.error || "批量删除失败");
            }
          } catch (error) {
            console.error("批量删除失败:", error);
            // 显示后端返回的具体错误信息
            const errorMsg = error.response?.data?.error || "批量删除失败";
            message.error(errorMsg);
          }
        },
      });
    };

    function createColumns(): DataTableColumns<ElementData> {
      return [
        { type: "selection" },
        { title: "ID", key: "id", align: "center", width: 60 },
        { title: "所属项目", key: "project", align: "center", width: 120 },
        { title: "所属模块", key: "module", align: "center", width: 120 },
        { title: "元素名称", key: "elementName", align: "center", width: 150 },
        {
          title: "元素种类",
          key: "locate_type",
          align: "center",
          width: 90,
          render(row) {
            return row.locate_type === "css" ? "CSS" : "XPATH";
          },
        },
        {
          title: "XPath",
          key: "xpath",
          align: "center",
          width: 300,
          ellipsis: {
            tooltip: true,
          },
        },
        {
          title: "描述",
          key: "description",
          align: "center",
          width: 200,
          ellipsis: {
            tooltip: true,
          },
        },
        {
          title: "操作",
          key: "action",
          align: "center",
          width: 150,
          render(row) {
            return h(Fragment, null, [
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

    onMounted(() => {
      fetchData();
      fetchProjects();
    });

    return {
      data,
      columns: createColumns(),
      checkedRowKeys: checkedRowKeysRef,
      pagination: { pageSize: 10 },
      rowKey: (row: ElementData) => row.id,
      handleCheck,
      searchForm,
      handleSearch,
      handleReset,
      projectOptions,
      showAddModal,
      addFormRef,
      addForm,
      rules,
      locateTypeOptions,
      getLocateLabel,
      getLocatePlaceholder,
      handleAdd,
      closeAddModal,
      submitAddForm,
      showEditModal,
      editFormRef,
      editForm,
      currentEditId,
      handleEdit,
      closeEditModal,
      submitEditForm,
      handleDelete,
      batchDelete,
    };
  },
});
</script>

<style scoped>
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
</style>

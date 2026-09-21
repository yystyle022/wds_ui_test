<template>
  <div class="testcase-form-container">
    <n-space vertical :size="16">
      <n-space justify="space-between" align="center">
        <h2>{{ isEditMode ? "编辑用例" : "新建用例" }}</h2>
        <n-button @click="handleCancel">返回列表</n-button>
      </n-space>

      <n-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-placement="left"
        label-width="100"
        class="modal-form"
      >
        <n-grid :cols="3" :x-gap="16">
          <n-form-item-gi label="所属项目" path="project">
            <n-select
              v-model:value="form.project"
              :options="projectOptions"
              placeholder="请选择所属项目"
              clearable
            />
          </n-form-item-gi>
          <n-form-item-gi label="所属模块" path="module">
            <n-input v-model:value="form.module" placeholder="请输入模块名称" />
          </n-form-item-gi>
          <n-form-item-gi label="页面" path="page">
            <n-input v-model:value="form.page" placeholder="请输入页面名称" />
          </n-form-item-gi>
          <n-form-item-gi label="用例概述" path="name">
            <n-input v-model:value="form.name" placeholder="请输入用例概述" />
          </n-form-item-gi>
          <n-form-item-gi label="用例类型" path="type">
            <n-select
              v-model:value="form.type"
              :options="typeOptions"
              placeholder="请选择用例类型"
              clearable
            />
          </n-form-item-gi>
        </n-grid>
        <n-form-item label="用例步骤" path="steps">
          <div class="steps-scroll-container">
            <div class="steps-container">
              <div
                v-for="(step, index) in form.steps"
                :key="index"
                class="step-row"
                :class="{
                  'has-input': step.action === 'input',
                  'has-get-text': step.action === 'get_element_text',
                  'has-verify-var': step.action === 'verify_variable_value',
                  'has-verify': step.action === 'verify_element_value',
                  'has-locate': isLocateOnlyStep(step.action),
                  'is-dragging': dragStepIndex === index,
                }"
                draggable="true"
                @dragstart="onStepDragStart(index)"
                @dragover.prevent
                @drop="onStepDrop(index)"
                @dragend="onStepDragEnd"
              >
                <div class="step-number">
                  <span class="drag-handle" title="拖动调整步骤顺序">⠿</span>
                  步骤 {{ index + 1 }}
                </div>

                <!-- 操作选择框 -->
                <div class="step-field">
                  <label class="step-label">操作</label>
                  <n-select
                    v-model:value="step.action"
                    :options="actionOptions"
                    placeholder="请选择操作类型"
                  />
                </div>

                <!-- 定位方式选择框（二级菜单）- 仅需要定位元素的操作类型显示 -->
                <div v-if="needsLocateType(step.action)" class="step-field">
                  <label class="step-label">定位方式</label>
                  <n-select
                    v-model:value="step.locateType"
                    :options="locateTypeOptions"
                    placeholder="请选择定位方式"
                    @update:value="() => onLocateTypeChange(step)"
                  />
                </div>

                <!-- 网址或者元素 -->
                <div
                  v-if="
                    step.action !== 'reference_testcase' &&
                    step.action !== 'verify_variable_value'
                  "
                  class="step-field"
                >
                  <label class="step-label">网址或者元素</label>
                  <!-- 如果是需要定位元素的操作且定位方式为XPath/CSS，显示元素选择器和手动输入 -->
                  <div
                    v-if="
                      needsLocateType(step.action) &&
                      (!step.locateType ||
                        step.locateType === 'xpath' ||
                        step.locateType === 'css')
                    "
                    class="xpath-input-container"
                  >
                    <div class="xpath-selection">
                      <n-select
                        v-model:value="step.selectedElement"
                        :options="getElementOptions(step)"
                        placeholder="选择元素"
                        clearable
                        filterable
                        @search="(query) => handleElementSearch(step, query)"
                        @update:value="(value) => onElementSelect(step, value)"
                        style="margin-bottom: 8px"
                      />
                    </div>
                    <n-input
                      v-model:value="step.xpath"
                      :placeholder="
                        getXPathPlaceholder(step.action, step.locateType)
                      "
                    />
                    <div
                      v-if="step.selectedElement"
                      class="selected-element-name"
                      style="font-size: 12px; color: #666; margin-top: 4px"
                    >
                      元素: {{ step.selectedElement }}
                    </div>
                  </div>
                  <!-- 其他定位方式（CSS/文本定位）或URL类型，直接显示输入框 -->
                  <n-input
                    v-else
                    v-model:value="step.xpath"
                    :placeholder="
                      getXPathPlaceholder(step.action, step.locateType)
                    "
                  />
                </div>

                <!-- 引用其他用例专用字段 - 仅在操作类型为"引用其他用例"时显示 -->
                <div
                  v-if="step.action === 'reference_testcase'"
                  class="step-field"
                >
                  <label class="step-label">选择用例</label>
                  <n-select
                    v-model:value="step.referencedCaseId"
                    :options="getReferencedCaseOptions(step)"
                    placeholder="请选择同项目下的用例"
                    filterable
                    clearable
                    @focus="loadReferencedCaseOptions"
                  />
                  <div style="font-size: 12px; color: #666; margin-top: 4px">
                    只能引用当前用例所属项目下的其他用例，执行时会在此步骤位置插入被引用用例的完整步骤
                  </div>
                </div>

                <!-- 输入内容框 - 仅在操作类型为"输入内容"时显示 -->
                <div v-if="step.action === 'input'" class="step-field">
                  <label class="step-label">输入内容</label>
                  <n-input
                    v-model:value="step.inputValue"
                    placeholder="请输入要填写的内容"
                  />
                </div>

                <!-- 验证值框 - 仅在操作类型为"验证元素的值"时显示 -->
                <div
                  v-if="step.action === 'verify_element_value'"
                  class="step-field"
                >
                  <label class="step-label">期望值</label>
                  <n-input
                    v-model:value="step.expectedValue"
                    placeholder="请输入期望的值"
                  />
                </div>

                <!-- 变量名框 - 仅在操作类型为"获取元素的文案"时显示 -->
                <div
                  v-if="step.action === 'get_element_text'"
                  class="step-field"
                >
                  <label class="step-label">变量名</label>
                  <n-input
                    v-model:value="step.varName"
                    placeholder="请输入变量名（可选）"
                  />
                  <div style="font-size: 12px; color: #666; margin-top: 4px">
                    获取到的文案将保存到此变量中，后续步骤可使用 ${变量名} 引用
                  </div>
                </div>

                <!-- 验证变量名框 - 仅在操作类型为"验证获取的变量值"时显示 -->
                <div
                  v-if="step.action === 'verify_variable_value'"
                  class="step-field"
                >
                  <label class="step-label">变量名</label>
                  <n-input
                    v-model:value="step.varName"
                    placeholder="请输入要验证的变量名"
                  />
                </div>

                <!-- 预期值框 - 仅在操作类型为"验证获取的变量值"时显示 -->
                <div
                  v-if="step.action === 'verify_variable_value'"
                  class="step-field"
                >
                  <label class="step-label">预期值</label>
                  <n-input
                    v-model:value="step.expectedValue"
                    placeholder="请输入预期的变量值"
                  />
                </div>

                <!-- 步骤描述框 -->
                <div class="step-field">
                  <label class="step-label">步骤描述</label>
                  <n-input
                    v-model:value="step.description"
                    placeholder="请输入步骤描述"
                  />
                </div>

                <!-- 操作按钮组 -->
                <div class="step-actions">
                  <n-button
                    circle
                    quaternary
                    type="default"
                    size="small"
                    class="delete-btn"
                    @click="removeStep(index)"
                    title="删除此步骤"
                  >
                    <template #icon>
                      <span>×</span>
                    </template>
                  </n-button>
                  <n-button
                    type="primary"
                    size="small"
                    @click="insertStepAfter(index)"
                    title="在此步骤之后插入新步骤"
                    style="margin-left: 8px"
                  >
                    ＋插入
                  </n-button>
                </div>
              </div>
              <div class="add-step">
                <n-button type="primary" @click="addStep" class="add-step-btn">
                  添加步骤
                </n-button>
              </div>
            </div>
          </div>
        </n-form-item>
      </n-form>

      <n-space justify="end">
        <n-button @click="handleCancel">取消</n-button>
        <n-button type="primary" @click="submitForm">确定</n-button>
      </n-space>
    </n-space>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import axios from "axios";
import {
  NButton,
  NForm,
  NFormItem,
  NFormItemGi,
  NGrid,
  NInput,
  NSelect,
  NSpace,
  FormInst,
  useMessage,
} from "naive-ui";

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
  client: string;
  page: string;
  elementName: string;
  xpath: string;
  locate_type?: string;
  description?: string;
}

interface TestCaseFormData {
  project: string | null;
  module: string;
  page: string;
  name: string;
  type: string | null;
  steps: StepItem[];
}

export default defineComponent({
  name: "TestCaseForm",
  components: {
    NButton,
    NForm,
    NFormItem,
    NFormItemGi,
    NGrid,
    NInput,
    NSelect,
    NSpace,
  },

  setup() {
    const route = useRoute();
    const router = useRouter();
    const message = useMessage();

    const formRef = ref<FormInst | null>(null);

    // 路由带id参数即为编辑模式，否则为新建模式
    const currentEditId = computed<number | null>(() => {
      const idParam = route.params.id;
      return idParam ? Number(idParam) : null;
    });
    const isEditMode = computed(() => currentEditId.value !== null);

    const form = ref<TestCaseFormData>({
      project: null,
      module: "",
      page: "",
      name: "",
      type: null,
      steps: [],
    });

    const elementsData = ref<ElementData[]>([]);
    const stepElementOptions = ref(new Map<StepItem, any[]>());
    const projectOptions = ref<{ label: string; value: string }[]>([]);
    const allTestCasesForReference = ref<
      { id: number; name: string; project: string }[]
    >([]);

    const typeOptions = [
      { label: "主流程", value: "主流程" },
      { label: "分流程", value: "分流程" },
      { label: "异常流程", value: "异常流程" },
      { label: "UI验证", value: "UI验证" },
    ];

    const actionOptions = [
      { label: "引用其他用例", value: "reference_testcase" },
      { label: "打开网址", value: "open_url" },
      { label: "点击元素", value: "click" },
      { label: "输入内容", value: "input" },
      { label: "等待时长", value: "wait" },
      { label: "检查元素存在", value: "check_element_exists" },
      { label: "检查元素不存在", value: "check_element_not_exists" },
      { label: "获取元素的文案", value: "get_element_text" },
      { label: "验证元素的值", value: "verify_element_value" },
      { label: "验证获取的变量值", value: "verify_variable_value" },
    ];

    // 需要选择"定位方式"（二级菜单）的操作类型：XPath 或 其他定位方式
    const locateTypeOptions = [
      { label: "XPath", value: "xpath" },
      { label: "CSS选择器", value: "css" },
      { label: "文本定位", value: "text" },
    ];

    const needsLocateType = (action: string): boolean => {
      const locateActions = [
        "click",
        "input",
        "check_element_exists",
        "check_element_not_exists",
        "get_element_text",
        "verify_element_value",
      ];
      return locateActions.includes(action);
    };

    // 判断该步骤是否只需要"定位方式"这一个额外字段（不像input/get_element_text/verify_element_value还有其他专属字段）
    // 用于给步骤行匹配对应的CSS网格布局（has-locate）
    const isLocateOnlyStep = (action: string): boolean =>
      needsLocateType(action) &&
      !["input", "get_element_text", "verify_element_value"].includes(action);

    // 切换定位方式后，旧的定位值（XPath/CSS/文本）不再适用，清空输入框和已选元素
    const onLocateTypeChange = (step: StepItem) => {
      step.xpath = "";
      step.selectedElement = null;
      step.elementName = "";
      step.element_id = undefined;
      // 定位方式变了，之前缓存的元素选项（按旧定位方式过滤）已不适用，需清除
      stepElementOptions.value.delete(step);
    };

    const fetchElements = async () => {
      try {
        const response = await axios.get("/api/elements");
        elementsData.value = response.data;
      } catch (error) {
        console.error("获取元素列表失败:", error);
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

    const filteredElementOptions = (step: StepItem) => {
      const stepLocateType = step.locateType || "xpath";
      return elementsData.value
        .filter(
          (element) => (element.locate_type || "xpath") === stepLocateType
        )
        .map((element) => ({
          label: `${element.elementName} (${element.page})`,
          value: element.id.toString(),
          xpath: element.xpath,
          elementName: element.elementName,
          page: element.page,
          id: element.id,
        }));
    };

    const getElementOptions = (step: StepItem) => {
      if (stepElementOptions.value.has(step)) {
        return stepElementOptions.value.get(step) || [];
      }

      const allOptions = filteredElementOptions(step);

      if (step.selectedElement) {
        const selectedOption = allOptions.find(
          (option) => option.value === step.selectedElement
        );
        if (selectedOption) {
          const otherOptions = allOptions
            .filter((option) => option.value !== step.selectedElement)
            .slice(0, 4);
          return [selectedOption, ...otherOptions];
        }
      }

      return allOptions.slice(0, 5);
    };

    const handleElementSearch = (step: StepItem, query: string) => {
      if (!query.trim()) {
        const allOptions = filteredElementOptions(step);
        stepElementOptions.value.set(step, allOptions.slice(0, 5));
        return;
      }

      const allOptions = filteredElementOptions(step);
      const filteredResults = allOptions.filter(
        (option) =>
          option.label.toLowerCase().includes(query.toLowerCase()) ||
          option.elementName.toLowerCase().includes(query.toLowerCase()) ||
          option.page.toLowerCase().includes(query.toLowerCase())
      );

      stepElementOptions.value.set(step, filteredResults.slice(0, 8));
    };

    const onElementSelect = (step: StepItem, value: string | null) => {
      if (value) {
        const selectedOption = filteredElementOptions(step).find(
          (option) => option.value === value
        );
        if (selectedOption) {
          step.xpath = selectedOption.xpath;
          step.selectedElement = value;
          step.elementName = selectedOption.label;
          step.element_id = parseInt(value);
        }
      } else {
        step.selectedElement = null;
        step.element_id = undefined;
      }
    };

    const loadReferencedCaseOptions = async () => {
      try {
        const response = await axios.get("/api/testcases");
        if (response.data.success) {
          allTestCasesForReference.value = response.data.testcases;
        }
      } catch (error) {
        console.error("加载用例列表失败:", error);
      }
    };

    // 只能引用当前用例所属项目下的其他用例，且不能引用当前正在编辑的用例自身（避免自引用死循环）
    const getReferencedCaseOptions = (_step: StepItem) => {
      const currentProject = form.value.project;
      const currentCaseId = currentEditId.value;

      return allTestCasesForReference.value
        .filter(
          (tc) =>
            tc.project === currentProject &&
            (currentCaseId === null || tc.id !== currentCaseId)
        )
        .map((tc) => ({
          label: `${tc.name} (ID: ${tc.id})`,
          value: tc.id,
        }));
    };

    const getXPathPlaceholder = (action: string, locateType?: string) => {
      if (needsLocateType(action)) {
        if (locateType === "css") return "请输入CSS选择器";
        if (locateType === "text") return "请输入元素文本内容";
        return "请输入元素XPath";
      }

      const placeholderMap: Record<string, string> = {
        open_url: "请输入网址",
        wait: "请输入等待时长（秒）",
      };

      return placeholderMap[action] || "请输入元素XPath";
    };

    const makeEmptyStep = (stepNo: number): StepItem => ({
      stepNo,
      action: "",
      xpath: "",
      inputValue: "",
      description: "",
      locateType: "xpath",
      selectedElement: null,
      varName: "",
      referencedCaseId: null,
    });

    const addStep = () => {
      form.value.steps.push(makeEmptyStep(form.value.steps.length + 1));
    };

    const insertStepAfter = (index: number) => {
      form.value.steps.splice(index + 1, 0, makeEmptyStep(index + 2));
      form.value.steps.forEach((step, idx) => {
        step.stepNo = idx + 1;
      });
    };

    const removeStep = (index: number) => {
      form.value.steps.splice(index, 1);
      form.value.steps.forEach((step, idx) => {
        step.stepNo = idx + 1;
      });
    };

    // 拖动步骤排序
    const dragStepIndex = ref<number | null>(null);

    const onStepDragStart = (index: number) => {
      dragStepIndex.value = index;
    };

    const onStepDrop = (targetIndex: number) => {
      const fromIndex = dragStepIndex.value;
      if (fromIndex === null || fromIndex === targetIndex) return;

      const steps = form.value.steps;
      const [moved] = steps.splice(fromIndex, 1);
      steps.splice(targetIndex, 0, moved);
      steps.forEach((step, idx) => {
        step.stepNo = idx + 1;
      });
      dragStepIndex.value = null;
    };

    const onStepDragEnd = () => {
      dragStepIndex.value = null;
    };

    const rules = {
      project: { required: true, message: "请选择所属项目", trigger: "blur" },
      module: { required: true, message: "请输入模块", trigger: "blur" },
      name: { required: true, message: "请输入用例概述", trigger: "blur" },
      type: { required: true, message: "请选择用例类型", trigger: "blur" },
    };

    const loadTestCase = async (id: number) => {
      try {
        if (elementsData.value.length === 0) {
          await fetchElements();
        }

        const response = await axios.get(`/api/testcase/${id}`);
        const data = response.data;

        form.value = {
          project: data.project || null,
          module: data.module || "",
          page: data.page || "",
          name: data.name || "",
          type: data.type || null,
          steps: data.testcase_step
            ? data.testcase_step.map((step: any) => {
                const stepItem: any = {
                  stepNo: step.step,
                  action: step.operate,
                  inputValue: step.input_value || "",
                  description: step.describe,
                  locateType: step.locate_type || "xpath",
                  selectedElement: null,
                  elementName: "",
                  expectedValue: step.expected_value || "",
                  varName: step.var_name || "",
                  referencedCaseId: step.referenced_case_id ?? null,
                };

                stepItem.xpath = step.xpath || "";

                // 优先使用后端返回的element_id来设置selectedElement
                if (step.element_id) {
                  stepItem.selectedElement = step.element_id.toString();
                  const matchingElement = elementsData.value.find(
                    (element) => element.id === step.element_id
                  );
                  if (matchingElement) {
                    stepItem.elementName = `${matchingElement.elementName} (${matchingElement.page})`;
                  }
                }
                // 兼容旧数据：如果没有element_id，根据xpath查找
                else if (stepItem.xpath && elementsData.value.length > 0) {
                  const matchingElement = elementsData.value.find(
                    (element) => element.xpath === stepItem.xpath
                  );
                  if (matchingElement) {
                    stepItem.selectedElement = matchingElement.id.toString();
                    stepItem.elementName = `${matchingElement.elementName} (${matchingElement.page})`;
                  }
                }

                return stepItem;
              })
            : [],
        };
      } catch (error) {
        console.error("获取用例详情失败:", error);
        message.error("获取用例详情失败");
      }
    };

    const buildTestcaseStep = (step: StepItem, index: number) => {
      const stepData: any = {
        step: index + 1,
        operate: step.action,
        input_value: step.inputValue || "",
        describe: step.description,
        // 定位方式（xpath/css/text）
        locate_type: step.locateType || "xpath",
        // 验证元素值专用字段
        expected_value: step.expectedValue || "",
        // 变量名字段
        var_name: step.varName || "",
        // 引用其他用例专用字段
        referenced_case_id:
          step.action === "reference_testcase" ? step.referencedCaseId : null,
      };

      stepData.xpath = step.xpath || "";

      // 添加元素ID，用于后续同步更新
      if (step.selectedElement) {
        stepData.element_id = parseInt(step.selectedElement);
      }
      // 如果没有选择元素但有xpath，从描述中提取元素名称
      else if (stepData.xpath && step.description) {
        const description = step.description.trim();
        const dashIndex = description.indexOf("-");
        if (dashIndex > 0 && dashIndex < description.length - 1) {
          stepData.element_name = description.substring(dashIndex + 1).trim();
        } else {
          stepData.element_name = description;
        }
      }

      return stepData;
    };

    const submitForm = async () => {
      try {
        await formRef.value?.validate();

        const testcaseData = {
          project: form.value.project,
          module: form.value.module,
          page: form.value.page,
          name: form.value.name,
          type: form.value.type,
          testcase_step: form.value.steps.map(buildTestcaseStep),
        };

        const response = isEditMode.value
          ? await axios.put(
              `/api/testcase/${currentEditId.value}`,
              testcaseData
            )
          : await axios.post("/api/add_case", testcaseData);

        if (response.data.message) {
          message.success(
            isEditMode.value ? "测试用例更新成功" : "测试用例添加成功"
          );
          router.push("/test-cases");
        } else {
          message.error(
            response.data.error ||
              (isEditMode.value ? "更新用例失败" : "添加用例失败")
          );
        }
      } catch (error) {
        console.error(
          isEditMode.value ? "更新用例失败:" : "添加用例失败:",
          error
        );
        message.error(
          isEditMode.value
            ? "更新用例失败，请检查表单内容"
            : "添加用例失败，请检查表单内容"
        );
      }
    };

    const handleCancel = () => {
      router.push("/test-cases");
    };

    onMounted(async () => {
      await fetchProjects();
      await fetchElements();
      if (currentEditId.value !== null) {
        await loadTestCase(currentEditId.value);
      }
    });

    return {
      form,
      formRef,
      isEditMode,
      rules,
      typeOptions,
      actionOptions,
      locateTypeOptions,
      projectOptions,
      needsLocateType,
      isLocateOnlyStep,
      onLocateTypeChange,
      getElementOptions,
      handleElementSearch,
      onElementSelect,
      getReferencedCaseOptions,
      loadReferencedCaseOptions,
      getXPathPlaceholder,
      addStep,
      insertStepAfter,
      removeStep,
      dragStepIndex,
      onStepDragStart,
      onStepDrop,
      onStepDragEnd,
      submitForm,
      handleCancel,
    };
  },
});
</script>

<style scoped>
.testcase-form-container {
  background-color: #fff;
  padding: 16px;
  border-radius: 4px;
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

.modal-form :deep(.n-select) {
  width: 100%;
}

/* 步骤滚动容器 */
.steps-scroll-container {
  max-height: 60vh;
  min-height: 200px;
  overflow-y: auto;
  overflow-x: hidden;
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  padding: 4px;
  background-color: #fbfbfb;
  width: 100%;
  box-sizing: border-box;
}

.steps-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  min-width: 0;
}

.step-row {
  display: grid;
  grid-template-columns: 60px 0.55fr 2fr 1.5fr 120px;
  gap: 12px;
  padding: 16px;
  border: 1px solid #eee;
  border-radius: 4px;
  background-color: #fafafa;
  width: auto;
  position: relative;
  align-items: center;
  min-width: 0;
  box-sizing: border-box;
}

.step-row.has-locate {
  grid-template-columns: 60px 0.55fr 0.5fr 2fr 1.5fr 120px;
}

.step-row.has-input {
  grid-template-columns: 60px 0.55fr 0.5fr 2fr 1fr 1fr 120px;
}

.step-row.has-get-text {
  grid-template-columns: 60px 0.55fr 0.5fr 2fr 1fr 1fr 120px;
}

.step-row.has-verify-var {
  grid-template-columns: 60px 0.55fr 1fr 1fr 1fr 120px;
}

.step-row.has-verify {
  grid-template-columns: 60px 0.55fr 0.5fr 1.2fr 0.8fr 1.5fr 120px;
}

.step-row.is-dragging {
  opacity: 0.4;
}

.step-number {
  color: #666;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 100%;
  cursor: grab;
}

.drag-handle {
  color: #b0b3b8;
  font-size: 16px;
  line-height: 1;
}

.step-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
  word-wrap: break-word;
  align-self: stretch;
  justify-content: center;
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

.xpath-input-container {
  width: 100%;
}

.xpath-selection {
  width: 100%;
}

.xpath-selection :deep(.n-select) {
  width: 100%;
}

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

@media (max-width: 1500px) {
  .step-row {
    grid-template-columns: 50px 0.55fr 2fr 1.5fr 50px;
  }

  .step-row.has-locate {
    grid-template-columns: 50px 0.55fr 0.5fr 2fr 1.5fr 50px;
  }

  .step-row.has-input {
    grid-template-columns: 50px 0.55fr 0.5fr 1.5fr 1fr 1fr 50px;
  }

  .step-row.has-get-text {
    grid-template-columns: 50px 0.55fr 0.5fr 1.5fr 1fr 1fr 50px;
  }

  .step-row.has-verify-var {
    grid-template-columns: 50px 0.55fr 1fr 1fr 1fr 50px;
  }
}

@media (max-width: 1300px) {
  .step-row {
    grid-template-columns: 50px 0.55fr 2fr 1.5fr 50px;
  }

  .step-row.has-locate {
    grid-template-columns: 50px 0.55fr 0.5fr 2fr 1.5fr 50px;
  }

  .step-row.has-input {
    grid-template-columns: 50px 0.55fr 0.5fr 1.5fr 1fr 1fr 50px;
  }

  .step-row.has-get-text {
    grid-template-columns: 50px 0.55fr 0.5fr 1.5fr 1fr 1fr 50px;
  }

  .step-row.has-verify-var {
    grid-template-columns: 50px 0.55fr 1fr 1fr 1fr 50px;
  }

  .step-row.has-verify {
    grid-template-columns: 50px 0.55fr 0.5fr 1.1fr 0.8fr 1.4fr 50px;
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

@media (max-width: 768px) {
  .step-field {
    min-width: 100%;
  }

  .steps-scroll-container {
    max-height: 300px;
  }
}

@media (max-width: 480px) {
  .steps-scroll-container {
    max-height: 250px;
  }
}
</style>

<template>
  <n-popover
    trigger="manual"
    :show="showTooltip"
    :x="tooltipX"
    :y="tooltipY"
    placement="top"
  >
    <template #trigger>
      <div
        class="variable-input-wrapper"
        @mousemove="handleMouseMove"
        @mouseleave="handleMouseLeave"
      >
        <n-input
          v-model:value="localValue"
          v-bind="$attrs"
          @update:value="handleUpdate"
          class="variable-input"
        />
        <div class="highlight-overlay" v-html="highlightedHtml"></div>
      </div>
    </template>
    <div v-if="currentVariable">
      <div style="font-weight: 600; color: #ff8c00; margin-bottom: 4px">
        {{ currentVariable.name }}
      </div>
      <div style="color: #666; font-size: 13px">
        值: {{ currentVariable.value || "加载中..." }}
      </div>
    </div>
  </n-popover>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { NInput, NPopover } from "naive-ui";
import axios from "axios";

interface Props {
  modelValue?: string;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
});

const emit = defineEmits(["update:modelValue"]);

const localValue = ref(props.modelValue);
const variableCache = ref<Record<string, string>>({});
const showTooltip = ref(false);
const tooltipX = ref(0);
const tooltipY = ref(0);
const currentVariable = ref<{ name: string; value: string } | null>(null);

watch(
  () => props.modelValue,
  (newVal) => {
    localValue.value = newVal || "";
  }
);

const handleUpdate = (value: string) => {
  localValue.value = value;
  emit("update:modelValue", value);
  loadVariables();
};

// 提取变量名
const extractVariables = (text: string): string[] => {
  const pattern = /\{\{([^}]+)\}\}|\$\{([^}]+)\}/g;
  const variables: string[] = [];
  let match;

  while ((match = pattern.exec(text)) !== null) {
    const varName = (match[1] || match[2]).trim();
    if (varName && !variables.includes(varName)) {
      variables.push(varName);
    }
  }

  return variables;
};

// 加载变量值
const loadVariables = async () => {
  const variables = extractVariables(localValue.value);

  for (const varName of variables) {
    if (!variableCache.value[varName]) {
      try {
        const response = await axios.get("/api/variables/generate", {
          params: { var_name: varName },
        });

        if (response.data.success) {
          variableCache.value[varName] = response.data.value;
        }
      } catch (error) {
        console.error(`获取变量值失败:`, error);
        variableCache.value[varName] = "(未找到)";
      }
    }
  }
};

// 生成高亮HTML
const highlightedHtml = computed(() => {
  if (!localValue.value) return "";

  const pattern = /(\{\{[^}]+\}\}|\$\{[^}]+\})/g;
  const escaped = localValue.value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return escaped.replace(pattern, (match) => {
    const varName = match.replace(/\{\{|\}\}|\$\{|\}/g, "").trim();
    return `<span class="variable-token" data-var="${varName}">${match}</span>`;
  });
});

// 处理鼠标移动
const handleMouseMove = (e: MouseEvent) => {
  const target = e.target as HTMLElement;
  const varToken = target.closest(".variable-token") as HTMLElement;

  if (varToken) {
    const varName = varToken.dataset.var;
    if (varName) {
      showTooltip.value = true;
      tooltipX.value = e.clientX;
      tooltipY.value = e.clientY - 10;
      currentVariable.value = {
        name: varName,
        value: variableCache.value[varName] || "加载中...",
      };
    }
  } else {
    showTooltip.value = false;
    currentVariable.value = null;
  }
};

const handleMouseLeave = () => {
  showTooltip.value = false;
  currentVariable.value = null;
};

onMounted(() => {
  loadVariables();
});
</script>

<style scoped>
.variable-input-wrapper {
  position: relative;
  width: 100%;
}

.variable-input {
  position: relative;
  z-index: 1;
}

.highlight-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  padding: 9px 12px;
  font-family: v-mono, SFMono-Regular, Menlo, Consolas, Courier, monospace;
  font-size: 14px;
  line-height: 1.5;
  color: transparent;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow: hidden;
  z-index: 2;
}

:deep(.variable-token) {
  color: #ff8c00;
  font-weight: 600;
  background-color: rgba(255, 140, 0, 0.15);
  padding: 2px 4px;
  border-radius: 3px;
  cursor: help;
  pointer-events: auto;
}

:deep(.n-input__input-el) {
  background: transparent !important;
}
</style>

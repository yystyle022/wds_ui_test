<template>
  <div class="log-viewer">
    <n-card title="日志查询">
      <!-- 工具栏 -->
      <template #header-extra>
        <n-space>
          <n-input
            v-model:value="searchText"
            placeholder="搜索日志内容"
            clearable
            style="width: 250px"
            @keyup.enter="fetchLogs"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>

          <n-select
            v-model:value="logLevel"
            placeholder="日志级别"
            :options="logLevelOptions"
            clearable
            style="width: 120px"
            @update:value="fetchLogs"
          />

          <n-input-number
            v-model:value="lineCount"
            placeholder="显示行数"
            :min="100"
            :max="10000"
            :step="100"
            style="width: 140px"
          />

          <n-button type="primary" @click="fetchLogs" :loading="loading">
            <template #icon>
              <n-icon :component="RefreshOutline" />
            </template>
            刷新
          </n-button>

          <n-button
            @click="toggleAutoRefresh"
            :type="autoRefresh ? 'warning' : 'default'"
          >
            <template #icon>
              <n-icon :component="TimeOutline" />
            </template>
            {{ autoRefresh ? "停止自动刷新" : "自动刷新" }}
          </n-button>

          <n-popconfirm
            @positive-click="clearLogs"
            positive-text="确认"
            negative-text="取消"
          >
            <template #trigger>
              <n-button type="error">
                <template #icon>
                  <n-icon :component="TrashOutline" />
                </template>
                清空日志
              </n-button>
            </template>
            确定要清空所有日志吗？此操作不可恢复。
          </n-popconfirm>

          <n-button @click="downloadLogs">
            <template #icon>
              <n-icon :component="DownloadOutline" />
            </template>
            下载日志
          </n-button>
        </n-space>
      </template>

      <!-- 日志统计信息 -->
      <n-space style="margin-bottom: 16px">
        <n-tag type="info"> 总共: {{ logStats.total }} 条 </n-tag>
        <n-tag type="success"> 显示: {{ logStats.showing }} 条 </n-tag>
        <n-tag v-if="autoRefresh" type="warning">
          自动刷新中 ({{ autoRefreshCountdown }}s)
        </n-tag>
      </n-space>

      <!-- 日志内容区域 -->
      <div class="log-container">
        <n-scrollbar style="max-height: calc(100vh - 220px)" trigger="hover">
          <n-code
            :code="logsContent"
            language="log"
            :word-wrap="true"
            show-line-numbers
            class="log-code"
          />
        </n-scrollbar>
      </div>

      <!-- 空状态 -->
      <n-empty
        v-if="logs.length === 0 && !loading"
        description="暂无日志"
        style="margin-top: 40px"
      />
    </n-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import {
  NCard,
  NButton,
  NIcon,
  NSpace,
  NInput,
  NInputNumber,
  NSelect,
  NCode,
  NScrollbar,
  NTag,
  NEmpty,
  NPopconfirm,
  useMessage,
} from "naive-ui";
import {
  SearchOutline,
  RefreshOutline,
  TrashOutline,
  TimeOutline,
  DownloadOutline,
} from "@vicons/ionicons5";
import axios from "axios";

const message = useMessage();

// 日志数据
const logs = ref<string[]>([]);
const loading = ref(false);
const searchText = ref("");
const logLevel = ref("");
const lineCount = ref(500);

// 自动刷新
const autoRefresh = ref(false);
const autoRefreshInterval = ref<number | null>(null);
const autoRefreshCountdown = ref(5);
const countdownInterval = ref<number | null>(null);

// 日志统计
const logStats = ref({
  total: 0,
  showing: 0,
});

// 日志级别选项
const logLevelOptions = [
  { label: "全部", value: "" },
  { label: "INFO", value: "INFO" },
  { label: "WARNING", value: "WARNING" },
  { label: "ERROR", value: "ERROR" },
  { label: "DEBUG", value: "DEBUG" },
];

// 计算属性：日志内容字符串
const logsContent = computed(() => {
  if (logs.value.length === 0) {
    return "暂无日志";
  }
  return logs.value.join("\n");
});

// 获取日志
const fetchLogs = async () => {
  loading.value = true;
  try {
    const params: any = {
      lines: lineCount.value,
    };

    if (searchText.value) {
      params.search = searchText.value;
    }

    if (logLevel.value) {
      params.level = logLevel.value;
    }

    const response = await axios.get("/api/logs", { params });

    if (response.data.success) {
      logs.value = response.data.logs;
      logStats.value = {
        total: response.data.total,
        showing: response.data.showing,
      };
    } else {
      message.error("获取日志失败: " + response.data.error);
    }
  } catch (error: any) {
    message.error("获取日志失败: " + (error.message || "网络错误"));
    console.error("获取日志错误:", error);
  } finally {
    loading.value = false;
  }
};

// 清空日志
const clearLogs = async () => {
  try {
    const response = await axios.post("/api/logs/clear");

    if (response.data.success) {
      message.success("日志已清空");
      logs.value = [];
      logStats.value = { total: 0, showing: 0 };
    } else {
      message.error("清空日志失败: " + response.data.error);
    }
  } catch (error: any) {
    message.error("清空日志失败: " + (error.message || "网络错误"));
    console.error("清空日志错误:", error);
  }
};

// 下载日志
const downloadLogs = () => {
  if (logs.value.length === 0) {
    message.warning("暂无日志可下载");
    return;
  }

  const content = logs.value.join("\n");
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `logs_${new Date().getTime()}.txt`;
  link.click();
  window.URL.revokeObjectURL(url);
  message.success("日志已下载");
};

// 切换自动刷新
const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value;

  if (autoRefresh.value) {
    // 立即刷新一次
    fetchLogs();
    // 启动自动刷新定时器（每5秒）
    autoRefreshCountdown.value = 5;
    autoRefreshInterval.value = window.setInterval(() => {
      fetchLogs();
      autoRefreshCountdown.value = 5;
    }, 5000);
    // 启动倒计时显示
    countdownInterval.value = window.setInterval(() => {
      if (autoRefreshCountdown.value > 0) {
        autoRefreshCountdown.value--;
      }
    }, 1000);
    message.info("已开启自动刷新（每5秒）");
  } else {
    // 停止自动刷新
    if (autoRefreshInterval.value) {
      clearInterval(autoRefreshInterval.value);
      autoRefreshInterval.value = null;
    }
    if (countdownInterval.value) {
      clearInterval(countdownInterval.value);
      countdownInterval.value = null;
    }
    message.info("已停止自动刷新");
  }
};

// 组件挂载时获取日志
onMounted(() => {
  fetchLogs();
});

// 组件卸载时清除定时器
onUnmounted(() => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value);
  }
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value);
  }
});
</script>

<style scoped>
.log-viewer {
  width: 100%;
}

.log-container {
  background-color: #1e1e1e;
  border-radius: 4px;
  padding: 12px;
  min-height: 400px;
  overflow: hidden;
}

.log-code {
  font-family: "Consolas", "Monaco", "Courier New", monospace;
  font-size: 14px;
  line-height: 1.6;
}

:deep(.n-scrollbar) {
  border: 1px solid #3a3a3a;
}

:deep(.n-scrollbar-rail) {
  background-color: #2a2a2a;
}

:deep(.n-scrollbar-rail__scrollbar) {
  background-color: #555 !important;
}

:deep(.n-scrollbar-rail__scrollbar:hover) {
  background-color: #777 !important;
}

:deep(.n-code) {
  background-color: #1e1e1e !important;
}

:deep(.n-code .hljs) {
  background-color: #1e1e1e !important;
  color: #f0f0f0;
}

:deep(.n-code pre) {
  color: #f0f0f0 !important;
}

:deep(.n-code code) {
  color: #f0f0f0 !important;
}
</style>

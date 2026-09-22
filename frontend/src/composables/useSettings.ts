import { ref, reactive } from "vue";
import axios from "axios";

// 设置表单接口（用例设置与任务设置共用同一套字段结构）
export interface SettingsForm {
  defaultBrowser: string;
  defaultHeadless: string;
  saveScreenshots: string;
  enableMultiThread: string;
  defaultEnvironment: string;
  useAuthorization: string;
  useLoginState: string;
}

export type SettingsScope = "case" | "task";

const SCOPE_CONFIG: Record<SettingsScope, { apiPath: string; label: string }> = {
  case: { apiPath: "/api/settings", label: "设置" },
  task: { apiPath: "/api/task-settings", label: "任务设置" },
};

function createDefaultForm(): SettingsForm {
  return {
    defaultBrowser: "chrome",
    defaultHeadless: "false",
    saveScreenshots: "false",
    enableMultiThread: "false",
    defaultEnvironment: "生产环境",
    useAuthorization: "true",
    useLoginState: "true",
  };
}

function createInstance(scope: SettingsScope) {
  const { apiPath, label } = SCOPE_CONFIG[scope];

  // 每个 scope 独立持有一份单例状态，两套数据互不干扰
  const showSettingsModal = ref(false);
  const settingsForm = reactive<SettingsForm>(createDefaultForm());
  const environmentOptions = ref<{ label: string; value: string }[]>([]);
  let messageApi: any = null;

  const browserOptions = [
    { label: "Chrome", value: "chrome" },
    { label: "Firefox", value: "firefox" },
    { label: "Chromium", value: "chromium" },
    { label: "Edge", value: "msedge" },
  ];

  const headlessOptions = [
    { label: "否（显示浏览器界面）", value: "false" },
    { label: "是（无头模式运行）", value: "true" },
  ];

  const screenshotOptions = [
    { label: "否（不保存截图）", value: "false" },
    { label: "是（保存步骤截图）", value: "true" },
  ];

  const multiThreadOptions = [
    { label: "否（顺序执行）", value: "false" },
    { label: "是（并行执行）", value: "true" },
  ];

  const useAuthorizationOptions = [
    { label: "否（不携带Authorization）", value: "false" },
    { label: "是（自动匹配并携带Token）", value: "true" },
  ];

  const useLoginStateOptions = [
    { label: "否（未登录状态执行）", value: "false" },
    { label: "是（自动注入登录后的Cookie）", value: "true" },
  ];

  // 辅助函数
  const getBrowserLabel = (value: string) => {
    const option = browserOptions.find((opt) => opt.value === value);
    return option ? option.label : value;
  };

  const getHeadlessDisplayText = (value: string) => {
    return value === "true" ? "无头模式" : "显示界面";
  };

  const getScreenshotDisplayText = (value: string) => {
    return value === "true" ? "启用" : "禁用";
  };

  const getMultiThreadDisplayText = (value: string) => {
    return value === "true" ? "并行执行" : "顺序执行";
  };

  const getEnvironmentDisplayText = (value: string) => {
    return value || "生产环境";
  };

  const getUseAuthorizationDisplayText = (value: string) => {
    return value === "false" ? "不使用" : "使用";
  };

  const getUseLoginStateDisplayText = (value: string) => {
    return value === "false" ? "不使用" : "使用";
  };

  // 获取环境列表（用于"默认环境"下拉选项）
  const fetchEnvironments = async () => {
    try {
      const response = await axios.get("/api/environments");
      if (response.data.success) {
        const environments = response.data.environments || [];
        environmentOptions.value = environments.map((env: any) => ({
          label: env.name,
          value: env.name,
        }));
      }
    } catch (error) {
      console.error("加载环境列表失败:", error);
    }
  };

  const loadSettings = async () => {
    try {
      await fetchEnvironments();
      const response = await axios.get(apiPath);
      if (response.data) {
        Object.assign(settingsForm, {
          defaultBrowser: response.data.defaultBrowser || "chrome",
          defaultHeadless: response.data.defaultHeadless ? "true" : "false",
          saveScreenshots: response.data.saveScreenshots ? "true" : "false",
          enableMultiThread: response.data.enableMultiThread
            ? "true"
            : "false",
          defaultEnvironment: response.data.defaultEnvironment || "生产环境",
          useAuthorization:
            response.data.useAuthorization === false ? "false" : "true",
          useLoginState:
            response.data.useLoginState === false ? "false" : "true",
        });
      }
    } catch (error) {
      console.error(`加载${label}失败:`, error);
      messageApi?.error(`加载${label}失败`);
    }
  };

  const handleSettings = async () => {
    await loadSettings();
    showSettingsModal.value = true;
  };

  const closeSettingsModal = () => {
    showSettingsModal.value = false;
  };

  const saveSettings = async () => {
    try {
      const settingsData = {
        defaultBrowser: settingsForm.defaultBrowser,
        defaultHeadless: settingsForm.defaultHeadless === "true",
        saveScreenshots: settingsForm.saveScreenshots === "true",
        enableMultiThread: settingsForm.enableMultiThread === "true",
        defaultEnvironment: settingsForm.defaultEnvironment,
        useAuthorization: settingsForm.useAuthorization === "true",
        useLoginState: settingsForm.useLoginState === "true",
      };

      const response = await axios.post(apiPath, settingsData);

      if (response.data.message) {
        messageApi?.success(`${label}保存成功`);
        showSettingsModal.value = false;
      } else {
        messageApi?.error(response.data.error || `保存${label}失败`);
      }
    } catch (error) {
      console.error(`保存${label}失败:`, error);
      messageApi?.error(`保存${label}失败，请检查网络连接`);
    }
  };

  return {
    // 状态
    showSettingsModal,
    settingsForm,

    // 选项
    browserOptions,
    headlessOptions,
    screenshotOptions,
    multiThreadOptions,
    useAuthorizationOptions,
    useLoginStateOptions,
    environmentOptions,

    // 辅助函数
    getBrowserLabel,
    getHeadlessDisplayText,
    getScreenshotDisplayText,
    getMultiThreadDisplayText,
    getEnvironmentDisplayText,
    getUseAuthorizationDisplayText,
    getUseLoginStateDisplayText,
    fetchEnvironments,

    // 操作函数
    handleSettings,
    closeSettingsModal,
    saveSettings,
    loadSettings,

    // 注入 message 实例（每次调用都刷新，避免绑定到某一次调用方的过期实例）
    setMessage(api: any) {
      messageApi = api;
    },
  };
}

// 按 scope 缓存的单例实例：case 和 task 各自独立，数据互不干扰
const instances = new Map<SettingsScope, ReturnType<typeof createInstance>>();

export function useSettings(scope: SettingsScope = "case", message?: any) {
  let instance = instances.get(scope);
  if (!instance) {
    instance = createInstance(scope);
    instances.set(scope, instance);
  }
  if (message) {
    instance.setMessage(message);
  }
  return instance;
}

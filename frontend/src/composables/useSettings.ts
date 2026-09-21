import { ref, reactive } from "vue";
import axios from "axios";

// 设置表单接口
export interface SettingsForm {
  defaultBrowser: string;
  defaultHeadless: string;
  saveScreenshots: string;
  enableMultiThread: string;
  clientAuthToken: string;
  adminAuthToken: string;
}

// 全局单例状态
const showSettingsModal = ref(false);
const settingsForm = reactive<SettingsForm>({
  defaultBrowser: "chrome",
  defaultHeadless: "false",
  saveScreenshots: "false",
  enableMultiThread: "false",
  clientAuthToken: "",
  adminAuthToken: "",
});

export function useSettings(message?: any) {
  // 选项配置
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

  // 设置操作函数
  const handleSettings = () => {
    console.log("handleSettings被调用");
    loadSettings();
    showSettingsModal.value = true;
    console.log("showSettingsModal设置为:", showSettingsModal.value);
  };

  const closeSettingsModal = () => {
    showSettingsModal.value = false;
  };

  const saveSettings = async () => {
    try {
      // 将字符串转换为布尔值以匹配后端API
      const settingsData = {
        defaultBrowser: settingsForm.defaultBrowser,
        defaultHeadless: settingsForm.defaultHeadless === "true",
        saveScreenshots: settingsForm.saveScreenshots === "true",
        enableMultiThread: settingsForm.enableMultiThread === "true",
        clientAuthToken: settingsForm.clientAuthToken,
        adminAuthToken: settingsForm.adminAuthToken,
      };

      const response = await axios.post(
        "http://127.0.0.1:5000/api/settings",
        settingsData
      );

      if (response.data.message) {
        message?.success("设置保存成功");
        showSettingsModal.value = false;
      } else {
        message?.error(response.data.error || "保存设置失败");
      }
    } catch (error) {
      console.error("保存设置失败:", error);
      message?.error("保存设置失败，请检查网络连接");
    }
  };

  const loadSettings = async () => {
    try {
      const response = await axios.get("http://127.0.0.1:5000/api/settings");
      if (response.data) {
        // 将后端的数据转换匹配前端表单
        const loadedSettings = {
          defaultBrowser: response.data.defaultBrowser,
          defaultHeadless: String(response.data.defaultHeadless),
          saveScreenshots: String(response.data.saveScreenshots),
          enableMultiThread: String(response.data.enableMultiThread),
          clientAuthToken: response.data.clientAuthToken || "",
          adminAuthToken: response.data.adminAuthToken || "",
        };
        Object.assign(settingsForm, loadedSettings);
      }
    } catch (error) {
      console.error("加载设置失败:", error);
      message?.error("加载设置失败");
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

    // 辅助函数
    getBrowserLabel,
    getHeadlessDisplayText,
    getScreenshotDisplayText,
    getMultiThreadDisplayText,

    // 操作函数
    handleSettings,
    closeSettingsModal,
    saveSettings,
    loadSettings,
  };
}

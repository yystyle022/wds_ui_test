<template>
  <!-- 设置弹窗 -->
  <n-modal
    v-model:show="showSettingsModal"
    preset="dialog"
    title="测试执行设置"
    style="width: 500px"
  >
    <n-form
      :model="settingsForm"
      label-placement="left"
      label-width="120"
      class="settings-form"
    >
      <n-form-item label="默认浏览器">
        <n-select
          v-model:value="settingsForm.defaultBrowser"
          :options="browserOptions"
          placeholder="请选择默认浏览器"
        />
      </n-form-item>

      <n-form-item label="默认无头模式">
        <n-select
          v-model:value="settingsForm.defaultHeadless"
          :options="headlessOptions"
          placeholder="请选择默认运行模式"
        />
      </n-form-item>

      <n-form-item label="保存步骤截图">
        <n-select
          v-model:value="settingsForm.saveScreenshots"
          :options="screenshotOptions"
          placeholder="请选择是否保存截图"
        />
      </n-form-item>

      <n-form-item label="批量执行模式">
        <n-select
          v-model:value="settingsForm.enableMultiThread"
          :options="multiThreadOptions"
          placeholder="请选择批量执行模式"
        />
      </n-form-item>

      <n-form-item label="官网Authorization">
        <n-input
          v-model:value="settingsForm.clientAuthToken"
          type="textarea"
          placeholder="请粘贴官网Authorization token（可选）"
          :autosize="{ minRows: 2, maxRows: 4 }"
        />
      </n-form-item>

      <n-form-item label="管理端Authorization">
        <n-input
          v-model:value="settingsForm.adminAuthToken"
          type="textarea"
          placeholder="请粘贴管理端Authorization token（可选）"
          :autosize="{ minRows: 2, maxRows: 4 }"
        />
      </n-form-item>

      <!-- 设置预览 -->
      <n-divider style="margin: 16px 0" />
      <div class="settings-preview">
        <n-text depth="3" style="font-size: 12px">
          <div>
            默认浏览器:
            <n-text strong>{{
              getBrowserLabel(settingsForm.defaultBrowser)
            }}</n-text>
          </div>
          <div>
            运行模式:
            <n-text strong>{{
              getHeadlessDisplayText(settingsForm.defaultHeadless)
            }}</n-text>
          </div>
          <div>
            步骤截图:
            <n-text strong>{{
              getScreenshotDisplayText(settingsForm.saveScreenshots)
            }}</n-text>
          </div>
          <div>
            批量执行:
            <n-text strong>{{
              getMultiThreadDisplayText(settingsForm.enableMultiThread)
            }}</n-text>
          </div>
          <div>
            官网Authorization:
            <n-text strong>{{
              settingsForm.clientAuthToken ? "已设置" : "未设置"
            }}</n-text>
          </div>
          <div>
            管理端Authorization:
            <n-text strong>{{
              settingsForm.adminAuthToken ? "已设置" : "未设置"
            }}</n-text>
          </div>
        </n-text>
      </div>
    </n-form>

    <template #action>
      <n-space>
        <n-button @click="closeSettingsModal">取消</n-button>
        <n-button type="primary" @click="saveSettings">保存设置</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import {
  NModal,
  NForm,
  NFormItem,
  NSelect,
  NInput,
  NButton,
  NSpace,
  NText,
  NDivider,
  NAlert,
  useMessage,
} from "naive-ui";

import { useSettings } from "../composables/useSettings";

// 使用message实例
const message = useMessage();

// 使用共享的设置逻辑
const {
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
  closeSettingsModal,
  saveSettings,
} = useSettings(message);

// 添加调试
console.log("SettingsModal组件加载，showSettingsModal:", showSettingsModal);
</script>

<style scoped>
.settings-form {
  padding: 16px 0;
}

.settings-preview {
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  border-left: 4px solid #18a058;
}

.settings-preview div {
  margin-bottom: 4px;
}

.settings-preview div:last-child {
  margin-bottom: 0;
}
</style>
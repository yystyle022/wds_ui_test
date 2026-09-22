<template>
  <!-- 设置弹窗（用例列表 / 任务管理共用，通过 scope 区分数据源） -->
  <n-modal
    v-model:show="showSettingsModal"
    preset="dialog"
    :title="title"
    style="width: 750px"
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

      <n-form-item label="默认环境">
        <n-select
          v-model:value="settingsForm.defaultEnvironment"
          :options="environmentOptions"
          placeholder="请选择默认环境"
        />
      </n-form-item>

      <n-form-item label="使用Authorization">
        <n-select
          v-model:value="settingsForm.useAuthorization"
          :options="useAuthorizationOptions"
          placeholder="请选择是否使用Authorization"
        />
      </n-form-item>

      <n-form-item label="使用登录态">
        <n-select
          v-model:value="settingsForm.useLoginState"
          :options="useLoginStateOptions"
          placeholder="请选择是否使用登录态"
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
            默认环境:
            <n-text strong>{{
              getEnvironmentDisplayText(settingsForm.defaultEnvironment)
            }}</n-text>
          </div>
          <div>
            使用Authorization:
            <n-text strong>{{
              getUseAuthorizationDisplayText(settingsForm.useAuthorization)
            }}</n-text>
          </div>
          <div>
            使用登录态:
            <n-text strong>{{
              getUseLoginStateDisplayText(settingsForm.useLoginState)
            }}</n-text>
          </div>
        </n-text>
      </div>
    </n-form>

    <p class="settings-hint">
      使用Authorization：开启后，执行时会按用例所属项目+环境自动匹配变量管理中配置的Authorization变量，在请求对应域名时携带Token；关闭则不携带任何Authorization。<br />
      使用登录态：开启后，执行时会按用例所属项目+环境自动匹配变量管理中配置的Cookie变量，在浏览器打开时预先注入登录后的Cookie；关闭则以未登录状态开始执行。
    </p>

    <template #action>
      <n-space>
        <n-button @click="closeSettingsModal">取消</n-button>
        <n-button type="primary" @click="saveSettings">保存设置</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  NModal,
  NForm,
  NFormItem,
  NSelect,
  NButton,
  NSpace,
  NText,
  NDivider,
  useMessage,
} from "naive-ui";

import { useSettings, type SettingsScope } from "../composables/useSettings";

const props = withDefaults(defineProps<{ scope?: SettingsScope }>(), {
  scope: "case",
});

const title = computed(() =>
  props.scope === "task" ? "任务执行设置" : "测试执行设置"
);

// 使用message实例
const message = useMessage();

// 使用共享的设置逻辑，按 scope 各自持有独立的数据，互不干扰
const {
  showSettingsModal,
  settingsForm,

  browserOptions,
  headlessOptions,
  screenshotOptions,
  multiThreadOptions,
  useAuthorizationOptions,
  useLoginStateOptions,
  environmentOptions,

  getBrowserLabel,
  getHeadlessDisplayText,
  getScreenshotDisplayText,
  getMultiThreadDisplayText,
  getEnvironmentDisplayText,
  getUseAuthorizationDisplayText,
  getUseLoginStateDisplayText,

  closeSettingsModal,
  saveSettings,
} = useSettings(props.scope, message);
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

.settings-hint {
  margin-top: 12px;
  font-size: 12px;
  color: #999;
  line-height: 1.6;
}
</style>

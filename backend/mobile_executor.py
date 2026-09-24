"""移动端（Android）测试执行器，基于 Airtest + Poco。

与 test_executor.py 里的 Playwright 执行器并列存在：数据模型（用例/步骤/报告 JSON 结构）
完全复用，只是把"打开网页 + XPath/CSS 定位"换成"连接设备 + Poco 控件属性定位"。
"""

import time
import logging
from datetime import datetime
from typing import Any, Dict, List

from test_executor import TestExecutor, OPERATION_MAPPING, expand_testcase_steps, SCREENSHOTS_DIR

logger = logging.getLogger("mobile_executor")

# 移动端专属操作的中文名称（Web 端没有的操作类型）
MOBILE_OPERATION_MAPPING = {
    "launch_app": "启动App",
    "swipe": "滑动",
}


def get_operation_name(action: str) -> str:
    return OPERATION_MAPPING.get(action) or MOBILE_OPERATION_MAPPING.get(action, action)


def build_poco_query(poco, selector: str):
    """将 "text=登录;type=android.widget.Button" 形式的字符串解析为 Poco 查询条件"""
    kwargs = {}
    for pair in (selector or "").split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        key = key.strip()
        if key:
            kwargs[key] = value.strip()

    if not kwargs:
        raise ValueError(f"无效的Poco选择器: {selector}")

    return poco(**kwargs)


class MobileTestExecutor:
    """封装 Airtest 设备连接 + Poco 控件操作"""

    def __init__(self):
        self.device = None
        self.poco = None
        self.save_screenshots = False
        # 变量替换/存取直接复用 TestExecutor 的实现（该类的这部分逻辑不依赖 Playwright，
        # 构造函数也不会启动浏览器），避免重复实现一套变量解析逻辑
        self._vars = TestExecutor()

    def initialize(
        self,
        device_serial: str,
        save_screenshots: bool = False,
        environment: str = "",
        project: str = "",
    ):
        from airtest.core.api import connect_device, device as current_device
        from poco.drivers.android.uiautomation import AndroidUiautomationPoco

        logger.info(f"连接Android设备: {device_serial}")
        connect_device(f"android://127.0.0.1:5037/{device_serial}")
        self.device = current_device()
        self.poco = AndroidUiautomationPoco()

        self.save_screenshots = save_screenshots
        self._vars.current_environment = environment
        self._vars.current_project = project
        return self

    def close(self):
        # Airtest/Poco 走的是 adb 长连接，没有需要显式释放的资源
        pass

    def replace_variables(self, text: str) -> str:
        return self._vars.replace_variables(text)

    def set_variable(self, var_name: str, value: str):
        self._vars.set_variable(var_name, value)

    def take_screenshot(self, step_name: str = "", is_error: bool = False):
        if not self.save_screenshots or not self.device:
            return None
        try:
            import cv2

            timestamp = int(time.time())
            suffix = "_error" if is_error else ""
            screenshot_path = f"{SCREENSHOTS_DIR}/{timestamp}_{step_name}{suffix}.png"
            frame = self.device.snapshot()
            cv2.imwrite(screenshot_path, frame)
            logger.info(f"截图已保存: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return None

    def _wait_for_control(self, selector: str, timeout: int = 10):
        query = build_poco_query(self.poco, selector)
        query.wait_for_appearance(timeout=timeout)
        return query

    def launch_app(self, package: str) -> Dict[str, Any]:
        package = self.replace_variables(package)
        logger.info(f"启动App: {package}")
        try:
            from airtest.core.api import start_app

            start_app(package)
            time.sleep(2)
            screenshot_path = self.take_screenshot("launch_app")
            return {"screenshot": screenshot_path, "success": True}
        except Exception as e:
            logger.error(f"启动App失败: {str(e)}")
            screenshot_path = self.take_screenshot("launch_app", is_error=True)
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def click_element(self, selector: str) -> Dict[str, Any]:
        selector = self.replace_variables(selector)
        logger.info(f"点击元素: {selector}")
        try:
            query = self._wait_for_control(selector)
            query.click()
            screenshot_path = self.take_screenshot("click")
            return {"screenshot": screenshot_path, "success": True}
        except Exception as e:
            logger.error(f"点击元素失败: {str(e)}")
            screenshot_path = self.take_screenshot("click", is_error=True)
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def click_image(self, image_path: str) -> Dict[str, Any]:
        """使用 Airtest 图像识别点击"""
        logger.info(f"图像识别点击: {image_path}")
        try:
            from airtest.core.api import touch, Template

            # 使用 Template 进行图像识别
            template = Template(image_path, threshold=0.8)
            touch(template)
            time.sleep(0.5)
            screenshot_path = self.take_screenshot("click_image")
            return {"screenshot": screenshot_path, "success": True}
        except Exception as e:
            logger.error(f"图像识别点击失败: {str(e)}")
            screenshot_path = self.take_screenshot("click_image", is_error=True)
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def fill_text(self, selector: str, text: str) -> Dict[str, Any]:
        selector = self.replace_variables(selector)
        text = self.replace_variables(text)
        logger.info(f"填入文本: {selector} = {text}")
        try:
            query = self._wait_for_control(selector)
            query.set_text(text)
            screenshot_path = self.take_screenshot("input")
            return {"screenshot": screenshot_path, "success": True}
        except Exception as e:
            logger.error(f"填入文本失败: {str(e)}")
            screenshot_path = self.take_screenshot("input", is_error=True)
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def wait_seconds(self, seconds: str) -> Dict[str, Any]:
        logger.info(f"等待时长: {seconds}秒")
        try:
            time.sleep(float(seconds))
            screenshot_path = self.take_screenshot("wait")
            return {"screenshot": screenshot_path, "success": True}
        except Exception as e:
            logger.error(f"等待失败: {str(e)}")
            return {"error": str(e), "success": False}

    def swipe(self, direction: str) -> Dict[str, Any]:
        direction = (direction or "up").strip().lower()
        logger.info(f"滑动方向: {direction}")
        try:
            from airtest.core.api import swipe as airtest_swipe

            width, height = self.device.get_current_resolution()
            cx, cy = width * 0.5, height * 0.5
            offsets = {
                "up": ((cx, height * 0.75), (cx, height * 0.25)),
                "down": ((cx, height * 0.25), (cx, height * 0.75)),
                "left": ((width * 0.75, cy), (width * 0.25, cy)),
                "right": ((width * 0.25, cy), (width * 0.75, cy)),
            }
            point_from, point_to = offsets.get(direction, offsets["up"])
            airtest_swipe(point_from, point_to)
            screenshot_path = self.take_screenshot("swipe")
            return {"screenshot": screenshot_path, "success": True}
        except Exception as e:
            logger.error(f"滑动失败: {str(e)}")
            screenshot_path = self.take_screenshot("swipe", is_error=True)
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def check_element_exists(self, selector: str) -> Dict[str, Any]:
        selector = self.replace_variables(selector)
        logger.info(f"检查元素存在: {selector}")
        try:
            query = build_poco_query(self.poco, selector)
            exists = query.exists()
            if not exists:
                try:
                    query.wait_for_appearance(timeout=5)
                    exists = True
                except Exception:
                    exists = False

            if exists:
                screenshot_path = self.take_screenshot("check_element_exists")
                return {
                    "screenshot": screenshot_path,
                    "success": True,
                    "message": f"元素存在: {selector}",
                }
            else:
                screenshot_path = self.take_screenshot(
                    "check_element_exists", is_error=True
                )
                return {
                    "error": f"元素不存在: {selector}",
                    "screenshot": screenshot_path,
                    "success": False,
                }
        except Exception as e:
            logger.error(f"检查元素存在性失败: {str(e)}")
            screenshot_path = self.take_screenshot("check_element_exists", is_error=True)
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def check_element_not_exists(self, selector: str) -> Dict[str, Any]:
        selector = self.replace_variables(selector)
        logger.info(f"检查元素不存在: {selector}")
        try:
            query = build_poco_query(self.poco, selector)
            exists = query.exists()

            if exists:
                logger.error(f"元素存在（预期不存在）: {selector}")
                screenshot_path = self.take_screenshot(
                    "check_element_not_exists", is_error=True
                )
                return {
                    "error": f"元素存在（预期不存在）: {selector}",
                    "screenshot": screenshot_path,
                    "success": False,
                }
            else:
                screenshot_path = self.take_screenshot("check_element_not_exists")
                return {
                    "screenshot": screenshot_path,
                    "success": True,
                    "message": f"元素不存在（验证通过）: {selector}",
                }
        except Exception as e:
            logger.error(f"检查元素不存在失败: {str(e)}")
            screenshot_path = self.take_screenshot(
                "check_element_not_exists", is_error=True
            )
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def get_element_text(self, selector: str, var_name: str = "") -> Dict[str, Any]:
        selector = self.replace_variables(selector)
        logger.info(f"获取元素的文案: {selector}")
        try:
            query = self._wait_for_control(selector)
            element_text = query.get_text() or ""

            if var_name:
                self.set_variable(var_name, element_text)

            screenshot_path = self.take_screenshot("get_element_text")
            return {
                "screenshot": screenshot_path,
                "success": True,
                "message": f"成功获取元素文案: {element_text}"
                + (f"，已保存到变量 {var_name}" if var_name else ""),
                "element_text": element_text,
                "variable_name": var_name if var_name else None,
            }
        except Exception as e:
            logger.error(f"获取元素文案失败: {str(e)}")
            screenshot_path = self.take_screenshot("get_element_text", is_error=True)
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def verify_element_value(self, selector: str, expected_value: str) -> Dict[str, Any]:
        selector = self.replace_variables(selector)
        expected_value = self.replace_variables(expected_value)
        logger.info(f"验证元素的值: {selector}, 期望值: {expected_value}")
        try:
            query = self._wait_for_control(selector)
            actual_value = (query.get_text() or "").strip()
            expected_stripped = (expected_value or "").strip()

            if actual_value == expected_stripped:
                screenshot_path = self.take_screenshot("verify_element_value")
                return {
                    "screenshot": screenshot_path,
                    "success": True,
                    "message": f"验证成功: 元素值 [{actual_value}] 等于期望值 [{expected_value}]",
                    "actual_value": actual_value,
                    "expected_value": expected_value,
                }
            else:
                screenshot_path = self.take_screenshot(
                    "verify_element_value", is_error=True
                )
                return {
                    "error": f"验证失败: 元素值 [{actual_value}] 不等于期望值 [{expected_value}]",
                    "screenshot": screenshot_path,
                    "success": False,
                    "actual_value": actual_value,
                    "expected_value": expected_value,
                }
        except Exception as e:
            logger.error(f"验证元素值失败: {str(e)}")
            screenshot_path = self.take_screenshot("verify_element_value", is_error=True)
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def verify_variable_value(self, var_name: str, expected_value: str) -> Dict[str, Any]:
        logger.info(f"验证变量值: {var_name}, 期望值: {expected_value}")
        try:
            variables = self._vars.variables
            if var_name in variables:
                actual_value = variables[var_name]
                if str(actual_value).strip() == str(expected_value).strip():
                    screenshot_path = self.take_screenshot("verify_variable_value")
                    return {
                        "screenshot": screenshot_path,
                        "success": True,
                        "message": f"验证成功: 变量 '{var_name}' 的值 [{actual_value}] 等于期望值 [{expected_value}]",
                        "actual_value": actual_value,
                        "expected_value": expected_value,
                        "variable_name": var_name,
                    }
                else:
                    screenshot_path = self.take_screenshot(
                        "verify_variable_value", is_error=True
                    )
                    return {
                        "error": f"验证失败: 变量 '{var_name}' 的值 [{actual_value}] 不等于期望值 [{expected_value}]",
                        "screenshot": screenshot_path,
                        "success": False,
                        "actual_value": actual_value,
                        "expected_value": expected_value,
                        "variable_name": var_name,
                    }
            else:
                screenshot_path = self.take_screenshot(
                    "verify_variable_value", is_error=True
                )
                return {
                    "error": f"变量不存在: {var_name}",
                    "screenshot": screenshot_path,
                    "success": False,
                    "variable_name": var_name,
                    "available_variables": list(variables.keys()),
                }
        except Exception as e:
            logger.error(f"验证变量值失败: {str(e)}")
            screenshot_path = self.take_screenshot("verify_variable_value", is_error=True)
            return {"error": str(e), "screenshot": screenshot_path, "success": False}

    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        action = step.get("operate", "")
        xpath = step.get("xpath", "")
        input_value = step.get("input_value", "")
        locate_type = step.get("locate_type", "poco")
        expected_value = step.get("expected_value", "")
        var_name = step.get("var_name", "")
        image_data = step.get("image_data", "")  # Base64 图片数据

        logger.info(
            f"执行移动端步骤: 操作={action}, 定位串={xpath}, 定位方式={locate_type}, 输入值={input_value}"
        )

        try:
            if action == "launch_app":
                return self.launch_app(xpath)
            elif action == "click":
                # 如果是图像识别模式
                if locate_type == "image" and image_data:
                    # 保存 base64 图片到临时文件
                    import base64
                    import os

                    # 解析 base64 数据（移除 data:image/png;base64, 前缀）
                    if "base64," in image_data:
                        image_data = image_data.split("base64,")[1]

                    # 保存到临时文件
                    temp_image_path = os.path.join(SCREENSHOTS_DIR, f"temp_template_{int(time.time())}.png")
                    with open(temp_image_path, "wb") as f:
                        f.write(base64.b64decode(image_data))

                    logger.info(f"图像识别模式，临时图片保存到: {temp_image_path}")
                    result = self.click_image(temp_image_path)

                    # 删除临时文件
                    try:
                        os.remove(temp_image_path)
                    except Exception:
                        pass

                    return result
                else:
                    # Poco 控件定位
                    return self.click_element(xpath)
            elif action == "input":
                return self.fill_text(xpath, input_value)
            elif action == "wait":
                return self.wait_seconds(xpath)
            elif action == "swipe":
                return self.swipe(xpath)
            elif action == "check_element_exists":
                return self.check_element_exists(xpath)
            elif action == "check_element_not_exists":
                return self.check_element_not_exists(xpath)
            elif action == "get_element_text":
                return self.get_element_text(xpath, var_name)
            elif action == "verify_element_value":
                return self.verify_element_value(xpath, expected_value)
            elif action == "verify_variable_value":
                return self.verify_variable_value(var_name, expected_value)
            else:
                logger.warning(f"未实现的移动端操作类型: {action}")
                return {"success": False, "error": f"未实现的操作类型: {action}"}
        except ValueError as ve:
            logger.error(f"变量错误: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"执行移动端步骤失败: {str(e)}")
            return {"success": False, "error": str(e)}


async def execute_test_case_mobile(
    test_case: Dict[str, Any], config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """执行完整的移动端用例，返回结构与 test_executor.execute_test_case 完全一致的报告字典。

    Airtest/Poco 是同步 API；声明成 async 只是为了让 app.py 里 `asyncio.run(...)` 的调用方式
    对 Web/Android 两种用例保持一致，函数体内部并没有真正的并发。
    """
    if config is None:
        config = {}

    device_serial = config.get("deviceSerial", "")
    save_screenshots = config.get("saveScreenshots", False)
    custom_name = config.get("reportName", "")
    environment = config.get("executeEnvironment") or test_case.get("environment", "")
    project = test_case.get("project", "")

    case_id = test_case.get("id")
    case_name = test_case.get("name", "未命名测试")
    steps = expand_testcase_steps(
        test_case.get("testcase_step", []), {case_id} if case_id else set()
    )

    report_name = custom_name if custom_name else case_name

    logger.info(
        f"开始执行移动端测试用例: ID={case_id}, 名称={case_name}, 设备={device_serial}, 步骤数={len(steps)}"
    )

    executor = None
    start_time = time.time()
    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []

    try:
        if not device_serial:
            raise RuntimeError("未配置执行设备，请先在设置或设备管理中指定一台Android设备")

        try:
            executor = MobileTestExecutor().initialize(
                device_serial=device_serial,
                save_screenshots=save_screenshots,
                environment=environment,
                project=project,
            )
        except Exception as init_error:
            logger.error(f"设备连接失败: {str(init_error)}")
            end_time = time.time()
            duration_seconds = end_time - start_time
            minutes, seconds = divmod(int(duration_seconds), 60)
            duration = f"{int(minutes):02d}:{int(seconds):02d}"

            return {
                "id": int(time.time()),
                "test_id": case_id,
                "name": report_name,
                "time": start_time_str,
                "status": "fail",
                "pass_rate": 0,
                "duration": duration,
                "config": config,
                "steps": [
                    {
                        "case_id": case_id,
                        "case_name": case_name,
                        "step_number": 1,
                        "action": "设备连接",
                        "value": "",
                        "describe": f"设备连接失败: {str(init_error)}",
                        "result": "fail",
                        "details": {"error": str(init_error)},
                    }
                ],
                "executed_cases": [{"id": case_id, "name": case_name}],
            }

        for i, step in enumerate(steps):
            logger.info(
                f"开始执行步骤 {i + 1}/{len(steps)}: {step.get('describe', '未知步骤')}"
            )

            try:
                step_result = executor.execute_step(step)
            except ValueError as var_error:
                logger.error(f"变量错误: {str(var_error)}")
                step_result = {"success": False, "error": str(var_error), "screenshot": None}
                action_name = get_operation_name(step.get("operate", ""))
                results.append(
                    {
                        "case_id": case_id,
                        "case_name": case_name,
                        "step_number": i + 1,
                        "action": action_name,
                        "value": step.get("xpath", ""),
                        "describe": step.get("describe", ""),
                        "result": "fail",
                        "details": step_result,
                    }
                )
                if i < len(steps) - 1:
                    for j in range(i + 1, len(steps)):
                        skipped_step = steps[j]
                        results.append(
                            {
                                "case_id": case_id,
                                "case_name": case_name,
                                "step_number": j + 1,
                                "action": get_operation_name(skipped_step.get("operate", "")),
                                "value": skipped_step.get("xpath", ""),
                                "describe": skipped_step.get("describe", ""),
                                "result": "skip",
                                "details": {"message": "由于前序步骤失败而跳过"},
                            }
                        )
                break
            except Exception as step_exception:
                logger.error(f"步骤 {i + 1} 执行时发生异常: {str(step_exception)}")
                step_result = {
                    "success": False,
                    "error": f"步骤执行异常: {str(step_exception)}",
                    "screenshot": None,
                }

            action_name = get_operation_name(step.get("operate", ""))
            step_info = {
                "case_id": case_id,
                "case_name": case_name,
                "step_number": i + 1,
                "action": action_name,
                "value": step.get("xpath", ""),
                "describe": step.get("describe", ""),
                "result": "success" if step_result.get("success", False) else "fail",
                "details": step_result,
            }
            results.append(step_info)

            if not step_result.get("success", False) and i < len(steps) - 1:
                for j in range(i + 1, len(steps)):
                    skipped_step = steps[j]
                    results.append(
                        {
                            "case_id": case_id,
                            "case_name": case_name,
                            "step_number": j + 1,
                            "action": get_operation_name(skipped_step.get("operate", "")),
                            "value": skipped_step.get("xpath", ""),
                            "describe": skipped_step.get("describe", ""),
                            "result": "skip",
                            "details": {"message": "由于前序步骤失败而跳过"},
                        }
                    )
                break

    except Exception as e:
        logger.error(f"移动端测试执行过程中发生错误: {str(e)}")
        results.append(
            {
                "case_id": case_id,
                "case_name": case_name,
                "step_number": len(results) + 1,
                "action": "测试过程异常",
                "value": "",
                "describe": f"测试执行过程中发生错误: {str(e)}",
                "result": "error",
                "details": {"error": str(e)},
            }
        )
    finally:
        if executor:
            executor.close()

    end_time = time.time()
    duration_seconds = end_time - start_time
    minutes, seconds = divmod(int(duration_seconds), 60)
    duration = f"{int(minutes):02d}:{int(seconds):02d}"

    total_steps = len(results)
    failed_steps = sum(1 for r in results if r["result"] == "fail")
    pass_rate = 100 if failed_steps == 0 and total_steps > 0 else 0

    report = {
        "id": int(time.time()),
        "test_id": case_id,
        "name": report_name,
        "time": start_time_str,
        "status": "success" if pass_rate == 100 else "fail",
        "pass_rate": pass_rate,
        "duration": duration,
        "config": config,
        "steps": results,
        "executed_cases": [{"id": case_id, "name": case_name}],
    }

    if config.get("description"):
        report["description"] = config.get("description")

    logger.info(
        f"移动端测试执行完成: 报告名称={report_name}, 通过率={pass_rate}%, 耗时={duration}"
    )

    return report


async def execute_batch_test_cases_mobile(
    test_cases: List[Dict[str, Any]], config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """顺序执行一批移动端用例并生成汇总报告，报告结构与 test_executor.execute_batch_test_cases 一致"""
    if config is None:
        config = {}

    device_serial = config.get("deviceSerial", "")
    save_screenshots = config.get("saveScreenshots", False)

    logger.info(f"开始顺序执行移动端测试用例: 数量={len(test_cases)}, 设备={device_serial}")

    executor = None
    start_time = time.time()
    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    batch_results = []
    case_results_summary = []

    try:
        if not device_serial:
            raise RuntimeError("未配置执行设备，请先在设置或设备管理中指定一台Android设备")

        first_env = config.get("executeEnvironment") or (
            test_cases[0].get("environment", "") if test_cases else ""
        )
        first_project = test_cases[0].get("project", "") if test_cases else ""

        executor = MobileTestExecutor().initialize(
            device_serial=device_serial,
            save_screenshots=save_screenshots,
            environment=first_env,
            project=first_project,
        )

        for i, test_case in enumerate(test_cases):
            case_id = test_case.get("id")
            case_name = test_case.get("name", "未命名测试")

            try:
                steps = expand_testcase_steps(
                    test_case.get("testcase_step", []), {case_id} if case_id else set()
                )

                logger.info(
                    f"执行移动端用例 {i + 1}/{len(test_cases)}: ID={case_id}, 名称={case_name}"
                )

                case_results = []

                for j, step in enumerate(steps):
                    step_result = executor.execute_step(step)
                    action_name = get_operation_name(step.get("operate", ""))
                    step_info = {
                        "case_id": case_id,
                        "case_name": case_name,
                        "step_number": j + 1,
                        "action": action_name,
                        "value": step.get("xpath", ""),
                        "describe": step.get("describe", ""),
                        "result": (
                            "success" if step_result.get("success", False) else "fail"
                        ),
                        "details": step_result,
                    }
                    case_results.append(step_info)

                    if not step_result.get("success", False) and j < len(steps) - 1:
                        for k in range(j + 1, len(steps)):
                            skipped_step = steps[k]
                            case_results.append(
                                {
                                    "case_id": case_id,
                                    "case_name": case_name,
                                    "step_number": k + 1,
                                    "action": get_operation_name(
                                        skipped_step.get("operate", "")
                                    ),
                                    "value": skipped_step.get("xpath", ""),
                                    "describe": skipped_step.get("describe", ""),
                                    "result": "skip",
                                    "details": {"message": "由于前序步骤失败而跳过"},
                                }
                            )
                        break

                case_failed = sum(1 for r in case_results if r["result"] == "fail")
                case_total = len(
                    [r for r in case_results if r["result"] in ["success", "fail"]]
                )
                case_success = case_failed == 0 and case_total > 0

                case_results_summary.append(
                    {"case_id": case_id, "case_name": case_name, "success": case_success}
                )
                batch_results.extend(case_results)

            except Exception as case_error:
                logger.error(f"移动端用例 {case_name} 执行过程中发生错误: {str(case_error)}")
                batch_results.append(
                    {
                        "case_id": case_id,
                        "case_name": case_name,
                        "step_number": 0,
                        "action": "用例执行异常",
                        "value": "",
                        "describe": "用例执行过程中发生错误",
                        "result": "error",
                        "details": {"error": str(case_error)},
                    }
                )
                case_results_summary.append(
                    {"case_id": case_id, "case_name": case_name, "success": False}
                )

    except Exception as e:
        logger.error(f"移动端批量执行过程中发生错误: {str(e)}")
        batch_results.append(
            {
                "case_id": 0,
                "case_name": "批量执行过程",
                "step_number": 0,
                "action": "批量执行",
                "value": "",
                "describe": "批量执行过程中发生错误",
                "result": "error",
                "details": {"error": str(e)},
            }
        )
    finally:
        if executor:
            executor.close()

    end_time = time.time()
    duration_seconds = end_time - start_time
    minutes, seconds = divmod(int(duration_seconds), 60)
    duration = f"{int(minutes):02d}:{int(seconds):02d}"

    total_cases = len(case_results_summary)
    passed_cases = sum(1 for case in case_results_summary if case["success"])
    failed_cases = total_cases - passed_cases
    overall_pass_rate = int((passed_cases / total_cases) * 100) if total_cases > 0 else 0

    if total_cases > 0 and passed_cases == total_cases:
        status = "success"
    elif passed_cases > 0 and failed_cases > 0:
        status = "partial"
    else:
        status = "fail"

    case_info_list = [
        {
            "id": case.get("id"),
            "name": case.get("name", f"用例{case.get('id', '')}"),
            "client": case.get("client", "未知客户端"),
            "page": case.get("page", "未知页面"),
        }
        for case in test_cases
    ]
    case_names = [info["name"] for info in case_info_list]

    custom_name = config.get("reportName", "") if config else ""
    if custom_name:
        batch_name = custom_name
    else:
        batch_name = f"移动端批量执行: {', '.join(case_names[:3])}" + (
            f" 等{len(test_cases)}个用例" if len(test_cases) > 3 else ""
        )

    batch_report = {
        "id": int(time.time()),
        "test_id": f"mobile_batch_{int(time.time())}",
        "name": batch_name,
        "time": start_time_str,
        "status": status,
        "pass_rate": overall_pass_rate,
        "duration": duration,
        "config": config,
        "batch_info": {
            "total_cases": len(test_cases),
            "case_ids": [case.get("id") for case in test_cases],
            "case_names": case_names,
            "execution_mode": "sequential",
        },
        "steps": batch_results,
        "executed_cases": case_info_list,
    }

    if config and config.get("description"):
        batch_report["description"] = config.get("description")

    logger.info(
        f"移动端批量执行完成: 总用例数={total_cases}, 成功={passed_cases}, 通过率={overall_pass_rate}%"
    )

    return batch_report

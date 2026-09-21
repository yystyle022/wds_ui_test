import os
import json
import time
import logging
import asyncio
import base64
import concurrent.futures
import cv2
import numpy as np
import requests
import re
from typing import Dict, List, Any, Optional, Union
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# 配置日志
logger = logging.getLogger("test_executor")

# 确保截图目录存在
SCREENSHOTS_DIR = "screenshots"
if not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)
    logger.info(f"创建截图目录: {SCREENSHOTS_DIR}")

# 确保cookie目录存在
COOKIE_DIR = os.path.join(os.path.dirname(__file__), "..", "cookie")
if not os.path.exists(COOKIE_DIR):
    os.makedirs(COOKIE_DIR)
    logger.info(f"创建cookie目录: {COOKIE_DIR}")

# 操作类型映射表
OPERATION_MAPPING = {
    "open_url": "打开网址",
    "click": "点击元素",
    "input": "输入内容",
    "wait": "等待时长",
    "check_element_exists": "检查元素存在",
    "check_element_not_exists": "检查元素不存在",
    "get_element_text": "获取元素的文案",
    "verify_element_value": "验证元素的值",
    "verify_variable_value": "验证获取的变量值",
    "reference_testcase": "引用其他用例",
}


def build_selector(value: str, locate_type: str = "xpath") -> str:
    """根据步骤配置的定位方式，拼接成Playwright可识别的选择器字符串"""
    value = value or ""
    locate_type = (locate_type or "xpath").lower()
    if locate_type == "css":
        return f"css={value}"
    if locate_type == "text":
        return f"text={value}"
    # xpath：兼容已有数据（本身已是//或xpath=开头）
    if value.startswith("xpath=") or value.startswith("//") or value.startswith(".."):
        return value
    return f"xpath={value}"


class ClientLoginBase:
    """滑块验证相关的XPath配置"""

    @staticmethod
    def sliderVerificationIframeXpath():
        """滑动验证窗口xpath"""
        return "//iframe[@id='tcaptcha_iframe']"

    @staticmethod
    def sliderPicXpath():
        """滑块图片xpath"""
        return "//img[@id='slideBlock']"

    @staticmethod
    def sliderBackPicXpath():
        """背景图片xpath"""
        return "//img[@id='slideBg']"


def download_image(src, save_path):
    """下载图片到本地"""
    try:
        if src.startswith("data:"):
            # 处理base64图片
            header, data = src.split(",", 1)
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(data))
        else:
            # 处理URL图片
            response = requests.get(src, timeout=10)
            response.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(response.content)
        logger.info(f"图片下载成功: {save_path}")
    except Exception as e:
        logger.error(f"图片下载失败: {str(e)}")


async def download_images(page, image_name, frame_xpath, image_xpath, save_directory):
    """下载验证码图片"""
    try:
        frame = page.frame_locator(frame_xpath)
        if not frame:
            print("Frame not found for the given XPath.")
            return False

        # 定位图片
        images = frame.locator(image_xpath)
        if not images:
            print("No images found for the given XPath.")
            return False

        # 创建图片文件夹
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # 获取图片下载src
        src = await images.get_attribute("src")
        if src:
            image_filename = f"{image_name}.jpg"
            image_save_path = os.path.join(save_directory, image_filename)
            download_image(src, image_save_path)
            print(f"Downloaded image to: {image_save_path}")
            return True
    except Exception as e:
        logger.error(f"下载图片失败: {str(e)}")
        return False


async def dragbox_location(page):
    """获取滑块位置"""
    dragbox_bounding = (
        await page.frame_locator("//iframe[@id='tcaptcha_iframe']")
        .locator("//img[@id='slideBlock']")
        .bounding_box()
    )
    if dragbox_bounding is not None and dragbox_bounding["x"] > 20:
        return dragbox_bounding
    return None


def get_slide_locus(distance):
    """
    获取滑块的滑动点，以列表形式输出
    @param distance: 计算出的滑动距离
    @return: 返回滑动点的列表
    """
    distance += 7
    v = 0
    m = 0.312
    # 保存0.3内的位移
    tracks = []
    current = 0
    mid = distance * 4 / 5
    # 判断每次滑动后的距离是否小于滑动距离
    while current <= distance:
        if current < mid:
            a = 2
        else:
            a = -3
        v0 = v
        s = v0 * m + 0.5 * a * (m**2)
        current += s
        tracks.append(round(s))
        v = v0 + a * m
    return tracks


class TestExecutor:
    """
    测试执行器类，封装Playwright相关操作
    """

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.save_screenshots = False  # 是否保存截图的配置
        self.auth_profiles = []  # 动态Authorization配置列表：[{"name","domains","token"}, ...]
        self.variables = {}  # 存储动态变量的字典
        self.current_environment = ""  # 当前执行环境
        self.current_project = ""  # 当前执行项目
        # 初始化时加载已保存的变量
        self.load_variables_from_file()

    def set_auth_profiles(self, profiles):
        """设置当前用例生效的Authorization配置列表"""
        self.auth_profiles = profiles or []

    async def initialize(
        self,
        browser_name: str = "chrome",
        headless: bool = False,
        save_screenshots: bool = False,
        width: int = 1920,
        height: int = 1080,
        auth_profiles: Optional[list] = None,
        auth_token: str = "",
        cookies: Optional[Union[list, dict]] = None,
        environment: str = "",
        project: str = "",
    ):
        """初始化Playwright环境"""
        logger.info(
            f"初始化Playwright环境 (browser={browser_name}, headless={headless}, save_screenshots={save_screenshots}, resolution={width}x{height})"
        )

        # 保存截图配置、authorization配置、环境和项目信息
        self.save_screenshots = save_screenshots
        self.auth_profiles = auth_profiles or []
        self.current_environment = environment
        self.current_project = project

        logger.info(f"当前执行环境: {environment}, 当前项目: {project}")

        try:
            self.playwright = await async_playwright().start()

            # 根据浏览器类型启动不同的浏览器
            if browser_name == "firefox":
                self.browser = await self.playwright.firefox.launch(
                    headless=headless, args=["--start-maximized"]
                )
            elif browser_name == "chromium":
                self.browser = await self.playwright.chromium.launch(
                    headless=headless, args=["--start-maximized"]
                )
            elif browser_name == "msedge":
                # Microsoft Edge
                self.browser = await self.playwright.chromium.launch(
                    channel="msedge",
                    headless=headless,
                    args=["--start-maximized", "--disable-gpu"],
                )
            else:
                # 默认使用Chrome
                self.browser = await self.playwright.chromium.launch(
                    channel="chrome",
                    headless=headless,
                    args=["--start-maximized", "--disable-gpu"],
                )

            # 创建浏览器上下文配置
            # 有头模式下窗口已通过--start-maximized铺满屏幕，若再固定viewport会导致
            # 页面渲染区域被锁定为传入的width/height，与实际窗口大小不一致（表现为窗口只占屏幕一部分）
            # 因此有头模式不限制viewport，让页面跟随窗口实际大小；无头模式没有真实窗口，仍需固定viewport保证截图尺寸一致
            context_options = {
                "viewport": None if not headless else {"width": width, "height": height},
                "device_scale_factor": 1,
            }

            # 如果提供了Cookie，加载到上下文中
            if cookies:
                if isinstance(cookies, dict):
                    # 如果是storage_state格式（从playwright保存的）
                    if "cookies" in cookies:
                        context_options["storage_state"] = cookies
                        logger.info(f"加载storage_state格式的Cookie")
                    else:
                        # 单个cookie对象
                        logger.warning("Cookie格式不正确，需要是列表或storage_state格式")
                elif isinstance(cookies, list):
                    # Cookie列表，在创建上下文后添加
                    logger.info(f"准备添加 {len(cookies)} 个Cookie")

            # 创建浏览器上下文
            self.context = await self.browser.new_context(**context_options)

            # 如果有Cookie列表，添加到上下文
            if cookies and isinstance(cookies, list):
                try:
                    await self.context.add_cookies(cookies)
                    logger.info(f"成功添加 {len(cookies)} 个Cookie到浏览器上下文")
                except Exception as e:
                    logger.error(f"添加Cookie失败: {str(e)}")

            # 如果提供了Token，设置为默认请求头
            if auth_token:
                await self.context.set_extra_http_headers(
                    {"Authorization": auth_token}
                )
                logger.info(f"设置Authorization Token (前50字符): {auth_token[:50]}...")

            # 不在初始化时注入Authorization token
            # 将在open_url方法中根据访问的域名动态注入对应的token
            for profile in self.auth_profiles:
                logger.info(
                    f"检测到Authorization配置: {profile.get('name')} -> 域名: {profile.get('domains')}"
                )

            # 创建页面
            self.page = await self.context.new_page()

            # 设置页面事件监听
            self.page.on(
                "console", lambda msg: logger.info(f"浏览器控制台: {msg.text}")
            )
            self.page.on("pageerror", lambda err: logger.error(f"页面错误: {err}"))

            logger.info("浏览器初始化成功")
            return self

        except Exception as e:
            logger.error(f"浏览器初始化失败: {str(e)}")
            # 确保资源释放
            await self.close()
            raise

    async def close(self):
        """关闭浏览器和Playwright"""
        logger.info("正在关闭浏览器资源...")

        if self.context:
            try:
                await self.context.close()
                logger.info("上下文已关闭")
            except Exception as e:
                logger.error(f"关闭上下文时出错: {str(e)}")
            finally:
                self.context = None

        if self.browser:
            try:
                await self.browser.close()
                logger.info("浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {str(e)}")
            finally:
                self.browser = None

        if self.playwright:
            try:
                await self.playwright.stop()
                logger.info("Playwright已停止")
            except Exception as e:
                logger.error(f"停止Playwright时出错: {str(e)}")
            finally:
                self.playwright = None

        self.page = None
        logger.info("所有浏览器资源已释放")

    # 变量存储文件路径
    VARIABLES_FILE = "variables.json"

    def load_variables_from_file(self):
        """从文件加载变量数据"""
        try:
            if os.path.exists(self.VARIABLES_FILE):
                with open(self.VARIABLES_FILE, "r", encoding="utf-8") as f:
                    file_variables = json.load(f)
                    # 合并文件中的变量到内存变量
                    self.variables.update(file_variables)
                    logger.info(f"从文件加载了 {len(file_variables)} 个变量")
        except Exception as e:
            logger.error(f"从文件加载变量失败: {str(e)}")

    def save_variables_to_file(self):
        """将变量数据保存到文件"""
        try:
            with open(self.VARIABLES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.variables, f, ensure_ascii=False, indent=2)
                logger.info(f"保存了 {len(self.variables)} 个变量到文件")
                return True
        except Exception as e:
            logger.error(f"保存变量到文件失败: {str(e)}")
            return False

    def set_variable(self, var_name: str, value: str):
        """设置变量值"""
        self.variables[var_name] = value
        logger.info(f"设置变量: {var_name} = {value}")
        # 同时保存到文件
        self.save_variables_to_file()

    def get_variable(self, var_name: str) -> str:
        """获取变量值，支持从配置文件加载预定义变量"""
        logger.info(f"尝试获取变量: {var_name}")

        # 如果内存中没有，尝试从文件加载
        if var_name not in self.variables:
            logger.info(f"变量 {var_name} 不在内存中，尝试从文件加载")
            self.load_variables_from_file()

        # 获取现有值
        existing_value = self.variables.get(var_name, "")
        logger.info(f"从内存获取变量 {var_name} = {existing_value}")

        # 如果变量不存在或值为空，尝试从变量配置中生成
        if not existing_value:
            logger.info(f"变量 {var_name} 值为空，尝试从配置文件生成")
            value = self.generate_variable_from_config(var_name)
            if value:
                # 缓存生成的值（对于随机数，每次执行生成一次），并落盘保存
                # 供用例列表页"变量管理"弹窗展示本次执行实际解析出的变量值，方便排查问题
                self.variables[var_name] = value
                self.save_variables_to_file()
                logger.info(f"从配置生成并缓存变量: {var_name} = {value}")
                return value
            else:
                logger.warning(f"无法从配置文件生成变量: {var_name}")

        return existing_value

    def generate_variable_from_config(self, var_name: str) -> str:
        """从变量配置中生成变量值，根据当前环境和项目筛选"""
        try:
            import json
            import random

            # 获取配置文件的绝对路径（与其他配置文件在同一目录）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(current_dir, "variables_config.json")

            logger.info(
                f"尝试从配置文件加载变量: {var_name}, 配置文件路径: {config_file}"
            )
            logger.info(
                f"当前环境: {self.current_environment}, 当前项目: {self.current_project}"
            )

            if not os.path.exists(config_file):
                logger.warning(f"变量配置文件不存在: {config_file}")
                return ""

            with open(config_file, "r", encoding="utf-8") as f:
                configs = json.load(f)

            logger.info(f"成功读取变量配置，共 {len(configs)} 个配置项")

            # 查找匹配的变量配置，需要匹配名称、环境和项目
            matching_vars = [
                v for v in configs
                if v["name"] == var_name
                and v.get("environment", "全局") in [self.current_environment, "全局"]
                and (not v.get("project") or v.get("project", "") == self.current_project)
            ]

            if not matching_vars:
                logger.warning(
                    f"未找到匹配的变量配置: {var_name} (环境: {self.current_environment}, 项目: {self.current_project})"
                )
                return ""

            # 优先使用环境和项目都匹配的，其次环境匹配、项目为空的，最后使用全局环境的
            var_config = None
            for v in matching_vars:
                if v.get("environment") == self.current_environment and v.get("project") == self.current_project:
                    var_config = v
                    break
            if not var_config:
                for v in matching_vars:
                    if v.get("environment") == self.current_environment and not v.get("project"):
                        var_config = v
                        break
            if not var_config:
                var_config = matching_vars[0]

            logger.info(
                f"找到变量配置: {var_name}, 类型: {var_config.get('type')}, "
                f"环境: {var_config.get('environment')}, 项目: {var_config.get('project')}"
            )

            # 根据类型生成值
            if var_config["type"] == "fixed":
                value = var_config.get("value", "")
                logger.info(f"从配置加载固定变量: {var_name} = {value}")
                return value
            elif var_config["type"] == "random":
                min_val = var_config.get("minValue", 0)
                max_val = var_config.get("maxValue", 100)
                value = str(random.randint(min_val, max_val))
                logger.info(
                    f"从配置生成随机变量: {var_name} = {value} (范围: {min_val}-{max_val})"
                )
                return value

            return ""
        except Exception as e:
            logger.error(f"从配置生成变量失败: {str(e)}", exc_info=True)
            return ""

    def replace_variables(self, text: str) -> str:
        """替换文本中的变量引用
        支持格式:
        - ${变量名} 或 {{变量名}}
        - ${变量名 + 数字} 或 {{变量名 + 数字}} (支持 +, -, *, / 运算)
        示例: {{test_period + 2}} 会将 "3天" 转换为 "5天"
        """
        if not text:
            return text

        logger.info(f"开始替换变量，原始文本: {text}")

        # 确保加载了最新的变量
        self.load_variables_from_file()

        result = text

        # 替换 ${变量名} 格式（支持表达式）
        def replace_dollar_var(match):
            expression = match.group(1).strip()
            return self._evaluate_variable_expression(expression, "${}")

        # 替换 {{变量名}} 格式（支持表达式）
        def replace_brace_var(match):
            expression = match.group(1).strip()
            return self._evaluate_variable_expression(expression, "{{}}")

        result = re.sub(r"\$\{([^}]+)\}", replace_dollar_var, result)
        result = re.sub(r"\{\{([^}]+)\}\}", replace_brace_var, result)

        if result != text:
            logger.info(f"变量替换完成，结果文本: {result}")
        else:
            logger.info("未发现需要替换的变量")

        return result

    def _evaluate_variable_expression(self, expression: str, bracket_type: str) -> str:
        """计算变量表达式
        支持: 变量名 或 变量名 + 数字 或 变量名 - 数字 等
        示例: "test_period + 2" 将 "3天" 转换为 "5天"
        """
        # 检查是否包含运算符
        operators = ["+", "-", "*", "/"]
        has_operator = any(op in expression for op in operators)

        if not has_operator:
            # 简单变量替换
            var_name = expression.strip()
            var_value = self.get_variable(var_name)
            # 根据bracket_type格式化日志输出
            if bracket_type == "${}":
                logger.info(f"替换变量 ${{{var_name}}} = {var_value}")
            else:  # "{{}}"
                logger.info(f"替换变量 {{{{{var_name}}}}} = {var_value}")
            return var_value

        # 解析表达式 (变量名 运算符 数字)
        # 支持格式: "var_name + 2", "var_name - 1", "var_name * 2", "var_name / 2"
        pattern = r"^\s*(\w+)\s*([+\-*/])\s*(\d+(?:\.\d+)?)\s*$"
        match = re.match(pattern, expression)

        if not match:
            logger.warning(f"无法解析变量表达式: {expression}，返回原表达式")
            return expression

        var_name = match.group(1)
        operator = match.group(2)
        operand = float(match.group(3))

        # 获取变量值
        var_value = self.get_variable(var_name)

        if not var_value:
            logger.warning(f"变量 {var_name} 不存在或为空，返回原表达式")
            return expression

        # 从变量值中提取数字和单位
        # 支持格式: "3天", "5个月", "10.5小时", "100", "3.14"
        number_pattern = r"^([+-]?\d+(?:\.\d+)?)(.*?)$"
        value_match = re.match(number_pattern, var_value.strip())

        if not value_match:
            logger.warning(f"变量值 {var_value} 中未找到数字，返回原值")
            return var_value

        number = float(value_match.group(1))
        unit = value_match.group(2).strip()  # 单位部分（如"天", "个月"）

        # 执行运算
        try:
            if operator == "+":
                result_number = number + operand
            elif operator == "-":
                result_number = number - operand
            elif operator == "*":
                result_number = number * operand
            elif operator == "/":
                if operand == 0:
                    logger.error("除数不能为0，返回原值")
                    return var_value
                result_number = number / operand
            else:
                logger.warning(f"不支持的运算符: {operator}")
                return var_value

            # 如果结果是整数，转为整数格式
            if result_number == int(result_number):
                result_number = int(result_number)

            # 组合结果（数字 + 单位）
            result_value = f"{result_number}{unit}"

            logger.info(
                f"计算变量表达式: {var_name}({var_value}) {operator} {operand} = {result_value}"
            )

            return result_value

        except Exception as e:
            logger.error(f"计算变量表达式失败: {str(e)}")
            return var_value

    async def take_screenshot(
        self, step_name: str = "", is_error: bool = False
    ) -> Optional[str]:
        """根据配置决定是否截图"""
        if not self.save_screenshots or not self.page:
            return None

        try:
            timestamp = int(time.time())
            suffix = "_error" if is_error else ""
            screenshot_path = f"{SCREENSHOTS_DIR}/{timestamp}_{step_name}{suffix}.png"
            await self.page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"截图已保存: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return None

    async def check_element_with_timeout(self, selector: str, timeout: int = 3) -> bool:
        """检查元素是否存在，带超时设置"""
        if not self.page:
            return False

        try:
            await self.page.wait_for_selector(
                selector, state="visible", timeout=timeout * 1000
            )
            return True
        except Exception:
            return False

    def get_slide_locus(self, distance: float) -> List[int]:
        """
        使用您的方法生成滑动轨迹 - 基于物理加速度模型
        @param distance: 计算出的滑动距离
        @return: 返回滑动点的列表
        """
        logger.info(f"开始生成滑动轨迹，目标距离: {distance:.1f}px")

        # 输入验证
        if distance <= 0:
            logger.warning(f"距离无效: {distance}, 使用默认轨迹")
            return [5, 8, 10, 12, 10, 8, 5]

        # 使用您的方法生成轨迹
        tracks = get_slide_locus(distance)

        final_distance = sum(tracks)
        logger.info(
            f"轨迹生成完成: 目标={distance:.1f}px, 实际={final_distance:.1f}px, 步数={len(tracks)}"
        )
        logger.info(f"轨迹: {tracks}")

        return tracks

    def get_slide_distance(self) -> float:
        """
        获取未补偿前的滑动距离
        @return:
        """
        try:
            save_directory = SCREENSHOTS_DIR
            slider = os.path.join(save_directory, "slider.jpg")
            background = os.path.join(save_directory, "background.jpg")

            # 检查图片文件是否存在
            if not os.path.exists(slider) or not os.path.exists(background):
                logger.warning("滑块或背景图片不存在，使用默认距离")
                return 160

            slider_pic = cv2.imread(slider, 0)
            background_pic = cv2.imread(background, 0)

            if slider_pic is None or background_pic is None:
                logger.warning("无法读取图片，使用默认距离")
                return 160

            # 获取缺口图数组的形状 -->缺口图的宽和高
            width, height = slider_pic.shape[::-1]

            # 将处理之后的图片另存
            slider01 = os.path.join(save_directory, "slider01.jpg")
            background_01 = os.path.join(save_directory, "background01.jpg")
            cv2.imwrite(background_01, background_pic)
            cv2.imwrite(slider01, slider_pic)

            # 读取另存的滑块图
            slider_pic = cv2.imread(slider01)
            # 进行色彩转换
            slider_pic = cv2.cvtColor(slider_pic, cv2.COLOR_BGR2GRAY)
            # 获取色差的绝对值
            slider_pic = abs(255 - slider_pic)
            # 保存图片
            cv2.imwrite(slider01, slider_pic)

            # 读取滑块
            slider_pic = cv2.imread(slider01)
            # 读取背景图
            background_pic = cv2.imread(background_01)

            # 比较两张图的重叠区域
            result = cv2.matchTemplate(slider_pic, background_pic, cv2.TM_CCOEFF_NORMED)
            # 获取图片的缺口位置
            top, left = np.unravel_index(result.argmax(), result.shape)

            # 背景图中的图片缺口坐标位置
            print("当前滑块的缺口位置：", (left, top, left + width, top + height))
            logger.info(
                f"当前滑块的缺口位置: ({left}, {top}, {left + width}, {top + height})"
            )

            return float(left)

        except Exception as e:
            logger.error(f"距离计算失败: {str(e)}")
            return 160

    async def download_slider_images(self) -> bool:
        """下载滑块验证的图片 - 按照您的方法"""
        if not self.page:
            return False

        try:
            frame_xpath = ClientLoginBase().sliderVerificationIframeXpath()

            # 使用您的方法下载滑块图片
            logger.info("下载滑块图片...")
            slider_success = await download_images(
                self.page,
                image_name="slider",
                frame_xpath=frame_xpath,
                image_xpath=ClientLoginBase().sliderPicXpath(),
                save_directory=SCREENSHOTS_DIR,
            )

            # 使用您的方法下载背景图片
            logger.info("下载背景图片...")
            background_success = await download_images(
                self.page,
                image_name="background",
                frame_xpath=frame_xpath,
                image_xpath=ClientLoginBase().sliderBackPicXpath(),
                save_directory=SCREENSHOTS_DIR,
            )

            if slider_success and background_success:
                logger.info("下载滑块图片成功")
                return True
            else:
                logger.error("下载滑块图片失败")
                return False

        except Exception as e:
            logger.error(f"下载滑块图片失败: {str(e)}")
            return False

    async def refresh_slider(self):
        """刷新滑块按钮"""
        try:
            frame_xpath = "//iframe[@id='tcaptcha_iframe']"
            frame_locator = self.page.frame_locator(frame_xpath)

            # 尝试多种刷新按钮选择器
            refresh_selectors = [
                "//div[@aria-label='刷新']/div",
                "//div[@class='tc-action-item tc-reload']",
                "//div[contains(@class,'reload')]",
                "//div[contains(@class,'refresh')]",
                "//span[contains(@class,'reload')]",
                "//div[@title='刷新']",
            ]

            refresh_clicked = False
            for selector in refresh_selectors:
                try:
                    logger.info(f"尝试刷新按钮选择器: {selector}")
                    refresh_button = frame_locator.locator(selector)
                    await refresh_button.click(timeout=3000)
                    logger.info(f"点击刷新滑块按钮成功 (使用选择器: {selector})")
                    refresh_clicked = True
                    break
                except Exception as e:
                    logger.warning(f"刷新选择器 {selector} 失败: {str(e)}")
                    continue

            if not refresh_clicked:
                logger.warning("所有刷新按钮选择器都失败了")

            await asyncio.sleep(2)  # 等待刷新完成
        except Exception as e:
            logger.warning(f"刷新滑块失败: {str(e)}")

    async def save_login_state(self):
        """保存登录状态到cookie文件"""
        try:
            ss_file = os.path.join(
                os.path.dirname(__file__), "..", "cookie", "client_login_data.json"
            )

            # 确保cookie目录存在
            cookie_dir = os.path.dirname(ss_file)
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)

            # 保存存储状态
            await self.context.storage_state(path=ss_file)
            logger.info(f"登录状态已保存到: {ss_file}")
        except Exception as e:
            logger.error(f"保存登录状态失败: {str(e)}")

    async def dragbox_location(self) -> Optional[Dict[str, float]]:
        """获取滑块位置 - 使用您的方法"""
        if not self.page:
            return None

        try:
            # 使用您的方法获取滑块位置
            position = await dragbox_location(self.page)
            if position:
                logger.info(
                    f"找到滑块位置: x={position['x']:.1f}, y={position['y']:.1f}, w={position['width']:.1f}, h={position['height']:.1f}"
                )
                return position
            else:
                logger.error("无法找到滑块元素")
                return None
        except Exception as e:
            logger.error(f"获取滑块位置失败: {str(e)}")
            return None

    async def handle_slide_captcha_step(self) -> Dict[str, Any]:
        """处理滑动滑块验证步骤 - 作为独立的测试步骤"""
        if not self.page:
            raise RuntimeError("Playwright未初始化")

        logger.info("执行滑动滑块验证步骤")

        try:
            # 直接调用与登录官网相同的滑块验证方法
            success = await self.handle_slider_verification()

            # 截图
            screenshot_path = await self.take_screenshot("slide_captcha")

            if success:
                logger.info("滑动滑块验证步骤执行成功")
                return {
                    "success": True,
                    "screenshot": screenshot_path,
                    "message": "滑动滑块验证成功",
                }
            else:
                logger.error("滑动滑块验证步骤执行失败")
                return {
                    "success": False,
                    "screenshot": screenshot_path,
                    "error": "滑动滑块验证失败",
                }

        except Exception as e:
            logger.error(f"滑动滑块验证步骤异常: {str(e)}")
            screenshot_path = await self.take_screenshot("slide_captcha", is_error=True)
            return {"success": False, "screenshot": screenshot_path, "error": str(e)}

    async def handle_slider_verification(self) -> bool:
        """处理滑块验证"""
        if not self.page:
            return False

        logger.info("开始处理滑块验证...")

        try:
            # 第一步：获取滑动验证窗口的XPATH
            frame_xpath = "//iframe[@id='tcaptcha_iframe']"
            if not await self.check_element_with_timeout(frame_xpath, timeout=3):
                logger.info("未检测到滑块验证iframe")
                return True

            logger.info("检测到滑块验证iframe，开始处理...")

            # 持续重试直到成功（最多重试5次）
            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                retry_count += 1
                logger.info(f"滑块验证尝试 {retry_count}/{max_retries}")
                try:
                    # 首先检查控制台是否已存在（验证是否已成功）
                    console_selector = "//a[contains(text(),'控制台')]"
                    if await self.check_element_with_timeout(
                        console_selector, timeout=1
                    ):
                        logger.info("检测到控制台元素，滑块验证已成功")
                        # 登录成功，保存cookie
                        await self.save_login_state()
                        return True

                    # 第二步：分别下载背景图和滑块图
                    logger.info("开始下载滑块验证图片...")
                    if not await self.download_slider_images():
                        logger.warning("下载滑块图片失败，刷新滑块后重试")
                        await self.refresh_slider()
                        continue

                    # 获取滑块位置
                    position = await self.dragbox_location()
                    if not position:
                        logger.warning("无法获取滑块位置，刷新滑块后重试")
                        await self.refresh_slider()
                        continue

                    # 第三步：精确计算滑动距离和轨迹
                    start_x = position["x"] + position["width"] / 2
                    start_y = position["y"] + position["height"] / 2

                    # 快速获取滑动距离
                    raw_distance = self.get_slide_distance()
                    logger.info(f"图像识别距离: {raw_distance:.1f}px")

                    try:
                        # 按照您的代码执行滑动验证
                        frame_xpath = ClientLoginBase().sliderVerificationIframeXpath()
                        await download_images(
                            self.page,
                            image_name="slider",
                            frame_xpath=frame_xpath,
                            image_xpath=ClientLoginBase().sliderPicXpath(),
                            save_directory=SCREENSHOTS_DIR,
                        )
                        await download_images(
                            self.page,
                            image_name="background",
                            frame_xpath=frame_xpath,
                            image_xpath=ClientLoginBase().sliderBackPicXpath(),
                            save_directory=SCREENSHOTS_DIR,
                        )
                        logger.info("下载滑块图片成功")

                        position = await dragbox_location(self.page)
                        if not position:
                            logger.warning("无法获取滑块位置，刷新滑块后重试")
                            await self.refresh_slider()
                            continue

                        x = position["x"] + position["width"] / 2
                        y = position["y"] + position["height"] / 2
                        distance = get_slide_locus(
                            self.get_slide_distance() * (280 / 680) + 6
                        )
                        logger.info(f"计算滑块的滑动距离成功,滑动距离为：{distance}")

                        await self.page.mouse.move(x, y)
                        await self.page.mouse.down()
                        for i in distance:
                            x = x + i
                            await self.page.mouse.move(x, y)
                        await self.page.mouse.up()

                        logger.info(f"滑动完成: 最终位置=({x:.1f}, {y:.1f})")

                    except Exception as slide_error:
                        logger.error(f"滑动失败: {str(slide_error)}")
                        # 确保鼠标被释放
                        try:
                            await self.page.mouse.up()
                        except:
                            pass
                        await self.refresh_slider()
                        continue

                    # 减少等待时间，更快检查结果
                    await asyncio.sleep(1.5)  # 从2秒减少到1.5秒

                    # 第五步：检查控制台是否存在
                    if await self.check_element_with_timeout(
                        console_selector, timeout=3
                    ):
                        logger.info("滑块验证成功！检测到控制台元素")
                        # 登录成功，保存cookie
                        await self.save_login_state()
                        return True

                    # 没有成功，点击刷新滑块按钮，重复上述步骤
                    logger.info("验证失败，刷新滑块重试...")
                    await self.refresh_slider()

                except Exception as e:
                    logger.error(f"滑块验证过程出错: {str(e)}")
                    await self.refresh_slider()
                    continue

            # 超过最大重试次数
            logger.error(f"滑块验证失败：已重试{max_retries}次，仍未成功")
            return False

        except Exception as e:
            logger.error(f"处理滑块验证时发生错误: {str(e)}")
            return False

    async def open_url(self, url: str) -> Dict[str, Any]:
        """打开指定URL"""
        if not self.page:
            raise RuntimeError("Playwright未初始化")

        # 替换URL中的变量
        url = self.replace_variables(url)
        logger.info(f"打开网址: {url}")
        try:
            # 判断URL对应的域名，注入相应的Authorization token
            from urllib.parse import urlparse

            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower()
            logger.info(f"解析URL hostname: {hostname}")

            token_to_inject = None
            matched_profile_name = None

            for profile in self.auth_profiles:
                domains = [d.lower() for d in profile.get("domains", []) if d]
                if hostname in domains and profile.get("token"):
                    token_to_inject = profile.get("token")
                    matched_profile_name = profile.get("name")
                    logger.info(
                        f"检测到域名 {hostname} 匹配Authorization配置「{matched_profile_name}」，准备设置Authorization请求头"
                    )
                    break

            # 如果有token需要注入
            if token_to_inject:
                # 统一：通过HTTP请求头注入 Authorization
                await self.context.set_extra_http_headers(
                    {"Authorization": token_to_inject}
                )
                logger.info("成功设置Authorization请求头")
                logger.info(f"Token前50字符: {token_to_inject[:50]}...")

            # 增加超时时间并确保等待网络空闲
            response = await self.page.goto(
                url, timeout=60000, wait_until="networkidle"
            )
            status = response.status if response else "未知"
            logger.info(f"页面加载完成，状态码: {status}")

            # 等待额外时间确保页面稳定
            await asyncio.sleep(1)

            # 获取页面标题
            title = await self.page.title()
            logger.info(f"页面标题: {title}")

            # 截图
            screenshot_path = await self.take_screenshot("open_url")

            return {
                "title": title,
                "status": status,
                "screenshot": screenshot_path,
                "success": True,
            }
        except Exception as e:
            logger.error(f"打开网址失败: {str(e)}")
            screenshot_path = await self.take_screenshot("open_url", is_error=True)
            return {
                "error": str(e),
                "screenshot": screenshot_path,
                "success": False,
            }

    async def click_element(self, selector: str) -> Dict[str, Any]:
        """点击指定元素"""
        if not self.page:
            raise RuntimeError("Playwright未初始化")

        # 替换选择器中的变量
        selector = self.replace_variables(selector)
        logger.info(f"点击元素: {selector}")

        try:
            # 记录点击前的状态
            before_url = self.page.url
            before_page_count = len(self.context.pages) if self.context else 0
            logger.info(f"点击前URL: {before_url}")

            # 先检查元素是否在下拉菜单中（可能需要等待更长时间）
            element = await self.page.wait_for_selector(
                selector, state="attached", timeout=10000
            )

            # 等待元素稳定并可见
            try:
                await self.page.wait_for_selector(
                    selector, state="visible", timeout=5000
                )
            except Exception:
                logger.warning("元素不可见，尝试滚动到可见区域")
                # 如果不可见，尝试滚动到元素位置
                await element.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)

            # 先尝试正常点击（不使用force，确保触发所有事件）
            try:
                await self.page.click(selector, timeout=5000)
                logger.info(f"点击元素成功（正常点击）: {selector}")
            except Exception as e:
                # 如果正常点击失败，使用force点击（适用于下拉菜单等特殊场景）
                logger.warning(f"正常点击失败，尝试强制点击: {str(e)}")
                await self.page.click(selector, force=True, timeout=5000)
                logger.info(f"点击元素成功（强制点击）: {selector}")

            # 等待短暂时间让点击事件触发
            await asyncio.sleep(0.3)

            # 检测是否打开了新页面/新标签页
            if self.context and len(self.context.pages) > before_page_count:
                new_page = self.context.pages[-1]
                if new_page != self.page:
                    logger.info(
                        f"检测到打开新页面，从 {len(self.context.pages) - 1} 个页面变为 {len(self.context.pages)} 个"
                    )
                    self.page = new_page
                    logger.info("已切换到新打开的页面")
                    # 等待新页面加载
                    try:
                        await self.page.wait_for_load_state(
                            "domcontentloaded", timeout=5000
                        )
                    except Exception:
                        pass

            # 等待可能的SPA路由跳转或页面加载
            await asyncio.sleep(0.5)
            after_url = self.page.url

            # 检测是否跳转到登录页面（被强制登出）
            if "/login" in after_url and "/login" not in before_url:
                logger.warning(f"检测到被重定向到登录页面: {after_url}")

                # 检查是否需要重新设置Authorization token
                from urllib.parse import urlparse

                parsed = urlparse(after_url)
                hostname = (parsed.hostname or "").lower()

                token_to_reinject = None
                for profile in self.auth_profiles:
                    domains = [d.lower() for d in profile.get("domains", []) if d]
                    if hostname in domains and profile.get("token"):
                        token_to_reinject = profile.get("token")
                        break

                # 如果找到匹配当前域名的Authorization配置，重新设置
                if token_to_reinject:
                    logger.info(f"尝试重新注入Authorization token到域名: {hostname}")

                    # 方法1: 设置HTTP请求头
                    try:
                        await self.context.set_extra_http_headers(
                            {"Authorization": token_to_reinject}
                        )
                        logger.info("已设置Authorization请求头")
                    except Exception as e:
                        logger.warning(f"设置请求头失败: {str(e)}")

                    # 方法2: 注入到Cookie
                    try:
                        await self.context.add_cookies(
                            [
                                {
                                    "name": "Authorization",
                                    "value": token_to_reinject,
                                    "domain": hostname,
                                    "path": "/",
                                    "httpOnly": False,
                                    "secure": False,
                                    "sameSite": "Lax",
                                }
                            ]
                        )
                        logger.info("已注入Authorization到Cookie")
                    except Exception as e:
                        logger.warning(f"注入Cookie失败: {str(e)}")

                    # 尝试返回上一页
                    try:
                        logger.info(f"尝试返回原页面: {before_url}")
                        await self.page.goto(
                            before_url, timeout=15000, wait_until="domcontentloaded"
                        )
                        await asyncio.sleep(1)
                        current_url = self.page.url

                        # 检查是否还在登录页面
                        if "/login" in current_url:
                            logger.error(
                                "返回后仍在登录页面，Authorization token可能已失效"
                            )
                        else:
                            logger.info(f"成功返回原页面: {current_url}")

                            # 返回成功后，重新执行点击操作
                            logger.info("尝试重新点击元素...")
                            await asyncio.sleep(1)  # 等待页面完全加载

                            try:
                                # 等待元素出现
                                element = await self.page.wait_for_selector(
                                    selector, state="visible", timeout=5000
                                )
                                # 重新点击
                                await self.page.click(selector, timeout=5000)
                                logger.info("重新点击成功")

                                # 等待页面跳转
                                await asyncio.sleep(2)
                                after_url = self.page.url
                                logger.info(f"重新点击后URL: {after_url}")
                            except Exception as click_error:
                                logger.warning(f"重新点击失败: {str(click_error)}")
                    except Exception as e:
                        logger.error(f"返回原页面失败: {str(e)}")

            # 检测URL是否变化（SPA路由跳转）
            elif after_url != before_url:
                logger.info(f"检测到URL变化: {before_url} -> {after_url}")
                # URL变化了，等待页面稳定
                await asyncio.sleep(1.0)
            else:
                # URL没变化，可能是传统页面跳转或普通交互
                try:
                    await self.page.wait_for_load_state(
                        "domcontentloaded", timeout=3000
                    )
                except Exception:
                    # 如果没有页面跳转，只是普通点击，这里超时是正常的
                    pass
                await asyncio.sleep(0.5)

            # 截图
            screenshot_path = await self.take_screenshot("click")

            return {"screenshot": screenshot_path, "success": True}
        except Exception as e:
            logger.error(f"点击元素失败: {str(e)}")
            screenshot_path = await self.take_screenshot("click", is_error=True)
            return {
                "error": str(e),
                "screenshot": screenshot_path,
                "success": False,
            }

    async def wait_seconds(self, seconds: str) -> Dict[str, Any]:
        """等待指定秒数"""
        logger.info(f"等待时长: {seconds}秒")
        try:
            wait_time = float(seconds)
            await asyncio.sleep(wait_time)
            logger.info(f"等待完成: {wait_time}秒")

            # 截图
            screenshot_path = await self.take_screenshot("wait")

            return {"screenshot": screenshot_path, "success": True}
        except Exception as e:
            logger.error(f"等待失败: {str(e)}")
            return {"error": str(e), "success": False}

    async def fill_text(self, selector: str, text: str) -> Dict[str, Any]:
        """在指定元素中填入文本"""
        if not self.page:
            raise RuntimeError("Playwright未初始化")

        # 替换选择器和文本中的变量
        selector = self.replace_variables(selector)
        text = self.replace_variables(text)

        logger.info(f"填入文本: {selector} = {text}")
        try:
            # 等待元素出现
            await self.page.wait_for_selector(selector, state="visible", timeout=10000)

            # 获取元素信息
            element = await self.page.query_selector(selector)
            if element:
                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                class_name = await element.get_attribute("class") or ""

                logger.info(f"元素标签: {tag_name}, class: {class_name}")

                # 判断是否是ant-design的Select组件
                if "ant-select" in class_name or tag_name == "div":
                    logger.info("检测到可能是Select组件或div元素，尝试点击后输入")

                    # 先点击元素打开下拉框或激活输入
                    await self.page.click(selector)
                    logger.info("已点击元素，等待输入框出现")

                    # 等待更长时间，特别是弹窗内的元素
                    await asyncio.sleep(1)

                    # 尝试找到打开的输入框（ant-design会创建一个input）
                    try:
                        # 尝试多个可能的输入框选择器
                        input_selectors = [
                            "input.ant-select-search__field:visible",
                            "input.ant-input:visible",
                            ".ant-select-dropdown input:visible",
                            "input[type='text']:visible",
                        ]

                        input_found = False
                        for input_selector in input_selectors:
                            try:
                                await self.page.wait_for_selector(
                                    input_selector, state="visible", timeout=3000
                                )
                                logger.info(f"找到输入框: {input_selector}")

                                # 在输入框中输入文本
                                await self.page.fill(input_selector, text)
                                logger.info(f"在Select组件的输入框中成功输入: {text}")

                                # 等待一下让下拉选项出现并稳定
                                await asyncio.sleep(1.2)

                                # 不自动按Enter，让用户通过下一步点击操作来选择具体选项
                                logger.info("输入完成，等待后续点击操作选择具体选项")

                                input_found = True
                                break
                            except Exception:
                                continue

                        if not input_found:
                            raise Exception("未找到任何输入框")

                    except Exception as select_error:
                        logger.warning(
                            f"Select组件输入框处理失败: {str(select_error)}，尝试直接键盘输入"
                        )
                        # 如果找不到输入框，尝试直接keyboard输入
                        await asyncio.sleep(0.5)
                        await self.page.keyboard.type(text)
                        await asyncio.sleep(1.2)
                        # 不自动按Enter，让用户通过下一步点击操作来选择具体选项
                        logger.info("使用键盘输入完成，等待后续点击操作")
                else:
                    # 普通输入框，使用原来的逻辑
                    # 先清空现有内容
                    await self.page.fill(selector, "")

                    # 填入文本
                    await self.page.fill(selector, text)
                    logger.info(f"填入文本成功: {selector}")

            # 截图
            screenshot_path = await self.take_screenshot("input")

            return {"screenshot": screenshot_path, "success": True}

        except Exception as e:
            logger.error(f"填入文本失败: {str(e)}")
            screenshot_path = await self.take_screenshot("input", is_error=True)
            return {
                "error": str(e),
                "screenshot": screenshot_path,
                "success": False,
            }

    async def check_element_exists(self, selector: str) -> Dict[str, Any]:
        """检查指定元素是否存在"""
        if not self.page:
            raise RuntimeError("Playwright未初始化")

        # 替换选择器中的变量
        selector = self.replace_variables(selector)
        logger.info(f"检查元素存在: {selector}")
        try:
            # 元素可能因页面跳转/异步渲染尚未出现，等待最多5秒（而非只查询一次）
            try:
                element = await self.page.wait_for_selector(
                    selector, timeout=5000, state="visible"
                )
            except Exception:
                element = None

            if element:
                # 元素存在，进一步检查是否可见
                is_visible = await element.is_visible()
                logger.info(f"元素存在且可见: {selector}")

                # 截图
                screenshot_path = await self.take_screenshot("check_element_exists")

                return {
                    "screenshot": screenshot_path,
                    "success": True,
                    "message": f"元素存在且可见: {selector}",
                }
            else:
                logger.error(f"元素不存在: {selector}")
                screenshot_path = await self.take_screenshot(
                    "check_element_exists", is_error=True
                )
                return {
                    "error": f"元素不存在: {selector}",
                    "screenshot": screenshot_path,
                    "success": False,
                }

        except Exception as e:
            logger.error(f"检查元素存在性失败: {str(e)}")
            screenshot_path = await self.take_screenshot(
                "check_element_exists", is_error=True
            )
            return {
                "error": str(e),
                "screenshot": screenshot_path,
                "success": False,
            }

    async def check_element_not_exists(self, selector: str) -> Dict[str, Any]:
        """检查指定元素不存在（元素不存在时返回成功）"""
        if not self.page:
            raise RuntimeError("Playwright未初始化")

        # 替换选择器中的变量
        selector = self.replace_variables(selector)
        logger.info(f"检查元素不存在: {selector}")
        try:
            # 尝试查找元素，设置较短的超时时间
            element = await self.page.query_selector(selector)

            if element:
                # 元素存在，检查是否可见
                is_visible = await element.is_visible()
                if is_visible:
                    logger.error(f"元素存在且可见（预期不存在）: {selector}")
                    screenshot_path = await self.take_screenshot(
                        "check_element_not_exists", is_error=True
                    )
                    return {
                        "error": f"元素存在（预期不存在）: {selector}",
                        "screenshot": screenshot_path,
                        "success": False,
                    }
                else:
                    # 元素存在但不可见，认为是不存在
                    logger.info(f"元素不可见（视为不存在）: {selector}")
                    screenshot_path = await self.take_screenshot(
                        "check_element_not_exists"
                    )
                    return {
                        "screenshot": screenshot_path,
                        "success": True,
                        "message": f"元素不存在（验证通过）: {selector}",
                    }
            else:
                # 元素不存在，符合预期
                logger.info(f"元素不存在（验证通过）: {selector}")
                screenshot_path = await self.take_screenshot("check_element_not_exists")
                return {
                    "screenshot": screenshot_path,
                    "success": True,
                    "message": f"元素不存在（验证通过）: {selector}",
                }

        except Exception as e:
            logger.error(f"检查元素不存在失败: {str(e)}")
            screenshot_path = await self.take_screenshot(
                "check_element_not_exists", is_error=True
            )
            return {
                "error": str(e),
                "screenshot": screenshot_path,
                "success": False,
            }

    async def get_element_text(
        self, selector: str, var_name: str = ""
    ) -> Dict[str, Any]:
        """获取指定元素的文案"""
        if not self.page:
            raise RuntimeError("Playwright未初始化")

        # 替换选择器中的变量
        selector = self.replace_variables(selector)
        logger.info(f"获取元素的文案: {selector}")

        try:
            # 等待元素可见
            await self.page.wait_for_selector(selector, state="visible", timeout=10000)

            # 获取元素文案
            element = await self.page.query_selector(selector)
            if element:
                text_content = await element.text_content()
                inner_text = (
                    await element.inner_text()
                    if hasattr(element, "inner_text")
                    else text_content
                )

                # 使用更准确的文本内容
                element_text = (
                    inner_text.strip()
                    if inner_text
                    else (text_content.strip() if text_content else "")
                )

                logger.info(f"成功获取元素文案: [{element_text}]")

                # 如果指定了变量名，保存到变量中
                if var_name:
                    self.set_variable(var_name, element_text)

                # 截图
                screenshot_path = await self.take_screenshot("get_element_text")

                return {
                    "screenshot": screenshot_path,
                    "success": True,
                    "message": f"成功获取元素文案: {element_text}"
                    + (f"，已保存到变量 {var_name}" if var_name else ""),
                    "element_text": element_text,
                    "variable_name": var_name if var_name else None,
                }
            else:
                logger.error(f"元素不存在: {selector}")
                screenshot_path = await self.take_screenshot(
                    "get_element_text", is_error=True
                )
                return {
                    "error": f"元素不存在: {selector}",
                    "screenshot": screenshot_path,
                    "success": False,
                }

        except Exception as e:
            logger.error(f"获取元素文案失败: {str(e)}")
            screenshot_path = await self.take_screenshot(
                "get_element_text", is_error=True
            )
            return {
                "error": str(e),
                "screenshot": screenshot_path,
                "success": False,
            }

    async def verify_element_value(
        self, selector: str, expected_value: str
    ) -> Dict[str, Any]:
        """验证指定元素的值是否等于期望值"""
        if not self.page:
            raise RuntimeError("Playwright未初始化")

        # 替换选择器和期望值中的变量
        selector = self.replace_variables(selector)
        expected_value = self.replace_variables(expected_value)
        logger.info(f"验证元素的值: {selector}, 期望值: {expected_value}")
        try:
            # 等待元素可见
            await self.page.wait_for_selector(selector, state="visible", timeout=10000)

            # 获取元素
            element = await self.page.query_selector(selector)
            if element:
                # 获取元素的值，尝试多种属性
                element_value = ""

                # 尝试获取 value 属性（适用于 input 元素）
                value_attr = await element.get_attribute("value")
                if value_attr is not None:
                    element_value = value_attr.strip()
                else:
                    # 尝试获取文本内容（适用于普通元素）
                    text_content = await element.text_content()
                    inner_text = (
                        await element.inner_text()
                        if hasattr(element, "inner_text")
                        else text_content
                    )
                    element_value = (
                        inner_text.strip()
                        if inner_text
                        else (text_content.strip() if text_content else "")
                    )

                logger.info(
                    f"获取到元素实际值: [{element_value}], 期望值: [{expected_value}]"
                )

                # 进行值比较
                if element_value == expected_value.strip():
                    logger.info(
                        f"验证成功: 元素值 [{element_value}] 等于期望值 [{expected_value}]"
                    )

                    # 截图
                    screenshot_path = await self.take_screenshot("verify_element_value")

                    return {
                        "screenshot": screenshot_path,
                        "success": True,
                        "message": f"验证成功: 元素值 [{element_value}] 等于期望值 [{expected_value}]",
                        "actual_value": element_value,
                        "expected_value": expected_value,
                    }
                else:
                    logger.error(
                        f"验证失败: 元素值 [{element_value}] 不等于期望值 [{expected_value}]"
                    )
                    screenshot_path = await self.take_screenshot(
                        "verify_element_value", is_error=True
                    )
                    return {
                        "error": f"验证失败: 元素值 [{element_value}] 不等于期望值 [{expected_value}]",
                        "screenshot": screenshot_path,
                        "success": False,
                        "actual_value": element_value,
                        "expected_value": expected_value,
                    }
            else:
                logger.error(f"元素不存在: {selector}")
                screenshot_path = await self.take_screenshot(
                    "verify_element_value", is_error=True
                )
                return {
                    "error": f"元素不存在: {selector}",
                    "screenshot": screenshot_path,
                    "success": False,
                }

        except Exception as e:
            logger.error(f"验证元素值失败: {str(e)}")
            screenshot_path = await self.take_screenshot(
                "verify_element_value", is_error=True
            )
            return {
                "error": str(e),
                "screenshot": screenshot_path,
                "success": False,
            }

    async def verify_variable_value(
        self, var_name: str, expected_value: str
    ) -> Dict[str, Any]:
        """验证指定变量的值是否等于期望值"""
        logger.info(f"验证变量值: {var_name}, 期望值: {expected_value}")

        try:
            # 获取变量的实际值
            if var_name in self.variables:
                actual_value = self.variables[var_name]
                logger.info(
                    f"获取到变量 '{var_name}' 的实际值: [{actual_value}], 期望值: [{expected_value}]"
                )

                # 进行值比较
                if str(actual_value).strip() == str(expected_value).strip():
                    logger.info(
                        f"验证成功: 变量 '{var_name}' 的值 [{actual_value}] 等于期望值 [{expected_value}]"
                    )

                    # 截图
                    screenshot_path = await self.take_screenshot(
                        "verify_variable_value"
                    )

                    return {
                        "screenshot": screenshot_path,
                        "success": True,
                        "message": f"验证成功: 变量 '{var_name}' 的值 [{actual_value}] 等于期望值 [{expected_value}]",
                        "actual_value": actual_value,
                        "expected_value": expected_value,
                        "variable_name": var_name,
                    }
                else:
                    logger.error(
                        f"验证失败: 变量 '{var_name}' 的值 [{actual_value}] 不等于期望值 [{expected_value}]"
                    )
                    screenshot_path = await self.take_screenshot(
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
                logger.error(f"变量不存在: {var_name}")
                screenshot_path = await self.take_screenshot(
                    "verify_variable_value", is_error=True
                )
                return {
                    "error": f"变量不存在: {var_name}",
                    "screenshot": screenshot_path,
                    "success": False,
                    "variable_name": var_name,
                    "available_variables": list(self.variables.keys()),
                }

        except Exception as e:
            logger.error(f"验证变量值失败: {str(e)}")
            screenshot_path = await self.take_screenshot(
                "verify_variable_value", is_error=True
            )
            return {
                "error": str(e),
                "screenshot": screenshot_path,
                "success": False,
            }

    async def login_website(
        self, login_params: Union[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """登录官网 - 封装完整的登录流程"""
        if not self.page:
            raise RuntimeError("Playwright未初始化")

        logger.info("开始执行登录官网流程")

        # 解析登录信息
        if isinstance(login_params, dict):
            # 新格式：从前端传来的字典参数
            website_url = login_params.get("website_url", "").strip()
            username = login_params.get("username", "").strip()
            password = login_params.get("password", "").strip()
            description = login_params.get("description", "")

            # 替换变量
            website_url = self.replace_variables(website_url)
            username = self.replace_variables(username)
            password = self.replace_variables(password)

            logger.info(
                f"使用新格式登录参数: 网站={website_url}, 用户名={username}, 描述={description}"
            )

            # 验证必要参数
            if not website_url:
                website_url = "https://bss-front-uat.sixents.com"
                logger.warning(f"网站地址为空，使用默认值: {website_url}")

            if not username:
                username = "18322369885"
                logger.warning(f"用户名为空，使用默认值: {username}")

            if not password:
                password = "YANGyang022"
                logger.warning(f"密码为空，使用默认值")
        else:
            # 兼容旧格式：从xpath字段解析（格式：用户名|密码|网站URL）
            logger.info("使用旧格式登录参数兼容模式")
            try:
                parts = str(login_params).split("|")
                if len(parts) >= 3:
                    username = parts[0]
                    password = parts[1]
                    website_url = parts[2]
                else:
                    # 如果没有提供完整信息，使用默认值
                    username = "18322369885"
                    password = "YANGyang022"
                    website_url = "https://bss-front-uat.sixents.com"
            except Exception:
                # 解析失败时使用默认值
                username = "18322369885"
                password = "YANGyang022"
                website_url = "https://bss-front-uat.sixents.com"

            # 替换变量（旧格式也需要支持变量）
            website_url = self.replace_variables(website_url)
            username = self.replace_variables(username)
            password = self.replace_variables(password)

        sub_steps = []

        try:
            # 步骤1: 打开官网首页
            logger.info(f"步骤1: 打开官网首页 - {website_url}")
            await self.page.goto(website_url)
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            screenshot_path = await self.take_screenshot("login_step1_open_homepage")

            sub_steps.append(
                {
                    "step_name": "打开官网首页",
                    "status": "success",
                    "screenshot": screenshot_path,
                    "details": f"成功打开 {website_url}",
                }
            )

            # 检查是否已经登录，如果已登录则先退出
            success_indicators = [
                "//a[contains(text(),'控制台')]",  # 主要成功标志
                "//div[contains(@class,'console')]",  # 控制台元素
                "//span[contains(text(),'欢迎')]",  # 欢迎信息
                "//a[contains(text(),'退出')]",  # 退出按钮
            ]

            already_logged_in = False
            for indicator in success_indicators:
                try:
                    await self.page.wait_for_selector(
                        indicator, state="visible", timeout=2000
                    )
                    already_logged_in = True
                    logger.info(f"检测到已登录标志: {indicator}")
                    break
                except:
                    continue

            if already_logged_in:
                logger.info("检测到用户已登录，需要先退出登录")

                # 尝试多种退出登录的方式
                logout_selectors = [
                    "//a[contains(text(),'退出')]",
                    "//button[contains(text(),'退出')]",
                    "//span[contains(text(),'退出')]",
                    "//div[contains(text(),'退出')]",
                    "//a[contains(text(),'退出登录')]",
                    "//button[contains(text(),'退出登录')]",
                ]

                logout_success = False
                for logout_selector in logout_selectors:
                    try:
                        # 检查退出按钮是否存在
                        element = await self.page.query_selector(logout_selector)
                        if element:
                            logger.info(f"找到退出按钮: {logout_selector}")
                            await self.page.click(logout_selector)
                            await asyncio.sleep(2)  # 等待退出完成
                            logout_success = True
                            screenshot_path = await self.take_screenshot(
                                "login_step_logout"
                            )
                            sub_steps.append(
                                {
                                    "step_name": "退出当前登录",
                                    "status": "success",
                                    "screenshot": screenshot_path,
                                    "details": "检测到已登录，已退出当前用户",
                                }
                            )
                            break
                    except Exception as e:
                        logger.debug(f"尝试退出按钮 {logout_selector} 失败: {str(e)}")
                        continue

                if not logout_success:
                    # 如果找不到退出按钮，尝试清除cookies后重新加载页面
                    logger.warning("未找到退出按钮，尝试清除cookies")
                    await self.context.clear_cookies()
                    await self.page.goto(website_url)
                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                    screenshot_path = await self.take_screenshot(
                        "login_step_clear_cookies"
                    )
                    sub_steps.append(
                        {
                            "step_name": "清除登录状态",
                            "status": "success",
                            "screenshot": screenshot_path,
                            "details": "通过清除cookies退出登录",
                        }
                    )

                logger.info("退出登录完成，准备重新登录")

            # 步骤2: 点击登录按钮
            logger.info("步骤2: 点击登录按钮")
            login_btn_selector = "//a[contains(text(),'登录')]"
            try:
                await self.page.wait_for_selector(
                    login_btn_selector, state="visible", timeout=5000
                )
                await self.page.click(login_btn_selector)
                await self.page.wait_for_load_state("networkidle", timeout=5000)
                screenshot_path = await self.take_screenshot("login_step2_click_login")

                sub_steps.append(
                    {
                        "step_name": "点击登录按钮",
                        "status": "success",
                        "screenshot": screenshot_path,
                        "details": "成功点击登录按钮",
                    }
                )
            except Exception as e:
                logger.warning(f"点击登录按钮失败，可能已在登录页面: {str(e)}")
                screenshot_path = await self.take_screenshot(
                    "login_step2_skip_login_btn"
                )
                sub_steps.append(
                    {
                        "step_name": "点击登录按钮",
                        "status": "skipped",
                        "screenshot": screenshot_path,
                        "details": "跳过，可能已在登录页面",
                    }
                )

            # 步骤3: 输入用户名
            logger.info(f"步骤3: 输入用户名 - {username}")
            username_selector = "//input[@placeholder='请输入账号或手机号码']"
            await self.page.wait_for_selector(
                username_selector, state="visible", timeout=10000
            )
            await self.page.fill(username_selector, username)
            screenshot_path = await self.take_screenshot("login_step3_input_username")

            sub_steps.append(
                {
                    "step_name": "输入用户名",
                    "status": "success",
                    "screenshot": screenshot_path,
                    "details": f"成功输入用户名: {username}",
                }
            )

            # 步骤4: 输入密码
            logger.info("步骤4: 输入密码")
            password_selector = "//input[@placeholder='请输入密码']"
            await self.page.wait_for_selector(
                password_selector, state="visible", timeout=10000
            )
            await self.page.fill(password_selector, password)
            screenshot_path = await self.take_screenshot("login_step4_input_password")

            sub_steps.append(
                {
                    "step_name": "输入密码",
                    "status": "success",
                    "screenshot": screenshot_path,
                    "details": "成功输入密码",
                }
            )

            # 步骤5: 勾选同意协议
            logger.info("步骤5: 勾选同意协议")
            agree_selector = "//span[text()='已阅读并同意']/..//input"
            try:
                await self.page.wait_for_selector(
                    agree_selector, state="visible", timeout=5000
                )
                is_checked = await self.page.is_checked(agree_selector)
                if not is_checked:
                    await self.page.click(agree_selector)

                # 检查是否有协议弹窗需要处理
                logger.info("检查协议弹窗...")
                if await self.check_element_with_timeout(
                    "//span[contains(text(),'同意（')]", timeout=3
                ):
                    logger.info("检测到协议弹窗，开始处理...")
                    await asyncio.sleep(11)  # 等待11秒

                    try:
                        # 第一次点击同意
                        await self.page.click("//span[text()='同 意']")
                        logger.info("第一次点击同意按钮成功")
                        await asyncio.sleep(16)  # 等待16秒

                        # 第二次点击同意
                        await self.page.click("//span[text()='同 意']")
                        logger.info("第二次点击同意按钮成功")
                    except Exception as agree_error:
                        logger.warning(f"处理协议弹窗失败: {str(agree_error)}")

                screenshot_path = await self.take_screenshot("login_step5_agree_terms")

                sub_steps.append(
                    {
                        "step_name": "勾选同意协议",
                        "status": "success",
                        "screenshot": screenshot_path,
                        "details": "成功勾选同意协议并处理弹窗",
                    }
                )
            except Exception as e:
                logger.warning(f"勾选协议失败: {str(e)}")
                screenshot_path = await self.take_screenshot(
                    "login_step5_agree_terms_failed"
                )
                sub_steps.append(
                    {
                        "step_name": "勾选同意协议",
                        "status": "failed",
                        "screenshot": screenshot_path,
                        "details": f"勾选协议失败: {str(e)}",
                    }
                )

            # 步骤6: 点击登录提交按钮
            logger.info("步骤6: 点击登录提交按钮")
            submit_selector = "//button[contains(text(),'登录') or @type='submit']"
            await self.page.wait_for_selector(
                submit_selector, state="visible", timeout=10000
            )
            await self.page.click(submit_selector)

            # 等待登录结果
            await asyncio.sleep(2)
            screenshot_path = await self.take_screenshot("login_step6_submit_login")

            sub_steps.append(
                {
                    "step_name": "点击登录提交按钮",
                    "status": "success",
                    "screenshot": screenshot_path,
                    "details": "成功点击登录提交按钮",
                }
            )

            # 步骤7: 处理验证码（如果存在）
            logger.info("步骤7: 检查验证码")
            try:
                # 检查是否有滑块验证码
                slider_frame_selector = "//iframe[contains(@src,'captcha')] | //iframe[@id='tcaptcha_iframe']"
                slider_count = await self.page.locator(slider_frame_selector).count()

                if slider_count > 0:
                    logger.info("检测到滑块验证码，开始自动处理...")
                    await asyncio.sleep(3)  # 等待验证码加载

                    # 使用我们的滑块验证处理函数
                    slider_success = await self.handle_slider_verification()

                    screenshot_path = await self.take_screenshot(
                        "login_step7_captcha_handled"
                    )

                    if slider_success:
                        sub_steps.append(
                            {
                                "step_name": "处理滑块验证码",
                                "status": "success",
                                "screenshot": screenshot_path,
                                "details": "滑块验证码处理成功",
                            }
                        )
                    else:
                        sub_steps.append(
                            {
                                "step_name": "处理滑块验证码",
                                "status": "failed",
                                "screenshot": screenshot_path,
                                "details": "滑块验证码处理失败，可能需要人工处理",
                            }
                        )
                else:
                    screenshot_path = await self.take_screenshot(
                        "login_step7_no_captcha"
                    )
                    sub_steps.append(
                        {
                            "step_name": "检查验证码",
                            "status": "success",
                            "screenshot": screenshot_path,
                            "details": "无验证码",
                        }
                    )
            except Exception as e:
                logger.warning(f"检查验证码失败: {str(e)}")
                screenshot_path = await self.take_screenshot(
                    "login_step7_captcha_check_failed"
                )
                sub_steps.append(
                    {
                        "step_name": "检查验证码",
                        "status": "failed",
                        "screenshot": screenshot_path,
                        "details": f"检查验证码失败: {str(e)}",
                    }
                )

            # 步骤8: 验证登录状态
            logger.info("步骤8: 验证登录状态")
            await asyncio.sleep(3)  # 等待页面跳转

            # 检查登录是否成功（通过页面元素判断）
            success_indicators = [
                "//a[contains(text(),'控制台')]",  # 主要成功标志
                "//div[contains(@class,'console')]",  # 控制台元素
                "//span[contains(text(),'欢迎')]",  # 欢迎信息
                "//a[contains(text(),'退出')]",  # 退出按钮
                "//div[contains(@class,'user')]",  # 用户信息区域
            ]

            login_success = False
            for indicator in success_indicators:
                try:
                    await self.page.wait_for_selector(
                        indicator, state="visible", timeout=3000
                    )
                    login_success = True
                    logger.info(f"检测到登录成功标志: {indicator}")
                    break
                except:
                    continue

            screenshot_path = await self.take_screenshot("login_step8_verify_status")

            if login_success:
                sub_steps.append(
                    {
                        "step_name": "验证登录状态",
                        "status": "success",
                        "screenshot": screenshot_path,
                        "details": "登录成功，检测到用户已登录状态",
                    }
                )

                logger.info("登录官网流程执行成功")
                return {
                    "success": True,
                    "sub_steps": sub_steps,
                    "screenshot": screenshot_path,
                    "message": "登录官网成功",
                }
            else:
                sub_steps.append(
                    {
                        "step_name": "验证登录状态",
                        "status": "failed",
                        "screenshot": screenshot_path,
                        "details": "登录失败，未检测到登录成功标识",
                    }
                )

                return {
                    "success": False,
                    "sub_steps": sub_steps,
                    "screenshot": screenshot_path,
                    "error": "登录验证失败",
                }

        except Exception as e:
            logger.error(f"登录官网流程失败: {str(e)}")
            screenshot_path = await self.take_screenshot("login_error", is_error=True)

            sub_steps.append(
                {
                    "step_name": "登录流程异常",
                    "status": "error",
                    "screenshot": screenshot_path,
                    "details": f"登录流程异常: {str(e)}",
                }
            )

            return {
                "success": False,
                "sub_steps": sub_steps,
                "screenshot": screenshot_path,
                "error": str(e),
            }

    async def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个测试步骤"""
        logger.info(f"执行步骤: {step}")

        # 获取操作类型和参数
        action = step.get("operate", "")
        xpath = step.get("xpath", "")
        input_value = step.get("input_value", "")
        description = step.get("describe", "")

        # 获取定位方式（xpath/css/text），用于需要定位元素的操作类型
        locate_type = step.get("locate_type", "xpath")

        # 获取验证元素值专用字段
        expected_value = step.get("expected_value", "")

        # 获取变量名字段（用于存储获取的文案）
        var_name = step.get("var_name", "")

        logger.info(
            f"步骤详情: 操作={action}, XPath={xpath}, 定位方式={locate_type}, 输入值={input_value}, 期望值={expected_value}, 变量名={var_name}, 描述={description}"
        )

        try:
            if action == "open_url":
                return await self.open_url(xpath)
            elif action == "click":
                return await self.click_element(build_selector(xpath, locate_type))
            elif action == "input":
                return await self.fill_text(
                    build_selector(xpath, locate_type), input_value
                )
            elif action == "wait":
                return await self.wait_seconds(xpath)
            elif action == "check_element_exists":
                return await self.check_element_exists(
                    build_selector(xpath, locate_type)
                )
            elif action == "check_element_not_exists":
                return await self.check_element_not_exists(
                    build_selector(xpath, locate_type)
                )
            elif action == "get_element_text":
                return await self.get_element_text(
                    build_selector(xpath, locate_type), var_name
                )
            elif action == "verify_element_value":
                return await self.verify_element_value(
                    build_selector(xpath, locate_type), expected_value
                )
            elif action == "verify_variable_value":
                return await self.verify_variable_value(var_name, expected_value)
            else:
                logger.warning(f"未实现的操作类型: {action}")
                return {
                    "success": False,
                    "error": f"未实现的操作类型: {action}",
                }
        except Exception as e:
            logger.error(f"执行步骤失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }


def expand_testcase_steps(steps, visited_case_ids=None):
    """
    展开步骤列表中的"引用其他用例"(reference_testcase)步骤：
    用被引用用例的完整步骤列表（递归展开）替换该步骤，使执行时能在原位置
    依次执行被引用用例的每一步，报告中也能看到展开后每一步的详情。

    保存用例时已做循环引用检测拒绝保存，这里的visited_case_ids是执行期的兜底防护
    （防止历史数据或未走过保存校验的数据在执行时死循环），命中时跳过该引用步骤并记录警告。

    Args:
        steps: 原始步骤列表
        visited_case_ids: 当前展开路径上已访问过的用例ID集合（用于兜底防循环）

    Returns:
        展开后的步骤列表
    """
    if visited_case_ids is None:
        visited_case_ids = set()

    try:
        with open("data.json", "r", encoding="utf-8") as f:
            all_testcases = json.load(f)
        cases_by_id = {tc["id"]: tc for tc in all_testcases}
    except Exception as e:
        logger.error(f"展开引用用例步骤时读取data.json失败: {str(e)}")
        cases_by_id = {}

    expanded = []
    for step in steps:
        if step.get("operate") != "reference_testcase":
            expanded.append(step)
            continue

        ref_id = step.get("referenced_case_id")
        referenced_case = cases_by_id.get(ref_id) if ref_id else None

        if not referenced_case:
            logger.warning(f"引用的用例不存在或未指定(ID={ref_id})，跳过该引用步骤")
            continue

        if ref_id in visited_case_ids:
            logger.warning(f"检测到执行期循环引用(ID={ref_id})，跳过该引用步骤")
            continue

        logger.info(f"展开引用用例: ID={ref_id}, 名称={referenced_case.get('name')}")
        sub_steps = expand_testcase_steps(
            referenced_case.get("testcase_step", []),
            visited_case_ids | {ref_id},
        )
        expanded.extend(sub_steps)

    return expanded


async def execute_test_case(
    test_case: Dict[str, Any], config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """执行完整测试用例"""
    if config is None:
        config = {}

    # 获取执行配置
    browser_name = config.get("browser", "chrome")
    headless = config.get("headless", False)
    save_screenshots = config.get("saveScreenshots", False)
    custom_name = config.get("reportName", "")
    auth_profiles = (
        test_case.get("_authProfiles")
        if test_case.get("_authProfiles") is not None
        else config.get("authProfiles", [])
    )

    # 获取"是否使用登录态"开关下组装好的Cookie（按项目+环境匹配的Cookie类型变量）
    cookies = (
        test_case.get("_loginStateCookies")
        if test_case.get("_loginStateCookies") is not None
        else config.get("loginStateCookies")
    )

    # 获取环境和项目信息
    environment = config.get("executeEnvironment") or test_case.get("environment", "")
    project = test_case.get("project", "")

    case_id = test_case.get("id")
    case_name = test_case.get("name", "未命名测试")
    steps = expand_testcase_steps(
        test_case.get("testcase_step", []), {case_id} if case_id else set()
    )

    # 使用自定义名称或默认名称
    report_name = custom_name if custom_name else case_name

    logger.info(
        f"开始执行测试用例: ID={case_id}, 名称={case_name}, 报告名称={report_name}, 步骤数={len(steps)}"
    )
    logger.info(
        f"执行配置: 浏览器={browser_name}, 无头模式={headless}, 保存截图={save_screenshots}"
    )

    # 记录认证信息
    if cookies:
        if isinstance(cookies, list):
            logger.info(f"使用登录态Cookie，共 {len(cookies)} 个")
        elif isinstance(cookies, dict):
            logger.info(f"使用storage_state格式的Cookie")

    for profile in auth_profiles:
        logger.info(
            f"检测到Authorization配置: {profile.get('name')} -> 域名: {profile.get('domains')}"
        )

    executor = None
    start_time = time.time()
    from datetime import datetime

    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []

    try:
        # 初始化测试执行器 - 使用配置参数
        try:
            executor = await TestExecutor().initialize(
                browser_name=browser_name,
                headless=headless,
                save_screenshots=save_screenshots,
                width=1920,
                height=1080,
                auth_profiles=auth_profiles,
                cookies=cookies,
                environment=environment,
                project=project,
            )
        except Exception as init_error:
            logger.error(f"浏览器初始化失败: {str(init_error)}")
            # 浏览器初始化失败，直接返回失败报告
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
                        "action": "浏览器初始化",
                        "value": "",
                        "describe": f"浏览器初始化失败: {str(init_error)}",
                        "result": "fail",
                        "details": {"error": str(init_error)},
                    }
                ],
                "executed_cases": [{"id": case_id, "name": case_name}],
            }

        # 执行测试步骤
        for i, step in enumerate(steps):
            logger.info(
                f"开始执行步骤 {i + 1}/{len(steps)}: {step.get('describe', '未知步骤')}"
            )

            try:
                step_result = await executor.execute_step(step)
                logger.info(
                    f"步骤 {i + 1} 执行完成: {step_result.get('success', False)}"
                )
            except Exception as step_exception:
                logger.error(f"步骤 {i + 1} 执行时发生异常: {str(step_exception)}")
                step_result = {
                    "success": False,
                    "error": f"步骤执行异常: {str(step_exception)}",
                    "screenshot": None,
                }

            # 获取操作的中文名称
            action_name = OPERATION_MAPPING.get(
                step.get("operate", ""), step.get("operate", "未知操作")
            )

            step_info = {
                "case_id": case_id,
                "case_name": case_name,
                "step_number": i + 1,
                "action": action_name,
                "value": step.get("xpath", ""),
                "describe": step.get("describe", ""),
                "result": ("success" if step_result.get("success", False) else "fail"),
                "details": step_result,
            }

            results.append(step_info)
            logger.info(f"步骤 {i + 1} 结果已记录: {step_info['result']}")

            # 如果步骤失败且不是最后一个步骤，记录后续步骤为跳过
            if not step_result.get("success", False) and i < len(steps) - 1:
                logger.warning(
                    f"步骤 {i + 1} 失败，跳过后续 {len(steps) - i - 1} 个步骤"
                )
                for j in range(i + 1, len(steps)):
                    skipped_step = steps[j]
                    skipped_action = OPERATION_MAPPING.get(
                        skipped_step.get("operate", ""),
                        skipped_step.get("operate", "未知操作"),
                    )
                    skip_info = {
                        "case_id": case_id,
                        "case_name": case_name,
                        "step_number": j + 1,
                        "action": skipped_action,
                        "value": skipped_step.get("xpath", ""),
                        "describe": skipped_step.get("describe", ""),
                        "result": "skip",
                        "details": {"message": "由于前序步骤失败而跳过"},
                    }
                    results.append(skip_info)
                    logger.info(f"步骤 {j + 1} 已标记为跳过")
                break

        logger.info(f"所有步骤执行完成，共记录 {len(results)} 个步骤结果")

    except Exception as e:
        logger.error(f"测试执行过程中发生错误: {str(e)}")
        # 确保异常信息不会覆盖已有的步骤结果
        error_step_number = len(results) + 1
        results.append(
            {
                "case_id": case_id,
                "case_name": case_name,
                "step_number": error_step_number,
                "action": "测试过程异常",
                "value": "",
                "describe": f"测试执行过程中发生错误: {str(e)}",
                "result": "error",
                "details": {"error": str(e)},
            }
        )

    finally:
        # 确保关闭浏览器
        if executor:
            await executor.close()

    # 计算执行时间
    end_time = time.time()
    duration_seconds = end_time - start_time
    minutes, seconds = divmod(int(duration_seconds), 60)
    duration = f"{int(minutes):02d}:{int(seconds):02d}"

    # 计算通过率 - 对于单个用例，任何步骤失败都算用例失败
    total_steps = len(results)
    passed_steps = sum(1 for r in results if r["result"] == "success")
    failed_steps = sum(1 for r in results if r["result"] == "fail")

    # 单个用例的通过率：所有步骤都成功才算100%，否则0%
    pass_rate = 100 if failed_steps == 0 and total_steps > 0 else 0

    # 日志记录最终统计
    logger.info(
        f"测试执行统计: 总步骤={total_steps}, 通过={passed_steps}, 失败={failed_steps}, 用例通过率={pass_rate}%"
    )

    # 统计各类结果的数量
    result_counts = {}
    for result in results:
        result_type = result["result"]
        result_counts[result_type] = result_counts.get(result_type, 0) + 1

    logger.info(f"步骤结果分布: {result_counts}")

    # 构建测试报告
    report = {
        "id": int(time.time()),
        "test_id": case_id,  # 保持原有的单个用例ID
        "name": report_name,
        "time": start_time_str,
        "status": "success" if pass_rate == 100 else "fail",
        "pass_rate": pass_rate,
        "duration": duration,
        "config": config,
        "steps": results,
        # 新增用例信息，用于报告列表显示
        "executed_cases": [{"id": case_id, "name": case_name}],
    }

    if config.get("description"):
        report["description"] = config.get("description")

    logger.info(
        f"测试执行完成: 报告名称={report_name}, 通过率={pass_rate}%, 耗时={duration}"
    )

    return report


async def execute_test_case_and_capture_auth_token(
    test_case: Dict[str, Any], config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    执行一个（通常是登录）测试用例，同时监听浏览器网络请求，
    抓取最后一次带 Authorization 请求头的请求，作为Token值返回。
    用于变量管理中"Authorization"类型变量选择"引用登录测试用例获取"时调用。

    返回: {"success": bool, "token": str, "error": str}
    """
    if config is None:
        config = {}

    browser_name = config.get("browser", "chrome")
    headless = config.get("headless", False)

    case_name = test_case.get("name", "未命名测试")
    steps = test_case.get("testcase_step", [])

    logger.info(f"开始执行登录用例并抓取Authorization: {case_name}, 步骤数={len(steps)}")

    captured_token: Dict[str, str] = {"value": ""}

    def on_request(request):
        try:
            headers = request.headers
            auth_header = headers.get("authorization")
            if auth_header:
                captured_token["value"] = auth_header
        except Exception as capture_error:
            logger.warning(f"读取请求头失败: {str(capture_error)}")

    executor = None
    try:
        executor = await TestExecutor().initialize(
            browser_name=browser_name,
            headless=headless,
            save_screenshots=False,
            width=1920,
            height=1080,
        )

        # 监听所有请求，抓取Authorization请求头（登录成功后签发的最新token会覆盖之前的值）
        executor.page.on("request", on_request)

        for i, step in enumerate(steps):
            logger.info(f"[抓取Token] 执行步骤 {i + 1}/{len(steps)}: {step.get('describe', '未知步骤')}")
            step_result = await executor.execute_step(step)
            if not step_result.get("success", False):
                logger.warning(f"[抓取Token] 步骤 {i + 1} 执行失败: {step_result.get('error')}")

        if captured_token["value"]:
            logger.info(f"抓取到Authorization Token (前50字符): {captured_token['value'][:50]}...")
            return {"success": True, "token": captured_token["value"]}
        else:
            logger.warning("登录用例执行完成，但未捕获到任何Authorization请求头")
            return {"success": False, "error": "未捕获到Authorization请求头，请检查登录用例是否能正常完成登录"}

    except Exception as e:
        logger.error(f"执行登录用例抓取Token失败: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        if executor:
            await executor.close()


async def execute_test_case_and_capture_cookies(
    test_case: Dict[str, Any], config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    执行一个（通常是登录）测试用例，执行完成后读取浏览器上下文的Cookie，
    以JSON数组形式返回。
    用于变量管理中"Cookie"类型变量选择"引用登录测试用例获取"时调用。

    返回: {"success": bool, "cookies": str, "error": str}  # cookies为JSON字符串
    """
    if config is None:
        config = {}

    browser_name = config.get("browser", "chrome")
    headless = config.get("headless", False)

    case_name = test_case.get("name", "未命名测试")
    steps = test_case.get("testcase_step", [])

    logger.info(f"开始执行登录用例并抓取Cookie: {case_name}, 步骤数={len(steps)}")

    executor = None
    try:
        executor = await TestExecutor().initialize(
            browser_name=browser_name,
            headless=headless,
            save_screenshots=False,
            width=1920,
            height=1080,
        )

        for i, step in enumerate(steps):
            logger.info(f"[抓取Cookie] 执行步骤 {i + 1}/{len(steps)}: {step.get('describe', '未知步骤')}")
            step_result = await executor.execute_step(step)
            if not step_result.get("success", False):
                logger.warning(f"[抓取Cookie] 步骤 {i + 1} 执行失败: {step_result.get('error')}")

        cookies_list = await executor.context.cookies()

        if cookies_list:
            logger.info(f"抓取到Cookie，共 {len(cookies_list)} 个")
            return {"success": True, "cookies": json.dumps(cookies_list, ensure_ascii=False)}
        else:
            logger.warning("登录用例执行完成，但浏览器上下文中没有任何Cookie")
            return {"success": False, "error": "未捕获到Cookie，请检查登录用例是否能正常完成登录"}

    except Exception as e:
        logger.error(f"执行登录用例抓取Cookie失败: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        if executor:
            await executor.close()


async def execute_batch_test_cases(
    test_cases: List[Dict[str, Any]], config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """顺序执行批量测试用例并生成汇总报告"""
    if config is None:
        config = {}

    # 获取执行配置
    browser_name = config.get("browser", "chrome")
    headless = config.get("headless", False)
    save_screenshots = config.get("saveScreenshots", False)

    logger.info(f"开始顺序执行测试用例: 数量={len(test_cases)}")
    logger.info(
        f"执行配置: 浏览器={browser_name}, 无头模式={headless}, 保存截图={save_screenshots}"
    )

    executor = None
    start_time = time.time()
    from datetime import datetime

    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    batch_results = []
    total_steps = 0
    total_passed_steps = 0
    case_results_summary = []  # 新增：跟踪每个用例的成功/失败状态

    try:
        # 初始化测试执行器 - 使用配置参数（Authorization配置改为逐个用例动态设置）
        # 获取第一个用例的环境和项目信息用于初始化（之后每个用例会更新）
        first_env = config.get("executeEnvironment") or (test_cases[0].get("environment", "") if test_cases else "")
        first_project = test_cases[0].get("project", "") if test_cases else ""

        executor = await TestExecutor().initialize(
            browser_name=browser_name,
            headless=headless,
            save_screenshots=save_screenshots,
            width=1920,
            height=1080,
            environment=first_env,
            project=first_project,
        )

        # 逐个执行测试用例
        for i, test_case in enumerate(test_cases):
            case_id = test_case.get("id")
            case_name = test_case.get("name", "未命名测试")
            steps = expand_testcase_steps(
                test_case.get("testcase_step", []), {case_id} if case_id else set()
            )

            # 更新当前用例的环境和项目信息
            current_env = config.get("executeEnvironment") or test_case.get("environment", "")
            current_project = test_case.get("project", "")
            executor.current_environment = current_env
            executor.current_project = current_project

            logger.info(
                f"执行测试用例 {i + 1}/{len(test_cases)}: ID={case_id}, 名称={case_name}, 环境={current_env}, 项目={current_project}"
            )

            # 按当前用例所属项目/环境设置对应的Authorization配置
            executor.set_auth_profiles(test_case.get("_authProfiles", []))

            case_start_time = time.time()
            case_results = []

            # 执行当前用例的所有步骤
            for j, step in enumerate(steps):
                step_result = await executor.execute_step(step)

                # 获取操作的中文名称
                action_name = OPERATION_MAPPING.get(
                    step.get("operate", ""), step.get("operate", "未知操作")
                )

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
                total_steps += 1

                if step_result.get("success", False):
                    total_passed_steps += 1

                # 如果步骤失败且不是最后一个步骤，记录后续步骤为跳过
                if not step_result.get("success", False) and j < len(steps) - 1:
                    logger.warning(f"用例 {case_name} 第 {j + 1} 步失败，跳过后续步骤")
                    for k in range(j + 1, len(steps)):
                        skipped_step = steps[k]
                        skipped_action = OPERATION_MAPPING.get(
                            skipped_step.get("operate", ""),
                            skipped_step.get("operate", "未知操作"),
                        )
                        skip_info = {
                            "case_id": case_id,
                            "case_name": case_name,
                            "step_number": k + 1,
                            "action": skipped_action,
                            "value": skipped_step.get("xpath", ""),
                            "describe": skipped_step.get("describe", ""),
                            "result": "skip",
                            "details": {"message": "由于前序步骤失败而跳过"},
                        }
                        case_results.append(skip_info)
                        total_steps += 1
                    break

            # 计算当前用例的执行时间和通过率
            case_end_time = time.time()
            case_duration = case_end_time - case_start_time
            case_passed = sum(1 for r in case_results if r["result"] == "success")
            case_failed = sum(1 for r in case_results if r["result"] == "fail")
            case_total = len(
                [r for r in case_results if r["result"] in ["success", "fail"]]
            )

            # 用例级别的通过/失败判定：所有步骤都成功才算用例成功
            case_success = case_failed == 0 and case_total > 0
            case_pass_rate = 100 if case_success else 0

            # 记录用例级别的结果
            case_results_summary.append(
                {
                    "case_id": case_id,
                    "case_name": case_name,
                    "success": case_success,
                    "duration": case_duration,
                }
            )

            # 添加用例汇总信息
            batch_results.extend(case_results)

            logger.info(
                f"用例 {case_name} 执行完成: 用例状态={'成功' if case_success else '失败'}, 步骤通过率={case_passed}/{case_total}, 耗时={case_duration:.2f}秒"
            )

    except Exception as e:
        logger.error(f"批量测试执行过程中发生错误: {str(e)}")
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
        # 确保关闭浏览器
        if executor:
            await executor.close()

    # 计算总执行时间
    end_time = time.time()
    duration_seconds = end_time - start_time
    minutes, seconds = divmod(int(duration_seconds), 60)
    duration = f"{int(minutes):02d}:{int(seconds):02d}"

    # 计算总通过率 - 基于用例数而非步骤数
    total_cases = len(case_results_summary)
    passed_cases = sum(1 for case in case_results_summary if case["success"])
    failed_cases = total_cases - passed_cases
    overall_pass_rate = (
        int((passed_cases / total_cases) * 100) if total_cases > 0 else 0
    )

    # 判断状态：全部成功、部分成功、全部失败
    if passed_cases == total_cases:
        status = "success"
    elif passed_cases > 0 and failed_cases > 0:
        status = "partial"
    else:
        status = "fail"

    logger.info(
        f"批量执行汇总: 总用例数={total_cases}, 成功用例数={passed_cases}, 用例通过率={overall_pass_rate}%"
    )

    # 生成批量测试用例名称和用例信息
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
        batch_name = f"顺序批量执行: {', '.join(case_names[:3])}" + (
            f" 等{len(test_cases)}个用例" if len(test_cases) > 3 else ""
        )

    # 构建汇总测试报告
    batch_report = {
        "id": int(time.time()),
        "test_id": f"sequential_batch_{int(time.time())}",
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
        # 新增执行的用例信息
        "executed_cases": case_info_list,
    }

    if config and config.get("description"):
        batch_report["description"] = config.get("description")

    return batch_report


# 新增并行执行函数
async def execute_batch_test_cases_parallel(
    test_cases: List[Dict[str, Any]], config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """并行执行批量测试用例并生成汇总报告"""
    if config is None:
        config = {}

    logger.info(f"开始并行执行测试用例: 数量={len(test_cases)}")
    logger.info(f"执行配置: {config}")

    start_time = time.time()
    from datetime import datetime

    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 创建线程池，限制最大并发数
    max_workers = min(len(test_cases), 4)  # 最多4个并发线程
    logger.info(f"使用线程池并发数: {max_workers}")

    # 使用线程池执行器
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 为每个测试用例创建任务
        futures = []
        for test_case in test_cases:
            future = executor.submit(run_single_test_case_sync, test_case, config)
            futures.append((future, test_case))

        # 收集所有结果
        all_results = []
        total_steps = 0
        total_passed_steps = 0
        case_success_list = []  # 新增：记录每个用例的成功状态

        for future, test_case in futures:
            try:
                case_report = future.result(timeout=300)  # 5分钟超时
                all_results.extend(case_report["steps"])
                total_steps += case_report["total_steps"]
                total_passed_steps += case_report["passed_steps"]

                # 记录用例级别的成功状态
                case_success = case_report["pass_rate"] == 100
                case_success_list.append(
                    {
                        "case_id": test_case.get("id"),
                        "case_name": test_case.get("name"),
                        "success": case_success,
                    }
                )

                logger.info(
                    f"用例 {test_case.get('name')} 执行完成: 用例状态={'成功' if case_success else '失败'}"
                )
            except concurrent.futures.TimeoutError:
                logger.error(f"用例 {test_case.get('name')} 执行超时")
                error_step = {
                    "case_id": test_case.get("id"),
                    "case_name": test_case.get("name", "未命名测试"),
                    "step_number": 1,
                    "action": "执行超时",
                    "value": "",
                    "describe": "测试用例执行超时",
                    "result": "error",
                    "details": {"error": "执行超时（5分钟）"},
                }
                all_results.append(error_step)
                total_steps += 1

                # 记录失败的用例
                case_success_list.append(
                    {
                        "case_id": test_case.get("id"),
                        "case_name": test_case.get("name"),
                        "success": False,
                    }
                )
            except Exception as e:
                logger.error(f"用例 {test_case.get('name')} 执行失败: {str(e)}")
                error_step = {
                    "case_id": test_case.get("id"),
                    "case_name": test_case.get("name", "未命名测试"),
                    "step_number": 1,
                    "action": "执行异常",
                    "value": "",
                    "describe": "测试用例执行异常",
                    "result": "error",
                    "details": {"error": str(e)},
                }
                all_results.append(error_step)
                total_steps += 1

                # 记录失败的用例
                case_success_list.append(
                    {
                        "case_id": test_case.get("id"),
                        "case_name": test_case.get("name"),
                        "success": False,
                    }
                )

    # 计算总执行时间
    end_time = time.time()
    duration_seconds = end_time - start_time
    minutes, seconds = divmod(int(duration_seconds), 60)
    duration = f"{int(minutes):02d}:{int(seconds):02d}"

    # 计算总通过率 - 基于用例数而非步骤数
    total_cases = len(case_success_list)
    passed_cases = sum(1 for case in case_success_list if case["success"])
    failed_cases = total_cases - passed_cases
    overall_pass_rate = (
        int((passed_cases / total_cases) * 100) if total_cases > 0 else 0
    )

    # 判断状态：全部成功、部分成功、全部失败
    if passed_cases == total_cases:
        status = "success"
    elif passed_cases > 0 and failed_cases > 0:
        status = "partial"
    else:
        status = "fail"

    logger.info(
        f"并行执行汇总: 总用例数={total_cases}, 成功用例数={passed_cases}, 用例通过率={overall_pass_rate}%"
    )

    # 生成批量测试用例名称和用例信息
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
        batch_name = f"并行批量执行: {', '.join(case_names[:3])}" + (
            f" 等{len(test_cases)}个用例" if len(test_cases) > 3 else ""
        )

    # 构建汇总测试报告
    batch_report = {
        "id": int(time.time()),
        "test_id": f"parallel_batch_{int(time.time())}",
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
            "execution_mode": "parallel",
        },
        "steps": all_results,
        # 新增执行的用例信息
        "executed_cases": case_info_list,
    }

    if config and config.get("description"):
        batch_report["description"] = config.get("description")

    return batch_report


def run_single_test_case_sync(
    test_case: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """同步执行单个测试用例（用于线程池）"""
    try:
        # 在新的事件循环中执行异步代码
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            report = loop.run_until_complete(execute_test_case(test_case, config))

            # 返回用于汇总的数据
            return {
                "steps": report["steps"],
                "total_steps": len(
                    [s for s in report["steps"] if s["result"] in ["success", "fail"]]
                ),
                "passed_steps": len(
                    [s for s in report["steps"] if s["result"] == "success"]
                ),
                "pass_rate": report["pass_rate"],
            }
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"同步执行测试用例失败: {str(e)}")
        case_id = test_case.get("id")
        case_name = test_case.get("name", "未命名测试")

        error_step = {
            "case_id": case_id,
            "case_name": case_name,
            "step_number": 1,
            "action": "执行失败",
            "value": "",
            "describe": "测试用例执行失败",
            "result": "error",
            "details": {"error": str(e)},
        }

        return {
            "steps": [error_step],
            "total_steps": 1,
            "passed_steps": 0,
            "pass_rate": 0,
        }


def save_report(report: Dict[str, Any]) -> None:
    """保存测试报告到文件"""
    try:
        # 调试日志：保存前检查报告数据
        logger.info(
            f"准备保存报告 - ID: {report.get('id')}, 名称: {report.get('name', '未知')}"
        )
        logger.info(f"报告步骤数量: {len(report.get('steps', []))}")

        # 分析保存的步骤结果分布
        steps = report.get("steps", [])
        if steps:
            result_counts = {}
            for step in steps:
                result = step.get("result", "unknown")
                result_counts[result] = result_counts.get(result, 0) + 1
            logger.info(f"保存的步骤结果分布: {result_counts}")

            # 记录前几个步骤的详细信息
            logger.info("保存的前3个步骤详情:")
            for i, step in enumerate(steps[:3]):
                logger.info(
                    f"  步骤{i + 1}: {step.get('action', '未知')} - {step.get('result', '未知')} - {step.get('describe', '无描述')}"
                )
        else:
            logger.warning(f"准备保存的报告没有步骤数据")

        # 读取现有报告
        reports = []
        try:
            with open("reports.json", "r", encoding="utf-8") as f:
                reports = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            reports = []

        # 检查是否已存在相同ID的报告
        report_id = report.get("id")
        existing_index = None
        for i, r in enumerate(reports):
            if r.get("id") == report_id:
                existing_index = i
                logger.info(f"找到已存在的报告ID {report_id}，将更新而不是追加")
                break

        if existing_index is not None:
            # 更新现有报告
            reports[existing_index] = report
        else:
            # 添加新报告
            reports.append(report)

        # 写回文件
        with open("reports.json", "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        logger.info(
            f"测试报告保存成功: ID={report['id']}, 步骤数={len(report.get('steps', []))}"
        )
    except Exception as e:
        logger.error(f"保存测试报告失败: {str(e)}")
        # 添加更详细的错误信息
        logger.error(f"报告数据: {json.dumps(report, ensure_ascii=False, indent=2)}")


class CookieManager:
    """Cookie管理器 - 专门用于登录获取和保存Cookie"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def initialize(
        self,
        browser_name: str = "chrome",
        headless: bool = False,
        width: int = 1920,
        height: int = 1080,
    ):
        """初始化浏览器环境"""
        logger.info(f"初始化Cookie管理器浏览器环境: {browser_name}")

        try:
            self.playwright = await async_playwright().start()

            # 根据浏览器类型启动不同的浏览器
            if browser_name == "firefox":
                self.browser = await self.playwright.firefox.launch(
                    headless=headless, args=["--start-maximized"]
                )
            elif browser_name == "chromium":
                self.browser = await self.playwright.chromium.launch(
                    headless=headless, args=["--start-maximized"]
                )
            elif browser_name == "msedge":
                self.browser = await self.playwright.chromium.launch(
                    channel="msedge",
                    headless=headless,
                    args=["--start-maximized", "--disable-gpu"],
                )
            else:
                # 默认使用Chrome
                self.browser = await self.playwright.chromium.launch(
                    channel="chrome",
                    headless=headless,
                    args=["--start-maximized", "--disable-gpu"],
                )

            # 创建新的上下文（不加载已有的cookie）
            self.context = await self.browser.new_context(
                no_viewport=True, viewport=None
            )

            # 创建页面
            self.page = await self.context.new_page()

            logger.info("Cookie管理器浏览器初始化成功")
            return self

        except Exception as e:
            logger.error(f"Cookie管理器浏览器初始化失败: {str(e)}")
            await self.close()
            raise

    async def close(self):
        """关闭浏览器和资源"""
        logger.info("正在关闭Cookie管理器浏览器资源...")

        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                logger.error(f"关闭上下文时出错: {str(e)}")
            finally:
                self.context = None

        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {str(e)}")
            finally:
                self.browser = None

        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.error(f"停止Playwright时出错: {str(e)}")
            finally:
                self.playwright = None

        self.page = None
        logger.info("Cookie管理器浏览器资源已释放")

    async def login_and_save_cookie(
        self, login_params: Dict[str, str]
    ) -> Dict[str, Any]:
        """登录并保存Cookie"""
        logger.info("开始执行登录并保存Cookie流程")

        try:
            # 初始化浏览器（使用无头模式以提高效率）
            await self.initialize(browser_name="chrome", headless=False)

            # 创建TestExecutor实例来复用登录逻辑
            executor = TestExecutor()
            executor.browser = self.browser
            executor.context = self.context
            executor.page = self.page
            executor.save_screenshots = True  # 启用截图以便调试

            # 执行登录流程
            login_result = await executor.login_website(login_params)

            if login_result.get("success"):
                # 登录成功，保存Cookie
                cookie_file = os.path.join(
                    os.path.dirname(__file__), "..", "cookie", "client_login_data.json"
                )

                # 确保cookie目录存在
                cookie_dir = os.path.dirname(cookie_file)
                if not os.path.exists(cookie_dir):
                    os.makedirs(cookie_dir)

                # 保存存储状态（包含cookies、localStorage等）
                await self.context.storage_state(path=cookie_file)
                logger.info(f"Cookie已保存到: {cookie_file}")

                return {"success": True, "message": "登录成功，Cookie已保存"}
            else:
                logger.error(f"登录失败: {login_result.get('error')}")
                return {
                    "success": False,
                    "error": login_result.get("error", "登录失败"),
                }

        except Exception as e:
            logger.error(f"登录并保存Cookie失败: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            # 确保关闭浏览器资源
            await self.close()


class AdminCookieManager:
    """管理端Cookie管理器 - 专门用于管理端登录获取和保存Cookie"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def initialize(
        self,
        browser_name: str = "chrome",
        headless: bool = False,
        width: int = 1920,
        height: int = 1080,
    ):
        """初始化浏览器环境"""
        logger.info(f"初始化管理端Cookie管理器浏览器环境: {browser_name}")

        try:
            self.playwright = await async_playwright().start()

            # 根据浏览器类型启动不同的浏览器
            if browser_name == "firefox":
                self.browser = await self.playwright.firefox.launch(
                    headless=headless, args=["--start-maximized"]
                )
            elif browser_name == "chromium":
                self.browser = await self.playwright.chromium.launch(
                    headless=headless, args=["--start-maximized"]
                )
            elif browser_name == "msedge":
                self.browser = await self.playwright.chromium.launch(
                    channel="msedge",
                    headless=headless,
                    args=["--start-maximized", "--disable-gpu"],
                )
            else:
                # 默认使用Chrome
                self.browser = await self.playwright.chromium.launch(
                    channel="chrome",
                    headless=headless,
                    args=["--start-maximized", "--disable-gpu"],
                )

            # 创建新的上下文（不加载已有的cookie）
            self.context = await self.browser.new_context(
                no_viewport=True, viewport=None
            )

            # 创建页面
            self.page = await self.context.new_page()

            logger.info("管理端Cookie管理器浏览器初始化成功")
            return self

        except Exception as e:
            logger.error(f"管理端Cookie管理器浏览器初始化失败: {str(e)}")
            await self.close()
            raise

    async def close(self):
        """关闭浏览器和资源"""
        logger.info("正在关闭管理端Cookie管理器浏览器资源...")

        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                logger.error(f"关闭管理端上下文时出错: {str(e)}")
            finally:
                self.context = None

        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"关闭管理端浏览器时出错: {str(e)}")
            finally:
                self.browser = None

        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.error(f"停止管理端Playwright时出错: {str(e)}")
            finally:
                self.playwright = None

        self.page = None
        logger.info("管理端Cookie管理器浏览器资源已释放")

    async def login_and_save_cookie(
        self, login_params: Dict[str, str]
    ) -> Dict[str, Any]:
        """登录管理端并保存Cookie"""
        logger.info("开始执行管理端登录并保存Cookie流程")

        try:
            # 初始化浏览器（使用无头模式以提高效率）
            await self.initialize(browser_name="chrome", headless=False)

            # 创建TestExecutor实例来复用登录逻辑
            executor = TestExecutor()
            executor.browser = self.browser
            executor.context = self.context
            executor.page = self.page
            executor.save_screenshots = True  # 启用截图以便调试

            # 执行登录流程
            login_result = await executor.login_website(login_params)

            if login_result.get("success"):
                # 保存管理端Cookie到专门的文件
                admin_cookie_file = os.path.join(
                    os.path.dirname(__file__), "..", "cookie", "admin_login_data.json"
                )

                # 确保cookie目录存在
                cookie_dir = os.path.dirname(admin_cookie_file)
                if not os.path.exists(cookie_dir):
                    os.makedirs(cookie_dir)

                # 保存存储状态
                await self.context.storage_state(path=admin_cookie_file)
                logger.info(f"管理端登录状态已保存到: {admin_cookie_file}")

                return {
                    "success": True,
                    "message": "管理端登录成功，Cookie已保存",
                    "cookie_file": admin_cookie_file,
                }
            else:
                return {
                    "success": False,
                    "error": login_result.get("error", "管理端登录失败"),
                }

        except Exception as e:
            logger.error(f"管理端登录并保存Cookie失败: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            # 确保关闭浏览器资源
            await self.close()

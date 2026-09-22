import json
import logging
import time
import uuid
import os
from datetime import datetime
from flask_cors import CORS
from flask import Flask, jsonify, request, send_from_directory

# 导入测试执行器
from test_executor import (
    execute_test_case,
    save_report,
    execute_batch_test_cases,
    execute_batch_test_cases_parallel,
)

# 配置日志 - 同时输出到控制台和文件
LOG_FILE = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler(LOG_FILE, encoding="utf-8"),  # 输出到文件
    ],
)
logger = logging.getLogger("flask_api")

# 确保截图目录存在
SCREENSHOTS_DIR = "screenshots"
if not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)
    logger.info(f"创建截图目录: {SCREENSHOTS_DIR}")

# 设置文件路径
SETTINGS_FILE = "settings.json"
TASK_SETTINGS_FILE = "task_settings.json"  # 任务设置文件（独立于用例设置）

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="")
CORS(app)  # 启用 CORS

# 默认设置（用例设置）
DEFAULT_SETTINGS = {
    "defaultBrowser": "chrome",
    "defaultHeadless": False,
    "saveScreenshots": False,
    "enableMultiThread": False,
    "defaultEnvironment": "生产环境",
    "useAuthorization": True,
    "useLoginState": True,
}

# 默认任务设置（独立于用例设置，但字段结构与用例设置保持一致）
DEFAULT_TASK_SETTINGS = {
    "defaultBrowser": "chrome",
    "defaultHeadless": False,
    "saveScreenshots": False,
    "enableMultiThread": False,
    "defaultEnvironment": "生产环境",
    "useAuthorization": True,
    "useLoginState": True,
}


def load_settings():
    """加载设置配置"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                logger.info(f"加载设置成功: {settings}")
                return settings
        else:
            logger.info("设置文件不存在，使用默认设置")
            return DEFAULT_SETTINGS.copy()
    except Exception as e:
        logger.error(f"加载设置失败: {str(e)}")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """保存设置配置"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        logger.info(f"保存设置成功: {settings}")
        return True
    except Exception as e:
        logger.error(f"保存设置失败: {str(e)}")
        return False


def load_task_settings():
    """加载任务设置配置"""
    try:
        if os.path.exists(TASK_SETTINGS_FILE):
            with open(TASK_SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                logger.info(f"加载任务设置成功: {settings}")
                return settings
        else:
            logger.info("任务设置文件不存在，使用默认设置")
            return DEFAULT_TASK_SETTINGS.copy()
    except Exception as e:
        logger.error(f"加载任务设置失败: {str(e)}")
        return DEFAULT_TASK_SETTINGS.copy()


def save_task_settings(settings):
    """保存任务设置配置"""
    try:
        with open(TASK_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        logger.info(f"保存任务设置成功: {settings}")
        return True
    except Exception as e:
        logger.error(f"保存任务设置失败: {str(e)}")
        return False


def sync_extracted_variables_from_testcase(testcase_steps, project):
    """
    自动同步"提取变量"声明
    遍历用例步骤，对每个"获取元素文案"(get_element_text)步骤填写的var_name，
    如果variables_config.json中不存在同名+同环境+同项目的变量配置，则自动创建一条
    type=extracted的声明记录（不覆盖已存在的记录，避免覆盖执行后写入的真实值或用户已编辑的信息）。
    environment暂固定为"全局"（用例当前没有运行环境字段可同步）。

    Args:
        testcase_steps: 用例步骤列表
        project: 所属项目
    """
    try:
        var_names = {
            step.get("var_name", "").strip()
            for step in testcase_steps
            if step.get("operate") == "get_element_text" and step.get("var_name", "").strip()
        }
        if not var_names:
            return

        config = load_variables_config()
        existing_keys = {
            (v.get("name"), v.get("environment", "全局"), v.get("project", ""))
            for v in config
        }

        changed = False
        for var_name in var_names:
            key = (var_name, "全局", project or "")
            if key in existing_keys:
                continue
            config.append(
                {
                    "name": var_name,
                    "type": "extracted",
                    "description": "由用例步骤自动同步的提取变量声明",
                    "environment": "全局",
                    "project": project or "",
                    "value": "",
                }
            )
            existing_keys.add(key)
            changed = True

        if changed:
            save_variables_config(config)
            logger.info(f"自动同步提取变量声明: {sorted(var_names)}")
    except Exception as e:
        logger.error(f"自动同步提取变量声明失败: {str(e)}")


def find_reference_cycle(current_case_id, testcase_steps, all_testcases):
    """
    检测"引用其他用例"是否会形成循环引用。
    从当前用例出发，沿着reference_testcase步骤的引用链做DFS，
    如果在遍历路径中再次遇到current_case_id，则说明存在循环。

    Args:
        current_case_id: 当前正在保存的用例ID（新建用例时可传None，因为不可能被别人提前引用）
        testcase_steps: 当前正在保存的用例的步骤列表（用于取出它自己的引用关系）
        all_testcases: 所有已存在的用例列表（data.json内容），用于沿引用链继续往下查

    Returns:
        存在循环时返回循环路径上的用例名称列表（用于报错提示），否则返回None
    """
    cases_by_id = {tc["id"]: tc for tc in all_testcases}

    def get_referenced_ids(steps):
        return [
            step.get("referenced_case_id")
            for step in steps
            if step.get("operate") == "reference_testcase" and step.get("referenced_case_id")
        ]

    # 从当前用例的直接引用出发做DFS，path记录访问路径（用于检测回到current_case_id或路径中的重复节点）
    def dfs(case_id, steps, path):
        for ref_id in get_referenced_ids(steps):
            if ref_id == current_case_id or ref_id in path:
                return path + [ref_id]
            referenced_case = cases_by_id.get(ref_id)
            if not referenced_case:
                continue
            result = dfs(
                ref_id,
                referenced_case.get("testcase_step", []),
                path + [ref_id],
            )
            if result:
                return result
        return None

    cycle_ids = dfs(current_case_id, testcase_steps, [current_case_id] if current_case_id else [])
    if not cycle_ids:
        return None

    return [cases_by_id.get(cid, {}).get("name", f"ID:{cid}") for cid in cycle_ids if cid in cases_by_id]


def auto_create_missing_elements(testcase_steps, project, module, page):
    """
    自动创建缺失的元素
    遍历用例步骤，如果步骤中有xpath但element_id不存在或无效，则自动创建元素

    Args:
        testcase_steps: 用例步骤列表
        project: 所属项目
        module: 模块名称
        page: 页面名称
    """
    try:
        # 读取现有元素
        with open("elements.json", "r", encoding="utf-8") as f:
            elements = json.load(f)

        # 获取所有有效的element_id
        valid_element_ids = {elem["id"] for elem in elements}

        # 获取当前最大ID
        max_id = max([elem["id"] for elem in elements]) if elements else 0

        created_count = 0

        # 遍历步骤，查找需要创建的元素
        for step in testcase_steps:
            # 跳过不需要元素的操作
            operate = step.get("operate")
            if operate in [
                "open_url",
                "wait",
                "verify_variable_value",
            ]:
                continue

            # 元素库支持XPath和CSS两种定位方式，其他定位方式（如text）不写入元素库
            locate_type = step.get("locate_type", "xpath")
            if locate_type not in ("xpath", "css"):
                continue

            xpath = step.get("xpath", "").strip()
            element_id = step.get("element_id")

            # 如果有xpath但element_id不存在或无效，自动创建
            if xpath and (not element_id or element_id not in valid_element_ids):
                max_id += 1

                # 优先使用步骤中输入的元素名称，其次使用描述，最后使用默认名称
                input_element_name = step.get("element_name", "").strip()
                describe = step.get("describe", "")

                # 如果没有明确输入元素名称，从描述中提取
                if not input_element_name and describe:
                    # 如果描述中有"-"，取"-"前面的内容作为元素名称
                    if "-" in describe:
                        element_name = describe.split("-")[0].strip()
                    else:
                        # 没有"-"就用整个描述
                        element_name = describe.strip()
                else:
                    element_name = (
                        input_element_name if input_element_name else f"元素_{max_id}"
                    )

                # 创建新元素，描述格式为：模块-页面-名称
                new_element = {
                    "id": max_id,
                    "project": project,
                    "module": module,
                    "page": page,
                    "elementName": element_name,
                    "xpath": xpath,
                    "locate_type": locate_type,
                    "description": f"{module}-{page}-{element_name}",
                }

                elements.append(new_element)
                valid_element_ids.add(max_id)

                # 更新步骤中的element_id
                step["element_id"] = max_id

                created_count += 1
                logger.info(
                    f"自动创建元素: ID={max_id}, 名称={element_name}, xpath={xpath}"
                )

        # 如果有新创建的元素，保存到文件
        if created_count > 0:
            with open("elements.json", "w", encoding="utf-8") as f:
                json.dump(elements, f, ensure_ascii=False, indent=2)
            logger.info(f"自动创建了 {created_count} 个元素")

    except Exception as e:
        logger.error(f"自动创建元素失败: {str(e)}")
        raise


# 请求日志中间件
@app.before_request
def log_request_info():
    request_id = str(uuid.uuid4())[:8]  # 生成简短的请求ID
    request.request_id = request_id

    # 记录请求头信息
    headers = dict(request.headers)
    # 移除敏感信息
    if "Authorization" in headers:
        headers["Authorization"] = "******"

    # 记录请求体 (POST/PUT)
    body = None
    if request.method in ["POST", "PUT"] and request.is_json:
        body = request.get_json()

    # 记录查询参数 (GET)
    args = dict(request.args)

    logger.info(f"[{request_id}] 接收到请求: {request.method} {request.path}")
    logger.info(f"[{request_id}] 请求头: {headers}")

    if args:
        logger.info(f"[{request_id}] 查询参数: {args}")
    if body:
        logger.info(f"[{request_id}] 请求体: {body}")


# 响应日志中间件
@app.after_request
def log_response_info(response):
    request_id = getattr(request, "request_id", "unknown")

    # 记录响应状态和头信息
    logger.info(f"[{request_id}] 响应状态: {response.status}")
    logger.info(f"[{request_id}] 响应头: {dict(response.headers)}")

    # 尝试记录响应体 (如果是JSON)
    try:
        if response.is_json:
            resp_data = response.get_json()
            # 如果响应数据很大，只记录摘要
            if isinstance(resp_data, dict):
                if len(str(resp_data)) > 1000:
                    resp_summary = {
                        k: (
                            "..."
                            if isinstance(v, (list, dict)) and len(str(v)) > 100
                            else v
                        )
                        for k, v in resp_data.items()
                    }
                    logger.info(f"[{request_id}] 响应体(摘要): {resp_summary}")
                else:
                    logger.info(f"[{request_id}] 响应体: {resp_data}")
            elif isinstance(resp_data, list):
                logger.info(f"[{request_id}] 响应体: 列表数据, 长度 {len(resp_data)}")
                if len(resp_data) > 0 and len(resp_data) <= 3:
                    logger.info(f"[{request_id}] 响应体样本: {resp_data[0]}")
            else:
                logger.info(f"[{request_id}] 响应体: {resp_data}")
    except Exception as e:
        logger.warning(f"[{request_id}] 无法记录响应体: {str(e)}")

    return response


# 新增设置相关接口
@app.route("/api/settings", methods=["GET"])
def get_settings():
    """获取当前设置"""
    try:
        settings = load_settings()
        logger.info(f"获取设置成功: {settings}")
        return jsonify(settings)
    except Exception as e:
        logger.error(f"获取设置失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """更新设置"""
    try:
        new_settings = request.get_json()
        logger.info(f"收到设置更新请求: {new_settings}")

        # 验证设置格式
        if not isinstance(new_settings, dict):
            return jsonify({"error": "设置格式不正确"}), 400

        # 验证必要字段
        required_fields = [
            "defaultBrowser",
            "defaultHeadless",
            "saveScreenshots",
            "enableMultiThread",
        ]
        for field in required_fields:
            if field not in new_settings:
                return jsonify({"error": f"缺少必要字段: {field}"}), 400

        # 验证字段类型
        if not isinstance(new_settings["defaultBrowser"], str):
            return jsonify({"error": "defaultBrowser 必须是字符串"}), 400
        if not isinstance(new_settings["defaultHeadless"], bool):
            return jsonify({"error": "defaultHeadless 必须是布尔值"}), 400
        if not isinstance(new_settings["saveScreenshots"], bool):
            return jsonify({"error": "saveScreenshots 必须是布尔值"}), 400
        if not isinstance(new_settings["enableMultiThread"], bool):
            return jsonify({"error": "enableMultiThread 必须是布尔值"}), 400

        # 验证可选的环境字段
        if "defaultEnvironment" in new_settings and not isinstance(
            new_settings["defaultEnvironment"], str
        ):
            return jsonify({"error": "defaultEnvironment 必须是字符串"}), 400

        # 验证可选的Authorization/登录态开关字段
        if "useAuthorization" in new_settings and not isinstance(
            new_settings["useAuthorization"], bool
        ):
            return jsonify({"error": "useAuthorization 必须是布尔值"}), 400
        if "useLoginState" in new_settings and not isinstance(
            new_settings["useLoginState"], bool
        ):
            return jsonify({"error": "useLoginState 必须是布尔值"}), 400

        # 验证浏览器类型
        valid_browsers = ["chrome", "firefox", "chromium", "msedge"]
        if new_settings["defaultBrowser"] not in valid_browsers:
            return (
                jsonify(
                    {"error": f"不支持的浏览器类型: {new_settings['defaultBrowser']}"}
                ),
                400,
            )

        # 保存设置
        if save_settings(new_settings):
            logger.info(f"设置更新成功: {new_settings}")
            return jsonify({"message": "设置保存成功"})
        else:
            return jsonify({"error": "保存设置失败"}), 500

    except Exception as e:
        logger.error(f"更新设置失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/task-settings", methods=["GET"])
def get_task_settings():
    """获取任务设置"""
    try:
        settings = load_task_settings()
        logger.info(f"获取任务设置成功: {settings}")
        return jsonify(settings)
    except Exception as e:
        logger.error(f"获取任务设置失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/task-settings", methods=["POST"])
def update_task_settings():
    """更新任务设置"""
    try:
        new_settings = request.get_json()
        logger.info(f"收到任务设置更新请求: {new_settings}")

        # 验证设置格式
        if not isinstance(new_settings, dict):
            return jsonify({"error": "设置格式不正确"}), 400

        # 验证必要字段
        required_fields = [
            "defaultBrowser",
            "defaultHeadless",
            "saveScreenshots",
            "enableMultiThread",
        ]
        for field in required_fields:
            if field not in new_settings:
                return jsonify({"error": f"缺少必要字段: {field}"}), 400

        # 验证字段类型
        if not isinstance(new_settings["defaultBrowser"], str):
            return jsonify({"error": "defaultBrowser 必须是字符串"}), 400
        if not isinstance(new_settings["defaultHeadless"], bool):
            return jsonify({"error": "defaultHeadless 必须是布尔值"}), 400
        if not isinstance(new_settings["saveScreenshots"], bool):
            return jsonify({"error": "saveScreenshots 必须是布尔值"}), 400
        if not isinstance(new_settings["enableMultiThread"], bool):
            return jsonify({"error": "enableMultiThread 必须是布尔值"}), 400

        # 验证可选的环境字段
        if "defaultEnvironment" in new_settings and not isinstance(
            new_settings["defaultEnvironment"], str
        ):
            return jsonify({"error": "defaultEnvironment 必须是字符串"}), 400

        # 验证可选的Authorization/登录态开关字段
        if "useAuthorization" in new_settings and not isinstance(
            new_settings["useAuthorization"], bool
        ):
            return jsonify({"error": "useAuthorization 必须是布尔值"}), 400
        if "useLoginState" in new_settings and not isinstance(
            new_settings["useLoginState"], bool
        ):
            return jsonify({"error": "useLoginState 必须是布尔值"}), 400

        # 验证浏览器类型
        valid_browsers = ["chrome", "firefox", "chromium", "msedge"]
        if new_settings["defaultBrowser"] not in valid_browsers:
            return (
                jsonify(
                    {"error": f"不支持的浏览器类型: {new_settings['defaultBrowser']}"}
                ),
                400,
            )

        # 保存任务设置
        if save_task_settings(new_settings):
            logger.info(f"任务设置更新成功: {new_settings}")
            return jsonify({"message": "任务设置保存成功"})
        else:
            return jsonify({"error": "保存任务设置失败"}), 500

    except Exception as e:
        logger.error(f"更新任务设置失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/login-for-cookie", methods=["POST"])
def login_for_cookie():
    """登录官网获取Cookie"""
    import asyncio

    try:
        data = request.get_json()
        website_url = data.get("websiteUrl", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not website_url or not username or not password:
            return jsonify({"error": "请提供完整的登录信息"}), 400

        logger.info(f"开始登录官网获取Cookie: {website_url}")

        # 导入登录执行器
        from test_executor import CookieManager

        # 使用asyncio运行异步函数
        async def run_login():
            cookie_manager = CookieManager()
            return await cookie_manager.login_and_save_cookie(
                {"website_url": website_url, "username": username, "password": password}
            )

        # 执行异步登录
        result = asyncio.run(run_login())

        if result.get("success"):
            logger.info("Cookie获取成功")
            return jsonify({"success": True, "message": "登录成功，Cookie已保存"})
        else:
            logger.error(f"Cookie获取失败: {result.get('error')}")
            return (
                jsonify({"success": False, "error": result.get("error", "登录失败")}),
                400,
            )

    except Exception as e:
        logger.error(f"Cookie登录失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/login-for-admin-cookie", methods=["POST"])
def login_for_admin_cookie():
    """登录管理端获取Cookie"""
    import asyncio

    try:
        data = request.get_json()
        website_url = data.get("websiteUrl", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not website_url or not username or not password:
            return jsonify({"error": "请提供完整的管理端登录信息"}), 400

        logger.info(f"开始登录管理端获取Cookie: {website_url}")

        # 导入登录执行器
        from test_executor import AdminCookieManager

        # 使用asyncio运行异步函数
        async def run_admin_login():
            admin_cookie_manager = AdminCookieManager()
            return await admin_cookie_manager.login_and_save_cookie(
                {"website_url": website_url, "username": username, "password": password}
            )

        # 执行异步登录
        result = asyncio.run(run_admin_login())

        if result.get("success"):
            logger.info("管理端Cookie获取成功")
            return jsonify({"success": True, "message": "管理端登录成功，Cookie已保存"})
        else:
            logger.error(f"管理端Cookie获取失败: {result.get('error')}")
            return (
                jsonify(
                    {"success": False, "error": result.get("error", "管理端登录失败")}
                ),
                400,
            )

    except Exception as e:
        logger.error(f"管理端Cookie登录失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/data", methods=["GET"])
def get_data():
    try:
        # 获取查询参数
        project = request.args.get("project", "").lower()
        module = request.args.get("module", "").lower()
        page = request.args.get("page", "").lower()
        name = request.args.get("name", "").lower()
        type = request.args.get("type", "").lower()

        # 记录查询条件
        logger.info(
            f"获取数据查询条件: project={project}, module={module}, page={page}, name={name}, type={type}"
        )

        # 读取数据文件
        with open("data.json", "r", encoding="utf-8") as file:
            data = json.load(file)

        # 如果有查询参数，进行过滤
        if project or module or page or name or type:
            filtered_data = []
            for item in data:
                if (
                    (project and project not in item.get("project", "").lower())
                    or (module and module not in item.get("module", "").lower())
                    or (page and page not in item.get("page", "").lower())
                    or (name and name not in item.get("name", "").lower())
                    or (type and type not in item.get("type", "").lower())
                ):
                    continue
                filtered_data.append(item)

            logger.info(f"过滤后的数据条数: {len(filtered_data)}")
            return jsonify(filtered_data)

        # 如果没有查询参数，返回所有数据
        logger.info(f"返回所有数据, 总条数: {len(data)}")
        return jsonify(data)

    except FileNotFoundError:
        logger.error("数据文件不存在")
        return jsonify({"error": "数据文件不存在"}), 404
    except json.JSONDecodeError:
        logger.error("JSON 格式错误")
        return jsonify({"error": "JSON 格式错误"}), 500
    except Exception as e:
        logger.error(f"服务器错误: {str(e)}")
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500


@app.route("/api/add_case", methods=["POST"])
def add_testcase():
    try:
        # 获取请求数据
        new_case = request.get_json()
        logger.info(f"添加用例 - 请求数据: {new_case}")

        # 读取现有数据
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # 获取最大 id
        max_id = max([case["id"] for case in data]) if data else 0

        # 构建新的测试用例
        testcase = {
            "id": max_id + 1,
            "project": new_case.get("project"),
            "module": new_case.get("module"),
            "page": new_case.get("page"),
            "name": new_case.get("name"),
            "type": new_case.get("type"),
            "testcase_step": new_case.get("testcase_step", []),
        }
        logger.info(f"新建用例信息: {testcase}")

        # 检测"引用其他用例"是否形成循环引用，一旦发现直接拒绝保存
        cycle = find_reference_cycle(testcase["id"], testcase["testcase_step"], data)
        if cycle:
            logger.warning(f"检测到循环引用，拒绝保存: {' -> '.join(cycle)}")
            return (
                jsonify(
                    {"error": f"保存失败：检测到用例循环引用 ({' -> '.join(cycle)})，请检查步骤中引用的用例"}
                ),
                400,
            )

        # 自动创建缺失的元素
        auto_create_missing_elements(
            testcase["testcase_step"], testcase["project"], testcase["module"], testcase["page"]
        )

        # 自动同步"提取变量"声明（get_element_text步骤填写的var_name）
        sync_extracted_variables_from_testcase(testcase["testcase_step"], testcase["project"])

        # 添加新用例
        data.append(testcase)

        # 写回文件
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        response_data = {"message": "测试用例添加成功", "id": testcase["id"]}
        logger.info(f"添加用例成功, ID: {testcase['id']}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"添加用例失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 修改单个执行的接口，支持配置参数
@app.route("/api/execute", methods=["POST"])
def execute_test():
    """执行单个测试用例"""
    try:
        # 获取请求数据
        req_data = request.get_json()
        test_id = req_data.get("id")
        config = req_data.get("config", {})

        # 获取报告名称
        report_name = config.get("reportName", "")
        description = config.get("description", "")

        if test_id is None:
            logger.error("执行失败: 请求体中缺少'id'")
            return jsonify({"error": "Missing 'id' in request body"}), 400

        logger.info(f"执行测试用例 - ID: {test_id}, 报告名称: {report_name}")

        # 读取测试用例数据
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            # 查找指定ID的测试用例
            testcase = next((case for case in data if case["id"] == test_id), None)
            if not testcase:
                logger.error(f"找不到ID为{test_id}的测试用例")
                return jsonify({"error": f"找不到ID为{test_id}的测试用例"}), 404

            # 获取测试用例所属的项目
            project_name = testcase.get("project", "")

            # 如果没有提供配置，使用默认设置
            if not config:
                settings = load_settings()
                config = {
                    "browser": settings.get("defaultBrowser", "chrome"),
                    "headless": settings.get("defaultHeadless", False),
                    "saveScreenshots": settings.get("saveScreenshots", False),
                }

            # 按项目+环境组装按域名区分的Authorization配置（用例内打开不同域名时自动切换Token）
            # 分别受全局设置中"是否使用Authorization"/"是否使用登录态"开关控制，默认均为使用
            exec_environment = config.get("executeEnvironment") or testcase.get("environment", "")
            global_settings = load_settings()
            use_authorization = global_settings.get("useAuthorization", True)
            use_login_state = global_settings.get("useLoginState", True)

            config["authProfiles"] = (
                get_auth_profiles_for_execution(project_name, exec_environment)
                if use_authorization
                else []
            )
            config["loginStateCookies"] = (
                get_login_state_cookies_for_execution(project_name, exec_environment)
                if use_login_state
                else []
            )

            # 检查用例是否与登录相关（需要禁用认证信息）
            has_login = False

            # 检查步骤的xpath是否为登录按钮，或者操作类型是否为login_website
            for step in testcase.get("testcase_step", []):
                step_xpath = step.get("xpath", "")
                step_operate = step.get("operate", "")

                # 检查xpath是否为登录按钮
                if step_xpath == '//span[text()="登 录"]':
                    has_login = True
                    logger.info(f"检测到登录按钮XPath: {step_xpath}")
                    break

                # 检查操作类型是否为login_website
                if step_operate == "login_website":
                    has_login = True
                    logger.info(f"检测到login_website操作")
                    break

            # 如果检测到与登录相关，清空认证配置
            if has_login:
                logger.info("检测到用例与登录相关，禁用认证信息配置")
                config["authProfiles"] = []
                config["loginStateCookies"] = []

            # 创建一个"执行中"状态的临时报告
            from datetime import datetime

            temp_report_id = int(time.time())
            executing_report = {
                "id": temp_report_id,
                "test_id": test_id,
                "name": (
                    report_name if report_name else testcase.get("name", "未命名测试")
                ),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "executing",
                "pass_rate": 0,
                "duration": "00:00",
                "config": config,
                "steps": [],
                "executed_cases": [
                    {"id": test_id, "name": testcase.get("name", "未命名测试")}
                ],
            }
            if description:
                executing_report["description"] = description

            # 立即保存"执行中"状态的报告
            save_report(executing_report)
            logger.info(f"已创建执行中的临时报告，ID: {temp_report_id}")

            # 执行测试用例
            import asyncio

            try:
                report = asyncio.run(execute_test_case(testcase, config))

                # 使用相同的报告ID，覆盖之前的"执行中"报告
                report["id"] = temp_report_id

                # 如果提供了自定义报告名称，则使用它
                if report_name:
                    report["name"] = report_name
                if description:
                    report["description"] = description

                # 保存最终测试报告
                save_report(report)

                logger.info(
                    f"测试执行成功 - 报告名称: {report['name']}, 通过率: {report['pass_rate']}%"
                )
                return jsonify({"message": "测试用例执行成功", "report": report})
            except Exception as exec_error:
                # 执行失败，更新报告状态为失败
                logger.error(f"测试执行过程中出错: {str(exec_error)}")
                error_report = {
                    "id": temp_report_id,
                    "test_id": test_id,
                    "name": (
                        report_name
                        if report_name
                        else testcase.get("name", "未命名测试")
                    ),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "fail",
                    "pass_rate": 0,
                    "duration": "00:00",
                    "config": config,
                    "steps": [],
                    "error": str(exec_error),
                }
                if description:
                    error_report["description"] = description
                save_report(error_report)
                return jsonify({"error": f"执行失败: {str(exec_error)}"}), 500

        except FileNotFoundError:
            logger.error("数据文件不存在")
            return jsonify({"error": "数据文件不存在"}), 404

    except Exception as e:
        logger.error(f"执行测试失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 修改批量执行的接口，生成汇总报告
@app.route("/api/batch_execute", methods=["POST"])
def execute_batch():
    """批量执行测试用例"""
    try:
        # 从请求体中获取 id 列表和配置
        req_data = request.get_json()
        ids_to_execute = req_data.get("ids")
        config = req_data.get("config", {})

        # 获取报告名称
        report_name = config.get("reportName", "")
        description = config.get("description", "")

        if ids_to_execute is None or not isinstance(ids_to_execute, list):
            logger.error("批量执行失败: 请求体中缺少'ids'或格式不正确")
            return jsonify({"error": "Missing or invalid 'ids' in request body"}), 400

        logger.info(f"批量执行用例 - IDs: {ids_to_execute}, 报告名称: {report_name}")

        # 如果没有提供配置，使用默认设置
        if not config:
            settings = load_settings()
            config = {
                "browser": settings.get("defaultBrowser", "chrome"),
                "headless": settings.get("defaultHeadless", False),
                "saveScreenshots": settings.get("saveScreenshots", False),
                "enableMultiThread": settings.get("enableMultiThread", False),
                "clientAuthToken": settings.get("clientAuthToken", ""),
                "adminAuthToken": settings.get("adminAuthToken", ""),
                "privateAuthToken": settings.get("privateAuthToken", ""),
            }
            logger.info(f"使用默认设置: {config}")
        else:
            # 即使提供了config，也要确保包含authorization tokens
            settings = load_settings()
            if "clientAuthToken" not in config:
                config["clientAuthToken"] = settings.get("clientAuthToken", "")
            if "adminAuthToken" not in config:
                config["adminAuthToken"] = settings.get("adminAuthToken", "")
            if "privateAuthToken" not in config:
                config["privateAuthToken"] = settings.get("privateAuthToken", "")

        # 读取测试用例数据
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            testcases = [case for case in data if case["id"] in ids_to_execute]
            found_ids = [case["id"] for case in testcases]
            missing_ids = [id for id in ids_to_execute if id not in found_ids]

            if missing_ids:
                logger.warning(f"部分用例未找到: {missing_ids}")

            if not testcases:
                logger.error("执行失败: 未找到任何指定的测试用例")
                return (
                    jsonify({"error": "No test cases found with the specified IDs"}),
                    404,
                )

            # 按每个用例所属的项目+环境，各自组装按域名区分的Authorization配置和登录态Cookie
            # 分别受全局设置中"是否使用Authorization"/"是否使用登录态"开关控制，默认均为使用
            global_settings = load_settings()
            use_authorization = global_settings.get("useAuthorization", True)
            use_login_state = global_settings.get("useLoginState", True)
            for case in testcases:
                case_environment = config.get("executeEnvironment") or case.get("environment", "")
                case["_authProfiles"] = (
                    get_auth_profiles_for_execution(case.get("project", ""), case_environment)
                    if use_authorization
                    else []
                )
                case["_loginStateCookies"] = (
                    get_login_state_cookies_for_execution(case.get("project", ""), case_environment)
                    if use_login_state
                    else []
                )

            # 检查所有用例是否包含登录按钮XPath或login_website操作（需要禁用Authorization token）
            has_login = False

            for case in testcases:
                # 检查步骤的xpath是否为登录按钮，或者操作类型是否为login_website
                for step in case.get("testcase_step", []):
                    step_xpath = step.get("xpath", "")
                    step_operate = step.get("operate", "")

                    # 检查xpath是否为登录按钮
                    if step_xpath == '//span[text()="登 录"]':
                        has_login = True
                        logger.info(f"用例 {case.get('id')} 包含登录按钮XPath")
                        break

                    # 检查操作类型是否为login_website
                    if step_operate == "login_website":
                        has_login = True
                        logger.info(f"用例 {case.get('id')} 包含login_website操作")
                        break

                if has_login:
                    break

            # 如果检测到与登录相关，清空Authorization token配置
            if has_login:
                logger.info(
                    "检测到批量用例中包含登录相关操作，禁用Authorization token配置"
                )
                config["clientAuthToken"] = ""
                config["adminAuthToken"] = ""
                config["privateAuthToken"] = ""
                for case in testcases:
                    case["_authProfiles"] = []
                    case["_loginStateCookies"] = []

            # 创建一个"执行中"状态的临时报告
            from datetime import datetime

            temp_report_id = int(time.time())
            executed_case_info = [
                {"id": case["id"], "name": case.get("name", "未命名测试")}
                for case in testcases
            ]
            executing_report = {
                "id": temp_report_id,
                "name": (
                    report_name if report_name else f"批量测试 ({len(testcases)}个用例)"
                ),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "executing",
                "pass_rate": 0,
                "duration": "00:00",
                "config": config,
                "steps": [],
                "executed_cases": executed_case_info,
            }
            if description:
                executing_report["description"] = description

            # 立即保存"执行中"状态的报告
            save_report(executing_report)
            logger.info(f"已创建执行中的临时报告，ID: {temp_report_id}")

            # 根据配置选择执行模式
            import asyncio

            try:
                if config.get("enableMultiThread", False):
                    logger.info("使用多线程并行执行模式")
                    batch_report = asyncio.run(
                        execute_batch_test_cases_parallel(testcases, config)
                    )
                else:
                    logger.info("使用顺序执行模式")
                    batch_report = asyncio.run(
                        execute_batch_test_cases(testcases, config)
                    )

                # 使用相同的报告ID，覆盖之前的"执行中"报告
                batch_report["id"] = temp_report_id

                # 如果提供了自定义报告名称，则使用它
                if report_name:
                    batch_report["name"] = report_name
                if description:
                    batch_report["description"] = description

                save_report(batch_report)

                response_data = {
                    "message": f"Successfully executed {len(testcases)} test cases",
                    "report": batch_report,
                }

                logger.info(
                    f"批量执行成功 - 报告名称: {batch_report['name']}, 总数: {len(testcases)}, 汇总通过率: {batch_report['pass_rate']}%"
                )
                return jsonify(response_data)
            except Exception as exec_error:
                # 执行失败，更新报告状态为失败
                logger.error(f"批量执行过程中出错: {str(exec_error)}")
                error_report = {
                    "id": temp_report_id,
                    "name": (
                        report_name
                        if report_name
                        else f"批量测试 ({len(testcases)}个用例)"
                    ),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "fail",
                    "pass_rate": 0,
                    "duration": "00:00",
                    "config": config,
                    "steps": [],
                    "executed_cases": executed_case_info,
                    "error": str(exec_error),
                }
                if description:
                    error_report["description"] = description
                save_report(error_report)
                return jsonify({"error": f"批量执行失败: {str(exec_error)}"}), 500

        except FileNotFoundError:
            logger.error("数据文件不存在")
            return jsonify({"error": "数据文件不存在"}), 404

    except Exception as e:
        logger.error(f"批量执行失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 查看用例详情接口
@app.route("/api/testcase/<int:id>", methods=["GET"])
def get_testcase(id):
    logger.info(f"获取用例详情 - ID: {id}")
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        testcase = next((case for case in data if case["id"] == id), None)

        if testcase:
            logger.info(f"获取用例成功 - ID: {id}, 名称: {testcase.get('name')}")
            return jsonify(testcase)
        else:
            logger.warning(f"用例不存在 - ID: {id}")
            return jsonify({"error": "用例不存在"}), 404

    except Exception as e:
        logger.error(f"获取用例详情失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 删除用例接口
@app.route("/api/testcase/<int:id>", methods=["DELETE"])
def delete_testcase(id):
    logger.info(f"删除用例 - ID: {id}")
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # 找到要删除的用例索引
        index = next((i for i, case in enumerate(data) if case["id"] == id), None)

        if index is None:
            logger.warning(f"删除失败 - 用例不存在, ID: {id}")
            return jsonify({"error": "用例不存在"}), 404

        # 记录被删除的用例信息
        deleted_case = data[index]
        logger.info(f"删除用例信息 - ID: {id}, 名称: {deleted_case.get('name')}")

        # 检查是否有其他用例通过"引用其他用例"步骤引用了这条用例，有则拒绝删除，
        # 需要用户先解除引用（编辑对应用例，删除或改掉那个引用步骤）才能删除
        referencing_case_names = [
            case.get("name", f"ID:{case.get('id')}")
            for case in data
            if case["id"] != id
            and any(
                step.get("operate") == "reference_testcase"
                and step.get("referenced_case_id") == id
                for step in case.get("testcase_step", [])
            )
        ]
        if referencing_case_names:
            logger.warning(
                f"删除失败 - 用例(ID={id})被以下用例引用: {referencing_case_names}"
            )
            return (
                jsonify(
                    {
                        "error": f"删除失败：该用例被以下用例引用 ({', '.join(referencing_case_names)})，请先在这些用例中解除引用再删除"
                    }
                ),
                400,
            )

        # 删除用例
        data.pop(index)

        # 写回文件
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"删除用例成功 - ID: {id}")
        return jsonify({"message": "删除成功"})

    except Exception as e:
        logger.error(f"删除用例失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 编辑用例接口
@app.route("/api/testcase/<int:id>", methods=["PUT"])
def update_testcase(id):
    logger.info(f"更新用例 - ID: {id}")
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        index = next((i for i, case in enumerate(data) if case["id"] == id), None)

        if index is None:
            logger.warning(f"更新失败 - 用例不存在, ID: {id}")
            return jsonify({"error": "用例不存在"}), 404

        request_data = request.get_json()
        logger.info(f"更新用例请求数据 - ID: {id}, 数据: {request_data}")

        # 记录更新前的数据
        old_data = data[index].copy()
        logger.info(f"更新前数据 - ID: {id}, 数据: {old_data}")

        # 检测"引用其他用例"是否形成循环引用，一旦发现直接拒绝保存
        # 用更新后的步骤内容做检测，但排查时data里仍是旧版本，需要临时替换当前用例的步骤后再检测
        data_for_cycle_check = [
            {**case, "testcase_step": request_data["testcase_step"]} if case["id"] == id else case
            for case in data
        ]
        cycle = find_reference_cycle(id, request_data["testcase_step"], data_for_cycle_check)
        if cycle:
            logger.warning(f"检测到循环引用，拒绝保存: {' -> '.join(cycle)}")
            return (
                jsonify(
                    {"error": f"保存失败：检测到用例循环引用 ({' -> '.join(cycle)})，请检查步骤中引用的用例"}
                ),
                400,
            )

        # 自动创建缺失的元素
        auto_create_missing_elements(
            request_data["testcase_step"], request_data["project"], request_data["module"], request_data["page"]
        )

        # 自动同步"提取变量"声明（get_element_text步骤填写的var_name）
        sync_extracted_variables_from_testcase(request_data["testcase_step"], request_data["project"])

        # 更新数据
        data[index].update(
            {
                "project": request_data["project"],
                "module": request_data["module"],
                "page": request_data["page"],
                "name": request_data["name"],
                "type": request_data["type"],
                "testcase_step": request_data["testcase_step"],
            }
        )

        # 写回文件
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"更新用例成功 - ID: {id}, 名称: {data[index].get('name')}")
        return jsonify({"message": "更新成功"})

    except Exception as e:
        logger.error(f"更新用例失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard", methods=["GET"])
def get_dashboard_data():
    logger.info("获取仪表盘数据")
    start_time = time.time()

    try:
        # 从data.json读取测试用例数据
        test_cases = []
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                test_cases = json.load(f)
                logger.info(f"读取到测试用例数据: {len(test_cases)}条")
        except FileNotFoundError:
            logger.error("测试用例数据文件不存在")
            return jsonify({"error": "测试用例数据文件不存在"}), 404

        # 计算总用例数
        total_cases = len(test_cases)
        logger.info(f"总用例数: {total_cases}")

        # 按项目统计用例数量
        project_counts = {}
        for case in test_cases:
            project = case.get("project", "未分类")
            project_counts[project] = project_counts.get(project, 0) + 1

        # 以项目管理中的项目列表为基准展示（即使暂无用例也展示，数量为0）
        all_projects = load_projects()
        project_stats = [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "count": project_counts.pop(p.get("name"), 0),
            }
            for p in all_projects
        ]
        # 剩余未匹配到项目列表的用例项目（如"未分类"）仍展示出来
        project_stats.extend(
            {"id": name, "name": name, "count": count}
            for name, count in project_counts.items()
        )
        logger.info(f"项目统计: {project_stats}")

        # 按类型统计用例分布
        type_counts = {}
        for case in test_cases:
            case_type = case.get("type", "未分类")
            type_counts[case_type] = type_counts.get(case_type, 0) + 1

        type_distribution = [{"name": k, "value": v} for k, v in type_counts.items()]
        logger.info(f"类型分布: {type_distribution}")

        # 按模块统计用例分布
        module_counts = {}
        for case in test_cases:
            module = case.get("module", "未分类")
            module_counts[module] = module_counts.get(module, 0) + 1

        module_distribution = [{"name": k, "value": v} for k, v in module_counts.items()]
        logger.info(f"模块分布: {module_distribution}")

        # 尝试从reports.json读取报告数据，如果不存在则使用默认数据
        recent_reports = []
        try:
            with open("reports.json", "r", encoding="utf-8") as f:
                all_reports = json.load(f)
                # 取最近3条记录
                recent_reports = sorted(
                    all_reports, key=lambda x: x.get("time", ""), reverse=True
                )[:3]
                logger.info(
                    f"读取到报告数据: {len(all_reports)}条, 取最近{len(recent_reports)}条"
                )
        except FileNotFoundError:
            # 使用默认报告数据
            logger.warning("报告数据文件不存在, 使用默认数据")
            recent_reports = [
                {
                    "id": 3,
                    "name": "官网登录流程测试",
                    "time": "2025-07-01 09:30:15",
                    "status": "success",
                    "pass_rate": 100,
                    "duration": "00:02:15",
                },
                {
                    "id": 2,
                    "name": "管理端批量操作测试",
                    "time": "2025-06-30 16:45:22",
                    "status": "fail",
                    "pass_rate": 85,
                    "duration": "00:04:30",
                },
                {
                    "id": 1,
                    "name": "吉利私有化部署测试",
                    "time": "2025-06-29 14:20:18",
                    "status": "success",
                    "pass_rate": 95,
                    "duration": "00:03:45",
                },
            ]

        # 构建响应数据
        response_data = {
            "total_cases": total_cases,
            "project_stats": project_stats,
            "type_distribution": type_distribution,
            "module_distribution": module_distribution,
            "recent_reports": recent_reports,
        }

        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"仪表盘数据处理完成, 耗时: {execution_time:.3f}秒")
        logger.info(f"返回仪表盘数据: {response_data}")

        return jsonify(response_data)

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.error(f"获取仪表盘数据失败: {str(e)}, 耗时: {execution_time:.3f}秒")
        return jsonify({"error": str(e)}), 500


@app.route("/api/reports", methods=["GET"])
def get_reports():
    """获取所有报告列表"""
    try:
        # 读取报告文件
        reports_file = os.path.join(os.path.dirname(__file__), "reports.json")
        if not os.path.exists(reports_file):
            logger.info("报告文件不存在，返回空列表")
            return jsonify([])

        with open(reports_file, "r", encoding="utf-8") as f:
            reports = json.load(f)

        # 确保报告数据包含必要字段，并按时间倒序排列
        formatted_reports = []
        for report in reports:
            formatted_report = {
                "id": report.get("id"),
                "test_id": report.get("test_id"),
                "name": report.get("name", "未命名测试"),
                "time": report.get("time", ""),
                "status": report.get("status", "unknown"),
                "pass_rate": report.get("pass_rate", 0),
                "duration": report.get("duration", "00:00"),
                "batch_info": report.get("batch_info"),
                "executed_cases": report.get("executed_cases"),  # 新增执行用例信息
            }
            formatted_reports.append(formatted_report)

        # 按报告ID倒序排列（最新的在前面）
        formatted_reports.sort(key=lambda x: x["id"], reverse=True)

        logger.info(f"获取报告列表成功，共 {len(formatted_reports)} 条报告")
        return jsonify(formatted_reports)

    except Exception as e:
        logger.error(f"获取报告列表失败: {str(e)}")
        return jsonify({"error": f"获取报告列表失败: {str(e)}"}), 500


@app.route("/api/reports/<int:report_id>", methods=["GET"])
def get_report_detail(report_id):
    """获取单个报告的详细信息"""
    try:
        logger.info(f"获取报告详情 - ID: {report_id}")

        # 读取报告文件
        reports_file = os.path.join(os.path.dirname(__file__), "reports.json")
        if not os.path.exists(reports_file):
            logger.error("报告文件不存在")
            return jsonify({"error": "报告文件不存在"}), 404

        with open(reports_file, "r", encoding="utf-8") as f:
            reports = json.load(f)

        # 查找指定ID的报告
        report = next((r for r in reports if r["id"] == report_id), None)

        if not report:
            logger.error(f"找不到ID为{report_id}的报告")
            return jsonify({"error": f"找不到ID为{report_id}的报告"}), 404

        # 调试日志：查看原始报告数据
        logger.info(
            f"📊 找到报告 - ID: {report_id}, 名称: {report.get('name', '未知')}"
        )
        logger.info(f"📋 原始步骤数据长度: {len(report.get('steps', []))}")

        # 分析步骤结果分布
        steps = report.get("steps", [])
        if steps:
            result_counts = {}
            for step in steps:
                result = step.get("result", "unknown")
                result_counts[result] = result_counts.get(result, 0) + 1
            logger.info(f"📊 步骤结果分布: {result_counts}")

            # 记录前几个步骤的详细信息
            logger.info("📝 前3个步骤详情:")
            for i, step in enumerate(steps[:3]):
                logger.info(
                    f"  步骤{i+1}: {step.get('action', '未知')} - {step.get('result', '未知')} - {step.get('describe', '无描述')}"
                )
        else:
            logger.warning(f"⚠️ 报告 {report_id} 没有步骤数据")

        # 确保返回的数据结构完整
        response_data = {
            "id": report.get("id"),
            "test_id": report.get("test_id"),
            "name": report.get("name", "未命名测试"),
            "time": report.get("time", ""),
            "status": report.get("status", "unknown"),
            "pass_rate": report.get("pass_rate", 0),
            "duration": report.get("duration", "00:00"),
            "config": report.get("config", {}),
            "batch_info": report.get("batch_info"),
            "steps": report.get("steps", []),
            "executed_cases": report.get("executed_cases"),  # 新增执行用例信息
            "description": report.get("description"),  # 包含描述信息
        }

        logger.info(f"✅ 成功返回报告详情 - 步骤数: {len(response_data['steps'])}")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"获取报告详情失败: {str(e)}")
        return jsonify({"error": f"获取报告失败: {str(e)}"}), 500


@app.route("/api/reports/<int:report_id>", methods=["DELETE"])
def delete_report(report_id):
    """删除单个报告"""
    try:
        logger.info(f"删除报告请求: {report_id}")

        reports_file = os.path.join(os.path.dirname(__file__), "reports.json")
        if not os.path.exists(reports_file):
            return jsonify({"error": "报告文件不存在"}), 404

        with open(reports_file, "r", encoding="utf-8") as f:
            reports = json.load(f)

        # 查找报告并获取截图列表
        target_report = None
        for r in reports:
            if r.get("id") == report_id:
                target_report = r
                break

        if not target_report:
            return jsonify({"error": "报告不存在"}), 404

        # 删除关联的截图文件
        deleted_screenshots = 0
        if "steps" in target_report:
            for step in target_report.get("steps", []):
                screenshot = step.get("details", {}).get("screenshot")
                if screenshot:
                    # 截图路径已经包含screenshots/前缀，直接使用
                    screenshot_path = (
                        screenshot
                        if screenshot.startswith("screenshots/")
                        else os.path.join(SCREENSHOTS_DIR, screenshot)
                    )
                    if os.path.exists(screenshot_path):
                        try:
                            os.remove(screenshot_path)
                            deleted_screenshots += 1
                            logger.info(f"删除截图: {screenshot}")
                        except Exception as e:
                            logger.warning(f"删除截图失败 {screenshot}: {str(e)}")

        # 从列表中删除报告
        reports = [r for r in reports if r.get("id") != report_id]

        # 保存更新后的数据
        with open(reports_file, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        logger.info(f"报告删除成功: {report_id}, 删除了 {deleted_screenshots} 个截图")
        return jsonify(
            {"message": "报告删除成功", "deleted_screenshots": deleted_screenshots}
        )

    except Exception as e:
        logger.error(f"删除报告失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/reports/batch", methods=["DELETE"])
def batch_delete_reports():
    """批量删除报告"""
    try:
        request_data = request.get_json()
        report_ids = request_data.get("ids", [])
        logger.info(f"批量删除报告请求, IDs: {report_ids}")

        if not report_ids:
            return jsonify({"error": "未提供要删除的报告ID"}), 400

        reports_file = os.path.join(os.path.dirname(__file__), "reports.json")
        if not os.path.exists(reports_file):
            return jsonify({"error": "报告文件不存在"}), 404

        with open(reports_file, "r", encoding="utf-8") as f:
            reports = json.load(f)

        # 删除关联的截图文件
        deleted_screenshots = 0
        for report in reports:
            if report.get("id") in report_ids:
                if "steps" in report:
                    for step in report.get("steps", []):
                        screenshot = step.get("details", {}).get("screenshot")
                        if screenshot:
                            # 截图路径已经包含screenshots/前缀，直接使用
                            screenshot_path = (
                                screenshot
                                if screenshot.startswith("screenshots/")
                                else os.path.join(SCREENSHOTS_DIR, screenshot)
                            )
                            if os.path.exists(screenshot_path):
                                try:
                                    os.remove(screenshot_path)
                                    deleted_screenshots += 1
                                    logger.info(f"删除截图: {screenshot}")
                                except Exception as e:
                                    logger.warning(
                                        f"删除截图失败 {screenshot}: {str(e)}"
                                    )

        # 删除指定ID的报告
        original_length = len(reports)
        reports = [r for r in reports if r.get("id") not in report_ids]
        deleted_count = original_length - len(reports)

        # 保存更新后的数据
        with open(reports_file, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        logger.info(
            f"批量删除完成, 删除 {deleted_count} 个报告, {deleted_screenshots} 个截图"
        )
        return jsonify(
            {
                "message": f"成功删除 {deleted_count} 个报告",
                "deleted_screenshots": deleted_screenshots,
            }
        )

    except Exception as e:
        logger.error(f"批量删除报告失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/screenshot/<path:filename>", methods=["GET"])
def get_screenshot(filename):
    """获取报告截图接口"""
    logger.info(f"获取截图: {filename}")
    try:
        return send_from_directory(SCREENSHOTS_DIR, filename)
    except Exception as e:
        logger.error(f"获取截图失败: {str(e)}")
        return jsonify({"error": str(e)}), 404


@app.route("/screenshots/<path:filename>")
def serve_screenshot(filename):
    """提供截图文件访问"""
    return send_from_directory("screenshots", filename)


if __name__ == "__main__":
    logger.info("服务启动中...")

    try:
        # 确保依赖已安装
        import pkg_resources

        required_packages = ["playwright"]
        missing_packages = []

        for package in required_packages:
            try:
                pkg_resources.get_distribution(package)
            except pkg_resources.DistributionNotFound:
                missing_packages.append(package)

        if missing_packages:
            logger.warning(f"缺少必要的依赖包: {', '.join(missing_packages)}")
            logger.warning(
                "请使用以下命令安装: pip install playwright && playwright install"
            )
    except Exception as e:
        logger.warning(f"检查依赖时出错: {str(e)}")


# ==================== 元素管理相关API ====================


@app.route("/api/elements", methods=["GET"])
def get_elements():
    """获取元素列表"""
    try:
        # 获取查询参数
        project = request.args.get("project", "").lower()
        module = request.args.get("module", "").lower()
        page = request.args.get("page", "").lower()
        element_name = request.args.get("elementName", "").lower()

        logger.info(
            f"获取元素列表查询条件: project={project}, module={module}, page={page}, elementName={element_name}"
        )

        # 读取元素数据文件
        elements_file = "elements.json"
        if not os.path.exists(elements_file):
            # 如果文件不存在，创建空文件
            with open(elements_file, "w", encoding="utf-8") as file:
                json.dump([], file, ensure_ascii=False, indent=2)
            return jsonify([])

        with open(elements_file, "r", encoding="utf-8") as file:
            elements = json.load(file)

        # 如果有查询参数，进行过滤
        if project or module or page or element_name:
            filtered_elements = []
            for element in elements:
                if (
                    (project and project not in element.get("project", "").lower())
                    or (module and module not in element.get("module", "").lower())
                    or (page and page not in element.get("page", "").lower())
                    or (
                        element_name
                        and element_name not in element.get("elementName", "").lower()
                    )
                ):
                    continue
                filtered_elements.append(element)

            logger.info(f"过滤后的元素数量: {len(filtered_elements)}")
            return jsonify(filtered_elements)

        logger.info(f"返回所有元素, 总数: {len(elements)}")
        return jsonify(elements)

    except Exception as e:
        logger.error(f"获取元素列表失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/elements", methods=["POST"])
def add_element():
    """添加新元素"""
    try:
        element_data = request.get_json()
        logger.info(f"添加元素请求数据: {element_data}")

        # 验证必要字段
        required_fields = ["project", "module", "page", "elementName", "xpath"]
        for field in required_fields:
            if not element_data.get(field):
                return jsonify({"error": f"缺少必要字段: {field}"}), 400

        # 读取现有元素数据
        elements_file = "elements.json"
        if os.path.exists(elements_file):
            with open(elements_file, "r", encoding="utf-8") as file:
                elements = json.load(file)
        else:
            elements = []

        # 生成新的ID
        new_id = max([element.get("id", 0) for element in elements], default=0) + 1

        # 创建新元素
        new_element = {
            "id": new_id,
            "project": element_data["project"],
            "module": element_data["module"],
            "page": element_data["page"],
            "elementName": element_data["elementName"],
            "xpath": element_data["xpath"],
            "locate_type": element_data.get("locate_type", "xpath"),
            "description": element_data.get("description", ""),
        }

        # 添加到列表
        elements.append(new_element)

        # 保存到文件
        with open(elements_file, "w", encoding="utf-8") as file:
            json.dump(elements, file, ensure_ascii=False, indent=2)

        logger.info(f"元素添加成功: {new_element}")
        return jsonify({"message": "元素添加成功", "element": new_element})

    except Exception as e:
        logger.error(f"添加元素失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/elements/<int:element_id>", methods=["GET"])
def get_element(element_id):
    """获取单个元素详情"""
    try:
        logger.info(f"获取元素详情, ID: {element_id}")

        elements_file = "elements.json"
        if not os.path.exists(elements_file):
            return jsonify({"error": "元素数据文件不存在"}), 404

        with open(elements_file, "r", encoding="utf-8") as file:
            elements = json.load(file)

        # 查找指定ID的元素
        element = next((e for e in elements if e["id"] == element_id), None)

        if not element:
            return jsonify({"error": "元素不存在"}), 404

        logger.info(f"返回元素详情: {element}")
        return jsonify(element)

    except Exception as e:
        logger.error(f"获取元素详情失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/elements/<int:element_id>", methods=["PUT"])
def update_element(element_id):
    """更新元素"""
    try:
        element_data = request.get_json()
        logger.info(f"更新元素请求, ID: {element_id}, 数据: {element_data}")

        # 验证必要字段
        required_fields = ["project", "module", "page", "elementName", "xpath"]
        for field in required_fields:
            if not element_data.get(field):
                return jsonify({"error": f"缺少必要字段: {field}"}), 400

        elements_file = "elements.json"
        if not os.path.exists(elements_file):
            return jsonify({"error": "元素数据文件不存在"}), 404

        with open(elements_file, "r", encoding="utf-8") as file:
            elements = json.load(file)

        # 查找并更新元素
        element_found = False
        for element in elements:
            if element["id"] == element_id:
                element.update(
                    {
                        "project": element_data["project"],
                        "module": element_data["module"],
                        "page": element_data["page"],
                        "elementName": element_data["elementName"],
                        "xpath": element_data["xpath"],
                        "locate_type": element_data.get("locate_type", "xpath"),
                        "description": element_data.get("description", ""),
                    }
                )
                element_found = True
                break

        if not element_found:
            return jsonify({"error": "元素不存在"}), 404

        # 保存更新后的数据
        with open(elements_file, "w", encoding="utf-8") as file:
            json.dump(elements, file, ensure_ascii=False, indent=2)

        logger.info(f"元素更新成功: {element_id}")
        return jsonify({"message": "元素更新成功"})

    except Exception as e:
        logger.error(f"更新元素失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/elements/<int:element_id>", methods=["DELETE"])
def delete_element(element_id):
    """删除元素"""
    try:
        logger.info(f"删除元素请求, ID: {element_id}")

        elements_file = "elements.json"
        if not os.path.exists(elements_file):
            return jsonify({"error": "元素数据文件不存在"}), 404

        with open(elements_file, "r", encoding="utf-8") as file:
            elements = json.load(file)

        # 检查元素是否存在
        element_exists = any(e["id"] == element_id for e in elements)
        if not element_exists:
            return jsonify({"error": "元素不存在"}), 404

        # 检查元素是否在用例中被引用
        data_file = "data.json"
        if os.path.exists(data_file):
            with open(data_file, "r", encoding="utf-8") as file:
                testcases = json.load(file)

            # 遍历所有用例的步骤，检查是否引用了该元素
            for testcase in testcases:
                for step in testcase.get("testcase_step", []):
                    if step.get("element_id") == element_id:
                        return jsonify({"error": "该元素已在用例中引用，需解除引用后才能删除"}), 400

        # 删除元素
        elements = [e for e in elements if e["id"] != element_id]

        # 保存更新后的数据
        with open(elements_file, "w", encoding="utf-8") as file:
            json.dump(elements, file, ensure_ascii=False, indent=2)

        logger.info(f"元素删除成功: {element_id}")
        return jsonify({"message": "元素删除成功"})

    except Exception as e:
        logger.error(f"删除元素失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/elements/batch", methods=["DELETE"])
def batch_delete_elements():
    """批量删除元素"""
    try:
        request_data = request.get_json()
        element_ids = request_data.get("ids", [])
        logger.info(f"批量删除元素请求, IDs: {element_ids}")

        if not element_ids:
            return jsonify({"error": "未提供要删除的元素ID"}), 400

        elements_file = "elements.json"
        if not os.path.exists(elements_file):
            return jsonify({"error": "元素数据文件不存在"}), 404

        with open(elements_file, "r", encoding="utf-8") as file:
            elements = json.load(file)

        # 检查要删除的元素是否在用例中被引用
        data_file = "data.json"
        if os.path.exists(data_file):
            with open(data_file, "r", encoding="utf-8") as file:
                testcases = json.load(file)

            # 收集被引用的元素ID
            referenced_element_ids = []
            for testcase in testcases:
                for step in testcase.get("testcase_step", []):
                    step_element_id = step.get("element_id")
                    if step_element_id in element_ids:
                        referenced_element_ids.append(step_element_id)

            # 如果有元素被引用，返回错误
            if referenced_element_ids:
                # 去重
                referenced_element_ids = list(set(referenced_element_ids))
                return jsonify({
                    "error": f"该元素已在用例中引用，需解除引用后才能删除",
                    "referenced_ids": referenced_element_ids
                }), 400

        # 删除指定ID的元素
        original_length = len(elements)
        elements = [e for e in elements if e["id"] not in element_ids]
        deleted_count = original_length - len(elements)

        # 保存更新后的数据
        with open(elements_file, "w", encoding="utf-8") as file:
            json.dump(elements, file, ensure_ascii=False, indent=2)

        logger.info(f"批量删除完成, 删除数量: {deleted_count}")
        return jsonify({"message": f"成功删除 {deleted_count} 个元素"})

    except Exception as e:
        logger.error(f"批量删除元素失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ==================== 任务管理相关API ====================


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    """获取任务列表"""
    try:
        # 获取查询参数
        name = request.args.get("name", "").lower()
        client = request.args.get("client", "").lower()
        execution_type = request.args.get("executionType", "").lower()
        schedule_time = request.args.get("scheduleTime", "").lower()

        logger.info(
            f"获取任务列表查询条件: name={name}, client={client}, executionType={execution_type}, scheduleTime={schedule_time}"
        )

        # 读取任务数据文件
        tasks_file = "tasks.json"
        if not os.path.exists(tasks_file):
            # 如果文件不存在，创建空文件
            with open(tasks_file, "w", encoding="utf-8") as file:
                json.dump([], file, ensure_ascii=False, indent=2)
            return jsonify([])

        with open(tasks_file, "r", encoding="utf-8") as file:
            tasks = json.load(file)

        # 如果有查询参数，进行过滤
        if name or client or execution_type or schedule_time:
            filtered_tasks = []
            for task in tasks:
                if (
                    (name and name not in task.get("name", "").lower())
                    or (client and client not in task.get("client", "").lower())
                    or (
                        execution_type
                        and execution_type not in task.get("executionType", "").lower()
                    )
                    or (
                        schedule_time
                        and schedule_time not in task.get("scheduleTime", "").lower()
                    )
                ):
                    continue
                filtered_tasks.append(task)

            logger.info(f"过滤后的任务数量: {len(filtered_tasks)}")
            return jsonify(filtered_tasks)

        logger.info(f"返回所有任务, 总数: {len(tasks)}")
        return jsonify(tasks)

    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tasks", methods=["POST"])
def add_task():
    """添加新任务"""
    try:
        task_data = request.get_json()
        logger.info(f"添加任务请求: {task_data}")

        # 验证必填字段
        required_fields = ["name", "client", "executionType", "selectedCases"]
        for field in required_fields:
            if field not in task_data or not task_data[field]:
                return jsonify({"error": f"缺少必填字段: {field}"}), 400

        # 验证定时执行必须有时间
        if task_data["executionType"] == "scheduled" and not task_data.get(
            "scheduleTime"
        ):
            return jsonify({"error": "定时执行必须设置执行时间"}), 400

        # 读取现有任务
        tasks_file = "tasks.json"
        if os.path.exists(tasks_file):
            with open(tasks_file, "r", encoding="utf-8") as file:
                tasks = json.load(file)
        else:
            tasks = []

        # 生成新的任务ID
        if tasks:
            new_id = max([task["id"] for task in tasks]) + 1
        else:
            new_id = 1

        # 创建新任务
        new_task = {
            "id": new_id,
            "name": task_data["name"],
            "description": task_data.get("description", ""),
            "client": task_data["client"],
            "executionType": task_data["executionType"],
            "scheduleTime": task_data.get("scheduleTime", ""),
            "selectedCases": task_data["selectedCases"],
            "createTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active",
        }

        tasks.append(new_task)

        # 保存到文件
        with open(tasks_file, "w", encoding="utf-8") as file:
            json.dump(tasks, file, ensure_ascii=False, indent=2)

        logger.info(f"任务添加成功: {new_task['name']} (ID: {new_id})")
        return jsonify({"message": "任务添加成功", "task": new_task})

    except Exception as e:
        logger.error(f"添加任务失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    """获取单个任务详情"""
    try:
        tasks_file = "tasks.json"
        if not os.path.exists(tasks_file):
            return jsonify({"error": "任务数据文件不存在"}), 404

        with open(tasks_file, "r", encoding="utf-8") as file:
            tasks = json.load(file)

        # 查找指定ID的任务
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return jsonify({"error": "任务不存在"}), 404

        logger.info(f"获取任务详情成功: {task_id}")
        return jsonify(task)

    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    """更新任务"""
    try:
        task_data = request.get_json()
        logger.info(f"更新任务请求: ID={task_id}, 数据={task_data}")

        tasks_file = "tasks.json"
        if not os.path.exists(tasks_file):
            return jsonify({"error": "任务数据文件不存在"}), 404

        with open(tasks_file, "r", encoding="utf-8") as file:
            tasks = json.load(file)

        # 查找并更新任务
        task_index = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
        if task_index is None:
            return jsonify({"error": "任务不存在"}), 404

        # 验证必填字段
        required_fields = ["name", "client", "executionType", "selectedCases"]
        for field in required_fields:
            if field not in task_data or not task_data[field]:
                return jsonify({"error": f"缺少必填字段: {field}"}), 400

        # 验证定时执行必须有时间
        if task_data["executionType"] == "scheduled" and not task_data.get(
            "scheduleTime"
        ):
            return jsonify({"error": "定时执行必须设置执行时间"}), 400

        # 更新任务数据
        tasks[task_index].update(
            {
                "name": task_data["name"],
                "description": task_data.get("description", ""),
                "client": task_data["client"],
                "executionType": task_data["executionType"],
                "scheduleTime": task_data.get("scheduleTime", ""),
                "selectedCases": task_data["selectedCases"],
            }
        )

        # 保存更新后的数据
        with open(tasks_file, "w", encoding="utf-8") as file:
            json.dump(tasks, file, ensure_ascii=False, indent=2)

        logger.info(f"任务更新成功: {task_id}")
        return jsonify({"message": "任务更新成功", "task": tasks[task_index]})

    except Exception as e:
        logger.error(f"更新任务失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """删除任务"""
    try:
        logger.info(f"删除任务请求: {task_id}")

        tasks_file = "tasks.json"
        if not os.path.exists(tasks_file):
            return jsonify({"error": "任务数据文件不存在"}), 404

        with open(tasks_file, "r", encoding="utf-8") as file:
            tasks = json.load(file)

        # 查找并删除任务
        original_length = len(tasks)
        tasks = [t for t in tasks if t["id"] != task_id]

        if len(tasks) == original_length:
            return jsonify({"error": "任务不存在"}), 404

        # 保存更新后的数据
        with open(tasks_file, "w", encoding="utf-8") as file:
            json.dump(tasks, file, ensure_ascii=False, indent=2)

        logger.info(f"任务删除成功: {task_id}")
        return jsonify({"message": "任务删除成功"})

    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tasks/<int:task_id>/execute", methods=["POST"])
def execute_task(task_id):
    """执行任务"""
    try:
        logger.info(f"执行任务请求: {task_id}")

        tasks_file = "tasks.json"
        if not os.path.exists(tasks_file):
            return jsonify({"error": "任务数据文件不存在"}), 404

        with open(tasks_file, "r", encoding="utf-8") as file:
            tasks = json.load(file)

        # 查找任务
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return jsonify({"error": "任务不存在"}), 404

        # 获取任务中的用例IDs
        case_ids = task.get("selectedCases", [])
        if not case_ids:
            return jsonify({"error": "任务中没有配置用例"}), 400

        logger.info(
            f"开始执行任务 '{task['name']}' 中的 {len(case_ids)} 个用例: {case_ids}"
        )

        # 获取任务设置配置（独立于用例设置，但字段结构与用例设置保持一致）
        settings = load_task_settings()
        config = {
            "browser": settings.get("defaultBrowser", "chrome"),
            "headless": settings.get("defaultHeadless", False),
            "saveScreenshots": settings.get("saveScreenshots", False),
            "enableMultiThread": settings.get("enableMultiThread", False),
            "executeEnvironment": settings.get("defaultEnvironment", ""),
            "reportName": f"任务执行报告-{task['name']}",
            "description": f"任务: {task['name']} - 自动执行 {len(case_ids)} 个用例",
        }

        # 读取测试用例数据
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            testcases = [case for case in data if case["id"] in case_ids]
            found_ids = [case["id"] for case in testcases]
            missing_ids = [id for id in case_ids if id not in found_ids]

            if missing_ids:
                logger.warning(f"部分用例未找到: {missing_ids}")

            if not testcases:
                return jsonify({"error": "任务中的用例均未找到"}), 404

            # 按每个用例所属的项目+环境，各自组装按域名区分的Authorization配置和登录态Cookie
            # 分别受任务设置中"是否使用Authorization"/"是否使用登录态"开关控制，默认均为使用
            use_authorization = settings.get("useAuthorization", True)
            use_login_state = settings.get("useLoginState", True)
            for case in testcases:
                case_environment = config.get("executeEnvironment") or case.get(
                    "environment", ""
                )
                case["_authProfiles"] = (
                    get_auth_profiles_for_execution(case.get("project", ""), case_environment)
                    if use_authorization
                    else []
                )
                case["_loginStateCookies"] = (
                    get_login_state_cookies_for_execution(case.get("project", ""), case_environment)
                    if use_login_state
                    else []
                )

            # 检查所有用例是否包含登录按钮XPath或login_website操作（需要禁用认证信息）
            has_login = False
            for case in testcases:
                for step in case.get("testcase_step", []):
                    step_xpath = step.get("xpath", "")
                    step_operate = step.get("operate", "")
                    if step_xpath == '//span[text()="登 录"]' or step_operate == "login_website":
                        has_login = True
                        break
                if has_login:
                    break

            if has_login:
                logger.info("检测到任务中的用例包含登录相关操作，禁用认证信息配置")
                for case in testcases:
                    case["_authProfiles"] = []
                    case["_loginStateCookies"] = []

            # 创建一个"执行中"状态的临时报告，让前端可以立即关闭确认弹窗并轮询该报告
            from datetime import datetime

            temp_report_id = int(time.time())
            executed_case_info = [
                {"id": case["id"], "name": case.get("name", "未命名测试")}
                for case in testcases
            ]
            executing_report = {
                "id": temp_report_id,
                "name": config["reportName"],
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "executing",
                "pass_rate": 0,
                "duration": "00:00",
                "config": config,
                "steps": [],
                "executed_cases": executed_case_info,
                "description": config.get("description", ""),
            }

            # 立即保存"执行中"状态的报告
            save_report(executing_report)
            logger.info(f"已创建任务执行中的临时报告，ID: {temp_report_id}")

            # 执行测试用例
            import asyncio
            from test_executor import (
                execute_batch_test_cases,
                execute_batch_test_cases_parallel,
            )

            try:
                if config.get("enableMultiThread", False):
                    logger.info(f"任务 '{task['name']}' 使用多线程并行执行模式")
                    batch_report = asyncio.run(
                        execute_batch_test_cases_parallel(testcases, config)
                    )
                else:
                    logger.info(f"任务 '{task['name']}' 使用顺序执行模式")
                    batch_report = asyncio.run(execute_batch_test_cases(testcases, config))

                # 使用相同的报告ID，覆盖之前的"执行中"报告
                batch_report["id"] = temp_report_id

                # 保存报告
                save_report(batch_report)

                logger.info(
                    f"任务 '{task['name']}' 执行完成，通过率: {batch_report.get('pass_rate', 0)}%"
                )
                return jsonify(
                    {
                        "success": True,
                        "message": f"任务 '{task['name']}' 执行完成",
                        "taskId": task_id,
                        "caseCount": len(testcases),
                        "report": batch_report,
                    }
                )
            except Exception as exec_error:
                # 执行失败，更新报告状态为失败，避免临时报告永远停留在"执行中"
                logger.error(f"任务 '{task['name']}' 执行过程中出错: {str(exec_error)}")
                error_report = {
                    "id": temp_report_id,
                    "name": config["reportName"],
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "fail",
                    "pass_rate": 0,
                    "duration": "00:00",
                    "config": config,
                    "steps": [],
                    "executed_cases": executed_case_info,
                    "description": config.get("description", ""),
                    "error": str(exec_error),
                }
                save_report(error_report)
                return jsonify({"error": str(exec_error)}), 500

        except FileNotFoundError:
            logger.error("测试用例数据文件不存在")
            return jsonify({"error": "测试用例数据文件不存在"}), 404

    except Exception as e:
        logger.error(f"执行任务失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ==================== 变量管理相关 API ====================

VARIABLES_FILE = "variables.json"


def load_variables():
    """加载变量数据"""
    try:
        if os.path.exists(VARIABLES_FILE):
            with open(VARIABLES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"加载变量数据失败: {str(e)}")
        return {}


def save_variables(variables):
    """保存变量数据"""
    try:
        with open(VARIABLES_FILE, "w", encoding="utf-8") as f:
            json.dump(variables, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存变量数据失败: {str(e)}")
        return False


@app.route("/api/variables", methods=["GET"])
def get_variables():
    """获取所有存储的变量"""
    try:
        variables = load_variables()
        return jsonify(
            {"success": True, "variables": variables, "message": "获取变量成功"}
        )
    except Exception as e:
        logger.error(f"获取变量失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/variables", methods=["DELETE"])
def clear_variables():
    """清除所有存储的变量"""
    try:
        if save_variables({}):
            return jsonify({"success": True, "message": "变量已清除"})
        else:
            return jsonify({"success": False, "error": "清除变量失败"}), 500
    except Exception as e:
        logger.error(f"清除变量失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/variables/<var_name>", methods=["GET"])
def get_variable(var_name):
    """获取指定变量的值"""
    try:
        variables = load_variables()
        variable_value = variables.get(var_name, "")
        return jsonify(
            {
                "success": True,
                "variable_name": var_name,
                "variable_value": variable_value,
                "message": f"获取变量 {var_name} 成功",
            }
        )
    except Exception as e:
        logger.error(f"获取变量 {var_name} 失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/variables/<var_name>", methods=["POST"])
def set_variable(var_name):
    """设置指定变量的值"""
    try:
        data = request.get_json()
        value = data.get("value", "")

        variables = load_variables()
        variables[var_name] = value

        if save_variables(variables):
            return jsonify(
                {
                    "success": True,
                    "variable_name": var_name,
                    "variable_value": value,
                    "message": f"设置变量 {var_name} 成功",
                }
            )
        else:
            return jsonify({"success": False, "error": "保存变量失败"}), 500
    except Exception as e:
        logger.error(f"设置变量 {var_name} 失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# 新增变量管理接口
VARIABLES_CONFIG_FILE = "variables_config.json"


def load_variables_config():
    """加载变量配置（包含类型、范围等信息）"""
    try:
        if os.path.exists(VARIABLES_CONFIG_FILE):
            with open(VARIABLES_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"加载变量配置失败: {str(e)}")
        return []


def save_variables_config(config):
    """保存变量配置"""
    try:
        with open(VARIABLES_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存变量配置失败: {str(e)}")
        return False


def _match_credential_variables(var_type, project_name, environment):
    """按项目+环境筛选出指定类型（auth/cookie）的变量，
    按变量名去重，优先取"环境和项目都精确匹配"的记录"""
    config = load_variables_config()

    matching = [
        v
        for v in config
        if v.get("type") == var_type
        and v.get("environment", "全局") in [environment, "全局"]
        and (not v.get("project") or v.get("project", "") == project_name)
    ]

    best_by_name = {}
    for v in matching:
        name = v.get("name")
        if name not in best_by_name:
            best_by_name[name] = v
            continue
        current = best_by_name[name]
        current_exact = current.get("environment") == environment and current.get("project") == project_name
        candidate_exact = v.get("environment") == environment and v.get("project") == project_name
        if candidate_exact and not current_exact:
            best_by_name[name] = v

    return list(best_by_name.values())


def get_auth_profiles_for_execution(project_name, environment):
    """根据项目+环境，从变量配置中筛选出Authorization类型的变量，
    组装为按域名区分的Authorization配置列表，供执行器动态切换Token使用"""
    try:
        matching = _match_credential_variables("auth", project_name, environment)

        return [
            {
                "name": v.get("name"),
                "domains": v.get("matchDomains", []),
                "token": v.get("value", ""),
            }
            for v in matching
            if v.get("value")
        ]
    except Exception as e:
        logger.error(f"组装Authorization配置失败: {str(e)}")
        return []


def get_login_state_cookies_for_execution(project_name, environment):
    """根据项目+环境，从变量配置中筛选出Cookie类型的变量，
    合并其Cookie内容（JSON数组），供执行器初始化浏览器上下文时注入登录态"""
    try:
        matching = _match_credential_variables("cookie", project_name, environment)

        merged_cookies = []
        for v in matching:
            raw_value = v.get("value", "")
            if not raw_value:
                continue
            try:
                cookie_list = json.loads(raw_value)
                if isinstance(cookie_list, list):
                    merged_cookies.extend(cookie_list)
                else:
                    logger.warning(f"Cookie变量 {v.get('name')} 的值不是JSON数组，已跳过")
            except json.JSONDecodeError:
                logger.warning(f"Cookie变量 {v.get('name')} 的值不是合法JSON，已跳过")

        return merged_cookies
    except Exception as e:
        logger.error(f"组装登录态Cookie失败: {str(e)}")
        return []


@app.route("/api/variables/list", methods=["GET"])
def get_variables_list():
    """获取变量列表（包含配置信息）"""
    try:
        config = load_variables_config()
        return jsonify({"success": True, "variables": config})
    except Exception as e:
        logger.error(f"获取变量列表失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


def run_capture_auth_token_for_testcase(test_case_id, headless=False):
    """执行指定的登录测试用例，抓取其网络请求中的Authorization请求头。
    供 /api/variables/capture-auth-token 路由和后台自动刷新线程共用。
    返回: {"success": bool, "token": str, "error": str}
    """
    import asyncio
    from test_executor import execute_test_case_and_capture_auth_token

    try:
        with open("data.json", "r", encoding="utf-8") as f:
            testcases = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"读取测试用例数据失败: {str(e)}"}

    test_case = next((tc for tc in testcases if tc["id"] == test_case_id), None)
    if not test_case:
        return {"success": False, "error": "测试用例不存在"}

    return asyncio.run(
        execute_test_case_and_capture_auth_token(test_case, {"headless": headless})
    )


def run_capture_cookies_for_testcase(test_case_id, headless=False):
    """执行指定的登录测试用例，抓取执行后浏览器上下文的Cookie（JSON数组字符串）。
    供 /api/variables/capture-cookie 路由和后台自动刷新线程共用。
    返回: {"success": bool, "cookies": str, "error": str}
    """
    import asyncio
    from test_executor import execute_test_case_and_capture_cookies

    try:
        with open("data.json", "r", encoding="utf-8") as f:
            testcases = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"读取测试用例数据失败: {str(e)}"}

    test_case = next((tc for tc in testcases if tc["id"] == test_case_id), None)
    if not test_case:
        return {"success": False, "error": "测试用例不存在"}

    return asyncio.run(
        execute_test_case_and_capture_cookies(test_case, {"headless": headless})
    )


@app.route("/api/variables/capture-auth-token", methods=["POST"])
def capture_auth_token():
    """执行指定的登录测试用例，抓取其网络请求中的Authorization请求头作为Token值"""
    try:
        data = request.get_json()
        test_case_id = data.get("testCaseId")

        if not test_case_id:
            return jsonify({"success": False, "error": "未指定登录测试用例"}), 400

        result = run_capture_auth_token_for_testcase(test_case_id, headless=False)

        if result.get("success"):
            return jsonify({"success": True, "token": result.get("token", "")})
        else:
            return jsonify({"success": False, "error": result.get("error", "抓取Token失败")}), 400

    except Exception as e:
        logger.error(f"抓取Authorization Token失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/variables/capture-cookie", methods=["POST"])
def capture_cookie():
    """执行指定的登录测试用例，抓取登录后浏览器上下文的Cookie作为Cookie值"""
    try:
        data = request.get_json()
        test_case_id = data.get("testCaseId")

        if not test_case_id:
            return jsonify({"success": False, "error": "未指定登录测试用例"}), 400

        result = run_capture_cookies_for_testcase(test_case_id, headless=False)

        if result.get("success"):
            return jsonify({"success": True, "cookies": result.get("cookies", "")})
        else:
            return jsonify({"success": False, "error": result.get("error", "抓取Cookie失败")}), 400

    except Exception as e:
        logger.error(f"抓取Cookie失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/variables/add", methods=["POST"])
def add_variable():
    """添加或更新变量配置"""
    try:
        data = request.get_json()
        name = data.get("name")
        var_type = data.get("type", "fixed")
        description = data.get("description", "")
        environment = data.get("environment", "全局")
        project = data.get("project", "")

        # 编辑模式：获取原始的环境和项目信息
        original_environment = data.get("originalEnvironment")
        original_project = data.get("originalProject")

        if not name:
            return jsonify({"success": False, "error": "变量名不能为空"}), 400

        config = load_variables_config()

        # 如果是编辑模式（有原始环境和项目信息），先删除旧记录
        if original_environment is not None and original_project is not None:
            # 删除旧记录
            config = [
                v
                for v in config
                if not (
                    v["name"] == name
                    and v.get("environment", "全局") == original_environment
                    and v.get("project", "") == original_project
                )
            ]
            # 添加新记录（相当于更新）
            existing_index = None
        else:
            # 新增模式：检查是否已存在（同名+同环境+同项目才算重复）
            existing_index = next(
                (
                    i
                    for i, v in enumerate(config)
                    if v["name"] == name
                    and v.get("environment", "全局") == environment
                    and v.get("project", "") == project
                ),
                None,
            )

        variable_config = {
            "name": name,
            "type": var_type,
            "description": description,
            "environment": environment,
            "project": project,
        }

        # 根据类型添加特定字段
        if var_type == "fixed":
            variable_config["value"] = data.get("value", "")
        elif var_type == "random":
            variable_config["minValue"] = data.get("minValue", 0)
            variable_config["maxValue"] = data.get("maxValue", 100)
        elif var_type == "database":
            variable_config["database"] = data.get("database", "")
            variable_config["query"] = data.get("query", "")
        elif var_type == "auth":
            source_type = data.get("sourceType", "manual")
            variable_config["sourceType"] = source_type
            variable_config["value"] = data.get("value", "")
            variable_config["matchDomains"] = data.get("matchDomains", [])
            if source_type == "testcase":
                variable_config["loginTestCaseId"] = data.get("loginTestCaseId")
                # 记录本次抓取时间，供后台线程判断6小时后是否需要自动刷新
                variable_config["lastCapturedAt"] = time.time()
        elif var_type == "cookie":
            source_type = data.get("sourceType", "manual")
            variable_config["sourceType"] = source_type
            variable_config["value"] = data.get("value", "")
            variable_config["matchDomains"] = data.get("matchDomains", [])
            if source_type == "testcase":
                variable_config["loginTestCaseId"] = data.get("loginTestCaseId")
                # 记录本次抓取时间，供后台线程判断6小时后是否需要自动刷新
                variable_config["lastCapturedAt"] = time.time()
        elif var_type == "extracted":
            # 提取变量：仅声明变量名+环境+项目，值不在此处设置，
            # 由用例执行"获取元素文案"步骤(get_element_text)时写入运行时变量存储(variables.json)
            variable_config["value"] = ""

        if existing_index is not None:
            config[existing_index] = variable_config
        else:
            config.append(variable_config)

        if save_variables_config(config):
            return jsonify({"success": True, "message": "变量保存成功"})
        else:
            return jsonify({"success": False, "error": "保存变量配置失败"}), 500
    except Exception as e:
        logger.error(f"添加变量失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/variables/<var_name>", methods=["DELETE"])
def delete_variable(var_name):
    """删除变量配置"""
    try:
        data = request.args
        environment = data.get("environment", "全局")
        project = data.get("project", "")

        config = load_variables_config()
        # 删除指定名称+环境+项目的变量
        config = [
            v
            for v in config
            if not (
                v["name"] == var_name
                and v.get("environment", "全局") == environment
                and v.get("project", "") == project
            )
        ]

        if save_variables_config(config):
            # 同时从运行时变量中删除
            variables = load_variables()
            if var_name in variables:
                del variables[var_name]
                save_variables(variables)

            return jsonify({"success": True, "message": "变量删除成功"})
        else:
            return jsonify({"success": False, "error": "删除变量失败"}), 500
    except Exception as e:
        logger.error(f"删除变量失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/variables/generate/<var_name>", methods=["GET"])
def generate_variable_value(var_name):
    """生成变量值（根据配置生成固定值或随机数）"""
    try:
        config = load_variables_config()
        var_config = next((v for v in config if v["name"] == var_name), None)

        if not var_config:
            return jsonify({"success": False, "error": "变量不存在"}), 404

        if var_config["type"] == "fixed":
            value = var_config.get("value", "")
        else:  # random
            min_val = var_config.get("minValue", 0)
            max_val = var_config.get("maxValue", 100)
            import random

            value = str(random.randint(min_val, max_val))

        return jsonify({"success": True, "name": var_name, "value": value})
    except Exception as e:
        logger.error(f"生成变量值失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 项目管理 API ====================
PROJECTS_FILE = "projects.json"


def load_projects():
    """加载项目列表"""
    try:
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"加载项目列表失败: {str(e)}")
        return []


def save_projects(projects):
    """保存项目列表"""
    try:
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存项目列表失败: {str(e)}")
        return False


@app.route("/api/projects", methods=["GET"])
def get_projects():
    """获取项目列表"""
    try:
        projects = load_projects()
        return jsonify({"success": True, "projects": projects})
    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects", methods=["POST"])
def create_project():
    """创建新项目"""
    try:
        data = request.get_json()
        name = data.get("name", "").strip()
        description = data.get("description", "")

        if not name:
            return jsonify({"success": False, "error": "项目名称不能为空"}), 400

        projects = load_projects()

        # 检查项目名称是否已存在
        if any(p["name"] == name for p in projects):
            return jsonify({"success": False, "error": "项目名称已存在"}), 400

        # 生成新ID
        new_id = max([p["id"] for p in projects], default=0) + 1

        # 创建新项目
        new_project = {
            "id": new_id,
            "name": name,
            "description": description,
            "createTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        projects.append(new_project)
        save_projects(projects)

        logger.info(f"创建项目成功: {name}")
        return jsonify({"success": True, "project": new_project})
    except Exception as e:
        logger.error(f"创建项目失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    """更新项目"""
    try:
        data = request.get_json()
        projects = load_projects()

        project = next((p for p in projects if p["id"] == project_id), None)
        if not project:
            return jsonify({"success": False, "error": "项目不存在"}), 404

        # 更新项目信息
        project["name"] = data.get("name", project["name"])
        project["description"] = data.get("description", project.get("description", ""))

        save_projects(projects)

        logger.info(f"更新项目成功: {project['name']}")
        return jsonify({"success": True, "project": project})
    except Exception as e:
        logger.error(f"更新项目失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    """删除项目"""
    try:
        projects = load_projects()
        project = next((p for p in projects if p["id"] == project_id), None)

        if not project:
            return jsonify({"success": False, "error": "项目不存在"}), 404

        projects = [p for p in projects if p["id"] != project_id]
        save_projects(projects)

        logger.info(f"删除项目成功: {project['name']}")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"删除项目失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 环境管理 API ====================
ENVIRONMENTS_FILE = "environments.json"


def load_environments():
    """加载环境列表"""
    try:
        if os.path.exists(ENVIRONMENTS_FILE):
            with open(ENVIRONMENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"加载环境列表失败: {str(e)}")
        return []


def save_environments(environments):
    """保存环境列表"""
    try:
        with open(ENVIRONMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(environments, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存环境列表失败: {str(e)}")
        return False


@app.route("/api/environments", methods=["GET"])
def get_environments():
    """获取环境列表"""
    try:
        environments = load_environments()
        return jsonify({"success": True, "environments": environments})
    except Exception as e:
        logger.error(f"获取环境列表失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/environments", methods=["POST"])
def add_environment():
    """新增环境"""
    try:
        data = request.get_json()
        name = data.get("name")
        description = data.get("description", "")
        project = data.get("project", "")

        if not name:
            return jsonify({"success": False, "error": "环境名称不能为空"}), 400

        environments = load_environments()
        if any(e.get("name") == name for e in environments):
            return jsonify({"success": False, "error": "环境名称已存在"}), 400

        new_id = max((e.get("id", 0) for e in environments), default=0) + 1
        new_env = {
            "id": new_id,
            "name": name,
            "description": description,
            "project": project,
            "createTime": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        environments.append(new_env)

        if save_environments(environments):
            return jsonify({"success": True, "environment": new_env})
        else:
            return jsonify({"success": False, "error": "保存环境失败"}), 500
    except Exception as e:
        logger.error(f"新增环境失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/environments/<int:env_id>", methods=["PUT"])
def update_environment(env_id):
    """编辑环境"""
    try:
        data = request.get_json()
        name = data.get("name")
        description = data.get("description", "")
        project = data.get("project", "")

        if not name:
            return jsonify({"success": False, "error": "环境名称不能为空"}), 400

        environments = load_environments()
        env = next((e for e in environments if e.get("id") == env_id), None)
        if env is None:
            return jsonify({"success": False, "error": "环境不存在"}), 404

        if any(e.get("name") == name and e.get("id") != env_id for e in environments):
            return jsonify({"success": False, "error": "环境名称已存在"}), 400

        old_name = env.get("name")
        env["name"] = name
        env["description"] = description
        env["project"] = project

        if save_environments(environments):
            # 环境名称变更时，同步更新已有变量的所属环境
            if old_name != name:
                config = load_variables_config()
                changed = False
                for v in config:
                    if v.get("environment", "全局") == old_name:
                        v["environment"] = name
                        changed = True
                if changed:
                    save_variables_config(config)

            return jsonify({"success": True, "environment": env})
        else:
            return jsonify({"success": False, "error": "保存环境失败"}), 500
    except Exception as e:
        logger.error(f"编辑环境失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/environments/<int:env_id>", methods=["DELETE"])
def delete_environment(env_id):
    """删除环境（同时删除该环境下的所有变量）"""
    try:
        environments = load_environments()
        env = next((e for e in environments if e.get("id") == env_id), None)
        if env is None:
            return jsonify({"success": False, "error": "环境不存在"}), 404

        environments = [e for e in environments if e.get("id") != env_id]

        if save_environments(environments):
            config = load_variables_config()
            config = [v for v in config if v.get("environment", "全局") != env.get("name")]
            save_variables_config(config)

            return jsonify({"success": True, "message": "环境删除成功"})
        else:
            return jsonify({"success": False, "error": "删除环境失败"}), 500
    except Exception as e:
        logger.error(f"删除环境失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 测试用例列表 API ====================
@app.route("/api/testcases", methods=["GET"])
def get_testcases():
    """获取所有测试用例（用于选择列表）"""
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            testcases = json.load(f)

        # 只返回必要的字段
        simple_testcases = [
            {"id": tc["id"], "name": tc["name"], "project": tc.get("project", ""), "module": tc.get("module", "")}
            for tc in testcases
        ]

        return jsonify({"success": True, "testcases": simple_testcases})
    except Exception as e:
        logger.error(f"获取测试用例列表失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/logs", methods=["GET"])
def get_logs():
    """获取日志内容"""
    try:
        # 获取查询参数
        lines = request.args.get("lines", default=500, type=int)  # 默认返回最后500行
        search_text = request.args.get("search", default="", type=str)  # 搜索关键词
        level = request.args.get("level", default="", type=str)  # 日志级别过滤

        # 读取日志文件
        if not os.path.exists(LOG_FILE):
            return jsonify({"success": True, "logs": [], "total": 0})

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        # 过滤日志
        filtered_lines = []
        for line in all_lines:
            # 如果指定了日志级别，进行过滤
            if level and f"[{level.upper()}]" not in line:
                continue
            # 如果指定了搜索关键词，进行过滤
            if search_text and search_text.lower() not in line.lower():
                continue
            filtered_lines.append(line.strip())

        # 获取最后N行并反转顺序（最新的在最前面）
        result_lines = (
            filtered_lines[-lines:] if len(filtered_lines) > lines else filtered_lines
        )
        result_lines.reverse()  # 反转顺序，最新的日志在最前面

        return jsonify(
            {
                "success": True,
                "logs": result_lines,
                "total": len(filtered_lines),
                "showing": len(result_lines),
            }
        )
    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/logs/clear", methods=["POST"])
def clear_logs():
    """清空日志文件"""
    try:
        # 清空日志文件
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
        logger.info("日志文件已清空")
        return jsonify({"success": True, "message": "日志已清空"})
    except Exception as e:
        logger.error(f"清空日志失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/")
def serve_frontend():
    """提供前端页面"""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    """提供静态文件，如果文件不存在则返回index.html（用于前端路由）"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")


# ==================== Authorization变量自动刷新（引用登录测试用例） ====================
AUTH_TOKEN_REFRESH_INTERVAL_SECONDS = 6 * 60 * 60  # 6小时刷新一次
AUTH_TOKEN_REFRESH_CHECK_INTERVAL_SECONDS = 5 * 60  # 每5分钟检查一次是否到期


def refresh_expired_captured_credential_variables():
    """扫描所有'引用登录测试用例'的Authorization/Cookie变量，
    对超过AUTH_TOKEN_REFRESH_INTERVAL_SECONDS未刷新的逐个重新执行登录用例并更新值"""
    config = load_variables_config()
    now = time.time()
    changed = False

    for var_config in config:
        var_type = var_config.get("type")
        if var_type not in ("auth", "cookie") or var_config.get("sourceType") != "testcase":
            continue

        test_case_id = var_config.get("loginTestCaseId")
        if not test_case_id:
            continue

        last_captured_at = var_config.get("lastCapturedAt", 0)
        if now - last_captured_at < AUTH_TOKEN_REFRESH_INTERVAL_SECONDS:
            continue

        type_label = "Authorization" if var_type == "auth" else "Cookie"
        logger.info(
            f"[{type_label}自动刷新] 变量 {var_config.get('name')} (项目={var_config.get('project')}, "
            f"环境={var_config.get('environment')}) 距上次刷新已超过6小时，开始重新执行登录用例..."
        )
        try:
            if var_type == "auth":
                result = run_capture_auth_token_for_testcase(test_case_id, headless=True)
                new_value = result.get("token", "")
            else:
                result = run_capture_cookies_for_testcase(test_case_id, headless=True)
                new_value = result.get("cookies", "")
        except Exception as e:
            logger.error(f"[{type_label}自动刷新] 变量 {var_config.get('name')} 执行异常: {str(e)}")
            continue

        if result.get("success"):
            var_config["value"] = new_value
            var_config["lastCapturedAt"] = now
            changed = True
            logger.info(f"[{type_label}自动刷新] 变量 {var_config.get('name')} 刷新成功")
        else:
            logger.warning(
                f"[{type_label}自动刷新] 变量 {var_config.get('name')} 刷新失败: {result.get('error')}"
            )

    if changed:
        save_variables_config(config)


def start_auth_token_refresh_worker():
    """启动后台线程，定期检查并自动刷新'引用登录测试用例'的Authorization变量"""
    import threading

    def worker_loop():
        logger.info(
            f"Authorization Token自动刷新线程已启动 "
            f"(检查间隔={AUTH_TOKEN_REFRESH_CHECK_INTERVAL_SECONDS}秒, 刷新周期={AUTH_TOKEN_REFRESH_INTERVAL_SECONDS}秒)"
        )
        while True:
            time.sleep(AUTH_TOKEN_REFRESH_CHECK_INTERVAL_SECONDS)
            try:
                refresh_expired_captured_credential_variables()
            except Exception as e:
                logger.error(f"[Token自动刷新] 后台线程执行异常: {str(e)}")

    thread = threading.Thread(target=worker_loop, daemon=True)
    thread.start()


if __name__ == "__main__":
    # 检查依赖
    try:
        import playwright

        logger.info("Playwright 依赖检查通过")
    except ImportError:
        logger.warning(
            "Playwright 未安装或版本不兼容，某些功能可能无法正常使用。"
            "请使用以下命令安装: pip install playwright && playwright install"
        )
    except Exception as e:
        logger.warning(f"检查依赖时出错: {str(e)}")

    # 启动Authorization Token自动刷新后台线程（每5分钟检查一次，超过6小时未刷新则自动重新登录抓取）
    start_auth_token_refresh_worker()

    # 从环境变量获取端口，默认为8081
    port = int(os.environ.get("PORT", 8081))
    app.run(host="0.0.0.0", port=port, debug=False)

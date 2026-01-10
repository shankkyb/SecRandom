# ==================================================
# 导入库
# ==================================================
import math
from random import SystemRandom
from loguru import logger

from app.tools.settings_access import readme_settings_async
from app.Language.obtain_language import get_content_combo_name_async
from app.common.history.file_utils import load_history_data
from app.common.history.history_reader import filter_roll_call_history_by_subject

system_random = SystemRandom()


# ==================================================
# 权重格式化函数
# ==================================================
def format_weight_for_display(weights_data: list, weight_key: str = "weight") -> tuple:
    """格式化权重显示，确保小数点对齐

    Args:
        weights_data: 包含权重数据的列表
        weight_key: 权重在数据项中的键名，默认为'weight'

    Returns:
        tuple: (格式化函数, 整数部分最大长度, 小数部分最大长度)
    """
    # 计算权重显示的最大长度，考虑小数点前后的对齐
    max_int_length = 0  # 整数部分最大长度
    max_dec_length = 2  # 固定为两位小数

    for item in weights_data:
        weight = item.get(weight_key, 0)
        weight_str = str(weight)
        if "." in weight_str:
            int_part, _ = weight_str.split(".", 1)
            max_int_length = max(max_int_length, len(int_part))
        else:
            max_int_length = max(max_int_length, len(weight_str))

    # 格式化权重显示，确保小数点对齐并保留两位小数
    def format_weight(weight):
        weight_str = str(weight)
        if "." in weight_str:
            int_part, dec_part = weight_str.split(".", 1)
            # 确保小数部分有两位
            if len(dec_part) < 2:
                dec_part = dec_part.ljust(2, "0")
            elif len(dec_part) > 2:
                dec_part = dec_part[:2]  # 截断多余的小数位
            # 整数部分右对齐，小数部分左对齐
            formatted_int = int_part.rjust(max_int_length)
            # 小数部分补齐到最大长度
            formatted_dec = dec_part.ljust(max_dec_length)
            return f"{formatted_int}.{formatted_dec}"
        else:
            # 没有小数点的情况，添加小数点和两位小数
            formatted_int = weight_str.rjust(max_int_length)
            formatted_dec = "00".ljust(max_dec_length)
            return f"{formatted_int}.{formatted_dec}"

    return format_weight, max_int_length, max_dec_length


# ==================================================
# 公平抽取权重计算函数
# ==================================================
def calculate_weight(students_data: list, class_name: str, subject: str = "") -> list:
    """计算学生权重

    Args:
        students_data: 学生数据列表
        class_name: 班级名称
        subject: 科目名称（可选，用于按科目筛选历史记录）

    Returns:
        list: 更新后的学生数据列表，包含权重信息
    """
    # 从设置中加载权重相关配置
    settings = {
        "fair_draw_enabled": readme_settings_async("fair_draw_settings", "fair_draw")
        or False,
        "fair_draw_group_enabled": readme_settings_async(
            "fair_draw_settings", "fair_draw_group"
        )
        or False,
        "fair_draw_gender_enabled": readme_settings_async(
            "fair_draw_settings", "fair_draw_gender"
        )
        or False,
        "fair_draw_time_enabled": readme_settings_async(
            "fair_draw_settings", "fair_draw_time"
        )
        or False,
        "base_weight": readme_settings_async("fair_draw_settings", "base_weight")
        or 1.0,
        "min_weight": readme_settings_async("fair_draw_settings", "min_weight") or 0.1,
        "max_weight": readme_settings_async("fair_draw_settings", "max_weight") or 5.0,
        "frequency_function": readme_settings_async(
            "fair_draw_settings", "frequency_function"
        )
        or 1,
        "frequency_weight": readme_settings_async(
            "fair_draw_settings", "frequency_weight"
        )
        or 1.0,
        "group_weight": readme_settings_async("fair_draw_settings", "group_weight")
        or 1.0,
        "gender_weight": readme_settings_async("fair_draw_settings", "gender_weight")
        or 1.0,
        "time_weight": readme_settings_async("fair_draw_settings", "time_weight")
        or 1.0,
        "cold_start_enabled": readme_settings_async(
            "fair_draw_settings", "cold_start_enabled"
        )
        or False,
        "cold_start_rounds": readme_settings_async(
            "fair_draw_settings", "cold_start_rounds"
        )
        or 10,
        "shield_enabled": readme_settings_async("advanced_settings", "shield_enabled")
        or False,
        "shield_time": readme_settings_async("advanced_settings", "shield_time") or 0,
        "shield_time_unit": readme_settings_async(
            "advanced_settings", "shield_time_unit"
        )
        or 0,
    }

    # 加载历史记录数据
    history_data = load_history_data("roll_call", class_name)

    # 如果指定了科目，按科目筛选历史记录
    if subject:
        history_data = filter_roll_call_history_by_subject(history_data, subject)

    # 获取小组和性别统计
    group_stats = history_data.get("group_stats", {})
    gender_stats = history_data.get("gender_stats", {})

    # 冷启动轮次配置
    current_stats = history_data.get("total_stats", 0)
    is_cold_start = (
        settings["cold_start_enabled"] and current_stats < settings["cold_start_rounds"]
    )

    # 初始化权重数据结构
    weight_data = {}
    for student in students_data:
        student_id = student.get("id", student.get("name", ""))
        weight_data[student_id] = {
            "total_count": 0,
            "group_count": 0,
            "gender_count": 0,
            "last_drawn_time": None,
            "rounds_missed": 0,
        }

    # 从历史记录中提取权重信息
    if isinstance(history_data, dict) and "students" in history_data:
        students_history = history_data.get("students", {})
        if isinstance(students_history, dict):
            for student_name, student_info in students_history.items():
                if student_name in weight_data and isinstance(student_info, dict):
                    # 更新总计数和最后抽取时间
                    weight_data[student_name]["total_count"] = student_info.get(
                        "total_count", 0
                    )
                    weight_data[student_name]["rounds_missed"] = student_info.get(
                        "rounds_missed", 0
                    )

                    last_drawn_time = student_info.get("last_drawn_time", "")
                    if last_drawn_time:
                        weight_data[student_name]["last_drawn_time"] = last_drawn_time

                    # 从历史记录中获取小组和性别信息
                    history = student_info.get("history", [])
                    if isinstance(history, list):
                        for record in history:
                            if isinstance(record, dict):
                                # 更新小组计数
                                draw_group = record.get("draw_group", "")
                                if (
                                    draw_group
                                    and draw_group
                                    != get_content_combo_name_async(
                                        "roll_call", "range_combobox"
                                    )[0]
                                ):
                                    weight_data[student_name]["group_count"] += 1

                                # 更新性别计数
                                draw_gender = record.get("draw_gender", "")
                                if (
                                    draw_gender
                                    and draw_gender
                                    != get_content_combo_name_async(
                                        "roll_call", "gender_combobox"
                                    )[0]
                                ):
                                    weight_data[student_name]["gender_count"] += 1

    # 获取所有学生的总抽取次数，用于计算相对频率
    all_total_counts = [data["total_count"] for data in weight_data.values()]
    max_total_count = max(all_total_counts) if all_total_counts else 0
    min_total_count = min(all_total_counts) if all_total_counts else 0
    total_count_range = (
        max_total_count - min_total_count if max_total_count > min_total_count else 1
    )

    # 为每个学生计算权重
    for student in students_data:
        student_id = student.get("id", student.get("name", ""))
        if student_id not in weight_data:
            continue

        student_weight_data = weight_data[student_id]
        total_count = student_weight_data["total_count"]

        # 计算频率惩罚因子 - 支持多种函数类型
        if settings["fair_draw_enabled"]:
            # 根据设置选择频率函数
            if settings["frequency_function"] == 0:  # 线性函数
                # 线性函数：(max_count - current_count + 1) / (max_count + 1)
                frequency_factor = (max_total_count - total_count + 1) / (
                    max_total_count + 1
                )
            elif settings["frequency_function"] == 1:  # 平方根函数
                # 平方根函数：sqrt(max_count + 1) / sqrt(current_count + 1)
                frequency_factor = math.sqrt(max_total_count + 1) / math.sqrt(
                    total_count + 1
                )
            elif settings["frequency_function"] == 2:  # 指数函数
                # 指数函数：exp((max_count - current_count) / max_count)
                # 当max_total_count为0时，避免除零错误
                if max_total_count == 0:
                    frequency_factor = 1.0  # 所有学生都未被抽中时，频率因子为1
                else:
                    frequency_factor = math.exp(
                        (max_total_count - total_count) / max_total_count
                    )
            else:  # 默认平方根函数
                frequency_factor = math.sqrt(max_total_count + 1) / math.sqrt(
                    total_count + 1
                )

            # 冷启动特殊处理 - 防止新学生权重过低
            if is_cold_start:
                # 冷启动模式下，降低频率因子的影响，使抽取更随机
                frequency_factor = min(0.8 + (frequency_factor * 0.2), frequency_factor)

            # 应用频率权重
            frequency_penalty = frequency_factor * settings["frequency_weight"]
        else:
            frequency_penalty = 0.0

        # 计算小组平衡因子
        if settings["fair_draw_group_enabled"]:
            # 获取学生当前小组
            current_student_group = student.get("group", "")

            # 获取有效小组统计数量（值>0的条目）
            valid_groups = [v for v in group_stats.values() if v > 0]

            if len(valid_groups) > 3:  # 有效小组数量达标
                group_history = max(group_stats.get(current_student_group, 0), 0)
                group_factor = 1.0 / (group_history * 0.2 + 1)
                group_balance = group_factor * settings["group_weight"]
            else:
                # 数据不足时，使用相对计数方法
                all_counts = [data["group_count"] for data in weight_data.values()]
                max_group_count = max(all_counts) if all_counts else 0

                if max_group_count == 0:
                    group_balance = (
                        0.2 * settings["group_weight"]
                    )  # 给所有学生一个小组平衡的基础权重提升
                elif student_weight_data["group_count"] == 0:
                    group_balance = (
                        0.5 * settings["group_weight"]
                    )  # 给从未在小组中被选中的学生一个基础权重提升
                else:
                    group_balance = settings["group_weight"] * (
                        1.0 - (student_weight_data["group_count"] / max_group_count)
                    )
        else:
            group_balance = 0.0

        # 计算性别平衡因子
        if settings["fair_draw_gender_enabled"]:
            # 获取学生当前性别
            current_student_gender = student.get("gender", "")

            # 获取有效性别统计数量（值>0的条目）
            valid_gender = [v for v in gender_stats.values() if v > 0]

            if len(valid_gender) > 3:  # 有效性别数量达标
                gender_history = max(gender_stats.get(current_student_gender, 0), 0)
                gender_factor = 1.0 / (gender_history * 0.2 + 1)
                gender_balance = gender_factor * settings["gender_weight"]
            else:
                # 数据不足时，使用相对计数方法
                all_counts = [data["gender_count"] for data in weight_data.values()]
                max_gender_count = max(all_counts) if all_counts else 0

                if max_gender_count == 0:
                    gender_balance = (
                        0.2 * settings["gender_weight"]
                    )  # 给所有学生一个性别平衡的基础权重提升
                elif student_weight_data["gender_count"] == 0:
                    gender_balance = (
                        0.5 * settings["gender_weight"]
                    )  # 给从未在性别平衡中被选中的学生一个基础权重提升
                else:
                    gender_balance = settings["gender_weight"] * (
                        1.0 - (student_weight_data["gender_count"] / max_gender_count)
                    )
        else:
            gender_balance = 0.0

        # 计算时间因子
        if (
            settings["fair_draw_time_enabled"]
            and student_weight_data["last_drawn_time"]
        ):
            try:
                from datetime import datetime

                last_time = datetime.fromisoformat(
                    student_weight_data["last_drawn_time"]
                )
                current_time = datetime.now()
                days_diff = (current_time - last_time).days
                time_factor = min(1.0, days_diff / 30.0) * settings["time_weight"]
            except Exception as e:
                logger.exception(
                    "Error calculating time factor for student weights: {}", e
                )
                time_factor = 0.0
        else:
            time_factor = 0.0

        # 检查是否处于屏蔽期
        is_shielded = False
        shield_remaining = 0
        if settings["shield_enabled"] and student_weight_data["last_drawn_time"]:
            try:
                from datetime import datetime, timedelta

                last_time = datetime.fromisoformat(
                    student_weight_data["last_drawn_time"]
                )
                current_time = datetime.now()

                # 根据时间单位计算屏蔽时间
                if settings["shield_time_unit"] == 0:  # 秒
                    shield_duration = timedelta(seconds=settings["shield_time"])
                elif settings["shield_time_unit"] == 1:  # 分钟
                    shield_duration = timedelta(minutes=settings["shield_time"])
                else:  # 小时
                    shield_duration = timedelta(hours=settings["shield_time"])

                # 检查是否在屏蔽期内
                if current_time - last_time < shield_duration:
                    is_shielded = True
                    shield_remaining = (
                        shield_duration - (current_time - last_time)
                    ).total_seconds()
            except Exception as e:
                logger.exception("Error calculating shield time for student: {}", e)

        # 计算总权重
        student_weights = {
            "base": settings["base_weight"],  # 基础权重
            "frequency": frequency_penalty,  # 频率惩罚
            "group": group_balance,  # 小组平衡
            "gender": gender_balance,  # 性别平衡
            "time": time_factor,  # 时间因子
        }

        total_weight = sum(student_weights.values())

        # 如果处于屏蔽期，设置极低权重
        if is_shielded:
            total_weight = settings["min_weight"] / 10  # 屏蔽期内权重为最小值的1/10

        # 确保权重在最小和最大值之间
        total_weight = max(
            settings["min_weight"] / 10, min(settings["max_weight"], total_weight)
        )
        total_weight = round(total_weight, 2)

        # 设置学生的权重和详细信息
        student["next_weight"] = total_weight
        student["weight_details"] = {
            "base_weight": student_weights["base"],
            "frequency_penalty": student_weights["frequency"],
            "group_balance": student_weights["group"],
            "gender_balance": student_weights["gender"],
            "time_factor": student_weights["time"],
            "total_weight": total_weight,
            "is_cold_start": is_cold_start,
            "total_count": total_count,
            "max_total_count": max_total_count,
            "frequency_function": settings["frequency_function"],
            "is_shielded": is_shielded,
            "shield_remaining": round(shield_remaining, 2),
            "shield_enabled": settings["shield_enabled"],
        }

    return students_data

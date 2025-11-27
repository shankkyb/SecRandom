# 基础设置语言配置
basic_settings = {
    "ZH_CN": {
        "title": {"name": "基础设置", "description": "配置软件的基本功能和外观"},
        "basic_function": {"name": "基础功能", "description": "配置软件的核心功能选项"},
        "data_management": {
            "name": "数据管理",
            "description": "管理软件的数据导入和导出",
        },
        "personalised": {"name": "个性化", "description": "自定义软件外观和用户体验"},
        "autostart": {
            "name": "开机自启",
            "description": "设置软件是否随系统启动自动运行",
            "switchbutton_name": {"enable": "", "disable": ""},
        },
        "background_resident": {
            "name": "后台驻留",
            "description": "关闭所有窗口后是否仍在后台常驻",
            "switchbutton_name": {"enable": "", "disable": ""}
        },
        "url_protocol": {
            "name": "URL协议注册",
            "description": "注册自定义URL协议(secrandom://)，支持通过链接启动应用",
            "switchbutton_name": {"enable": "", "disable": ""}
        },
        "export_diagnostic_data": {
            "name": "导出诊断数据",
            "description": "退出软件时导出诊断信息，用于排查问题",
            "pushbutton_name": "导出诊断数据",
        },
        "export_settings": {
            "name": "导出设置",
            "description": "将当前设置导出为配置文件，用于备份和迁移",
            "pushbutton_name": "导出设置",
        },
        "import_settings": {
            "name": "导入设置",
            "description": "从配置文件导入设置，覆盖当前配置信息",
            "pushbutton_name": "导入设置",
        },
        "export_all_data": {
            "name": "导出所有数据",
            "description": "退出软件时导出全部数据和设置",
            "pushbutton_name": "导出所有数据",
        },
        "import_all_data": {
            "name": "导入所有数据",
            "description": "启动软件时从备份文件恢复全部数据",
            "pushbutton_name": "导入所有数据",
        },
        "log_level": {
            "name": "日志等级",
            "description": "设置日志记录详细程度",
            "combo_items": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        },
        "dpiScale": {
            "name": "DPI缩放",
            "description": "调整软件界面缩放比例（重启软件后生效）",
            "combo_items": ["100%", "125%", "150%", "175%", "200%", "自动"],
        },
        "font": {
            "name": "字体",
            "description": "设置软件界面显示字体（重启软件后生效）",
        },
        "theme": {
            "name": "主题模式",
            "description": "选择软件界面主题样式",
            "combo_items": ["浅色", "深色", "跟随系统"],
        },
        "theme_color": {"name": "主题颜色", "description": "设置软件界面主题色彩"},
        "language": {
            "name": "显示语言",
            "description": "切换软件界面语言（重启软件后生效）",
        },
        "settings_import_export": {
            "export_success_title": {"name": "导出设置"},
            "export_success_content": {"name": "设置已成功导出到:\n{path}"},
            "export_failure_title": {"name": "导出设置"},
            "export_failure_content": {"name": "导出设置失败:\n{error}"},
            "import_confirm_title": {"name": "导入设置"},
            "import_confirm_content": {"name": "确定要导入这些设置吗？这将覆盖当前设置"},
            "import_confirm_button": {"name": "确认导入"},
            "import_cancel_button": {"name": "取消导入"},
            "import_success_title": {"name": "导入设置"},
            "import_success_content": {"name": "设置已成功导入\n重启应用程序以使更改生效"},
            "import_success_button": {"name": "我知道了"},
            "export_success_button": {"name": "我知道了"},
            "import_failure_title": {"name": "导入设置"},
            "import_failure_content": {"name": "导入设置失败:\n{error}"},
        },
        "data_import_export": {
            "export_success_title": {"name": "导出所有数据"},
            "export_success_content": {"name": "所有数据已成功导出到:\n{path}"},
            "export_failure_title": {"name": "导出所有数据"},
            "export_failure_content": {"name": "导出所有数据失败:\n{error}"},
            "import_confirm_title": {"name": "导入所有数据"},
            "import_confirm_content": {"name": "确定要导入这些数据吗？这将覆盖当前数据"},
            "import_confirm_button": {"name": "确认导入"},
            "import_cancel_button": {"name": "取消导入"},
            "import_success_title": {"name": "导入所有数据"},
            "import_success_content": {"name": "数据已成功导入\n重启应用程序以使更改生效"},
            "import_success_button": {"name": "我知道了"},
            "import_failure_title": {"name": "导入所有数据"},
            "import_failure_content": {"name": "导入所有数据失败:\n{error}"},
            "existing_files_count": {"name": "\n... 还有 {len} 个文件"},
            "existing_files_title": {"name": "文件已存在"},
            "existing_files_content": {"name": "以下文件已存在:\n{files}\n\n是否覆盖这些文件？"},
            "version_mismatch_title": {"name": "版本不匹配"},
            "version_mismatch_content": {"name": "导出数据的软件版本与当前版本不一致:\n\n导出数据的软件: {software_name} {version}\n当前软件: SecRandom {current_version}\n\n是否继续导入？"},
            "export_warning_title": {"name": "导出所有数据"},
            "export_warning_content": {"name": "即将导出所有数据，包括:\n\n软件版本、设置配置\n点名名单、抽奖名单\n历史记录、日志文件\n\n注意: 导出的数据可能包含敏感信息，请妥善保管。\n\n是否继续导出?"},
        },
        "diagnostic_data_export": {
            "export_confirm_button": {"name": "确认导出"},
            "export_cancel_button": {"name": "取消导出"},
            "export_success_title": {"name": "导出诊断数据"},
            "export_success_content": {"name": "诊断数据已成功导出到:\n{path}"},
            "export_failure_title": {"name": "导出诊断数据"},
            "export_failure_content": {"name": "导出诊断数据失败:\n{error}"},
            "export_warning_title": {"name": "导出诊断数据"},
            "export_warning_content": {"name": "即将导出诊断数据，包括:\n\n软件信息、设置配置\n点名名单、抽奖名单\n历史记录、日志文件\n\n注意: 导出的数据可能包含敏感信息，请妥善保管。\n\n是否继续导出?"},
        },
    }
}

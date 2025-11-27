from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from PySide6.QtNetwork import *
from qfluentwidgets import *

from loguru import logger

from app.tools.personalised import load_custom_font, get_theme_icon, is_dark_theme
from app.tools.settings_access import readme_settings_async, update_settings, get_settings_signals
from app.tools.path_utils import *
from app.Language.obtain_language import get_content_combo_name_async


class LevitationWindow(QWidget):
    rollCallRequested = Signal()
    quickDrawRequested = Signal()
    instantDrawRequested = Signal()
    customDrawRequested = Signal()
    lotteryRequested = Signal()
    visibilityChanged = Signal(bool)
    positionChanged = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self._shadow = None
        self._drag_timer = QTimer(self)
        self._drag_timer.setSingleShot(True)
        self._drag_timer.timeout.connect(self._begin_drag)
        self._dragging = False
        self._press_pos = QPoint()
        self._indicator = None
        self._retract_timer = QTimer(self)
        self._retract_timer.setSingleShot(True)
        self._retracted = False
        self._last_stuck = False
        self._edge_threshold = 5
        self._placement = 0
        self._display_style = 0
        self._stick_to_edge = True
        self._retract_seconds = 5
        self._long_press_ms = 500
        self._buttons_spec = []
        self._font_family = load_custom_font() or QFont().family()
        self._container = QWidget(self)
        self._layout = None
        self._btn_size = QSize(60, 60)
        self._icon_size = QSize(24, 24)
        self._spacing = 6
        self._margins = 6
        self._init_settings()
        self._build_ui()
        self._apply_window()
        self._apply_position()
        self._install_drag_filters()
        get_settings_signals().settingChanged.connect(self._on_setting_changed)
        # 连接主题变更信号
        try:
            qconfig.themeChanged.connect(self._on_theme_changed)
        except Exception as e:
            logger.exception("连接 themeChanged 信号时出错（已忽略）: {}", e)
        self._apply_theme_style()

    def rebuild_ui(self):
        """
        重新构建浮窗UI
        删除当前布局并创建新的布局
        """
        # 清除现有按钮
        self._clear_buttons()
        
        # 重新创建容器布局
        container_layout = self._create_container_layout()
        
        # 设置新的布局
        old_layout = self._container.layout()
        if old_layout:
            QWidget().setLayout(old_layout)  # 从容器中移除旧布局
            
        self._container.setLayout(container_layout)
        
        # 重新添加按钮
        for i, spec in enumerate(self._buttons_spec):
            btn = self._create_button(spec)
            self._add_button(btn, i, len(self._buttons_spec))
            
        self._container.adjustSize()
        self.adjustSize()
        self._install_drag_filters()

    def _clear_buttons(self):
        """清除所有按钮"""
        # 清除顶层和底层的按钮
        if hasattr(self, '_top') and self._top and self._top.layout():
            top_layout = self._top.layout()
            while top_layout.count():
                item = top_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                    
        if hasattr(self, '_bottom') and self._bottom and self._bottom.layout():
            bottom_layout = self._bottom.layout()
            while bottom_layout.count():
                item = bottom_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                    
        # 清除容器直接包含的按钮
        container_layout = self._container.layout()
        if container_layout:
            while container_layout.count():
                item = container_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                    
    def _font(self, size):
        s = int(size) if size and int(size) > 0 else 8
        if s <= 0:
            s = 8
        f = QFont(self._font_family) if self._font_family else QFont()
        if s > 0:  # 确保字体大小大于0
            f.setPointSize(s)
        return f

    def _apply_theme_style(self):
        # 主题样式应用：深色/浅色配色修正
        dark = is_dark_theme(qconfig)
        self._container.setAttribute(Qt.WA_StyledBackground, True)
        if dark:
            self._container.setStyleSheet("background-color: rgba(32,32,32,180); border-radius: 12px; border: 1px solid rgba(255,255,255,20);")
        else:
            self._container.setStyleSheet("background-color: rgba(255,255,255,220); border-radius: 12px; border: 1px solid rgba(0,0,0,12);")

    def _icon_pixmap(self, icon):
        if hasattr(icon, "icon"):
            qicon = icon.icon()
        elif isinstance(icon, QIcon):
            qicon = icon
        else:
            qicon = QIcon()
        return qicon.pixmap(self._icon_size)

    def _init_settings(self):
        self._visible_on_start = bool(readme_settings_async("floating_window_management", "startup_display_floating_window"))
        self._opacity = float(readme_settings_async("floating_window_management", "floating_window_opacity") or 0.8)
        self._placement = int(readme_settings_async("floating_window_management", "floating_window_placement") or 0)
        self._display_style = int(readme_settings_async("floating_window_management", "floating_window_display_style") or 0)
        self._stick_to_edge = bool(readme_settings_async("floating_window_management", "floating_window_stick_to_edge"))
        self._retract_seconds = int(readme_settings_async("floating_window_management", "floating_window_stick_to_edge_recover_seconds") or 0)
        self._long_press_ms = int(readme_settings_async("floating_window_management", "floating_window_long_press_duration") or 500)
        self._stick_indicator_style = int(readme_settings_async("floating_window_management", "floating_window_stick_to_edge_display_style") or 0)
        idx = int(readme_settings_async("floating_window_management", "floating_window_button_control") or 0)
        self._buttons_spec = self._map_button_control(idx)

    def _build_ui(self):
        # 两行布局按索引分配，避免 3+ 个按钮全部落到底部
        lay = self._container.layout()
        if lay:
            while lay.count():
                item = lay.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()
            lay.deleteLater()
        if not self._layout:
            self._layout = QHBoxLayout(self)
            self._layout.setContentsMargins(self._margins, self._margins, self._margins, self._margins)
            self._layout.addWidget(self._container)
        else:
            self._layout.setContentsMargins(self._margins, self._margins, self._margins, self._margins)
        self._container_layout = self._create_container_layout()
        self._container.setLayout(self._container_layout)
        self._container_layout.setAlignment(Qt.AlignCenter)
        for i, spec in enumerate(self._buttons_spec):
            btn = self._create_button(spec)
            self._add_button(btn, i, len(self._buttons_spec))
        self._container.adjustSize()
        self.adjustSize()
        self._install_drag_filters()

    def _apply_window(self):
        self.setWindowOpacity(self._opacity)
        if self._visible_on_start:
            self.show()
        else:
            self.hide()

    def _apply_position(self):
        x = int(readme_settings_async("float_position", "x") or 100)
        y = int(readme_settings_async("float_position", "y") or 100)
        nx, ny = self._clamp_to_screen(x, y)
        self.move(nx, ny)

    def _clamp_to_screen(self, x, y):
        fg = self.frameGeometry()
        scr = QGuiApplication.screenAt(fg.center()) or QApplication.primaryScreen()
        geo = scr.availableGeometry()
        cx = max(geo.left(), min(x, geo.right() - self.width() + 1))
        cy = max(geo.top(), min(y, geo.bottom() - self.height() + 1))
        return cx, cy

    def _create_container_layout(self):
        if hasattr(self, '_top') and self._top:
            self._top.deleteLater()
            self._top = None
        if hasattr(self, '_bottom') and self._bottom:
            self._bottom.deleteLater()
            self._bottom = None
        if self._placement == 1:
            lay = QVBoxLayout()
            lay.setContentsMargins(self._margins, self._margins, self._margins, self._margins)
            lay.setSpacing(self._spacing)
            return lay
        if self._placement == 2:
            lay = QHBoxLayout()
            lay.setContentsMargins(self._margins, self._margins, self._margins, self._margins)
            lay.setSpacing(self._spacing)
            return lay
        lay = QVBoxLayout()
        lay.setContentsMargins(self._margins, self._margins, self._margins, self._margins)
        lay.setSpacing(self._spacing)
        self._top = QWidget()
        self._bottom = QWidget()
        t = QHBoxLayout(self._top)
        t.setContentsMargins(0, 0, 0, 0)
        t.setSpacing(self._spacing)
        t.setAlignment(Qt.AlignCenter)
        b = QHBoxLayout(self._bottom)
        b.setContentsMargins(0, 0, 0, 0)
        b.setSpacing(self._spacing)
        b.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._top)
        lay.addWidget(self._bottom)
        return lay

    def _create_button(self, spec):
        text_map = get_content_combo_name_async("floating_window_management", "floating_window_button_control")
        names = [text_map[0], text_map[1], text_map[2], text_map[3], text_map[4]]
        if spec == "roll_call":
            icon = get_theme_icon("ic_fluent_people_20_filled")
            text = names[0]
            sig = self.rollCallRequested
        elif spec == "quick_draw":
            icon = get_theme_icon("ic_fluent_flash_20_filled")
            text = names[1]
            sig = self.quickDrawRequested
        elif spec == "instant_draw":
            icon = get_theme_icon("ic_fluent_play_20_filled")
            text = names[2]
            sig = self.instantDrawRequested
        elif spec == "custom_draw":
            icon = get_theme_icon("ic_fluent_edit_20_filled")
            text = names[3]
            sig = self.customDrawRequested
        else:
            icon = get_theme_icon("ic_fluent_gift_20_filled")
            text = names[4]
            sig = self.lotteryRequested
        
        if self._display_style == 1:
            btn = TransparentToolButton()
            btn.setIcon(icon)
            btn.setIconSize(self._icon_size)
            btn.setFixedSize(self._btn_size)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        elif self._display_style == 2:
            btn = PushButton(text)
            btn.setFixedSize(self._btn_size)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setFont(self._font(12))
        else:
            btn = PushButton()
            lay = QVBoxLayout(btn)
            lay.setContentsMargins(0, 4, 0, 4)
            lay.setSpacing(2)
            lab_icon = TransparentToolButton()
            lab_icon.setIcon(icon)
            lab_icon.setIconSize(self._icon_size)
            lab_icon.setFixedSize(self._icon_size)
            # 复合按钮图标不置灰，避免低对比；忽略鼠标事件
            lab_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lab_icon.setFocusPolicy(Qt.NoFocus)
            lab_text = BodyLabel(text)
            lab_text.setAlignment(Qt.AlignCenter)
            lab_text.setFont(self._font(10))
            lab_text.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lab_text.setFocusPolicy(Qt.NoFocus)
            lay.addWidget(lab_icon)
            lay.addWidget(lab_text)
            lay.setAlignment(Qt.AlignCenter)
            lay.setAlignment(lab_icon, Qt.AlignCenter)
            lay.setAlignment(lab_text, Qt.AlignCenter)
            btn.setFixedSize(self._btn_size)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.clicked.connect(sig.emit)
        return btn

    def _add_button(self, btn, index, total):
        if self._placement == 1:
            self._container.layout().addWidget(btn, 0, Qt.AlignCenter)
            return
        if self._placement == 2:
            self._container.layout().addWidget(btn, 0, Qt.AlignCenter)
            return
        # 前半放顶行，后半放底行
        split = (total + 1) // 2
        if index < split:
            self._top.layout().addWidget(btn, 0, Qt.AlignCenter)
        else:
            self._bottom.layout().addWidget(btn, 0, Qt.AlignCenter)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press_pos = e.globalPosition().toPoint()
            self._dragging = False
            self._drag_timer.stop()
            self._drag_timer.start(self._long_press_ms)

    def _begin_drag(self):
        self._dragging = True
        self.setCursor(Qt.ClosedHandCursor)
        pass

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            # 支持移动阈值触发拖拽，提升交互体验
            cur = e.globalPosition().toPoint()
            if not self._dragging:
                delta0 = cur - self._press_pos
                if abs(delta0.x()) >= 3 or abs(delta0.y()) >= 3:
                    self._begin_drag()
            if self._dragging:
                delta = cur - self._press_pos
                self.move(self.x() + delta.x(), self.y() + delta.y())
                self._press_pos = cur
                self._cancel_retract()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_timer.stop()
            self.setCursor(Qt.ArrowCursor)
            if self._dragging:
                self._dragging = False
                self._stick_to_nearest_edge()
                if self._last_stuck:
                    self._schedule_retract()
                else:
                    self._clear_indicator()
            self._save_position()
            pass

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self._press_pos = event.globalPosition().toPoint()
                self._dragging = False
                self._drag_timer.stop()
                self._drag_timer.start(self._long_press_ms)
            return False
        if event.type() == QEvent.MouseMove:
            if event.buttons() & Qt.LeftButton:
                cur = event.globalPosition().toPoint()
                if not self._dragging:
                    delta0 = cur - self._press_pos
                    if abs(delta0.x()) >= 3 or abs(delta0.y()) >= 3:
                        self._begin_drag()
                if self._dragging:
                    delta = cur - self._press_pos
                    self.move(self.x() + delta.x(), self.y() + delta.y())
                    self._press_pos = cur
                    self._cancel_retract()
                    return True
            return False
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                self._drag_timer.stop()
                if self._dragging:
                    self._dragging = False
                    self.setCursor(Qt.ArrowCursor)
                    self._stick_to_nearest_edge()
                    if self._last_stuck:
                        self._schedule_retract()
                    else:
                        self._clear_indicator()
                    self._save_position()
                    pass
                    return True
            return False
        return False

    def _install_drag_filters(self):
        self._container.installEventFilter(self)
        for w in self._container.findChildren(QWidget):
            w.installEventFilter(self)

    def enterEvent(self, e):
        if self._retracted:
            self._expand_from_edge()

    def leaveEvent(self, e):
        if self._retracted:
            self._schedule_retract()

    def _stick_to_nearest_edge(self):
        if not self._stick_to_edge:
            return
        fg = self.frameGeometry()
        scr = QGuiApplication.screenAt(fg.center()) or QApplication.primaryScreen()
        geo = scr.availableGeometry()
        left = fg.left() - geo.left()
        right = geo.right() - fg.right()
        self._last_stuck = False
        if left <= self._edge_threshold:
            self.move(geo.left(), self.y())
            self._show_indicator("left")
            self._last_stuck = True
            return
        if right <= self._edge_threshold:
            self.move(geo.right() - self.width() + 1, self.y())
            self._show_indicator("right")
            self._last_stuck = True

    def _schedule_retract(self):
        if not self._stick_to_edge:
            return
        if self._retract_seconds and self._retract_seconds > 0:
            self._retract_timer.stop()
            self._retract_timer.start(self._retract_seconds * 1000)

    def _cancel_retract(self):
        if self._retract_timer.isActive():
            self._retract_timer.stop()

    def _retract_into_edge(self):
        # 防多屏错位：基于当前屏幕几何
        fg = self.frameGeometry()
        scr = QGuiApplication.screenAt(fg.center()) or QApplication.primaryScreen()
        geo = scr.availableGeometry()
        handle = 16
        if self.x() <= geo.left():
            self.move(geo.left() - self.width() + handle, self.y())
            self._retracted = True
            self._show_indicator("right")
        elif self.x() + self.width() >= geo.right():
            self.move(geo.right() - handle + 1, self.y())
            self._retracted = True
            self._show_indicator("left")

    def _expand_from_edge(self):
        # 基于当前屏幕可用区域展开
        fg = self.frameGeometry()
        scr = QGuiApplication.screenAt(fg.center()) or QApplication.primaryScreen()
        geo = scr.availableGeometry()
        if self.x() < geo.left():
            self.move(geo.left(), self.y())
        elif self.x() + self.width() > geo.right():
            self.move(geo.right() - self.width() + 1, self.y())
        self._retracted = False
        self._clear_indicator()

    def _show_indicator(self, direction):
        self._clear_indicator()
        w = QWidget(self)
        w.resize(16, 16)
        if self._stick_indicator_style == 0:
            tb = ToolButton(w)
            qicon = get_theme_icon("ic_fluent_pin_20_filled").icon()
            tb.setIcon(qicon)
            tb.setIconSize(QSize(14, 14))
            tb.setFixedSize(16, 16)
        elif self._stick_indicator_style == 1:
            lab = BodyLabel("浮窗", w)
            lab.setAlignment(Qt.AlignCenter)
            lab.setFont(self._font(8))
        else:
            lab = BodyLabel(w)
            lab.setStyleSheet("border-radius: 2px;")
        if direction == "left":
            w.move(-8, self.height() // 2 - 8)
        elif direction == "right":
            w.move(self.width() - 8, self.height() // 2 - 8)
        else:
            w.move(self.width() // 2 - 8, -8)
        w.show()
        self._indicator = w

    def _clear_indicator(self):
        if self._indicator:
            self._indicator.hide()
            self._indicator.deleteLater()
            self._indicator = None

    def _save_position(self):
        update_settings("float_position", "x", self.x())
        update_settings("float_position", "y", self.y())
        self.positionChanged.emit(self.x(), self.y())

    def _on_setting_changed(self, first, second, value):
        if first == "floating_window_management":
            if second == "startup_display_floating_window":
                if bool(value):
                    self.show()
                else:
                    self.hide()
                self.visibilityChanged.emit(bool(value))
            elif second == "floating_window_opacity":
                self._opacity = float(value or 0.8)
                self.setWindowOpacity(self._opacity)
            elif second == "floating_window_placement":
                self._placement = int(value or 0)
                self.rebuild_ui()
            elif second == "floating_window_display_style":
                self._display_style = int(value or 0)
                self.rebuild_ui()
            elif second == "floating_window_stick_to_edge":
                self._stick_to_edge = bool(value)
            elif second == "floating_window_stick_to_edge_recover_seconds":
                self._retract_seconds = int(value or 0)
            elif second == "floating_window_long_press_duration":
                self._long_press_ms = int(value or 500)
            elif second == "floating_window_stick_to_edge_display_style":
                self._stick_indicator_style = int(value or 0)
            elif second == "floating_window_button_control":
                self._buttons_spec = self._map_button_control(int(value or 0))
                self.rebuild_ui()
            # 当任何影响外观的设置改变时，重新应用主题样式
            self._apply_theme_style()
        elif first == "float_position":
            if second == "x":
                x = int(value or 0)
                nx, ny = self._clamp_to_screen(x, self.y())
                self.move(nx, ny)
            elif second == "y":
                y = int(value or 0)
                nx, ny = self._clamp_to_screen(self.x(), y)
                self.move(nx, ny)

    def _on_theme_changed(self):
        """当系统主题变更时调用"""
        self._apply_theme_style()

    def _map_button_control(self, idx):
        combos = [
            ["roll_call"],
            ["quick_draw"],
            ["instant_draw"],
            ["custom_draw"],
            ["lottery"],
            ["roll_call", "quick_draw"],
            ["roll_call", "custom_draw"],
            ["roll_call", "lottery"],
            ["quick_draw", "custom_draw"],
            ["quick_draw", "lottery"],
            ["custom_draw", "lottery"],
            ["roll_call", "quick_draw", "custom_draw"],
            ["roll_call", "quick_draw", "lottery"],
            ["roll_call", "custom_draw", "lottery"],
            ["quick_draw", "custom_draw", "lottery"],
            ["roll_call", "quick_draw", "custom_draw", "lottery"],
        ]
        if idx < 0 or idx >= len(combos):
            return combos[0]
        return combos[idx]

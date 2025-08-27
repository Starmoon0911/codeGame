# level_editor.py
import sys, os, json
from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSlider, QPushButton, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush

# 從主遊戲引擎引入顏色定義
from engine3d import COLORS, HALF

class EditorGridWidget(QWidget):
    """核心的網格編輯區"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True) # 啟用滑鼠追蹤以實現拖曳繪製
        
        self.grid_range = range(-HALF, HALF + 1)
        self.cell_size = 0
        self.blocks = {}  # {(x, y, z): color_id}
        self.current_y = 0
        self.current_color = 1

    def set_layer(self, y_layer):
        self.current_y = y_layer
        self.update()

    def set_color(self, color_id):
        self.current_color = color_id

    def get_blocks_data(self):
        return self.blocks

    def _get_grid_pos(self, mouse_pos):
        """將像素座標轉換為網格座標 (x, z)"""
        if self.cell_size == 0: return None
        
        offset_x = (self.width() - self.cell_size * len(self.grid_range)) / 2
        offset_z = (self.height() - self.cell_size * len(self.grid_range)) / 2
        
        grid_x = int((mouse_pos.x() - offset_x) / self.cell_size) + min(self.grid_range)
        grid_z = int((mouse_pos.y() - offset_z) / self.cell_size) + min(self.grid_range)

        if grid_x in self.grid_range and grid_z in self.grid_range:
            return grid_x, grid_z
        return None

    def _handle_mouse_event(self, event):
        pos = self._get_grid_pos(event.pos())
        if not pos: return

        x, z = pos
        coord = (x, self.current_y, z)

        if event.buttons() & Qt.LeftButton:
            if self.blocks.get(coord) != self.current_color:
                self.blocks[coord] = self.current_color
                self.update()
        elif event.buttons() & Qt.RightButton:
            if coord in self.blocks:
                del self.blocks[coord]
                self.update()

    def mousePressEvent(self, event):
        self._handle_mouse_event(event)

    def mouseMoveEvent(self, event):
        self._handle_mouse_event(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#2E3440")) # 背景色

        grid_len = len(self.grid_range)
        self.cell_size = min(self.width(), self.height()) * 0.9 / grid_len
        
        offset_x = (self.width() - self.cell_size * grid_len) / 2
        offset_z = (self.height() - self.cell_size * grid_len) / 2

        # 繪製方塊
        for (x, y, z), color_id in self.blocks.items():
            if y == self.current_y:
                draw_x = (x - min(self.grid_range)) * self.cell_size + offset_x
                draw_z = (z - min(self.grid_range)) * self.cell_size + offset_z
                
                r, g, b = [int(c * 255) for c in COLORS.get(color_id, (0,0,0))]
                painter.setBrush(QBrush(QColor(r, g, b)))
                painter.setPen(Qt.NoPen)
                painter.drawRect(int(draw_x), int(draw_z), int(self.cell_size), int(self.cell_size))

        # 繪製網格線
        painter.setPen(QPen(QColor("#4C566A"), 1))
        for i in range(grid_len + 1):
            # 垂直線
            x_pos = offset_x + i * self.cell_size
            painter.drawLine(QPoint(int(x_pos), int(offset_z)), QPoint(int(x_pos), int(offset_z + grid_len * self.cell_size)))
            # 水平線
            z_pos = offset_z + i * self.cell_size
            painter.drawLine(QPoint(int(offset_x), int(z_pos)), QPoint(int(offset_x + grid_len * self.cell_size), int(z_pos)))

class LevelEditorDialog(QDialog):
    """關卡編輯器主視窗"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("關卡編輯器")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(parent.styleSheet() if parent else "") # 繼承主視窗樣式

        main_layout = QHBoxLayout(self)
        controls_layout = QVBoxLayout()
        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls_widget.setFixedWidth(250)

        # 1. 網格編輯區
        self.grid_widget = EditorGridWidget()

        # 2. 圖層控制
        controls_layout.addWidget(QLabel("<b>圖層 (Y軸)</b>"))
        layer_control_layout = QHBoxLayout()
        self.layer_slider = QSlider(Qt.Vertical)
        self.layer_slider.setRange(min(self.grid_widget.grid_range), max(self.grid_widget.grid_range))
        self.layer_slider.setValue(0)
        self.layer_slider.setTickPosition(QSlider.TicksRight)
        self.layer_slider.setTickInterval(1)
        
        self.layer_label = QLabel(f"Y = {self.layer_slider.value()}")
        self.layer_label.setAlignment(Qt.AlignCenter)

        layer_control_layout.addWidget(self.layer_label)
        layer_control_layout.addWidget(self.layer_slider)
        controls_layout.addLayout(layer_control_layout)

        # 3. 顏色選擇盤
        controls_layout.addWidget(QLabel("<b>顏色選擇</b>"))
        palette_layout = QVBoxLayout()
        self.color_buttons = {}
        for color_id, rgb in sorted(COLORS.items()):
            btn = QPushButton(f"顏色 {color_id}")
            r,g,b = [int(c*255) for c in rgb]
            btn.setStyleSheet(f"background-color: rgb({r},{g},{b}); color: {'black' if r > 200 and g > 200 else 'white'};")
            # 使用 lambda 傳遞參數
            btn.clicked.connect(lambda _, cid=color_id: self._select_color(cid))
            self.color_buttons[color_id] = btn
            palette_layout.addWidget(btn)
        controls_layout.addLayout(palette_layout)
        self._select_color(1) # 預設選中第一個顏色

        # 4. 關卡資訊和儲存
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("<b>關卡名稱</b>"))
        self.level_name_input = QLineEdit("我的新關卡")
        controls_layout.addWidget(self.level_name_input)

        save_button = QPushButton("儲存關卡")
        save_button.setStyleSheet("background-color: #A3BE8C; color: #2E3440;")
        controls_layout.addWidget(save_button)

        # 連接信號
        self.layer_slider.valueChanged.connect(self._update_layer)
        save_button.clicked.connect(self._save_level)

        main_layout.addWidget(controls_widget)
        main_layout.addWidget(self.grid_widget)

    def _update_layer(self, value):
        self.layer_label.setText(f"Y = {value}")
        self.grid_widget.set_layer(value)

    def _select_color(self, color_id):
        self.grid_widget.set_color(color_id)
        # 更新按鈕視覺效果
        for cid, btn in self.color_buttons.items():
            if cid == color_id:
                btn.setStyleSheet(btn.styleSheet() + "border: 2px solid #EBCB8B;")
            else:
                btn.setStyleSheet(btn.styleSheet().replace("border: 2px solid #EBCB8B;", ""))

    def _save_level(self):
        level_name = self.level_name_input.text().strip()
        if not level_name:
            QMessageBox.warning(self, "錯誤", "請輸入關卡名稱！")
            return

        blocks_data = self.grid_widget.get_blocks_data()
        if not blocks_data:
            QMessageBox.warning(self, "錯誤", "關卡中沒有任何方塊！")
            return
            
        # 格式化為遊戲可讀的 JSON
        output_data = {
            "name": level_name,
            "blocks": [{"pos": list(pos), "color": cid} for pos, cid in blocks_data.items()]
        }
        
        # 尋找一個不重複的檔案名稱
        i = 1
        while True:
            filename = f"custom_level_{i}.json"
            filepath = os.path.join("levels", filename)
            if not os.path.exists(filepath):
                break
            i += 1
            
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "成功", f"關卡已儲存至:\n{filepath}")
            self.accept() # 關閉編輯器視窗
        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", f"無法寫入檔案：\n{e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 測試用：需要一個基本的樣式表
    app.setStyleSheet("QWidget { background-color:#2E3440; color:#ECEFF4; }")
    editor = LevelEditorDialog()
    editor.exec_()
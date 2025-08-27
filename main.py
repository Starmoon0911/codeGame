# main.py
import sys, os, re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSplitter, QComboBox, QPushButton, QFrame,
    QInputDialog, QMessageBox, QSlider, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from engine3d import VoxelGLWidget, TargetPreviewWidget, COLORS, HALF
from editor import CodeEditor
from level_editor import LevelEditorDialog 
import json

COLOR_NAMES = {1:"亮紅色",2:"亮橘色",3:"亮黃色",4:"亮綠色",5:"亮青色",6:"亮藍色",7:"亮洋紅色",8:"亮白色"}
SETTINGS_FILE = "settings.json"

# 如果沒有 settings.json，自動建立
if not os.path.exists(SETTINGS_FILE):
    default_settings = {
        "volume": 100,
        "resolution": [1280, 720],
        "fullscreen": False
    }
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(default_settings, f, indent=4, ensure_ascii=False)
    print("已自動建立預設 settings.json")
def wrap_code(user_code):
    lines=user_code.split("\n");wrapped="def rule(x,y,z):\n"
    for l in lines:
        if l.strip()=="":continue
        wrapped+="    "+l+"\n"
    wrapped+="    return 0\n";return wrapped

# --- 【核心修正】這裡是包含所有樣式的完整 STYLESHEET ---
STYLESHEET="""
    QWidget{background-color:#2E3440;color:#ECEFF4;font-family:'Consolas','Menlo','Courier New',monospace;font-size:14px;}
    QComboBox{background-color:#3B4252;border:1px solid #4C566A;border-radius:4px;padding:4px 10px;}
    QComboBox:hover{border-color:#5E81AC;}QComboBox::drop-down{border:none;}
    QComboBox QAbstractItemView{background-color:#3B4252;border:1px solid #5E81AC;border-radius:4px;color:#ECEFF4;selection-background-color:#81A1C1;}
    QSplitter::handle{background-color:#434C5E;}QSplitter::handle:hover{background-color:#5E81AC;}QSplitter::handle:pressed{background-color:#81A1C1;}
    QLabel#errorLabel{padding:5px;font-size:13px;}
    QLabel#scoreLabel{font-size:18px;font-weight:bold;color:#EBCB8B;padding:5px;}
    QPushButton{background-color:#88C0D0;color:#2E3440;font-weight:bold;border-radius:4px;padding:8px 16px;border:none;}
    QPushButton:hover{background-color:#8FBCBB;}
    QPushButton:pressed{background-color:#81A1C1;}
    QPushButton#editorBtn { background-color: #5E81AC; color: #ECEFF4; }
    QPushButton#editorBtn:hover { background-color: #81A1C1; }
    QLabel.title{font-size:14px;font-weight:bold;color:#D8DEE9;margin-top:10px;margin-bottom:5px;}
    QSlider::groove:horizontal { border: 1px solid #4C566A; background: #3B4252; height: 5px; border-radius: 2px; }
    QSlider::handle:horizontal { background: #88C0D0; border: 1px solid #88C0D0; width: 16px; margin: -6px 0; border-radius: 8px; }
    QSlider::sub-page:horizontal { background: #5E81AC; }
    QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #4C566A; border-radius: 3px; background-color: #3B4252; }
    QCheckBox::indicator:checked { background-color: #88C0D0; }
    QTableView#completerPopup{background-color:#252526;border:1px solid #454545;border-radius:4px;color:#CCCCCC;gridline-color:transparent;}
    QTableView#completerPopup::item{padding-left:5px;}
    QTableView#completerPopup::item:selected{background-color:#04395E;color:#FFFFFF;}
    QTableView#completerPopup::item:!selected{color:#777777;}
    QTableView#completerPopup QHeaderView::section:horizontal{height:0px;border:none;}
    QTableView#completerPopup QHeaderView::section:vertical{width:0px;border:none;}
    QTableView#completerPopup QScrollBar:vertical{width:0px;}
    QTableView#completerPopup QScrollBar:horizontal{height:0px;}
"""

class GameWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D 即時方塊程式遊戲")
        self.resize(1600, 900)
        self.is_developer_mode = False
        self.load_settings()
        self.progress_data = {}
        self.save_file = "progress.json"
        self.load_progress()
        
        self.slicing_config = {
            'x': {'enabled': False, 'value': HALF},
            'y': {'enabled': False, 'value': HALF},
            'z': {'enabled': False, 'value': HALF}
        }
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
        self.init_ui()

    def load_settings(self):
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                self.is_developer_mode = settings.get("developer_mode", False)
        except (FileNotFoundError, json.JSONDecodeError):
            self.is_developer_mode = False

    def load_progress(self):
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file,"r",encoding="utf-8")as f:self.progress_data=json.load(f)
            except(json.JSONDecodeError,IOError):self.progress_data={}
        else:self.progress_data={}

    def save_progress(self):
        try:
            with open(self.save_file,"w",encoding="utf-8")as f:json.dump(self.progress_data,f,indent=4,ensure_ascii=False)
        except IOError as e:print(f"錯誤：無法儲存進度檔案: {e}")

    def create_color_palette(self):
        palette_widget=QWidget();layout=QVBoxLayout(palette_widget);layout.setContentsMargins(0,5,0,5);layout.setSpacing(6)
        for color_id,rgb_float in sorted(COLORS.items()):
            row_layout=QHBoxLayout();r,g,b=[int(c*255)for c in rgb_float];color_swatch=QLabel();color_swatch.setFixedSize(18,18);color_swatch.setStyleSheet(f"background-color:rgb({r},{g},{b});border-radius:4px;");label=QLabel(f"<b style='color:#81A1C1'>{color_id}</b> : {COLOR_NAMES.get(color_id,'')}");row_layout.addWidget(color_swatch);row_layout.addWidget(label);row_layout.addStretch();layout.addLayout(row_layout)
        return palette_widget
        
    def init_ui(self):
        self._load_ui_elements()

    def _load_ui_elements(self):
        if self.layout():
            while self.layout().count():
                child = self.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        self.level_selector = QComboBox()
        self.levels = []
        levels_dir = "./levels"

        if os.path.exists(levels_dir):
            levels_with_numbers = []
            for file in os.listdir(levels_dir):
                if file.endswith(".json"):
                    path = os.path.join(levels_dir, file)
                    file_id = os.path.splitext(file)[0]
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        num = float('inf')
                        match = re.match(r"^\s*(\d+)", data.get("name", ""))
                        if match:
                            num = int(match.group(1))
                        
                        levels_with_numbers.append({
                            "name": data["name"], "path": path, "id": file_id, "number": num
                        })
                    except Exception as e:
                        print(f"警告：無法載入關卡 {file}: {e}")
            
            levels_with_numbers.sort(key=lambda l: l['number'])
            
            self.levels = levels_with_numbers
            for level in self.levels:
                level_progress = self.progress_data.get(level["id"], {})
                display_name = f"✅ {level['name']}" if level_progress.get("completed") else level['name']
                self.level_selector.addItem(display_name)

        if not self.levels:
            self.level_selector.addItem("未找到關卡")
            self.current_level = None
        else:
            self.current_level = self.levels[0]
            self.level_selector.setCurrentIndex(0)
        
        self.target_voxels={};self.score_label=QLabel("分數: 0");self.score_label.setObjectName("scoreLabel");self.next_level_button=QPushButton("➡️ 前進下一關");self.next_level_button.clicked.connect(self.go_to_next_level);self.next_level_button.hide();self.target_widget=TargetPreviewWidget();self.target_widget.setFixedHeight(250);self.editor=CodeEditor();self.status_label=QLabel("");self.status_label.setObjectName("errorLabel");left_layout=QVBoxLayout()
        
        level_top_layout = QHBoxLayout()
        level_top_layout.addWidget(QLabel("關卡選擇"), 1)
        if self.is_developer_mode:
            editor_button = QPushButton("📝 編輯器");editor_button.setObjectName("editorBtn");editor_button.setFixedWidth(100);editor_button.clicked.connect(self._open_level_editor);level_top_layout.addWidget(editor_button)
        
        left_layout.addLayout(level_top_layout)
        left_layout.addWidget(self.level_selector)

        slicing_group = QWidget()
        slicing_layout = QVBoxLayout(slicing_group)
        slicing_layout.setContentsMargins(0, 10, 0, 5)
        slicing_layout.setSpacing(8)
        slicing_layout.addWidget(QLabel("剖面檢視"))

        self.slice_labels = {}
        for axis in ['x', 'y', 'z']:
            row_layout = QHBoxLayout()
            check_box = QCheckBox(f"啟用 {axis.upper()} 軸")
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-HALF, HALF)
            slider.setValue(HALF)
            slider.setEnabled(False)
            label = QLabel(f"{HALF}")
            self.slice_labels[axis] = label

            check_box.toggled.connect(lambda checked, a=axis, s=slider: self._update_slicing_controls(a, enabled=checked, slider=s))
            slider.valueChanged.connect(lambda value, a=axis: self._update_slicing_controls(a, value=value))
            
            row_layout.addWidget(check_box)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(label)
            slicing_layout.addLayout(row_layout)
        
        left_layout.addWidget(slicing_group)
        
        left_layout.addWidget(QLabel("顏色對照表"));left_layout.addWidget(self.create_color_palette());separator=QFrame();separator.setFrameShape(QFrame.HLine);separator.setFrameShadow(QFrame.Sunken);left_layout.addWidget(separator);
        
        editor_header_layout = QHBoxLayout();editor_header_layout.addWidget(QLabel("程式碼編輯器"));editor_header_layout.addStretch()
        if self.is_developer_mode:
            save_as_level_button = QPushButton("💾 存為關卡");save_as_level_button.setObjectName("editorBtn");save_as_level_button.setFixedWidth(120);save_as_level_button.clicked.connect(self._save_current_voxels_as_level);editor_header_layout.addWidget(save_as_level_button)
        
        left_layout.addLayout(editor_header_layout);left_layout.addWidget(self.editor,1);status_area_layout=QHBoxLayout();status_area_layout.addWidget(self.status_label,1);status_area_layout.addWidget(self.score_label);left_layout.addLayout(status_area_layout);left_layout.addWidget(self.next_level_button,0,Qt.AlignRight);left_widget=QWidget();left_widget.setLayout(left_layout);left_widget.setContentsMargins(10,10,10,10);self.engine_widget=VoxelGLWidget();right_splitter=QSplitter(Qt.Vertical);right_splitter.addWidget(self.target_widget);right_splitter.addWidget(self.engine_widget);right_splitter.setHandleWidth(10);right_splitter.setSizes([450,450]);main_splitter=QSplitter(Qt.Horizontal);main_splitter.addWidget(left_widget);main_splitter.addWidget(right_splitter);main_splitter.setHandleWidth(10);main_splitter.setSizes([800,800]);self.layout().addWidget(main_splitter)
        self.engine_widget.cameraChanged.connect(self.target_widget.set_camera_angles);self.level_selector.currentIndexChanged.connect(self.change_level);self.debounce_timer=QTimer();self.debounce_timer.setSingleShot(True);self.debounce_timer.timeout.connect(self.update_scene);self.editor.textChanged.connect(lambda:self.debounce_timer.start(500));
        if self.levels: self.change_level(0)
    
    def _update_slicing_controls(self, axis, enabled=None, value=None, slider=None):
        if enabled is not None:
            self.slicing_config[axis]['enabled'] = enabled
            if slider:
                slider.setEnabled(enabled)

        if value is not None:
            self.slicing_config[axis]['value'] = value
            self.slice_labels[axis].setText(f"{value}")
        
        self.engine_widget.set_slicing_config(self.slicing_config)
        self.target_widget.set_slicing_config(self.slicing_config)

    def _open_level_editor(self):
        editor_dialog = LevelEditorDialog(self)
        editor_dialog.exec_()
        self._load_ui_elements()

    def _save_current_voxels_as_level(self):
        current_voxels = self.engine_widget.voxels;
        if not current_voxels: QMessageBox.warning(self, "儲存失敗", "場景中沒有任何方塊可以儲存！"); return
        level_name, ok = QInputDialog.getText(self, "儲存新關卡", "請輸入新關卡的名稱：")
        if ok and level_name.strip():
            level_name = level_name.strip()
            output_data = { "name": level_name, "blocks": [{"pos": list(pos), "color": cid} for pos, cid in sorted(current_voxels.items())] }
            levels_dir = "./levels"
            if not os.path.exists(levels_dir):
                try: os.makedirs(levels_dir)
                except OSError as e: QMessageBox.critical(self, "儲存失敗", f"無法建立 levels 資料夾：\n{e}"); return
            i = 1
            while True:
                filename = f"custom_level_{i}.json"; filepath = os.path.join(levels_dir, filename)
                if not os.path.exists(filepath): break
                i += 1
            try:
                with open(filepath, "w", encoding="utf-8") as f: json.dump(output_data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "成功", f"關卡 '{level_name}' 已儲存至:\n{filepath}")
                self._load_ui_elements()
            except Exception as e: QMessageBox.critical(self, "儲存失敗", f"無法寫入檔案：\n{e}")
        elif ok: QMessageBox.warning(self, "儲存失敗", "關卡名稱不能為空！")

    def go_to_next_level(self):
        current_index=self.level_selector.currentIndex();
        if current_index+1<self.level_selector.count(): self.level_selector.setCurrentIndex(current_index+1)
        else: self.status_label.setText("🏆 <b>恭喜！您已完成所有關卡！</b>");self.next_level_button.setText("🎉");self.next_level_button.setEnabled(False)

    def change_level(self,index):
        if index<0 or not self.levels:return
        self.next_level_button.hide();self.next_level_button.setText("➡️ 前進下一關");self.next_level_button.setEnabled(True);self.current_level=self.levels[index];level_id=self.current_level.get("id","");level_progress=self.progress_data.get(level_id,{})
        if level_progress.get("completed"):best_code=level_progress.get("best_code","");best_score=level_progress.get("best_score",0);self.editor.setPlainText(best_code);self.score_label.setText(f"最高分: {best_score}")
        else:
            example_path=os.path.join("./levels/examples",f"{level_id}.py");default_code="# 在此編寫您的程式碼\nreturn 0"
            if os.path.exists(example_path):
                try:
                    with open(example_path,"r",encoding="utf-8")as f:self.editor.setPlainText(f.read())
                except Exception as e:self.editor.setPlainText(default_code)
            else:self.editor.setPlainText(default_code)
            self.score_label.setText("分數: 0")
        self.status_label.setText(f"🔹 已切換關卡: <b>{self.current_level['name']}</b>");self.status_label.setStyleSheet("color: #88C0D0;");self.update_target_preview(self.current_level['path']);self.update_scene();self.target_widget.set_camera_angles(self.engine_widget.angle_x,self.engine_widget.angle_y,self.engine_widget.distance)

    def update_scene(self):
        code=self.editor.toPlainText();wrapped=wrap_code(code);local_vars={}
        try:
            exec(wrapped,{},local_vars);rule_func=local_vars["rule"]
            try:rule_func(0,0,0)
            except Exception as e:raise e
            self.engine_widget.set_rule_func(rule_func);self.check_completion()
        except Exception as e:
            self.status_label.setText(f"❌ <b>錯誤:</b> {e}");self.status_label.setStyleSheet("color: #BF616A;");level_id=self.current_level.get("id","");best_score=self.progress_data.get(level_id,{}).get("best_score",0);score_text=f"最高分: {best_score}"if best_score>0 else"分數: 0";self.score_label.setText(score_text);self.next_level_button.hide();self.engine_widget.set_rule_func(lambda x,y,z:0)

    def update_target_preview(self,level_path):
        try:
            with open(level_path,"r",encoding="utf-8")as f:data=json.load(f)
            self.target_voxels={tuple(b["pos"]):b["color"]for b in data["blocks"]};self.target_widget.set_rule_func(lambda x,y,z:self.target_voxels.get((x,y,z),0))
        except Exception as e:print(f"錯誤：更新目標預覽失敗: {e}")

    def check_completion(self):
        user_voxels=self.engine_widget.voxels
        if user_voxels==self.target_voxels:
            self.engine_widget.trigger_completion_animation();code=self.editor.toPlainText().strip();score=max(0,1000-len(code)*2);level_id=self.current_level.get("id","");current_best_score=self.progress_data.get(level_id,{}).get("best_score",0)
            if score>current_best_score:
                self.progress_data[level_id]={"completed":True,"best_score":score,"best_code":code};self.save_progress();current_idx=self.level_selector.currentIndex();self.level_selector.setItemText(current_idx,f"✅ {self.current_level['name']}");self.status_label.setText("🎉 <b>新高分！</b>")
            else:self.status_label.setText("🎉 <b>關卡完成！</b>")
            self.score_label.setText(f"🏆 {score}");self.status_label.setStyleSheet("color: #EBCB8B; font-weight: bold;");self.next_level_button.show()
        else:
            level_id=self.current_level.get("id","");best_score=self.progress_data.get(level_id,{}).get("best_score",0);score_text=f"最高分: {best_score}"if best_score>0 else"分數: 0";self.score_label.setText(score_text);self.status_label.setText("✅ <b>渲染成功</b> - 請繼續嘗試");self.status_label.setStyleSheet("color: #A3BE8C;");self.next_level_button.hide()


if __name__=="__main__":
    app=QApplication(sys.argv);app.setStyleSheet(STYLESHEET);window=GameWindow();window.show();sys.exit(app.exec_())
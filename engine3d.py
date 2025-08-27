# engine3d.py
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from OpenGL.GL import *
from OpenGL.GLU import *
import OpenGL.GLUT as glut
import numpy as np
import math
import sys
import random

try: glut.glutInit(sys.argv)
except Exception as e: print(f"警告：GLUT 初始化失敗: {e}")

GRID_SIZE = 7
CELL_SIZE = 1.0
HALF = GRID_SIZE // 2
COLORS = {
    1: (1.0, 0.2, 0.2), 2: (1.0, 0.6, 0.0), 3: (1.0, 1.0, 0.0),
    4: (0.1, 1.0, 0.1), 5: (0.0, 1.0, 1.0), 6: (0.3, 0.5, 1.0),
    7: (1.0, 0.2, 1.0), 8: (0.95, 0.95, 0.95)
}

hs = CELL_SIZE / 2.0
CUBE_VERTICES = np.array([-hs,-hs,hs, hs,-hs,hs, hs,hs,hs, -hs,hs,hs, -hs,-hs,-hs, -hs,hs,-hs, hs,hs,-hs, hs,-hs,-hs, hs,-hs,-hs, hs,hs,-hs, hs,hs,hs, hs,-hs,hs, -hs,-hs,hs, -hs,hs,hs, -hs,hs,-hs, -hs,-hs,-hs, -hs,hs,hs, hs,hs,hs, hs,hs,-hs, -hs,hs,-hs, -hs,-hs,-hs, hs,-hs,-hs, hs,-hs,hs, -hs,-hs,hs], dtype=np.float32)
CUBE_NORMALS = np.array([0,0,1,0,0,1,0,0,1,0,0,1, 0,0,-1,0,0,-1,0,0,-1,0,0,-1, 1,0,0,1,0,0,1,0,0,1,0,0, -1,0,0,-1,0,0,-1,0,0,-1,0,0, 0,1,0,0,1,0,0,1,0,0,1,0, 0,-1,0,0,-1,0,0,-1,0,0,-1,0], dtype=np.float32)


class VoxelGLWidget(QOpenGLWidget):
    cameraChanged = pyqtSignal(float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle_x, self.angle_y, self.distance = 25.0, -30.0, 20.0
        self.last_mouse, self.quadric = None, None
        self.rule_func = lambda x, y, z: 0
        self.voxels = {}
        self.sorted_voxel_keys = []
        self.vbo_id = None
        self.vertex_count = 0
        self.visible_vertex_count = 0
        self.gl_initialized = False
        self.tick = 0
        self.animation_mode = 'build'
        self.particles = []
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_tick)
        self.anim_timer.start(30)
        self.slicing_config = {}

    def set_slicing_config(self, config):
        self.slicing_config = config
        self.update()

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST);glEnable(GL_CULL_FACE);glCullFace(GL_BACK);glEnable(GL_COLOR_MATERIAL);glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE);glEnable(GL_LIGHTING);glEnable(GL_LIGHT0);glLightfv(GL_LIGHT0, GL_POSITION, (1.0, 1.0, 1.0, 0.0));glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0));glLightfv(GL_LIGHT0, GL_AMBIENT, (0.4, 0.4, 0.4, 1.0));glClearColor(0.1, 0.12, 0.15, 1.0);self.quadric = gluNewQuadric();self.vbo_id = glGenBuffers(1);self.gl_initialized = True;self._update_vbo()

    def _update_voxel_cache(self):
        self.voxels.clear()
        coords = [(x,y,z) for z in range(-HALF,HALF+1) for y in range(-HALF,HALF+1) for x in range(-HALF,HALF+1)]
        for x, y, z in coords:
            try:
                color_id = self.rule_func(x, y, z)
                if color_id in COLORS: self.voxels[(x, y, z)] = color_id
            except Exception: continue
        self.sorted_voxel_keys = sorted(self.voxels.keys(), key=lambda k: abs(k[0]) + abs(k[1]) + abs(k[2]))

    def _update_vbo(self):
        if not self.voxels or not self.gl_initialized: self.vertex_count = 0; return
        num_voxels = len(self.sorted_voxel_keys)
        vbo_data = np.zeros(num_voxels * 24 * 9, dtype=np.float32)
        spacing = 1.0
        offset = 0
        for i, key in enumerate(self.sorted_voxel_keys):
            color_id = self.voxels[key]
            x, y, z = key
            pos_offset = np.array([x, y, z]) * spacing
            vertices = CUBE_VERTICES.reshape(-1, 3) + pos_offset
            color_arr = np.tile(COLORS[color_id], (24, 1))
            normals = CUBE_NORMALS.reshape(-1, 3)
            chunk = np.hstack([vertices, normals, color_arr]).flatten()
            vbo_data[offset : offset + chunk.size] = chunk
            offset += chunk.size
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_id)
        glBufferData(GL_ARRAY_BUFFER, vbo_data.nbytes, vbo_data, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.vertex_count = num_voxels * 24

    def set_rule_func(self, func):
        self.animation_mode = 'build';self.particles.clear();self.rule_func = func;self._update_voxel_cache();self.tick = 0
        if self.gl_initialized: self._update_vbo()
        self.update()

    def trigger_completion_animation(self):
        self.visible_vertex_count = self.vertex_count;self.animation_mode = 'celebrate';self.particles.clear()
        center = np.mean([list(pos) for pos in self.voxels.keys()], axis=0) if self.voxels else [0,0,0]
        for _ in range(200):
            vel = [random.uniform(-1.5, 1.5), random.uniform(2.0, 4.0), random.uniform(-1.5, 1.5)]
            color_id = random.choice(list(COLORS.keys()));self.particles.append({'pos': list(center), 'vel': vel, 'life': 100, 'color': COLORS[color_id]})

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);glMatrixMode(GL_MODELVIEW);glLoadIdentity();gluLookAt(0, 0, self.distance, 0, 0, 0, 0, 1, 0);glRotatef(self.angle_x, 1, 0, 0);glRotatef(self.angle_y, 0, 1, 0)
        self._draw_gizmo_frame_and_axes()
        
        if self.vertex_count > 0:
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_id)
            stride = (3 + 3 + 3) * 4
            
            def setup_draw(mode, line_width=1.5):
                if mode == 'line':
                    glDisable(GL_LIGHTING);glDisableClientState(GL_COLOR_ARRAY)
                    glColor3f(0.0, 0.0, 0.0);glLineWidth(line_width);glEnable(GL_POLYGON_OFFSET_LINE)
                    glPolygonOffset(-1.0, -1.0);glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                    glVertexPointer(3, GL_FLOAT, stride, None)
                elif mode == 'fill':
                    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);glDisable(GL_POLYGON_OFFSET_LINE)
                    glEnable(GL_LIGHTING);glEnableClientState(GL_COLOR_ARRAY);glEnableClientState(GL_NORMAL_ARRAY)
                    glVertexPointer(3, GL_FLOAT, stride, None)
                    glNormalPointer(GL_FLOAT, stride, ctypes.c_void_p(3 * 4))
                    glColorPointer(3, GL_FLOAT, stride, ctypes.c_void_p(6 * 4))

            def draw_pass(mode):
                setup_draw(mode)
                num_drawn_voxels = 0
                
                # 【核心修正】檢查是否處於建造動畫模式
                is_in_build_animation = self.animation_mode == 'build'

                for i, key in enumerate(self.sorted_voxel_keys):
                    # 【核心修正】只有在建造動畫模式下，才檢查 tick
                    if is_in_build_animation and (abs(key[0]) + abs(key[1]) + abs(key[2])) > self.tick:
                        break
                    
                    num_drawn_voxels += 1
                    
                    x, y, z = key
                    if self.slicing_config.get('x', {}).get('enabled') and x > self.slicing_config['x']['value']: continue
                    if self.slicing_config.get('y', {}).get('enabled') and y > self.slicing_config['y']['value']: continue
                    if self.slicing_config.get('z', {}).get('enabled') and z > self.slicing_config['z']['value']: continue
                    
                    glDrawArrays(GL_QUADS, i * 24, 24)
                
                if is_in_build_animation:
                    self.visible_vertex_count = num_drawn_voxels * 24

            glEnableClientState(GL_VERTEX_ARRAY)
            draw_pass('line')
            draw_pass('fill')
            glBindBuffer(GL_ARRAY_BUFFER, 0);glDisableClientState(GL_COLOR_ARRAY);glDisableClientState(GL_NORMAL_ARRAY);glDisableClientState(GL_VERTEX_ARRAY)

        if self.animation_mode == 'celebrate':
            glDisable(GL_LIGHTING);s = 0.2 / 2.0
            for p in self.particles:
                glColor3fv(p['color']);glPushMatrix();glTranslatef(p['pos'][0], p['pos'][1], p['pos'][2])
                glBegin(GL_QUADS);glVertex3f(-s, -s, s); glVertex3f(s, -s, s); glVertex3f(s, s, s); glVertex3f(-s, s, s);glVertex3f(-s, -s, -s); glVertex3f(-s, s, -s); glVertex3f(s, s, -s); glVertex3f(s, -s, -s);glVertex3f(-s, -s, s); glVertex3f(-s, s, s); glVertex3f(-s, s, -s); glVertex3f(-s, -s, -s);glVertex3f(s, -s, -s); glVertex3f(s, s, -s); glVertex3f(s, s, s); glVertex3f(s, -s, s);glVertex3f(-s, s, s); glVertex3f(s, s, s); glVertex3f(s, s, -s); glVertex3f(-s, s, -s);glVertex3f(-s, -s, s); glVertex3f(-s, -s, -s); glVertex3f(s, -s, -s); glVertex3f(s, -s, s);glEnd()
                glPopMatrix()
            glEnable(GL_LIGHTING)
        self._draw_gizmo_hud_labels()

    def _on_tick(self):
        if self.animation_mode == 'build':
            max_tick = (HALF * 3) + 3
            if self.tick < max_tick: self.tick += 1
        elif self.animation_mode == 'celebrate':
            for i in range(len(self.particles) - 1, -1, -1):
                p = self.particles[i];p['pos'][0] += p['vel'][0] * 0.1;p['pos'][1] += p['vel'][1] * 0.1;p['pos'][2] += p['vel'][2] * 0.1;p['vel'][1] -= 0.1;p['life'] -= 1
                if p['life'] <= 0: self.particles.pop(i)
        self.update()

    def _draw_gizmo_hud_labels(self):
        glDisable(GL_LIGHTING); s_num = (HALF + 1.2) * (CELL_SIZE + 0.18); label_offset = (HALF + 2.2) * (CELL_SIZE + 0.18); spacing = 1.0; rad_ax = math.radians(self.angle_x); rad_ay = math.radians(self.angle_y); cam_x = -math.sin(rad_ay)*math.cos(rad_ax); cam_y = math.sin(rad_ax); cam_z = math.cos(rad_ay)*math.cos(rad_ax); front_x_sign = 1 if cam_x >= 0 else -1; front_y_sign = 1 if cam_y >= 0 else -1; front_z_sign = 1 if cam_z >= 0 else -1; abs_cam_vals = {'x': abs(cam_x), 'y': abs(cam_y), 'z': abs(cam_z)}; axis_to_hide = max(abs_cam_vals, key=abs_cam_vals.get)
        def draw_text(x, y, z, text): glRasterPos3f(x, y, z); [glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_18, ord(char)) for char in text]
        if axis_to_hide != 'y': glColor3f(0.4, 1.0, 0.4); [draw_text(s_num*front_x_sign, i*spacing-0.3, s_num*front_z_sign, str(i)) for i in range(-HALF, HALF + 1) if i != 0]; draw_text(s_num*front_x_sign, label_offset, s_num*front_z_sign, "Y")
        if axis_to_hide != 'x': glColor3f(1.0, 0.4, 0.4); [draw_text(i*spacing-0.3, s_num*front_y_sign, s_num*front_z_sign, str(i)) for i in range(-HALF, HALF + 1) if i != 0]; draw_text(label_offset, s_num*front_y_sign, s_num*front_z_sign, "X")
        if axis_to_hide != 'z': glColor3f(0.4, 0.7, 1.0); [draw_text(s_num*front_x_sign, s_num*front_y_sign, i*spacing-0.3, str(i)) for i in range(-HALF, HALF + 1) if i != 0]; draw_text(s_num*front_x_sign, s_num*front_y_sign, label_offset, "Z")
        glEnable(GL_LIGHTING)
    def _draw_gizmo_frame_and_axes(self):
        glDisable(GL_LIGHTING); s = (HALF + 0.5) * (CELL_SIZE + 0.18); glLineWidth(2.0); glColor4f(0.8, 0.8, 0.8, 0.7); glBegin(GL_LINE_LOOP); glVertex3f(-s,-s,s); glVertex3f(s,-s,s); glVertex3f(s,s,s); glVertex3f(-s,s,s); glEnd(); glBegin(GL_LINE_LOOP); glVertex3f(-s,-s,-s); glVertex3f(s,-s,-s); glVertex3f(s,s,-s); glVertex3f(-s,s,-s); glEnd(); glBegin(GL_LINES); glVertex3f(-s,-s,s); glVertex3f(-s,-s,-s); glVertex3f(s,-s,s); glVertex3f(s,-s,-s); glVertex3f(s,s,s); glVertex3f(s,s,-s); glVertex3f(-s,s,s); glVertex3f(-s,s,-s); glEnd(); s_axis = (HALF + 1.0) * (CELL_SIZE + 0.18); arrow_radius, arrow_height = 0.25, 0.8; glLineWidth(3.5); glColor3f(1.0, 0.2, 0.2); glBegin(GL_LINES); glVertex3f(-s_axis,0,0); glVertex3f(s_axis,0,0); glEnd(); glPushMatrix(); glTranslatef(s_axis,0,0); glRotatef(90,0,1,0); gluCylinder(self.quadric,arrow_radius,0,arrow_height,15,1); glPopMatrix(); glColor3f(0.2, 1.0, 0.2); glBegin(GL_LINES); glVertex3f(0,-s_axis,0); glVertex3f(0,s_axis,0); glEnd(); glPushMatrix(); glTranslatef(0,s_axis,0); glRotatef(-90,1,0,0); gluCylinder(self.quadric,arrow_radius,0,arrow_height,15,1); glPopMatrix(); glColor3f(0.2, 0.6, 1.0); glBegin(GL_LINES); glVertex3f(0,0,-s_axis); glVertex3f(0,0,s_axis); glEnd(); glPushMatrix(); glTranslatef(0,0,s_axis); gluCylinder(self.quadric,arrow_radius,0,arrow_height,15,1); glPopMatrix(); glEnable(GL_LIGHTING)
    def resizeGL(self, w, h): glViewport(0, 0, w, max(1, h));glMatrixMode(GL_PROJECTION);glLoadIdentity();gluPerspective(45.0, w / max(1.0, float(h)), 0.1, 1000.0);glMatrixMode(GL_MODELVIEW)
    def mousePressEvent(self, e): self.last_mouse = (e.x(), e.y())
    def mouseMoveEvent(self, e):
        if self.last_mouse is None or not(e.buttons() & Qt.LeftButton): return
        dx = e.x()-self.last_mouse[0]; dy = e.y()-self.last_mouse[1]; self.angle_y+=dx*0.4; self.angle_x+=dy*0.4; self.angle_x = max(-89, min(89, self.angle_x)); self.last_mouse = (e.x(), e.y()); self.update_and_emit_camera()
    def wheelEvent(self, e): delta = e.angleDelta().y() / 120.0; self.distance = max(5.0, min(60.0, self.distance-delta*1.5)); self.update_and_emit_camera()
    def update_and_emit_camera(self): self.update(); self.cameraChanged.emit(self.angle_x, self.angle_y, self.distance)
    def set_camera_angles(self, ax, ay, dist): self.angle_x=ax; self.angle_y=ay; self.distance=dist; self.update()


class TargetPreviewWidget(VoxelGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 【核心修正】為預覽圖設定一個獨立的模式，以避免觸發動畫
        self.animation_mode = 'idle' 

    def set_rule_func(self, func):
        # 【核心修正】此函式不能呼叫父類別的 set_rule_func，以免 animation_mode 被重設
        self.rule_func = func
        self._update_voxel_cache()
        if self.gl_initialized:
            self._update_vbo()
        self.visible_vertex_count = self.vertex_count
        self.update()

    def _on_tick(self):
        pass

    def trigger_completion_animation(self):
        pass

    def mousePressEvent(self, e): pass
    def mouseMoveEvent(self, e): pass
    def wheelEvent(self, e): pass
# editor.py
import re
from PyQt5.QtWidgets import QPlainTextEdit, QWidget, QTextEdit, QCompleter, QTableView, QStyle
from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal, QSortFilterProxyModel
from PyQt5.QtGui import QColor, QPainter, QTextFormat, QFont, QStandardItemModel, QStandardItem, QTextCursor

from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat
from pygments import highlight
from pygments.formatter import Formatter
from pygments.lexers import PythonLexer
from pygments.token import Token
import pygments.styles

# (CompleterProxyModel 和 Pygments/Highlighter 類別與上一版相同，保持不變)
class CompleterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        if not self.filterRegExp().pattern(): return True
        index = self.sourceModel().index(source_row, self.filterKeyColumn(), source_parent)
        text = self.sourceModel().data(index)
        return text.lower().startswith(self.filterRegExp().pattern().lower())

class PygmentsFormatter(Formatter):
    def __init__(self): super().__init__(); self.data = []
    def format(self, tokensource, outfile): self.data = []; [self.data.append(t) for t in tokensource]
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, style_name='nord'):
        super().__init__(parent); self.formatter = PygmentsFormatter(); self.lexer = PythonLexer(); self.styles = {}
        pyg_style = pygments.styles.get_style_by_name(style_name)
        for ttype, style in pyg_style:
            color = style.get('color')
            if color:
                fmt = QTextCharFormat(); fmt.setForeground(QColor(f"#{color}"))
                if style.get('bold'): fmt.setFontWeight(QFont.Bold)
                if style.get('italic'): fmt.setFontItalic(True)
                self.styles[ttype] = fmt
    def highlightBlock(self, text):
        highlight(text, self.lexer, self.formatter); pos = 0
        for ttype, value in self.formatter.data:
            length = len(value); current_type = ttype
            while current_type not in self.styles and current_type.parent: current_type = current_type.parent
            if current_type in self.styles: self.setFormat(pos, length, self.styles[current_type])
            pos += length

class LineNumberArea(QWidget):
    def __init__(self, editor): super().__init__(editor); self.codeEditor = editor
    def sizeHint(self): return QSize(self.codeEditor.lineNumberAreaWidth(), 0)
    def paintEvent(self, event): self.codeEditor.lineNumberAreaPaintEvent(event)

# --- 主編輯器 ---
class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 12)); self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.lineNumberArea = LineNumberArea(self); self.highlighter = PythonHighlighter(self.document(), style_name='nord')
        self.setup_completer()
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0); self.highlightCurrentLine()

    def setup_completer(self):
        self.completer = QCompleter(self); self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion); self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionColumn(0)
        self.completer_view = QTableView(); self.completer_view.setObjectName("completerPopup")
        font = QFont("Consolas", 11); self.completer_view.setFont(font)
        self.completer_view.verticalHeader().setDefaultSectionSize(24)
        self.completer.setPopup(self.completer_view)
        style = self.style()
        self.icons = {
            'keyword': style.standardIcon(QStyle.SP_DialogApplyButton),
            'built-in': style.standardIcon(QStyle.SP_ToolBarHorizontalExtensionButton),
            'math': style.standardIcon(QStyle.SP_CommandLink),
            'variable': style.standardIcon(QStyle.SP_FileDialogDetailedView),
        }
        self.completion_list = {
            'keywords': ['return', 'if', 'else', 'elif', 'for', 'in', 'while', 'def', 'class', 'and', 'or', 'not', 'True', 'False', 'None'],
            'built-in': ['abs', 'min', 'max', 'pow', 'round', 'int', 'float', 'str', 'len', 'range'],
            'math': ['math.sin', 'math.cos', 'math.tan', 'math.sqrt', 'math.pi', 'math.e'],
            'variables': ['x', 'y', 'z']
        }
        self.completer.activated[str].connect(self.insertCompletion)

    def update_completer_model(self):
        text = self.toPlainText(); user_vars = set(re.findall(r'\b([a-zA-Z_]\w*)\s*=', text))
        model = QStandardItemModel()
        all_words = {}
        for category, words in self.completion_list.items():
            for word in words: all_words[word] = category
        for var in user_vars: all_words[var] = 'variable'
        for word, category in sorted(all_words.items()):
            item_name = QStandardItem(word)
            if category in self.icons: item_name.setIcon(self.icons[category])
            item_hint = QStandardItem(f"{category}")
            item_hint.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            model.appendRow([item_name, item_hint])
        proxy_model = CompleterProxyModel(self)
        proxy_model.setSourceModel(model)
        proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy_model.setFilterKeyColumn(0)
        self.completer.setModel(proxy_model)
        self.completer_view.resizeColumnsToContents()
        self.completer_view.setColumnWidth(0, 180); self.completer_view.setColumnWidth(1, 100)
        
    def insertCompletion(self, completion):
        tc = self.textCursor(); prefix = self.completer.completionPrefix()
        extra = len(completion) - len(prefix)
        tc.movePosition(QTextCursor.Left); tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def textUnderCursor(self):
        tc = self.textCursor(); tc.select(tc.WordUnderCursor); return tc.selectedText()

    def keyPressEvent(self, event):
        """【核心修改】重寫鍵盤事件，實現 Tab 補全、區塊縮排等高級功能"""
        popup = self.completer.popup()
        key = event.key()

        # --- 處理 Tab 和 Shift+Tab ---
        if key == Qt.Key_Tab or key == Qt.Key_Backtab:
            # 情況一：提示框可見，Tab 用於補全
            if popup.isVisible():
                event.ignore() # 將事件交給 Completer 處理
                return

            # 情況二：選取了文字，Tab 用於區塊縮排
            cursor = self.textCursor()
            if cursor.hasSelection():
                start_pos = cursor.selectionStart()
                end_pos = cursor.selectionEnd()
                
                # 獲取選區的起始和結束行號
                cursor.setPosition(start_pos)
                start_block = cursor.blockNumber()
                cursor.setPosition(end_pos)
                # 如果選區的結尾剛好是一行的開頭，則不包含該行
                if cursor.atBlockStart() and end_pos != start_pos:
                    cursor.movePosition(QTextCursor.Left)
                    end_pos = cursor.position()
                end_block = self.document().findBlock(end_pos).blockNumber()

                cursor.beginEditBlock()
                # 迴圈處理每一行
                for block_num in range(start_block, end_block + 1):
                    block_cursor = QTextCursor(self.document().findBlockByNumber(block_num))
                    block_cursor.movePosition(QTextCursor.StartOfLine)
                    
                    if key == Qt.Key_Tab: # 增加縮排
                        block_cursor.insertText("    ")
                    else: # 減少縮排 (Shift+Tab)
                        text = block_cursor.block().text()
                        if text.startswith("    "):
                            block_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 4)
                            block_cursor.removeSelectedText()
                cursor.endEditBlock()
                return

            # 情況三：普通情況，插入4個空格
            else:
                self.insertPlainText("    ")
                return
        
        # --- 處理 Enter ---
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if popup.isVisible():
                popup.hide() # 如果提示框可見，先隱藏它

            cursor = self.textCursor()
            line_text = cursor.block().text()
            indentation = re.match(r'^\s*', line_text).group(0)
            
            self.insertPlainText("\n" + indentation)
            
            if line_text.strip().endswith(":"):
                self.insertPlainText("    ")
            return

        # --- 處理其他按鍵（正常輸入文字）---
        super().keyPressEvent(event)

        # --- 處理完輸入後，判斷是否顯示提示框 ---
        prefix = self.textUnderCursor()
        if not event.text() or not event.text()[-1].isalnum() or len(prefix) < 1:
            popup.hide()
            return
        
        self.update_completer_model()
        self.completer.setCompletionPrefix(prefix)
        popup.setCurrentIndex(self.completer.model().index(0, 0))
        cr = self.cursorRect()
        cr.setWidth(popup.sizeHintForColumn(0) + popup.sizeHintForColumn(1) + 20)
        self.completer.complete(cr)
        
    # (行號和高亮行函式不變)
    def lineNumberAreaWidth(self):
        digits=1; count=max(1,self.blockCount());
        while count>=10: count/=10; digits+=1
        return 10+self.fontMetrics().width('9')*digits
    def updateLineNumberAreaWidth(self,_): self.setViewportMargins(self.lineNumberAreaWidth(),0,0,0)
    def updateLineNumberArea(self,rect,dy):
        if dy: self.lineNumberArea.scroll(0,dy)
        else: self.lineNumberArea.update(0,rect.y(),self.lineNumberArea.width(),rect.height())
        if rect.contains(self.viewport().rect()):self.updateLineNumberAreaWidth(0)
    def resizeEvent(self,event):
        super().resizeEvent(event); cr=self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(),cr.top(),self.lineNumberAreaWidth(),cr.height()))
    def lineNumberAreaPaintEvent(self,event):
        painter=QPainter(self.lineNumberArea); painter.fillRect(event.rect(),QColor("#3B4252"))
        block=self.firstVisibleBlock(); blockNumber=block.blockNumber()
        top=int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom=top+int(self.blockBoundingRect(block).height())
        while block.isValid() and top<=event.rect().bottom():
            if block.isVisible() and bottom>=event.rect().top():
                number=str(blockNumber+1)
                painter.setPen(QColor("#6D89B3"))
                painter.drawText(0,top,self.lineNumberArea.width()-5,self.fontMetrics().height(),Qt.AlignRight,number)
            block=block.next(); top=bottom; bottom=top+int(self.blockBoundingRect(block).height()); blockNumber+=1
    def highlightCurrentLine(self):
        extraSelections=[];
        if not self.isReadOnly():
            selection=QTextEdit.ExtraSelection(); lineColor=QColor("#434C5E")
            selection.format.setBackground(lineColor); selection.format.setProperty(QTextFormat.FullWidthSelection,True)
            selection.cursor=self.textCursor(); selection.cursor.clearSelection(); extraSelections.append(selection)
        self.setExtraSelections(extraSelections)
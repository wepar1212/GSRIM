"""Bilingual native Qt desktop application. No HTTP server or web engine."""
from __future__ import annotations

import copy
from datetime import datetime
import json
import os
from pathlib import Path
import sys

import numpy as np
from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTimer, Qt, QTranslator
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from .compounds import COMPOUNDS, ELEMENTS, layer_from_compound, species_from_element
from .element_defaults import binding_defaults, binding_hint
from .native_plot import ScientificPlot
from .output import PLOT_NAMES, export_bundle, fmt, plot_from_snapshot, reference_plots
from .project import DEFAULT, validate
from .simulation import AUTOSAVE_PATH, ENGINE_REVISION, ROOT, Simulation


STYLE = """
QMainWindow {background:#cadce7;}
QWidget {font-family:'Microsoft YaHei UI';font-size:12px;color:#142e49;}
QWidget#header {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e9f2f7,stop:1 #b8d3e5);border:1px solid #8eaabb;}
QLabel#brand {font-family:Georgia;font-size:34px;font-weight:700;color:#133b9a;}
QLabel#subtitle {font-size:13px;color:#335270;}
QGroupBox {font-weight:600;font-size:14px;border:1px solid #9bb1c1;background:#e5eef4;margin-top:13px;padding:12px 9px 8px;}
QGroupBox::title {subcontrol-origin:margin;left:12px;padding:0 6px;color:#183b87;}
QLineEdit,QComboBox {min-height:27px;background:#fffef2;border:1px solid #9aaebc;border-radius:2px;padding:0 6px;selection-background-color:#346ca8;}
QLineEdit:focus,QComboBox:focus {border:1px solid #1769b0;}
QLineEdit:disabled,QComboBox:disabled {background:#e4e7e9;color:#7f8b93;}
QPushButton {min-height:27px;padding:3px 11px;background:#f5f7f9;border:1px solid #92a5b5;border-radius:2px;}
QPushButton:hover {background:#dcecfb;border-color:#3975a6;}
QPushButton:pressed {background:#c4dbec;}
QPushButton:disabled {color:#8e9ba4;background:#e0e6eb;border-color:#bdc9d1;}
QPushButton#start {background:#167c45;color:white;font-weight:700;border-color:#086031;min-height:39px;font-size:15px;}
QPushButton#start:hover {background:#209253;}
QPushButton#resume {background:#fff3b7;color:#5b4808;}
QPushButton#stop {color:#a32525;}
QPushButton#start:disabled,QPushButton#resume:disabled,QPushButton#stop:disabled {color:#8e9ba4;background:#e0e6eb;border-color:#bdc9d1;}
QTableWidget {background:#fffef4;alternate-background-color:#f1f6f8;border:1px solid #9aaebc;gridline-color:#c4d1d9;selection-background-color:#c8deed;selection-color:#102c4a;}
QTableWidget::item {padding:4px;}
QHeaderView::section {background:#d7e6ee;padding:6px 4px;border:0;border-right:1px solid #afc2ce;border-bottom:1px solid #a7bbc7;color:#1d4265;font-weight:600;}
QTabWidget::pane {border:1px solid #91aabd;background:#d6e4ed;}
QTabBar::tab {background:#bccfdd;padding:9px 22px;border:1px solid #91aabd;margin-right:2px;font-weight:600;}
QTabBar::tab:selected {background:#edf4f8;color:#153d8b;border-top:3px solid #a73337;padding-top:7px;}
QPlainTextEdit {background:#f8fbfd;border:1px solid #b1c1cd;padding:8px;selection-background-color:#bfd8ec;}
QListWidget {background:#eff5f9;border:1px solid #a6bdcc;outline:0;}
QListWidget::item {padding:12px 8px;border-bottom:1px solid #d1dee7;}
QListWidget::item:selected {background:#c9dfef;color:#173d89;border-left:3px solid #b22e37;}
QProgressBar {background:#edf3f7;border:1px solid #9eb5c5;min-height:21px;text-align:center;}
QProgressBar::chunk {background:#2e7ca8;}
QCheckBox {spacing:6px;font-weight:400;}
QToolTip {background:#fffde9;color:#263b50;border:1px solid #a0b1bf;}
QStatusBar {background:#e5eef4;}
"""


def configure_fonts():
    # Windows' offscreen platform does not enumerate installed fonts itself.
    # Loading system fonts also makes automated chart exports readable.
    if not QFontDatabase.families() and os.name=="nt":
        fonts=Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts"
        for name in ("msyh.ttc","msyhbd.ttc","times.ttf","timesbd.ttf","georgia.ttf","georgiab.ttf"):
            if (fonts/name).is_file():QFontDatabase.addApplicationFont(str(fonts/name))


def reference_project():
    """Input transcribed from the user's H/TDATA.txt; no SRIM execution."""
    p=copy.deepcopy(DEFAULT)
    p["name"]="H 40 keV → Ga₂O₃"
    p["ion"]={"symbol":"H","z":1,"mass_u":1.008,"energy_kev":40.,"angle_deg":0.}
    p["layers"]=[{"name":"Ga2O3","thickness_a":6000.,"density_g_cm3":5.88,"species":[
        {"symbol":"O","z":8,"mass_u":15.999,"amount":3.,"displacement_ev":28.,"lattice_ev":3.,"surface_ev":2.},
        {"symbol":"Ga","z":31,"mass_u":69.723,"amount":2.,"displacement_ev":25.,"lattice_ev":3.,"surface_ev":2.82}]}]
    p["run"].update(ions=10000,batch_size=512,bins=100)
    return p


class MainWindow(QMainWindow):
    def __init__(self, *, settings=None):
        super().__init__()
        configure_fonts()
        self.settings=settings or QSettings("GSRIM","NativeDesktop")
        self.language=str(self.settings.value("language","zh"))
        if self.language not in ("zh","en"):self.language="zh"
        self.project=copy.deepcopy(DEFAULT)
        self.simulation=None
        self.state=None
        self.reference_folder=None
        self.references={}
        self.selected_layer=0
        self.bindings=[]
        self.combo_bindings=[]
        self.logs=[]
        self._loading=False
        self._last_token=None
        self._close_pending=False
        self._notified_error=None
        self.translator=QTranslator(self)
        self.setWindowTitle("GSRIM")
        self.resize(1460,970)
        self.setMinimumSize(1120,790)
        self.setStyleSheet(STYLE)
        icon=QPixmap(48,48);icon.fill(QColor("#163d89"))
        painter=QPainter(icon);painter.setPen(Qt.GlobalColor.white);painter.setFont(QFont("Georgia",20,QFont.Weight.Bold))
        painter.drawText(icon.rect(),Qt.AlignmentFlag.AlignCenter,"G");painter.end();self.setWindowIcon(QIcon(icon))
        self.build_ui()
        self.fill_project(self.project)
        self.retranslate()
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(400)
        self.log("原生界面已就绪", "Native interface ready")
        self.poll()

    def tr(self, zh, en):
        return zh if self.language=="zh" else en

    def bind(self, widget, zh, en, setter="setText"):
        self.bindings.append((widget,zh,en,setter))
        getattr(widget,setter)(self.tr(zh,en))
        return widget

    def label(self, zh, en):
        return self.bind(QLabel(),zh,en)

    def button(self, zh, en, callback, name=None):
        button=self.bind(QPushButton(),zh,en)
        if name:button.setObjectName(name)
        button.clicked.connect(callback)
        return button

    def group(self, zh, en):
        return self.bind(QGroupBox(),zh,en,"setTitle")

    def combo(self, options):
        widget=QComboBox()
        for value,zh,en in options:widget.addItem(self.tr(zh,en),value)
        self.combo_bindings.append((widget,options))
        return widget

    def edit(self, value, width=None):
        widget=QLineEdit(str(value))
        if width:widget.setMaximumWidth(width)
        return widget

    def build_ui(self):
        root=QWidget();layout=QVBoxLayout(root);layout.setContentsMargins(12,10,12,8);layout.setSpacing(8)
        header=QWidget();header.setObjectName("header");bar=QHBoxLayout(header)
        brand=QLabel("GSRIM");brand.setObjectName("brand");bar.addWidget(brand)
        subtitle=self.label("离子输运与反冲级联模拟\n原生桌面控制台", "Ion transport & recoil cascades\nNative desktop console")
        subtitle.setObjectName("subtitle");bar.addWidget(subtitle);bar.addStretch()
        self.open_button=self.button("打开项目", "Open project",self.open_project);bar.addWidget(self.open_button)
        self.save_button=self.button("保存项目", "Save project",self.save_project);bar.addWidget(self.save_button)
        self.load_button=self.button("载入结果 / 断点", "Load result / checkpoint",self.load_result);bar.addWidget(self.load_button)
        bar.addWidget(self.label("语言", "Language"))
        self.language_combo=QComboBox();self.language_combo.addItems(["中文","English"])
        self.language_combo.setCurrentIndex(0 if self.language=="zh" else 1)
        self.language_combo.currentIndexChanged.connect(self.change_language);bar.addWidget(self.language_combo)
        layout.addWidget(header)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        self.build_setup()
        self.build_results()
        footer=QHBoxLayout()
        self.status_label=QLabel();self.status_label.setMinimumWidth(130);footer.addWidget(self.status_label)
        self.progress=QProgressBar();self.progress.setRange(0,1000);footer.addWidget(self.progress,1)
        self.count_label=QLabel("0 / 0");self.count_label.setMinimumWidth(160);footer.addWidget(self.count_label)
        self.elapsed=QLabel("0.0 s");footer.addWidget(self.elapsed)
        self.quick_pause=self.button("暂停", "Pause",self.pause_run)
        self.quick_resume=self.button("继续", "Resume",self.resume_run)
        self.quick_stop=self.button("停止", "Stop",self.cancel_run)
        for button in (self.quick_pause,self.quick_resume,self.quick_stop):footer.addWidget(button)
        layout.addLayout(footer)
        note=self.label("研究模型 · 位移事件不等于稳定缺陷 · 请核对电子阻止来源", "Research model · Creation events are not stable defects · Check stopping sources")
        note.setStyleSheet("color:#526b7b;font-size:11px;");layout.addWidget(note)
        self.setCentralWidget(root)

    def build_setup(self):
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame)
        page=QWidget();self.setup_page=page;main=QVBoxLayout(page);main.setSpacing(9)
        self.ion_group=self.group("离子数据", "ION DATA");grid=QGridLayout(self.ion_group)
        self.name=self.edit(DEFAULT["name"])
        self.mode=self.combo([("cascades","完整反冲级联","Full recoil cascades"),("ions","仅入射离子（快速）","Incident ions only (quick)")])
        grid.addWidget(self.label("计算名称", "Calculation name"),0,0);grid.addWidget(self.name,0,1,1,3)
        grid.addWidget(self.label("计算类型", "Calculation type"),0,4);grid.addWidget(self.mode,0,5,1,3)
        self.ion_symbol=QComboBox();self.ion_symbol.setEditable(True);self.ion_symbol.addItems(list(ELEMENTS))
        self.ion_symbol.setMinimumWidth(76)
        self.ion_symbol.currentTextChanged.connect(self.ion_changed)
        self.ion_z=self.edit(2);self.ion_mass=self.edit(4.0026);self.ion_energy=self.edit(5);self.ion_angle=self.edit(0)
        for col,(zh,en,widget) in enumerate([("元素","Element",self.ion_symbol),("原子序数","Atomic number",self.ion_z),
            ("质量 (u)","Mass (u)",self.ion_mass),("能量 (keV)","Energy (keV)",self.ion_energy),
            ("入射角 (°，相对法线)","Angle (° from normal)",self.ion_angle)]):
            grid.addWidget(self.label(zh,en),1,col+1);grid.addWidget(widget,2,col+1)
        grid.addWidget(self.button("参考工况：H → Ga₂O₃", "Reference setup: H → Ga₂O₃",self.load_reference_setup),2,6,1,2)
        grid.setColumnStretch(7,1);main.addWidget(self.ion_group)
        line=QFrame();line.setFixedHeight(3);line.setStyleSheet("background:#ae363c;");main.addWidget(line)
        self.target_group=self.group("靶材数据", "TARGET DATA");target_layout=QHBoxLayout(self.target_group)
        layers=QWidget();left=QVBoxLayout(layers);left.setContentsMargins(0,0,0,0)
        layerbar=QHBoxLayout();layerbar.addWidget(self.label("靶材分层", "Target layers"));layerbar.addStretch()
        layerbar.addWidget(self.button("添加层", "Add layer",self.add_layer));layerbar.addWidget(self.button("删除层", "Remove layer",self.remove_layer));left.addLayout(layerbar)
        self.layers=QTableWidget(0,4);self.layers.setAlternatingRowColors(True)
        self.layers.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.layers.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.layers.verticalHeader().setVisible(False)
        self.layers.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for c,w in [(1,100),(2,78),(3,98)]:self.layers.setColumnWidth(c,w)
        self.layers.currentCellChanged.connect(self.layer_selected);left.addWidget(self.layers,1)
        self.layer_summary=QLabel();self.layer_summary.setWordWrap(True);left.addWidget(self.layer_summary)
        rightbox=QWidget();right=QVBoxLayout(rightbox);right.setContentsMargins(0,0,0,0)
        elementbar=QHBoxLayout();elementbar.addWidget(self.label("当前层的元素", "Elements in selected layer"));elementbar.addStretch()
        elementbar.addWidget(self.button("添加元素", "Add element",self.add_species));elementbar.addWidget(self.button("删除元素", "Remove element",self.remove_species))
        elementbar.addWidget(self.button("化合物字典", "Compound dictionary",self.choose_compound));right.addLayout(elementbar)
        self.species=QTableWidget(0,8);self.species.setAlternatingRowColors(True);self.species.verticalHeader().setVisible(False)
        self.species.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.species.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.species.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed)
        self.species.setColumnWidth(0,90)
        self.species.itemChanged.connect(self.update_fractions);right.addWidget(self.species,1)
        right.addWidget(self.label("配比按原子数输入；能量单位 eV。悬停查看默认值来源；空白项需按材料填写。", "Use atom ratios; energies in eV. Hover for default sources; blank values require material data."))
        splitter=QSplitter();splitter.addWidget(layers);splitter.addWidget(rightbox);splitter.setSizes([460,850]);target_layout.addWidget(splitter)
        self.target_group.setMinimumHeight(245);main.addWidget(self.target_group,1)
        lower=QHBoxLayout();self.run_group=self.group("特殊参数", "SPECIAL PARAMETERS");form=QGridLayout(self.run_group)
        self.run_fields={}
        params=[("ions", "入射离子数", "Incident histories",256), ("seed","随机种子","Random seed",12345),
                ("batch_size","每批历史数","Batch size",512),("bins","深度分箱数","Depth bins",160),
                ("cutoff_ev","截止能量 (eV)","Cutoff (eV)",3),("max_events","历史事件上限","Max events / history",100000),
                ("impact_scale","碰撞范围系数","Impact scale",1.0)]
        for i,(key,zh,en,value) in enumerate(params):
            row,col=divmod(i,3);widget=self.edit(value);self.run_fields[key]=widget
            form.addWidget(self.label(zh,en),row*2,col);form.addWidget(widget,row*2+1,col)
        self.stopping=self.combo([("iaea","自动数据表（NIST / IAEA）","Automatic tables (NIST / IAEA)"),
            ("biersack-varelas","BV 解析模型","BV analytic model"),("lindhard-scharff","LS 低能模型","LS low-energy model")])
        self.scattering=self.combo([("table","ZBL 散射表","ZBL lookup table"),("quadrature","ZBL 数值求积","ZBL quadrature")])
        form.addWidget(self.label("电子阻止", "Electronic stopping"),4,1);form.addWidget(self.stopping,5,1)
        form.addWidget(self.label("核散射", "Nuclear scattering"),4,2);form.addWidget(self.scattering,5,2)
        lower.addWidget(self.run_group,3)
        self.export_group=self.group("输出文件", "OUTPUT FILES");out=QGridLayout(self.export_group)
        self.output_checks={}
        for i,(filename,zh,en) in enumerate([
            ("RANGE.txt","离子 / 反冲分布","Ion / recoil ranges"),("IONIZ.txt","电离能量","Ionization"),
            ("PHONON.txt","晶格能量","Lattice energy"),("DISPLACEMENTS.txt","位移产生事件","Displacement events"),
            ("E2RECOIL.txt","反冲能量转移","Recoil energy transfer"),("LATERAL.txt","横向分布","Lateral spread"),
            ("BACKSCAT.txt","背散射能谱","Backscatter spectrum"),("TRANSMIT.txt","透射能谱","Transmission spectrum"),
            ("SPUTTER.txt","溅射能谱","Sputter spectrum"),("ION_HISTORY.txt","逐离子记录","Per-ion records")]):
            check=self.bind(QCheckBox(),zh,en);check.setChecked(filename!="ION_HISTORY.txt");check.setToolTip(filename)
            out.addWidget(check,i//2,i%2);self.output_checks[filename]=check
        self.extra_notes=self.label("汇总、参数与 JSON 始终保存；空位 / 替位标为不可用", "Summary, project and JSON always included; vacancies / replacements unavailable")
        self.extra_notes.setWordWrap(True);out.addWidget(self.extra_notes,5,0,1,2);lower.addWidget(self.export_group,2)
        actions=QVBoxLayout();self.start_button=self.button("保存输入并开始计算", "Save input & run",self.start_run,"start")
        self.resume_button=self.button("继续当前计算", "Resume calculation",self.resume_run,"resume")
        self.pause_button=self.button("暂停（批次结束后）", "Pause after batch",self.pause_run)
        self.cancel_button=self.button("停止计算", "Stop calculation",self.cancel_run,"stop")
        self.restore_button=self.button("恢复最近断点", "Restore last checkpoint",self.restore_last)
        for w in (self.start_button,self.resume_button,self.pause_button,self.cancel_button,self.restore_button):actions.addWidget(w)
        actions.addStretch();lower.addLayout(actions,1);main.addLayout(lower)
        main.addWidget(self.label("位移事件模式 · 静态非晶多层靶 · 不计算稳定空位或替位碰撞", "Creation-event mode · Static amorphous layers · Stable vacancies and replacements unavailable"))
        scroll.setWidget(page);self.tabs.addTab(scroll,"")

    def build_results(self):
        page=QWidget();layout=QVBoxLayout(page)
        bar=QHBoxLayout();bar.addWidget(self.label("结果来源", "Result source"))
        self.source=self.combo([("current","当前模拟","Current simulation"),("reference","SRIM 参考文件（独立显示）","SRIM reference files (separate)")])
        self.source.currentIndexChanged.connect(self.refresh_result);bar.addWidget(self.source)
        bar.addWidget(self.button("载入参考文件夹", "Load reference folder",self.load_reference))
        self.show_targets=self.bind(QCheckBox(),"显示靶原子分布","Show target distributions")
        self.show_targets.toggled.connect(self.refresh_result);bar.addWidget(self.show_targets);bar.addStretch()
        self.plot_save_button=self.button("保存图表", "Save chart",self.save_plot);bar.addWidget(self.plot_save_button)
        self.export_button=self.button("导出结果文件夹", "Export result folder",self.export_result);bar.addWidget(self.export_button)
        layout.addLayout(bar)
        self.result_caption=QLabel();self.result_caption.setWordWrap(True);layout.addWidget(self.result_caption)
        splitter=QSplitter();self.plot_list=QListWidget();self.plot_list.setMinimumWidth(180);self.plot_list.setMaximumWidth(245)
        self.plot_list.currentRowChanged.connect(self.refresh_result);splitter.addWidget(self.plot_list)
        self.result_tabs=QTabWidget();self.chart=ScientificPlot();self.result_tabs.addTab(self.chart,"")
        self.data_table=QTableWidget();self.data_table.setAlternatingRowColors(True)
        self.data_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.result_tabs.addTab(self.data_table,"")
        self.log_box=QPlainTextEdit();self.log_box.setReadOnly(True);self.result_tabs.addTab(self.log_box,"")
        splitter.addWidget(self.result_tabs)
        self.summary=QPlainTextEdit();self.summary.setReadOnly(True);self.summary.setMinimumWidth(240);self.summary.setMaximumWidth(330)
        splitter.addWidget(self.summary);splitter.setSizes([195,930,285]);layout.addWidget(splitter,1)
        self.dose_group=self.group("峰值浓度与剂量", "PEAK CONCENTRATION & DOSE");dose=QHBoxLayout(self.dose_group)
        dose.addWidget(self.label("目标峰值浓度 (cm⁻³)", "Desired peak concentration (cm⁻³)"));self.desired=self.edit("1e18",160)
        self.desired.textChanged.connect(self.render_dose);dose.addWidget(self.desired);self.dose_text=QLabel();dose.addWidget(self.dose_text,1);layout.addWidget(self.dose_group)
        self.tabs.addTab(page,"")

    def retranslate(self):
        app=QApplication.instance()
        app.removeTranslator(self.translator)
        if self.language=="zh":
            self.translator.load("qtbase_zh_CN",QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
            app.installTranslator(self.translator)
        QLocale.setDefault(QLocale("zh_CN" if self.language=="zh" else "en_US"))
        self.setWindowTitle(self.tr("GSRIM · 离子输运模拟", "GSRIM · Ion transport simulator"))
        for widget,zh,en,setter in self.bindings:getattr(widget,setter)(self.tr(zh,en))
        for combo,options in self.combo_bindings:
            combo.blockSignals(True)
            for i,(_,zh,en) in enumerate(options):combo.setItemText(i,self.tr(zh,en))
            combo.blockSignals(False)
        self.tabs.setTabText(0,self.tr("计算控制面板","Calculation setup"))
        self.tabs.setTabText(1,self.tr("结果与图表","Results & plots"))
        for i,pair in enumerate([("图表","Chart"),("数据表","Data table"),("运行记录","Run log")]):
            self.result_tabs.setTabText(i,self.tr(*pair))
        self.layers.setHorizontalHeaderLabels([self.tr("层名称","Layer name"),self.tr("厚度","Width"),self.tr("单位","Unit"),self.tr("密度 g/cm³","Density g/cm³")])
        self.species.setHorizontalHeaderLabels([self.tr("元素","Element"),"Z",self.tr("质量 u","Mass u"),self.tr("原子配比","Atom ratio"),self.tr("原子 %","Atomic %"),self.tr("位移 eV","Displ. eV"),self.tr("晶格 eV","Lattice eV"),self.tr("表面 eV","Surface eV")])
        self.refresh_binding_hints()
        row=self.plot_list.currentRow();self.plot_list.blockSignals(True);self.plot_list.clear()
        self.plot_list.addItems([pair[0 if self.language=="zh" else 1] for pair in PLOT_NAMES.values()])
        self.plot_list.setCurrentRow(max(0,row));self.plot_list.blockSignals(False)
        if self.reference_folder:self.references=reference_plots(self.reference_folder,self.language)
        self.update_layer_summary();self.update_logs();self.refresh_result();self.poll()

    def change_language(self,index):
        self.language="zh" if index==0 else "en"
        self.settings.setValue("language",self.language)
        self.retranslate()

    def log(self,zh,en=None):
        self.logs.append((datetime.now().strftime("%H:%M:%S"),zh,en or zh))
        self.update_logs()

    def update_logs(self):
        self.log_box.setPlainText("\n".join(f"[{t}] {self.tr(zh,en)}" for t,zh,en in self.logs))
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def error(self,zh,en,detail):
        self.log(zh+": "+str(detail),en+": "+str(detail))
        box=QMessageBox(QMessageBox.Icon.Warning,self.tr("操作未完成","Action could not complete"),self.tr(zh,en),parent=self)
        box.setDetailedText(str(detail));box.exec()

    def confirm(self,zh,en):
        return QMessageBox.question(self,self.tr("请确认","Confirm"),self.tr(zh,en),
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes

    def dialog(self,caption,save=False,filter="JSON (*.json)"):
        method=QFileDialog.getSaveFileName if save else QFileDialog.getOpenFileName
        return method(self,caption,str(ROOT),filter,options=QFileDialog.Option.DontUseNativeDialog)[0]

    def fill_project(self,project):
        self._loading=True
        self.project=copy.deepcopy(project);p=self.project
        self.name.setText(p["name"]);ion=p["ion"]
        self.ion_symbol.setCurrentText(ion["symbol"])
        for widget,key in [(self.ion_z,"z"),(self.ion_mass,"mass_u"),(self.ion_energy,"energy_kev"),(self.ion_angle,"angle_deg")]:widget.setText(str(ion[key]))
        for key,widget in self.run_fields.items():widget.setText(str(p["run"][key]))
        for combo,value in [(self.mode,p["run"]["mode"]),(self.stopping,p["physics"]["stopping"]),(self.scattering,p["physics"].get("scattering","table"))]:
            combo.setCurrentIndex(max(0,combo.findData(value)))
        self.layers.blockSignals(True);self.layers.setRowCount(len(p["layers"]))
        for row,layer in enumerate(p["layers"]):
            for col,key in [(0,"name"),(1,"thickness_a"),(3,"density_g_cm3")]:self.layers.setItem(row,col,QTableWidgetItem(str(layer[key])))
            old=self.layers.cellWidget(row,2)
            if old:old.hide()
            unit=QComboBox();unit.addItems(["Å","nm","µm"]);self.layers.setCellWidget(row,2,unit)
        self.selected_layer=0;self.layers.selectRow(0);self.layers.setCurrentCell(0,0);self.layers.blockSignals(False)
        self.fill_species(p["layers"][0]["species"]);self._loading=False;self.update_layer_summary()

    def fill_species(self,items):
        self.species.blockSignals(True)
        for row in range(self.species.rowCount()):
            old=self.species.cellWidget(row,0)
            if old:old.hide()
        self.species.setRowCount(len(items))
        for row,s in enumerate(items):
            element=QComboBox();element.setEditable(True);element.addItems(list(ELEMENTS));element.setCurrentText(s["symbol"])
            element.setProperty("binding_symbol",s["symbol"])
            element.currentTextChanged.connect(lambda text,r=row:self.target_element_changed(r,text))
            self.species.setCellWidget(row,0,element)
            for col,key in [(1,"z"),(2,"mass_u"),(3,"amount"),(5,"displacement_ev"),(6,"lattice_ev"),(7,"surface_ev")]:
                self.species.setItem(row,col,QTableWidgetItem("" if s[key] is None else str(s[key])))
            item=QTableWidgetItem();item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.species.setItem(row,4,item)
        self.species.blockSignals(False);self.update_fractions();self.refresh_binding_hints()

    def read_species(self):
        result=[]
        for row in range(self.species.rowCount()):
            s={"symbol":self.species.cellWidget(row,0).currentText().strip()}
            for col,key in [(1,"z"),(2,"mass_u"),(3,"amount"),(5,"displacement_ev"),(6,"lattice_ev"),(7,"surface_ev")]:
                text=self.species.item(row,col).text().strip()
                s[key]=None if not text and col>=5 else (int(text) if key=="z" else float(text))
            result.append(s)
        return result

    def collect(self,check=False):
        p=copy.deepcopy(self.project)
        p["layers"][self.selected_layer]["species"]=self.read_species()
        for row,layer in enumerate(p["layers"]):
            layer["name"]=self.layers.item(row,0).text()
            factor=[1.,10.,10000.][self.layers.cellWidget(row,2).currentIndex()]
            layer["thickness_a"]=float(self.layers.item(row,1).text())*factor
            layer["density_g_cm3"]=float(self.layers.item(row,3).text())
        p["name"]=self.name.text();p["ion"]={"symbol":self.ion_symbol.currentText().strip(),"z":int(self.ion_z.text()),
            "mass_u":float(self.ion_mass.text()),"energy_kev":float(self.ion_energy.text()),"angle_deg":float(self.ion_angle.text())}
        ints={"ions","seed","batch_size","bins","max_events"}
        for key,widget in self.run_fields.items():p["run"][key]=int(widget.text()) if key in ints else float(widget.text())
        p["run"].update(mode=self.mode.currentData(),damage="creation")
        p["physics"].update(stopping=self.stopping.currentData(),scattering=self.scattering.currentData(),validated=False)
        return validate(p)[0] if check else p

    def ion_changed(self,text):
        if self._loading:return
        if text in ELEMENTS:
            self.ion_z.setText(str(ELEMENTS[text]["z"]));self.ion_mass.setText(str(ELEMENTS[text]["mass_u"]))

    def target_element_changed(self,row,text):
        if text in ELEMENTS and row<self.species.rowCount():
            picker=self.species.cellWidget(row,0)
            if picker.property("binding_symbol")==text:return
            picker.setProperty("binding_symbol",text)
            self.species.item(row,1).setText(str(ELEMENTS[text]["z"]))
            self.species.item(row,2).setText(str(ELEMENTS[text]["mass_u"]))
            defaults=binding_defaults(text)
            for col,key in [(5,"displacement_ev"),(6,"lattice_ev"),(7,"surface_ev")]:
                value=defaults[key]
                self.species.item(row,col).setText("" if value is None else str(value))
            self.refresh_binding_hints()

    def refresh_binding_hints(self):
        for row in range(self.species.rowCount()):
            picker=self.species.cellWidget(row,0)
            if picker is None:continue
            for col,key in [(5,"displacement_ev"),(6,"lattice_ev"),(7,"surface_ev")]:
                item=self.species.item(row,col)
                if item is not None:item.setToolTip(binding_hint(picker.currentText(),key,self.language))

    def update_fractions(self,*args):
        self.species.blockSignals(True)
        try:
            values=[float(self.species.item(r,3).text()) for r in range(self.species.rowCount())];total=sum(values)
            for row,value in enumerate(values):self.species.item(row,4).setText(f"{100*value/total:.3f}" if total>0 else "—")
        except (ValueError,AttributeError):pass
        finally:self.species.blockSignals(False)

    def update_layer_summary(self):
        self.layer_summary.setText(self.tr("选中一层以编辑其元素。厚度可使用 Å / nm / µm。", "Select a layer to edit its elements. Width supports Å / nm / µm."))

    def layer_selected(self,row,column,previous,previous_col):
        if self._loading or row<0 or row==self.selected_layer:return
        try:self.project["layers"][self.selected_layer]["species"]=self.read_species()
        except Exception as exc:
            self.layers.blockSignals(True);self.layers.setCurrentCell(self.selected_layer,0);self.layers.blockSignals(False)
            self.error("请先修正当前层的元素参数", "Correct the selected layer's element values first",exc);return
        self.selected_layer=row;self.fill_species(self.project["layers"][row]["species"])

    def add_layer(self):
        try:
            p=self.collect()
            if len(p["layers"])>=8:raise ValueError(self.tr("最多 8 层", "At most 8 layers"))
            layer=layer_from_compound("Si",1000);layer["name"]=f"Layer {len(p['layers'])+1}"
            p["layers"].append(layer);self.fill_project(p);self.layers.setCurrentCell(len(p["layers"])-1,0)
        except Exception as exc:self.error("无法添加层", "Cannot add layer",exc)

    def remove_layer(self):
        try:
            p=self.collect()
            if len(p["layers"])<=1:raise ValueError(self.tr("至少保留一层", "Keep at least one layer"))
            p["layers"].pop(self.selected_layer);self.fill_project(p)
        except Exception as exc:self.error("无法删除层", "Cannot remove layer",exc)

    def add_species(self):
        try:
            items=self.read_species()
            if len(items)>=8:raise ValueError(self.tr("每层最多 8 种元素", "At most 8 species per layer"))
            symbol=next(s for s in ELEMENTS if s not in {item["symbol"] for item in items})
            items.append(species_from_element(symbol))
            self.fill_species(items)
        except Exception as exc:self.error("无法添加元素", "Cannot add element",exc)

    def remove_species(self):
        try:
            items=self.read_species()
            if len(items)<=1:raise ValueError(self.tr("至少保留一种元素", "Keep at least one species"))
            row=self.species.currentRow();items.pop(row if row>=0 else len(items)-1);self.fill_species(items)
        except Exception as exc:self.error("无法删除元素", "Cannot remove element",exc)

    def choose_compound(self):
        dialog=QDialog(self);dialog.setWindowTitle(self.tr("化合物字典", "Compound dictionary"));dialog.resize(530,250)
        layout=QVBoxLayout(dialog);picker=QComboBox();picker.addItems(sorted(COMPOUNDS));layout.addWidget(picker)
        info=QLabel();info.setWordWrap(True);layout.addWidget(info)
        def preview():
            c=COMPOUNDS[picker.currentText()]
            info.setText(self.tr("密度", "Density")+f": {c['density_g_cm3']} g/cm³\n"+
                " : ".join(f"{s['symbol']} ({s['amount']:g})" for s in c["species"])+"\n"+
                self.tr("替换当前层成分和密度，保留厚度。预设参数需按材料核对。", "Replaces composition and density; keeps width. Verify preset values for your material."))
        picker.currentIndexChanged.connect(preview);preview()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            try:
                p=self.collect();row=self.selected_layer
                p["layers"][row]=layer_from_compound(picker.currentText(),p["layers"][row]["thickness_a"])
                self.fill_project(p);self.layers.setCurrentCell(row,0)
            except Exception as exc:self.error("无法应用材料", "Cannot apply material",exc)

    def load_reference_setup(self):
        if self.confirm("用 H 40 keV → Ga₂O₃ 参考工况替换当前输入？", "Replace input with the H 40 keV → Ga₂O₃ reference setup?"):
            self.fill_project(reference_project())

    def open_project(self):
        file=self.dialog(self.tr("打开项目参数", "Open project"))
        if not file:return
        try:
            p=validate(json.loads(Path(file).read_text(encoding="utf-8-sig")))[0]
            self.fill_project(p);self.log("已载入项目参数", "Project input loaded")
        except Exception as exc:self.error("无法读取项目文件", "Cannot read project file",exc)

    def save_project(self):
        try:p=self.collect(check=True)
        except Exception as exc:self.error("输入参数无效", "Invalid input values",exc);return
        file=self.dialog(self.tr("保存项目参数", "Save project"),True)
        if file:
            try:
                Path(file).write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding="utf-8");self.log("项目已保存", "Project saved")
            except Exception as exc:self.error("无法保存项目", "Cannot save project",exc)

    def busy(self):
        return self.simulation is not None and self.simulation.thread is not None and self.simulation.thread.is_alive()

    def start_run(self):
        if self.busy():return
        try:p=self.collect(check=True)
        except Exception as exc:self.error("输入参数无效，请检查表格", "Invalid input; check the parameter tables",exc);return
        if self.state and self.state.get("completed") and not self.confirm("开始新计算将替换当前显示结果。需要保留时请先导出。继续？", "A new run replaces the displayed result. Export it first if needed. Continue?"):return
        try:
            storage=Path(os.environ.get("GSRIM_RESULTS_DIR",str(ROOT/"results/native")))
            folder=storage/("run-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f"));folder.mkdir(parents=True)
            path=folder/"autosave.npz"
            (folder/"project.json").write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding="utf-8")
            self.simulation=Simulation(p,checkpoint_path=path)
            self.settings.setValue("last_checkpoint",str(path))
            self._last_token=None;self._notified_error=None
            self.simulation.start();self.source.setCurrentIndex(0);self.tabs.setCurrentIndex(1)
            self.log("计算已启动，输入已保存", "Calculation started; input saved");self.poll()
        except Exception as exc:self.error("无法开始计算", "Cannot start calculation",exc)

    def pause_run(self):
        try:
            if self.simulation:self.simulation.pause();self.log("已请求暂停，将在当前批次结束后生效", "Pause requested; waiting for current batch")
        except Exception as exc:self.error("无法暂停", "Cannot pause",exc)

    def cancel_run(self):
        if self.simulation:self.simulation.cancel();self.log("已请求停止，将保存已完成批次", "Stop requested; completed batches will be saved")

    def resume_run(self):
        try:
            if self.simulation and not self.busy():
                self.fill_project(self.simulation.project);self.simulation.start();self.poll()
        except Exception as exc:self.error("无法继续计算", "Cannot resume calculation",exc)

    def restore_last(self):
        path=Path(str(self.settings.value("last_checkpoint",str(AUTOSAVE_PATH))))
        if not path.is_file():
            self.error("没有可用的最近断点，可使用“载入结果 / 断点”选择文件", "No recent checkpoint; use Load result / checkpoint",str(path));return
        self.restore_checkpoint(path)

    def restore_checkpoint(self,path):
        if self.busy():return
        if self.state and self.state.get("completed") and not self.confirm("用断点替换当前显示结果？", "Replace the displayed result with this checkpoint?"):return
        try:
            sim=Simulation.load_checkpoint(path);sim.autosave_path=Path(path)
            sim.status="completed" if sim.completed==sim.project["run"]["ions"] else "paused"
            if sim.records and any((r[:,16]>0).any() for r in sim.records):sim.status="error";sim.error="Checkpoint contains failed histories"
            self.simulation=sim;self.state=sim.snapshot();self.fill_project(sim.project)
            self.settings.setValue("last_checkpoint",str(path));self._last_token=None
            self.source.setCurrentIndex(0);self.tabs.setCurrentIndex(1);self.log("断点已载入", "Checkpoint loaded");self.poll()
        except Exception as exc:self.error("无法恢复断点", "Cannot restore checkpoint",exc)

    def load_result(self):
        if self.busy():return
        file=self.dialog(self.tr("载入结果或断点", "Load result or checkpoint"),filter="GSRIM (*.json *.npz)")
        if not file:return
        if Path(file).suffix.lower()==".npz":self.restore_checkpoint(file);return
        try:
            state=json.loads(Path(file).read_text(encoding="utf-8-sig"));validate(state["project"])
            for key in ("stats","profiles","depth_a","spectra","completed","status"):state[key]
            if state.get("engine_revision")!=ENGINE_REVISION:state["diagnostic_only"]=True
            plot_from_snapshot(state)
            self.simulation=None;self.state=state;self._last_token=None
            self.source.setCurrentIndex(0);self.tabs.setCurrentIndex(1);self.log("结果快照已载入（只读）", "Result snapshot loaded (read-only)")
            self.refresh_result();self.poll()
        except Exception as exc:self.error("无法读取结果", "Cannot read result",exc)

    def load_reference(self):
        folder=QFileDialog.getExistingDirectory(self,self.tr("选择包含 RANGE.txt / IONIZ.txt 的参考文件夹", "Select reference folder containing RANGE.txt / IONIZ.txt"),
            str(self.reference_folder or ROOT),QFileDialog.Option.DontUseNativeDialog)
        if not folder:return
        try:
            self.references=reference_plots(folder,self.language);self.reference_folder=folder
            self.source.setCurrentIndex(1);self.refresh_result();self.log("参考输出已载入，独立于当前模拟显示", "Reference output loaded separately from the simulation")
        except Exception as exc:self.error("无法载入参考文件夹", "Cannot load reference folder",exc)

    def poll(self):
        if self.simulation:
            token=(self.simulation.completed,self.simulation.status,self.simulation.error,self.language)
            if token!=self._last_token:
                self.state=self.simulation.snapshot();self._last_token=token;self.refresh_result()
                if self.simulation.status=="error" and self._notified_error!=self.simulation.error:
                    self._notified_error=self.simulation.error
                    self.log("计算失败，结果仅用于诊断："+self.simulation.error,"Calculation failed; diagnostic only: "+self.simulation.error)
            elapsed=self.simulation.elapsed
        else:elapsed=(self.state or {}).get("elapsed_s",0.)
        busy=self.busy();state=self.state or {};status=state.get("status","ready")
        labels={"ready":("就绪","Ready"),"preparing":("准备 GPU 与物理表","Preparing GPU & tables"),"running":("计算中","Running"),
            "paused":("已暂停","Paused"),"cancelled":("已停止","Stopped"),"completed":("计算完成","Completed"),"error":("计算失败 · 仅诊断","Failed · diagnostic")}
        self.status_label.setText(self.tr(*labels.get(status,(status,status))))
        if self.simulation is None and self.state:
            self.status_label.setText(self.tr("结果快照（只读）", "Result snapshot (read-only)"))
        n=state.get("completed",0);total=state.get("total",0)
        self.progress.setRange(0,0 if status=="preparing" else 1000)
        if status!="preparing":self.progress.setValue(int(n/max(1,total)*1000))
        self.count_label.setText(f"{n:,} / {total:,}");self.elapsed.setText(f"{elapsed:.1f} s")
        for group in (self.ion_group,self.target_group,self.run_group):group.setEnabled(not busy)
        for button in (self.open_button,self.save_button,self.load_button,self.start_button,self.restore_button):button.setEnabled(not busy)
        self.pause_button.setEnabled(busy and status in ("preparing","running"));self.cancel_button.setEnabled(busy)
        self.resume_button.setEnabled(not busy and self.simulation is not None and status in ("paused","cancelled") and not state.get("diagnostic_only"))
        self.quick_pause.setEnabled(self.pause_button.isEnabled());self.quick_resume.setEnabled(self.resume_button.isEnabled());self.quick_stop.setEnabled(self.cancel_button.isEnabled())
        self.export_button.setEnabled(bool(n) and not state.get("diagnostic_only") and self.source.currentData()=="current")
        self.plot_save_button.setEnabled(self.chart.data is not None)
        if self._close_pending and not busy:self.close()

    def refresh_result(self,*args):
        if not hasattr(self,"chart"):return
        mode=list(PLOT_NAMES)[max(0,self.plot_list.currentRow())]
        if self.source.currentData()=="reference":
            data=copy.deepcopy(self.references.get(mode));self.chart.set_data(data,language=self.language,
                empty_text=self.tr("参考文件夹没有此图表的数据", "This reference folder has no data for this chart"))
            self.result_caption.setText(self.tr("参考数据，非本程序计算结果：", "Reference data, not generated by this simulation: ")+str(self.reference_folder or "—"))
            if self.reference_folder:
                tdata=Path(self.reference_folder)/"TDATA.txt"
                self.summary.setPlainText(tdata.read_text(encoding="utf-8-sig",errors="replace") if tdata.is_file() else self.tr("参考数据", "Reference data"))
            else:self.summary.setPlainText(self.tr("请选择参考文件夹", "Select a reference folder"))
        elif self.state:
            data=plot_from_snapshot(self.state,mode,self.language)
            tracks=self.state.get("tracks",[]) if mode=="tracks" else None
            if mode=="tracks":
                data.xlabel=self.tr("靶材深度 (Å)", "Target depth (Å)");data.ylabel=self.tr("横向位置 X (Å)", "Lateral position X (Å)")
                data.notes=[self.tr("最多 48 条入射轨迹；不含完整反冲轨迹", "Up to 48 incident tracks; not full recoil trajectories")]
            self.chart.set_data(data,tracks,self.language)
            p=self.state["project"];ion=p["ion"]
            self.result_caption.setText(f"{p['name']}  |  {ion['symbol']} · {ion['energy_kev']:g} keV · {ion['angle_deg']:g}°  |  "+
                self.tr("已计算", "Calculated")+f" {self.state['completed']:,} "+self.tr("条入射历史", "incident histories"))
            self.render_summary()
        else:
            data=None;self.chart.set_data(None,language=self.language)
            self.result_caption.setText(self.tr("尚无模拟结果", "No simulation results yet"));self.summary.setPlainText(self.tr("计算完成后显示射程、能量收支与模型来源。", "Run a calculation to view ranges, energy accounting and model sources."))
        self.show_targets.setEnabled(mode=="range")
        if data is not None and mode=="range" and not self.show_targets.isChecked():
            data.series=data.series[:1]
            data.title=self.tr("离子分布", "ION RANGES")
            if self.source.currentData()=="reference":data.title+=self.tr(" · 参考数据", " · Reference")
            self.chart.update()
        self.render_table(data);self.render_dose()
        self.export_button.setEnabled(bool(self.state and self.state.get("completed")) and not (self.state or {}).get("diagnostic_only") and self.source.currentData()=="current")
        self.plot_save_button.setEnabled(data is not None)

    def render_table(self,data):
        if data is None:self.data_table.setRowCount(0);self.data_table.setColumnCount(0);return
        self.data_table.setUpdatesEnabled(False)
        self.data_table.setRowCount(len(data.x));self.data_table.setColumnCount(1+len(data.series))
        self.data_table.setHorizontalHeaderLabels([data.xlabel]+[s[0] for s in data.series])
        for row,x in enumerate(data.x):
            values=[x]+[s[1][row] if row<len(s[1]) else 0 for s in data.series]
            for col,value in enumerate(values):self.data_table.setItem(row,col,QTableWidgetItem(f"{value:.6E}"))
        self.data_table.setUpdatesEnabled(True)

    def render_summary(self):
        s=self.state["stats"];lines=[self.tr("计算摘要", "CALCULATION SUMMARY"),"─"*28]
        for zh,en,key,unit in [("投影射程","Projected range","mean_range_a","Å"),("射程展宽","Straggling","range_straggle_a","Å"),
            ("偏度","Skewness","range_skewness",""),("峰度（正态分布为 3）","Kurtosis (Gaussian=3)","range_kurtosis",""),
            ("横向射程","Lateral range","lateral_proj_a","Å"),("均值标准误","Range mean SE","mean_range_se_nm","nm"),
            ("注入离子","Implanted","implanted",""),("背散射离子","Backscattered","backscattered",""),("透射离子","Transmitted","transmitted",""),
            ("位移事件 / 离子","Displacements / ion","displacements_per_ion",""),("前表面溅射 / 离子","Front sputter / ion","sputter_yield_front",""),
            ("电子损失","Electronic loss","electronic_ev_per_ion","eV/ion"),("晶格沉积","Lattice deposition","lattice_ev_per_ion","eV/ion"),
            ("逃逸能量","Escape energy","escaped_ev_per_ion","eV/ion"),("未解决能量","Unresolved","unresolved_ev_per_ion","eV/ion"),
            ("最大能量误差","Max energy error","max_energy_error_ev","eV")]:
            lines += [self.tr(zh,en),f"  {fmt(s.get(key),4)} {unit}"]
        lines += ["",self.tr("稳定空位 / 替位：未实现", "Stable vacancies / replacements: unavailable"),
                  self.tr("电子阻止来源", "STOPPING SOURCES")]+self.state.get("se_sources",[])
        if self.state.get("diagnostic_only"):lines += ["",self.tr("仅诊断：结果含失败或旧版历史", "DIAGNOSTIC: failed or legacy histories")]
        if not self.state.get("detail_profiles"):lines += [self.tr("此快照无离子 / 反冲分项", "Ion / recoil splits unavailable in this snapshot")]
        if self.state.get("error"):lines += ["",self.tr("详细错误", "ERROR DETAILS"),self.state["error"]]
        self.summary.setPlainText("\n".join(lines))

    def render_dose(self,*args):
        if not hasattr(self,"dose_text"):return
        s=self.state or {};peak=s.get("stats",{}).get("peak_per_cm")
        if self.source.currentData()=="reference":
            self.dose_text.setText(self.tr("参考数据不参与本次剂量换算", "Reference data are excluded from dose calculation"));return
        if s.get("diagnostic_only"):
            self.dose_text.setText(self.tr("诊断结果：禁用剂量换算", "Diagnostic result: dose calculation disabled"));return
        try:
            desired=float(self.desired.text())
            if not np.isfinite(desired) or desired<=0:raise ValueError()
            if peak and peak>0:
                self.dose_text.setText(f"{desired/peak:.5E} ions/cm²"+self.tr("（部分统计）", " (partial result)")*(s.get("status")!="completed"))
            else:self.dose_text.setText(self.tr("等待有效注入分布", "Waiting for a valid implantation profile"))
        except ValueError:self.dose_text.setText(self.tr("请输入正的有限浓度", "Enter a positive finite concentration"))

    def save_plot(self):
        if self.chart.data is None:return
        file=self.dialog(self.tr("保存科学图表", "Save scientific chart"),True,"PNG (*.png);;Bitmap (*.bmp)")
        if file:
            if not Path(file).suffix:file+=".png"
            try:
                if not self.chart.image().save(file):raise OSError(file)
            except Exception as exc:self.error("无法保存图表", "Cannot save chart",exc)

    def export_result(self):
        if not self.state or self.state.get("diagnostic_only"):return
        folder=QFileDialog.getExistingDirectory(self,self.tr("选择输出目录，将创建独立结果子文件夹", "Choose output directory; a new result subfolder will be created"),
            str(ROOT/"results"),QFileDialog.Option.DontUseNativeDialog)
        if not folder:return
        try:
            selected={name for name,check in self.output_checks.items() if check.isChecked()};selected.update({"VACANCY.txt","NOVAC.txt"})
            if self.simulation:
                with self.simulation.lock:
                    state=self.simulation.snapshot()
                    records=np.concatenate(self.simulation.records) if self.simulation.records and "ION_HISTORY.txt" in selected else None
            else:state=self.state;records=None
            path=export_bundle(state,folder,records,selected)
            self.chart.image().save(str(path/"plot.png"))
            self.log("结果已导出："+str(path),"Results exported: "+str(path))
            QMessageBox.information(self,self.tr("导出完成", "Export complete"),str(path))
        except Exception as exc:self.error("无法导出结果", "Cannot export results",exc)

    def closeEvent(self,event):
        if self.busy():
            if not self._close_pending and not self.confirm("停止计算并在当前批次保存后关闭？", "Stop the calculation and close after saving the current batch?"):
                event.ignore();return
            self._close_pending=True;self.simulation.cancel();self.status_label.setText(self.tr("正在保存并关闭…", "Saving before closing…"));event.ignore();return
        self.settings.setValue("language",self.language);event.accept()


def main():
    app=QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion");app.setFont(QFont("Microsoft YaHei UI",10))
    window=MainWindow();window.show()
    return app.exec()


if __name__=="__main__":
    raise SystemExit(main())

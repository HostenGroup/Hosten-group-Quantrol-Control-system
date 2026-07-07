from PyQt5.QtCore import * 
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from datetime import datetime
import config  
import json
import other_handlers
import button_handlers
import change_handlers


class ReadOnlyDelegate(QStyledItemDelegate):
    '''
    Function is used to make some rows and columns read only   
    Example :   delegate = ReadOnlyDelegate(self)
                self.edges_table.setItemDelegateForColumn(2,delegate)
    '''
    def createEditor(self, parent, option, index):
        return
    
def making_separator(self):
#         '''
#         The function does include a separator in the table that is coloured in dark grey for better visual separation across all tabs
#         Fucntion is called each time the new edge is being incerted
#         '''
#         #making the separation rows a single column
#         if self.sequence_num_rows > 1: # to avoid having a warning that single cell span won't be added
#             if config.dds_channels_number > 0:
#                 self.digital_table.setSpan(0,3, self.sequence_num_rows, 1)
#             if config.analog_channels_number > 0:
#                 self.analog_table.setSpan(0,3, self.sequence_num_rows, 1)
#             if config.sampler_channels_number > 0:
#                 self.sampler_table.setSpan(0,3, self.sequence_num_rows, 1)
 
#         # grey coloured separating line digital tab
#         if config.digital_channels_number > 0:
#             self.digital_table.setItem(0,3, QTableWidgetItem())
#             self.digital_table.item(0,3).setBackground(self.grey)
#         # grey coloured separating line analog tab
#         if config.analog_channels_number > 0:
#             self.analog_table.setItem(0,3, QTableWidgetItem())
#             self.analog_table.item(0,3).setBackground(self.grey)
#         # grey coloured separating line dds tab
#         if config.dds_channels_number > 0:
#             self.dds_seq.setSpan(0,3, self.sequence_num_rows, 1)  
#             self.dds_seq.setItem(0,3, QTableWidgetItem())
#             self.dds_seq.item(0,3).setBackground(self.grey)
#             # grey coloured separating line in dds tab between channels
#             for i in range(config.dds_channels_number):
#                 self.dds_table.setSpan(0, 6*i + 3, self.sequence_num_rows, 1)
#                 self.dds_table.setItem(0,6*i + 3, QTableWidgetItem())
#                 self.dds_table.item(0, 6*i + 3).setBackground(self.grey)
#         # grey coloured separating line mirny tab
#         if config.mirny_channels_number > 0:
#             self.mirny_dummy.setSpan(0,3, self.sequence_num_rows, 1)  
#             self.mirny_dummy.setItem(0,3, QTableWidgetItem())
#             self.mirny_dummy.item(0,3).setBackground(self.grey)
#             # grey coloured separating line in mirny tab between channels
#             for i in range(config.mirny_channels_number):
#                 self.mirny_table.setSpan(0, 6*i + 3, self.sequence_num_rows, 1)
#                 self.mirny_table.setItem(0,6*i + 3, QTableWidgetItem())
#                 self.mirny_table.item(0, 6*i + 3).setBackground(self.grey)
#         # grey coloured separating line sampler tab
#         if config.sampler_channels_number > 0:
#             self.sampler_table.setItem(0,3, QTableWidgetItem())
#             self.sampler_table.item(0,3).setBackground(self.grey)
    return


def _create_header_separator(self, parent: QWidget, x: int, y: int, width: int) -> QFrame:
    """Add a thin gray separator between header widgets and their tables."""
    thickness = max(2, int(round(4*self.SCALE_H)))
    separator = QFrame(parent)
    separator.setGeometry(x, y, width, thickness)
    separator.setFrameShape(QFrame.NoFrame)
    separator.setFrameShadow(QFrame.Plain)
    separator.setStyleSheet(
        f"QFrame {{ background-color: {self.grey.name()}; border: 0px; margin: 0px; padding: 0px; }}"
    )
    separator.setAutoFillBackground(True)
    separator.setFocusPolicy(Qt.NoFocus)
    separator.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    separator.raise_()
    return separator


def _create_header_column_overlay(self, parent: QWidget, table: QTableWidget, column: int) -> QFrame:
    """Create a grey overlay covering the specified header column."""
    header = table.horizontalHeader()
    x = table.geometry().x() + header.sectionPosition(column)
    y = table.geometry().y()
    width = header.sectionSize(column)
    height = header.height()
    overlay = QFrame(parent)
    overlay.setGeometry(x, y, width, height)
    overlay.setFrameShape(QFrame.NoFrame)
    overlay.setFrameShadow(QFrame.Plain)
    overlay.setStyleSheet(
        f"QFrame {{ background-color: {self.grey.name()}; border: 0px; margin: 0px; padding: 0px; }}"
    )
    overlay.setAutoFillBackground(True)
    overlay.setFocusPolicy(Qt.NoFocus)
    overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    overlay.raise_()
    return overlay


def _build_live_camera_panel(self, parent: QWidget, slot_index: int, x: int, y: int, width: int, height: int) -> QGroupBox:
    """Build one live-camera control panel and wire its signals to the slot-aware handlers."""
    panel = QGroupBox(parent)
    panel.setTitle(f"Camera {slot_index + 1}")
    panel.setCheckable(True)
    panel.setChecked(False)
    panel.setFont(QFont('Arial', self.scale_font(14)))
    panel.move(x, y)
    panel.setFixedSize(width, height)
    panel.toggled.connect(lambda checked, slot=slot_index: self.handle_live_camera_toggled(checked, slot))

    form = QFormLayout(panel)

    suffix = "" if slot_index == 0 else f"_{slot_index}"
    setattr(self, f"live_camera_box{suffix}", panel)
    setattr(self, f"live_camera_checkbox{suffix}", panel)

    camera_combo = QComboBox(panel)
    camera_combo.addItems(list(config.camera_serial_numbers_dict.keys()))
    camera_combo.setEditable(True)
    camera_combo.lineEdit().setReadOnly(True)
    camera_combo.lineEdit().setPlaceholderText("Select camera...")
    camera_combo.setCurrentIndex(-1)
    camera_combo.currentTextChanged.connect(lambda _text, slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_which_cam_combo{suffix}", camera_combo)
    form.addRow("Which camera", camera_combo)

    gain_edit = QLineEdit(panel)
    gain_edit.setPlaceholderText("e.g. 20")
    gain_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_gain_edit{suffix}", gain_edit)
    form.addRow("Gain, dB", gain_edit)

    exposure_edit = QLineEdit(panel)
    exposure_edit.setPlaceholderText("e.g. 0.35")
    exposure_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_exposure_edit{suffix}", exposure_edit)
    form.addRow("Exposure time, ms", exposure_edit)

    format_combo = QComboBox(panel)
    format_combo.setEditable(True)
    format_combo.lineEdit().setReadOnly(True)
    format_combo.lineEdit().setPlaceholderText("Select image format...")
    format_combo.addItems(["Mono8", "Mono16"])
    format_combo.setCurrentIndex(-1)
    format_combo.currentTextChanged.connect(lambda _text, slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_format_combo{suffix}", format_combo)
    form.addRow("Image format", format_combo)

    subtract_checkbox = QCheckBox("Enable subtraction", panel)
    subtract_checkbox.setFont(QFont('Arial', self.scale_font(12)))
    subtract_checkbox.setEnabled(False)
    subtract_checkbox.toggled.connect(lambda enabled, slot=slot_index: self.handle_live_subtraction_toggled(enabled, slot))
    setattr(self, f"live_subtract_checkbox{suffix}", subtract_checkbox)
    form.addRow("", subtract_checkbox)

    dynamic_subtract_checkbox = QCheckBox("Dynamic background subtraction", panel)
    dynamic_subtract_checkbox.setFont(QFont('Arial', self.scale_font(12)))
    dynamic_subtract_checkbox.setEnabled(False)
    dynamic_subtract_checkbox.setChecked(False)
    dynamic_subtract_checkbox.toggled.connect(lambda enabled, slot=slot_index: self.handle_live_dynamic_subtraction_toggled(enabled, slot))
    setattr(self, f"live_dynamic_subtract_checkbox{suffix}", dynamic_subtract_checkbox)
    form.addRow("", dynamic_subtract_checkbox)

    hardware_trigger_checkbox = QCheckBox("Use hardware trigger", panel)
    hardware_trigger_checkbox.setFont(QFont('Arial', self.scale_font(12)))
    hardware_trigger_checkbox.setEnabled(False)
    hardware_trigger_checkbox.setChecked(False)
    hardware_trigger_checkbox.toggled.connect(lambda enabled, slot=slot_index: self.handle_live_hardware_trigger_toggled(enabled, slot))
    setattr(self, f"live_hardware_trigger_checkbox{suffix}", hardware_trigger_checkbox)
    form.addRow("", hardware_trigger_checkbox)

    gaussian_checkbox = QCheckBox("Enable Gaussian filter", panel)
    gaussian_checkbox.setFont(QFont('Arial', self.scale_font(12)))
    gaussian_checkbox.setEnabled(False)
    gaussian_checkbox.setChecked(False)
    gaussian_checkbox.toggled.connect(lambda enabled, slot=slot_index: self.handle_live_gaussian_toggled(enabled, slot))
    setattr(self, f"live_gaussian_checkbox{suffix}", gaussian_checkbox)
    form.addRow("", gaussian_checkbox)

    gaussian_sigma_edit = QLineEdit(panel)
    gaussian_sigma_edit.setPlaceholderText("e.g. 1.0")
    gaussian_sigma_edit.setEnabled(False)
    gaussian_sigma_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_gaussian_sigma_edit{suffix}", gaussian_sigma_edit)
    form.addRow("Gaussian sigma", gaussian_sigma_edit)

    gaussian_kernel_edit = QLineEdit(panel)
    gaussian_kernel_edit.setPlaceholderText("odd integer, e.g. 5")
    gaussian_kernel_edit.setEnabled(False)
    gaussian_kernel_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_gaussian_kernel_edit{suffix}", gaussian_kernel_edit)
    form.addRow("Gaussian kernel", gaussian_kernel_edit)

    roi_checkbox = QCheckBox("Enable ROI", panel)
    roi_checkbox.setFont(QFont('Arial', self.scale_font(12)))
    roi_checkbox.setEnabled(False)
    roi_checkbox.setChecked(False)
    roi_checkbox.toggled.connect(lambda enabled, slot=slot_index: self.handle_live_camera_roi_toggled(enabled, slot))
    setattr(self, f"live_roi_checkbox{suffix}", roi_checkbox)
    form.addRow("", roi_checkbox)

    roi_x_center_edit = QLineEdit(panel)
    roi_x_center_edit.setPlaceholderText("e.g. 512")
    roi_x_center_edit.setEnabled(False)
    roi_x_center_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_roi_x_center_edit{suffix}", roi_x_center_edit)
    form.addRow("ROI X center", roi_x_center_edit)

    roi_y_center_edit = QLineEdit(panel)
    roi_y_center_edit.setPlaceholderText("e.g. 384")
    roi_y_center_edit.setEnabled(False)
    roi_y_center_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_roi_y_center_edit{suffix}", roi_y_center_edit)
    form.addRow("ROI Y center", roi_y_center_edit)

    roi_width_edit = QLineEdit(panel)
    roi_width_edit.setPlaceholderText("e.g. 200")
    roi_width_edit.setEnabled(False)
    roi_width_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_roi_width_edit{suffix}", roi_width_edit)
    form.addRow("ROI X width", roi_width_edit)

    roi_height_edit = QLineEdit(panel)
    roi_height_edit.setPlaceholderText("e.g. 200")
    roi_height_edit.setEnabled(False)
    roi_height_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_roi_height_edit{suffix}", roi_height_edit)
    form.addRow("ROI Y height", roi_height_edit)

    display_gain_edit = QLineEdit(panel)
    display_gain_edit.setPlaceholderText("e.g. 0.0")
    display_gain_edit.setEnabled(False)
    display_gain_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_display_gain_edit{suffix}", display_gain_edit)
    form.addRow("Display digital gain, dB", display_gain_edit)

    downsample_factor_edit = QLineEdit(panel)
    downsample_factor_edit.setPlaceholderText("e.g. 2.0")
    downsample_factor_edit.setEnabled(False)
    downsample_factor_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_downsample_factor_edit{suffix}", downsample_factor_edit)
    form.addRow("Downsample factor", downsample_factor_edit)

    fps_limit_checkbox = QCheckBox("Enable camera FPS limit", panel)
    fps_limit_checkbox.setFont(QFont('Arial', self.scale_font(12)))
    fps_limit_checkbox.setEnabled(False)
    fps_limit_checkbox.setChecked(False)
    fps_limit_checkbox.toggled.connect(lambda enabled, slot=slot_index: self.handle_live_fps_limit_toggled(enabled, slot))
    setattr(self, f"live_fps_limit_checkbox{suffix}", fps_limit_checkbox)
    form.addRow("", fps_limit_checkbox)

    target_fps_edit = QLineEdit(panel)
    target_fps_edit.setPlaceholderText("e.g. 12")
    target_fps_edit.setEnabled(False)
    target_fps_edit.editingFinished.connect(lambda slot=slot_index: self.handle_live_camera_parameter_changed(slot))
    setattr(self, f"live_target_fps_edit{suffix}", target_fps_edit)
    form.addRow("Target FPS", target_fps_edit)

    return panel

def variables_sidebar_build(self,tab):
    width_of_table_variables = self.variables_table_width
    height_of_table_variables = self.bottom_buttons_y_val - self.top_margin - 10
    x_val = 1920 - width_of_table_variables - 10
    #VARIABLES LABLE
    variables_lable = QLabel(tab)
    variables_lable.setText("Constant variables")
    variables_lable.setFont(QFont('Arial', self.scale_font(14)))
    variables_lable.setGeometry(*self.scale_geom(x_val, 0, width_of_table_variables, self.top_margin))
    variables_lable.setAlignment(Qt.AlignCenter)
    
    #VARIABLES TABLE LAYOUT
    variables_table = QTableWidget(tab)
    variables_table.is_var_table = True
    
    
    variables_table.setGeometry(QRect(*self.scale_geom(x_val, self.top_margin, width_of_table_variables, height_of_table_variables)))     #size of the table
    variables_num_columns = 2 #2 for proof of concept
    variables_table.horizontalHeader().setMinimumSectionSize(1)
    variables_table.setColumnCount(variables_num_columns)
    variables_table.setHorizontalHeaderLabels(["Name", "Value"])
    variables_table.verticalHeader().setVisible(False)
    variables_table.horizontalHeader().setFixedHeight(int(self.SCALE_H*50))
    variables_table.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    variables_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    variables_table.setFont(QFont('Arial', self.scale_font(12)))
    variables_table.setColumnWidth(1,int(self.SCALE_W*(100)))
    variables_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    # variables_table.setColumnWidth(1,int(self.SCALE_W*(99)))
    #when table contents are changed
    variables_table.itemChanged.connect(lambda item: change_handlers.handle_variables_table_changed(self, item))

    #button to create new variable
    self.create_new_variable = QPushButton(tab)
    self.create_new_variable.setFont(QFont('Arial', self.scale_font(14)))
    self.create_new_variable.setGeometry(*self.scale_geom(x_val, self.top_margin + height_of_table_variables + self.sep, self.button_w, self.button_h))
    self.create_new_variable.setText("Create variable")
    self.create_new_variable.setToolTip("Button that is used to create a new variable.")
    self.create_new_variable.clicked.connect(lambda: button_handlers.handle_create_new_variable_button_clicked(self))
    #button to delete a variable
    delete_variable = QPushButton(tab)
    delete_variable.setFont(QFont('Arial', self.scale_font(14)))
    delete_variable.setGeometry(*self.scale_geom(x_val, self.top_margin + height_of_table_variables + 2*self.sep + self.button_h, self.button_w, self.button_h))
    delete_variable.setText("Delete variable")
    delete_variable.setToolTip("Button that is used to delete a new variable. First choose the new varibles by right clicking it in the variables table.")
    delete_variable.clicked.connect(lambda: button_handlers.handle_delete_variable_button_clicked(self))
    return (variables_table,delete_variable)


def bottom_buttons_build(self,tab):
    # BUTTONS AT THE BOTTOM
    y_val = self.bottom_buttons_y_val
    #button to stop continuous run
    self.stop_continuous_run_button = QPushButton(tab)
    self.stop_continuous_run_button.setFont(QFont('Arial', self.scale_font(14)))
    self.stop_continuous_run_button.setGeometry(*self.scale_geom(10, y_val, self.button_w, self.button_h))
    self.stop_continuous_run_button.setText("Stop experiment")
    self.stop_continuous_run_button.clicked.connect(lambda: button_handlers.handle_stop_continuous_run_button_clicked(self))
    self.stop_continuous_run_button.setToolTip("Stop continuous run button stops whatever experiment was running before. It generates the init_hardware.py according to the latest default edge values and sets the hardware to that state. Again, it does not only stop continuous run, it stops any experiment and can be used to interrupt whatever was running.")
   
    #button to start continuous run
    self.continuous_run_button = QPushButton(tab)
    self.continuous_run_button.setFont(QFont('Arial', self.scale_font(14)))
    self.continuous_run_button.setGeometry(*self.scale_geom(self.button_w + 20, y_val, self.button_w, self.button_h))
    self.continuous_run_button.setText("Continuous run")
    self.continuous_run_button.clicked.connect(lambda: button_handlers.handle_continuous_run_button_clicked(self))
    self.continuous_run_button.setToolTip("Continuous run button generates the experimental sequence description according to the current state of the Quatnrol as a run_experiment.py file and then runs that experimental sequence indefinitely.")
 
    #run experiment
    self.run_experiment_button = QPushButton(tab)
    self.run_experiment_button.setFont(QFont('Arial', self.scale_font(14)))
    self.run_experiment_button.setGeometry(*self.scale_geom(2*self.button_w + 30, y_val, self.button_w, self.button_h))
    self.run_experiment_button.setText("Run experiment")
    self.run_experiment_button.clicked.connect(lambda: button_handlers.handle_run_experiment_button_clicked(self)) 
    self.run_experiment_button.setToolTip("Run experiment button generates the experimental sequence description accodring to the current state of the Quantrol as a run_experiment.py file and then runs that experimental sequence once.")
    
    #go to edge
    self.go_to_edge_button = QPushButton(tab)
    self.go_to_edge_button.setFont(QFont('Arial', self.scale_font(14)))
    self.go_to_edge_button.setGeometry(*self.scale_geom(3*self.button_w + 40, y_val, self.button_w, self.button_h))
    self.go_to_edge_button.setText("Go to Edge")
    self.go_to_edge_button.clicked.connect(lambda: button_handlers.handle_go_to_edge_button_clicked(self))
    self.go_to_edge_button.setToolTip("Go to Edge button is used to set the state of the hardware to a specific state at a particular edge. The user first needs to choose the edge to go by right clicking the sequence table on the left")

    #multiple runs
    self.multiple_runs_button = QPushButton(tab)
    self.multiple_runs_button.setFont(QFont('Arial', self.scale_font(14)))
    self.multiple_runs_button.setGeometry(*self.scale_geom(4*self.button_w + 50, y_val, self.button_w, self.button_h))
    self.multiple_runs_button.setText("Multiple runs")
    self.multiple_runs_button.clicked.connect(lambda: button_handlers.handle_multiple_runs_button_clicked(self))
    self.multiple_runs_button.setToolTip("Multiple runs button generates the experimental sequence description accodring to the current state of the Quantrol as a run_experiment.py file and then runs that experimental sequence multiple times.")

     
    #num of runs for multiple runs
    self.number_of_runs_label = QLabel(tab)
    self.number_of_runs_label.setFont(QFont('Arial', self.scale_font(14)))
    self.number_of_runs_label.setText("Number of runs")
    self.number_of_runs_label.setGeometry(*self.scale_geom(5*self.button_w + 60, y_val, int(0.7*self.button_w), self.button_h))
    self.number_of_runs_input = QLineEdit(tab)
    self.number_of_runs_input.setGeometry(*self.scale_geom(5*self.button_w + 60 + int(0.7*self.button_w), y_val, int(0.3*self.button_w), self.button_h))
    self.number_of_runs_input.setFont(QFont('Arial', self.scale_font(14)))
    self.number_of_runs_input.editingFinished.connect(lambda: change_handlers.handle_number_of_runs_input_changed(self))
    self.number_of_runs_input.setText("10")
    return self.number_of_runs_input


def sequence_tab_buttons_build(self,width_of_table):
    #BUTTONS
    #button to save current sequence
    self.save_sequence_button = QPushButton(self.sequence_tab_widget)
    self.save_sequence_button.setFont(QFont('Arial', self.scale_font(14)))
    self.save_sequence_button.setGeometry(*self.scale_geom(width_of_table + 20, 30, 200, 30))
    self.save_sequence_button.setText("Save sequence")
    self.save_sequence_button.clicked.connect(lambda: button_handlers.handle_save_sequence_button_clicked(self))
    self.save_sequence_button.setToolTip("Save sequence button saves the experimental description to a file. Everything in the user interface will be saved including the title names, states of scanning table, and all tabs. The only difference will be the logger. It will not be saved. If a sequence was saved or loaded, it will overwrite the open sequence file! Therefore, be careful when pressing this button or you risk loosing the previous state of the experiment.")
    
    #button to save current sequence as
    self.save_sequence_as_button = QPushButton(self.sequence_tab_widget)
    self.save_sequence_as_button.setFont(QFont('Arial', self.scale_font(14)))
    self.save_sequence_as_button.setGeometry(*self.scale_geom(width_of_table + 20, 80, 200, 30))
    self.save_sequence_as_button.setText("Save sequence as")
    self.save_sequence_as_button.clicked.connect(lambda: button_handlers.handle_save_sequence_as_button_clicked(self))
    self.save_sequence_as_button.setToolTip("Save sequence as button allows the user to save sequences as a separate files. The currently open file will not be altered.")

    #button to load new sequence
    self.load_sequence_button = QPushButton(self.sequence_tab_widget)
    self.load_sequence_button.setFont(QFont('Arial', self.scale_font(14)))
    self.load_sequence_button.setGeometry(*self.scale_geom(width_of_table + 20, 130, 200, 30))
    self.load_sequence_button.setText("Load sequence")
    self.load_sequence_button.clicked.connect(lambda: button_handlers.handle_load_sequence_button_clicked(self))
    self.load_sequence_button.setToolTip("Load sequence button allows user to load the presaved sequences. It will load the full state of the experimental sequence leaving the logger at the same state as before loading the sequence. Do save your sequences before loading new ones in order to not lose them. The newly loaded sequence file will be linked with the current state of the Quantrol. By pressing the save sequence button the user can overwrite the loaded sequence!")
    #button to insert edge
    self.insert_edge_button = QPushButton(self.sequence_tab_widget)
    self.insert_edge_button.setFont(QFont('Arial', self.scale_font(14)))
    self.insert_edge_button.setGeometry(*self.scale_geom(width_of_table + 20, 200, 200, 30))
    self.insert_edge_button.setText("Insert Edge")
    self.insert_edge_button.clicked.connect(lambda: button_handlers.handle_insert_edge_button_clicked(self))
    self.insert_edge_button.setToolTip("Insert edge button inserts an edge in the edge of the sequence with a blank name and time expression exactly the same as the leading edge. All channels parameters will be not be user entered and therefore will display the previously set states. In other words, their changed parameters will be False meaning that they do not require the update of the hardware states at the newly inserted Edge.")
    #button to delete edge
    self.delete_edge_button = QPushButton(self.sequence_tab_widget)
    self.delete_edge_button.setFont(QFont('Arial', self.scale_font(14)))
    self.delete_edge_button.setGeometry(*self.scale_geom(width_of_table + 20, 250, 200, 30))
    self.delete_edge_button.setText("Delete Edge")
    self.delete_edge_button.clicked.connect(lambda: button_handlers.handle_delete_edge_button_clicked(self))
    self.delete_edge_button.setToolTip("Delete edge button requires the user to choose the edge that needs to be deleted by right clicking it in the Timing Sequence table. It checks if the corresponding ID variable of the edge that needs to be deleted is used anywhere and will not allow deletion in case it is used by showing the first instance it was found to be used at. Otherwise, it deletes the selected edge and updates the Timing Sequence table.")
    
   
    if config.allow_skipping_images:
        #trigger camera 10 times
        self.skip_images_button = QPushButton(self.sequence_tab_widget)
        self.skip_images_button.setFont(QFont('Arial', self.scale_font(14)))
        self.skip_images_button.setGeometry(*self.scale_geom(width_of_table + 20, 310, 200, 30))
        self.skip_images_button.setText("Skip images")
        self.skip_images_button.clicked.connect(lambda: button_handlers.handle_skip_images_button_clicked(self))
        self.skip_images_button.setStyleSheet(""" QPushButton {background-color: green; color: white}  QToolTip {color: black}""") 
        self.skip_images_button.setToolTip("Skip images button allows on demand triggering the camera acquisition 10 times in the beginning of experiment. Button's color represents current state where green indicates that the image triggering should be done, and red, when it should be avoided. Modify the write_to_python.py in order to change the triggering digital channels. The option of removing the button is in the config.py file. If not needed, set the allow_skipping_images to False")
        self.experiment.skip_images = True

    #camera trigger off cam_trigger_off_runs times
    self.cam_trigger_off_button = QPushButton(self.sequence_tab_widget)
    self.cam_trigger_off_button.setFont(QFont('Arial', self.scale_font(14)))
    self.cam_trigger_off_button.setGeometry(*self.scale_geom(width_of_table + 20, 350, 160, 30))
    self.cam_trigger_off_button.setText("Cam. trigger off")
    self.cam_trigger_off_button.clicked.connect(lambda: button_handlers.handle_cam_trigger_off_button_clicked(self))
    self.cam_trigger_off_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""") 
    self.cam_trigger_off_button.setToolTip("Camera trigger off button allows running the experiment without trigering the camera even when the corresponding tab is on. Button's color represents current state where green indicates that the cam triggering should be done, and red, when it should be avoided.")
    self.experiment.cam_trigger_off = False  # off at the beginning
    
    self.cam_trigger_off_input = QLineEdit(self.sequence_tab_widget)
    self.cam_trigger_off_input.setGeometry(*self.scale_geom(width_of_table + 20 + 162, 350, 38, 30))
    self.cam_trigger_off_input.setFont(QFont('Arial', self.scale_font(14)))
    self.cam_trigger_off_input.editingFinished.connect(lambda: change_handlers.handle_cam_trigger_off_input_changed(self))
    self.cam_trigger_off_input.setText("5")

    
    #button to save default
    self.save_default = QPushButton(self.sequence_tab_widget)
    self.save_default.setFont(QFont('Arial', self.scale_font(14)))
    self.save_default.setGeometry(*self.scale_geom(width_of_table + 20, 430, 200, 30))
    self.save_default.setText("Save default")
    self.save_default.clicked.connect(lambda: button_handlers.handle_save_default_button_clicked(self))
    self.save_default.setToolTip("Save default button allows the user to overwrite the default state which includes the Default edge, corresponding digital, analog, and dds channels values, and channels titles. Once the default is being overwritten, next time the program is initialized with the updated default values. However, when the seqeunce is being loaded it will overwrite accodring to the saved sequence definitions.")


    #button to load default
    self.load_default = QPushButton(self.sequence_tab_widget)
    self.load_default.setFont(QFont('Arial', self.scale_font(14)))
    self.load_default.setGeometry(*self.scale_geom(width_of_table + 20, 480, 200, 30))
    self.load_default.setText("Load default")
    self.load_default.clicked.connect(lambda: button_handlers.handle_load_default_button_clicked(self))
    self.load_default.setToolTip("Load default button allows the user to enforce the default state on the Default edge, corresponding digital, analog, and dds channels values, and channels titles. It is useful in case some older sequences are loaded and the user wants to quickly update their default edge and title names to the new default values. For example, if there is a sequence for cooling the atoms where a channel A11 was not used at all. Imagine with time the channel A11 started being used as something, for example MOT coils current voltage control. Then the user can load the old sequence, press Load default button and add whatever description was required for the A11.")

    #button to initialize the hardware
    self.init_hardware = QPushButton(self.sequence_tab_widget)
    self.init_hardware.setFont(QFont('Arial', self.scale_font(14)))
    self.init_hardware.setGeometry(*self.scale_geom(width_of_table + 20, 530, 200, 30))
    self.init_hardware.setText("Init. hardware")
    self.init_hardware.clicked.connect(lambda: button_handlers.handle_init_hardware_button_clicked(self))
    self.init_hardware.setToolTip("Init. hardware button initializes the hardware and sets its state to the default edge values. Check the init_hardware.py file in order to explicitly see what it does. In some cases the user might want to use additional functionality of Artiq that is beyond Quantrol, then the user should modify write_to_python.py go_to_edge function to include the things that require initialization. Same goes to the set_att definitions.")
    
    #button to create the run_experiment.py without running the sequence. An option nice to have in case of troubleshooting
    self.generate_run_experiment_py_button = QPushButton(self.sequence_tab_widget)
    self.generate_run_experiment_py_button.setFont(QFont('Arial', self.scale_font(14)))
    self.generate_run_experiment_py_button.setGeometry(*self.scale_geom(width_of_table + 20, 580, 200, 30))
    self.generate_run_experiment_py_button.setText("Generate experiment")
    self.generate_run_experiment_py_button.clicked.connect(lambda: button_handlers.handle_generate_run_experiment_py_button_clicked(self))
    self.generate_run_experiment_py_button.setToolTip("Generate experiment button is used to generate the python like description of the experimental sequence that is displayed in the Quantrol. It will generate the run_experiment.py file in the same directory of the source_code.py. It is useful for debugging the experimental sequence descriptions without asking to run it. If something does not work first check if you are asking Artiq to do the correct thing by looking at the generated run_experiment.py.")

    #button to submit the run_experiment.py without updating it with the current experimental description. It is useful in case one needs to hard code something in the sequence and wants to just run it
    self.submit_run_experiment_py_button = QPushButton(self.sequence_tab_widget)
    self.submit_run_experiment_py_button.setFont(QFont('Arial', self.scale_font(14)))
    self.submit_run_experiment_py_button.setGeometry(*self.scale_geom(width_of_table + 20, 630, 200, 30))
    self.submit_run_experiment_py_button.setText("Submit experiment")
    self.submit_run_experiment_py_button.clicked.connect(lambda: button_handlers.handle_submit_run_experiment_py_button_clicked(self))
    self.submit_run_experiment_py_button.setToolTip("Submit experiment button runs the current state of the run_experiment.py file without updating it with the experimental description shown in the Quantrol. It is useful when the user wants to make manual changes in the experimental sequence and run the updated run_experiment.py. For example, user can generate a two variable scan and then hardcore it to make a 2D scan with different setp sizes. Such run_experiment.py files should be properly named and saved in a separate folder for future use. Otherwise, the run_experiment.py will be overwritten by the Quantrol.")
    
    #dummy button for troubleshooting 
    self.dummy_button = QPushButton(self.sequence_tab_widget)
    self.dummy_button.setFont(QFont('Arial', self.scale_font(14)))
    self.dummy_button.setGeometry(*self.scale_geom(width_of_table + 20, 680, 200, 30))
    self.dummy_button.setText("Dummy button")
    self.dummy_button.clicked.connect(lambda: button_handlers.handle_dummy_button_clicked(self))
    self.dummy_button.setToolTip("Dummy button is used for the debugging purposes. In the source_code.py there is a dummy_button_clicked fucntion that can be used to print various parameters at different times in order to trace the reason if something is misbehaving. Commented out portions of code are good hints for how the user could use that dummy button for debugging. So in case the debugging is required modify the dummy_button_clicked function in the source_code.py and observe the values of interest in the console of the VS Code.")
    
    #continuous run after experiment
    self.cont_run_after_exp_button = QPushButton(self.sequence_tab_widget)
    self.cont_run_after_exp_button.setFont(QFont('Arial', self.scale_font(14)))
    self.cont_run_after_exp_button.setGeometry(*self.scale_geom(width_of_table + 20, 750, 200, 30))
    self.cont_run_after_exp_button.setText("Cont. run after exp.")
    self.cont_run_after_exp_button.clicked.connect(lambda: button_handlers.handle_cont_run_after_exp_button_clicked(self))
    self.cont_run_after_exp_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""") 
    self.cont_run_after_exp_button.setToolTip("Do automatic continuous run after expriment (run_experiment or multiple_runs). Button's color represents current state where green indicates that cont. run should be done, and red, when it should be avoided.")
    self.experiment.cont_run_after_exp = False  # off at the beginning

# SEQUENCE TAB
def sequence_tab_build(self):
    
    self.sequence_tab_widget = QWidget()
    self.sequence_lable = QLabel(self.sequence_tab_widget)
    self.sequence_lable.setText("Timing Sequence")
    self.sequence_lable.setFont(QFont('Arial', self.scale_font(14)))
    self.sequence_lable.setGeometry(*self.scale_geom(self.sep, 0, 200, self.top_margin))
    self.sequence_lable.setAlignment(Qt.AlignCenter)

    width_of_table = 600
    height_of_table = self.bottom_buttons_y_val - self.top_margin - self.sep
    #file_name label
    self.file_name_lable = QLabel(self.sequence_tab_widget)
    self.file_name_lable.setFont(QFont('Arial', self.scale_font(10)))
    self.file_name_lable.setGeometry(*self.scale_geom(200, 2, width_of_table+800, self.top_margin))

    #SEQUENCE TAB LAYOUT
    self.sequence_table = QTableWidget(self.sequence_tab_widget)
    
    self.sequence_table.setGeometry(QRect(*self.scale_geom(self.sep, self.top_margin, width_of_table, height_of_table)))  #size of the table
    sequence_num_columns = 5
    self.sequence_table.setColumnCount(sequence_num_columns)
    self.sequence_table.setRowCount(1)
    self.sequence_table.setHorizontalHeaderLabels(["#", "Name","ID", "Time expression","Time (ms)"])
    self.sequence_table.verticalHeader().setVisible(False)
    self.sequence_table.horizontalHeader().setMinimumSectionSize(1)
    self.sequence_table.horizontalHeader().setFixedHeight(int(self.SCALE_H*60))
    self.sequence_table.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.sequence_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    

    self.sequence_table.setFont(QFont('Arial', self.scale_font(12)))
    self.sequence_table.setColumnWidth(0,int(self.SCALE_W*30))
    self.sequence_table.setColumnWidth(1,int(self.SCALE_W*220))
    self.sequence_table.setColumnWidth(2,int(self.SCALE_W*40))
    self.sequence_table.setColumnWidth(3,int(self.SCALE_W*210))
    self.sequence_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
    # self.sequence_table.setColumnWidth(4,int(self.SCALE_W*100))
    self.sequence_table.itemChanged.connect(lambda item: change_handlers.handle_sequence_table_changed(self, item))
    delegate = ReadOnlyDelegate(self)
    self.sequence_table.setItemDelegateForRow(0,delegate)
    self.sequence_table.setItemDelegateForColumn(0,delegate)
    self.sequence_table.setItemDelegateForColumn(2,delegate)
    self.sequence_table.setItemDelegateForColumn(4,delegate)
    #Setting the default values 
    self.sequence_table.setItem(0, 0, QTableWidgetItem("0"))
    self.sequence_table.setItem(0, 1, QTableWidgetItem(self.experiment.sequence[0].name))
    self.sequence_table.setItem(0, 2, QTableWidgetItem(self.experiment.sequence[0].id))
    self.sequence_table.setItem(0, 3, QTableWidgetItem(self.experiment.sequence[0].expression))
    self.sequence_table.setItem(0, 4, QTableWidgetItem(str(self.experiment.sequence[0].value)))
    self.sequence_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    

    #TABLE OF SCANNING PARAMETERS
    self.scan_table_parameters = QTableWidget()
    self.scan_table_parameters.setColumnCount(5)
    self.scan_table_parameters.setRowCount(0)
    self.scan_table_parameters.verticalHeader().setVisible(False)
    self.scan_table_parameters.setFont(QFont('Arial', self.scale_font(14)))
    self.scan_table_parameters.setHorizontalHeaderLabels(["Variable","Min value", "Max value", "Steps", "Dim"])
    self.scan_table_parameters.setColumnWidth(0,int(self.SCALE_W*230))
    self.scan_table_parameters.setColumnWidth(1,int(self.SCALE_W*200))
    self.scan_table_parameters.setColumnWidth(2,int(self.SCALE_W*200))
    self.scan_table_parameters.setColumnWidth(3,int(self.SCALE_W*90))
    self.scan_table_parameters.setColumnWidth(4,int(self.SCALE_W*50))
    self.scan_table_parameters.itemChanged.connect(lambda item: change_handlers.handle_scan_table_changed(self, item))
    

    #Add scanned variable button
    self.add_scanned_variable_button = QPushButton()
    self.add_scanned_variable_button.setFont(QFont('Arial', self.scale_font(14)))
    self.add_scanned_variable_button.resize(int(self.SCALE_W*self.button_w), int(self.SCALE_H*self.button_h)) 
    self.add_scanned_variable_button.setText("Add scanned variable")
    self.add_scanned_variable_button.clicked.connect(lambda: button_handlers.handle_add_scanned_variable_button_pressed(self))
    self.add_scanned_variable_button.setToolTip("Add scanned variable button is used to add variables that require scanning. First the user should define the variables in the variblas tab and then add scanned variable and overwrite the name of the variable from None to the name of the variable that needs to be scanned. After that the variable value will be disabled and will display 'scanned'. The value of the scanned variable will be assigned to be the min value in order to allow sorting the time edges.")

    #Delete scanned variable button
    self.delete_scanned_variable_button = QPushButton()
    self.delete_scanned_variable_button.setFont(QFont('Arial', self.scale_font(14)))
    self.delete_scanned_variable_button.setText("Delete scanned variable")
    self.delete_scanned_variable_button.clicked.connect(lambda: button_handlers.handle_delete_scanned_variable_button_pressed(self))
    self.delete_scanned_variable_button.setToolTip("Delete scanned variable button is used to delete variables from the scanning table and hence disable their scans. The user should first right click the variable that needs to be deleted. The Quantrol will set the values of the deleted scanned variables to the values that were defined before the variable was set to scan.")
    

    #warning for the user # look into
    # self.warning_about_scan_range = QLabel(self.sequence_tab_widget)
    # self.warning_about_scan_range.setFont(QFont('Arial', self.scale_font(14)))
    # self.warning_about_scan_range.setGeometry(*self.scale_geom(width_of_table + 300, 330, 800, 30))

    #Horizontal layout
    hBox = QHBoxLayout()
    temp = QWidget()
    hBox.addWidget(self.add_scanned_variable_button)
    hBox.addWidget(self.delete_scanned_variable_button)  
    temp.setLayout(hBox)

    #Scan parameters
    x_val_ramp = 10 + width_of_table + 10 + self.button_w + 10
    w_val_ramp = 1920 - x_val_ramp - 10 - self.variables_table_width - 10

    
    self.scan_table = QGroupBox(self.sequence_tab_widget)
    self.scan_table.setTitle("Scan")
    self.scan_table.setCheckable(True)
    self.scan_table.setChecked(False)
    self.scan_table.setFont(QFont('Arial', self.scale_font(14)))
    self.scan_table.move(int(self.SCALE_W*x_val_ramp), int(self.SCALE_H*30))
    self.scan_table.setFixedSize(int(self.SCALE_W*w_val_ramp), int(self.SCALE_H*290))
    self.scan_table.toggled.connect(lambda: other_handlers.handle_scan_table_checked(self))
    vBox = QVBoxLayout()
    self.scan_table.setLayout(vBox)
    vBox.addWidget(temp)
    vBox.addWidget(self.scan_table_parameters)
    self.scan_table.setToolTip("This Scan checkbox is used to enable or disable the variables scan. In case of the scan was unchecked the state of the table will be disabled but the previously set parameters of the scan will remain in place. This allows the user to quickly scan and not scan variables on demand. In order to change the parameters of the scan the user should check the Scan checkbox first. Disables scanning table looks a little faded.")

    #TABLE OF RAMPING PARAMETERS
    self.ramp_table_parameters = QTableWidget()
    self.ramp_table_parameters.setColumnCount(5)
    self.ramp_table_parameters.setRowCount(0)
    self.ramp_table_parameters.verticalHeader().setVisible(False)
    self.ramp_table_parameters.setFont(QFont('Arial', self.scale_font(14)))
    self.ramp_table_parameters.setHorizontalHeaderLabels(["Variable","Start ID", "End ID","Function (use i)", "i"])
    self.ramp_table_parameters.setColumnWidth(0,int(self.SCALE_W*150))
    self.ramp_table_parameters.setColumnWidth(1,int(self.SCALE_W*80))
    self.ramp_table_parameters.setColumnWidth(2,int(self.SCALE_W*80))
    # self.ramp_table_parameters.setColumnWidth(3,int(self.SCALE_W*400))
    self.ramp_table_parameters.setColumnWidth(4,int(self.SCALE_W*50))
    self.ramp_table_parameters.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
    self.ramp_table_parameters.itemChanged.connect(lambda item: change_handlers.handle_ramp_table_changed(self, item))
    
    #Add ramped variable button
    self.add_ramped_variable_button = QPushButton()
    self.add_ramped_variable_button.setFont(QFont('Arial', self.scale_font(14)))
    self.add_ramped_variable_button.setFixedSize(int(self.SCALE_W*self.button_w), int(self.SCALE_H*self.button_h))
    self.add_ramped_variable_button.setText("Add ramped variable")
    self.add_ramped_variable_button.clicked.connect(lambda: button_handlers.handle_add_ramped_variable_button_pressed(self))
    self.add_ramped_variable_button.setToolTip("Ramped variables...")

    #Delete ramped variable button
    self.delete_ramped_variable_button = QPushButton()
    self.delete_ramped_variable_button.setFont(QFont('Arial', self.scale_font(14)))
    self.delete_ramped_variable_button.setFixedSize(int(self.SCALE_W*self.button_w), int(self.SCALE_H*self.button_h))
    self.delete_ramped_variable_button.setText("Delete ramped variable")
    self.delete_ramped_variable_button.clicked.connect(lambda: button_handlers.handle_delete_ramped_variable_button_pressed(self))
    self.delete_ramped_variable_button.setToolTip("Delete ramped variable button ...")

    #Explain ramped ID
    self.add_ramped_variable_label = QLabel("End ID edge right after Start ID edge!", self)
    self.add_ramped_variable_label.setFont(QFont('Arial', self.scale_font(14)))
    self.add_ramped_variable_label.setToolTip("The egde of end_ID has to be right after the edge of start_ID. This is indicated by the pink coloring in the sequence tab.")
    
    #Horizontal layout
    hBox = QHBoxLayout()
    temp = QWidget()  
    hBox.addWidget(self.add_ramped_variable_label)  
    hBox.addWidget(self.add_ramped_variable_button)
    hBox.addWidget(self.delete_ramped_variable_button)      
    temp.setLayout(hBox)

    #Ramp parameters
    self.ramp_table = QGroupBox(self.sequence_tab_widget)
    self.ramp_table.setTitle("Ramp")
    self.ramp_table.setCheckable(True)
    self.ramp_table.setChecked(False)
    self.ramp_table.setFont(QFont('Arial', self.scale_font(14)))
    self.ramp_table.move(int(self.SCALE_W*x_val_ramp), int(self.SCALE_H*320))
    self.ramp_table.setFixedSize(int(self.SCALE_W*w_val_ramp), int(self.SCALE_H*546))
    self.ramp_table.toggled.connect(lambda: other_handlers.handle_ramp_table_checked(self))
    vBox = QVBoxLayout()
    self.ramp_table.setLayout(vBox)
    vBox.addWidget(temp)
    vBox.addWidget(self.ramp_table_parameters)
    self.ramp_table.setToolTip("This ramp checkbox is used to enable or disable the variables ramp. ")



    #show logger of the program
    logger_width = 1920 - 10 - 10 - width_of_table - 10 - self.variables_table_width - 10
    self.logger = QPlainTextEdit(self.sequence_tab_widget)
    self.logger.setFont(QFont('Arial', self.scale_font(12)))
    self.logger.setGeometry(*self.scale_geom(width_of_table + 20, 870, logger_width, 210))
    self.logger.setReadOnly(True)
    self.logger.appendPlainText("Welcome to the %s lab! Hope you enjoy your stay here :)" %config.research_group_name)
    self.logger.appendPlainText("Don't forget to initialize the hardware after the power cycle!!!")
    self.logger.appendPlainText("")
    self.logger.appendPlainText(datetime.now().strftime("%D %H:%M:%S - ") + "Program initialized")
    
    #clear logger button
    
    self.clear_logger_button = QPushButton(self.sequence_tab_widget)
    self.clear_logger_button.setFont(QFont('Arial', self.scale_font(14)))
    self.clear_logger_button.setGeometry(*self.scale_geom(10 + width_of_table + 10, 820, self.button_w, self.button_h))
    self.clear_logger_button.setText("Clear logger")
    self.clear_logger_button.clicked.connect(lambda: button_handlers.handle_clear_logger_button_clicked(self))

    self.number_of_runs_input_sequence = bottom_buttons_build(self,self.sequence_tab_widget)
    self.variables_table_sequence, self.delete_variable_sequence = variables_sidebar_build(self,self.sequence_tab_widget)
    sequence_tab_buttons_build(self,width_of_table)


# DIGITAL TAB
def digital_tab_build(self):
    self.digital_tab_num_cols = config.digital_channels_number + 4    
    self.digital_and_analog_table_column_width = 130
    #DIGITAL TAB WIDGET
    self.digital_tab_widget = QWidget()
    digital_lable = QLabel(self.digital_tab_widget)
    digital_lable.setText("Digital channels")
    digital_lable.setFont(QFont('Arial', self.scale_font(14)))
    digital_lable.setGeometry(*self.scale_geom(85, 0, 400, 30))
    
    #DIGITAL TAB LAYOUT
    digital_table_w = 1920 - 2*self.sep - self.variables_table_width - self.sep
    digital_table_h = self.bottom_buttons_y_val - self.top_margin - self.sep
    self.digital_table = QTableWidget(self.digital_tab_widget)
    self.digital_table.setGeometry(QRect(*self.scale_geom(self.sep, self.top_margin, digital_table_w, digital_table_h)))  
    self.digital_table.setColumnCount(self.digital_tab_num_cols)
    self.digital_table.setRowCount(1) 
    self.digital_table.setHorizontalHeaderLabels(self.experiment.title_digital_tab)
    self.digital_table.verticalHeader().setVisible(False)
    self.digital_table.horizontalHeader().setFixedHeight(int(self.SCALE_H*60))
    self.digital_table.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.digital_table.setFont(QFont('Arial', self.scale_font(12)))
    self.digital_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.digital_table.horizontalHeader().setMinimumSectionSize(0)
    self.digital_table.setColumnWidth(0,int(self.SCALE_W*(50)))
    self.digital_table.setColumnWidth(1,int(self.SCALE_W*(180)))
    self.digital_table.setColumnWidth(2,int(self.SCALE_W*(100)))
    self.digital_table.setColumnWidth(3,int(self.SCALE_W*(5)))
    self.digital_table.setFrameStyle(QFrame.NoFrame)
    delegate = ReadOnlyDelegate(self)
    for _ in range(4):
        exec("self.digital_table.setItemDelegateForColumn(%d,delegate)" %_)
    #self.digital_table.setItemDelegateForRow(0, delegate)
    for i in range(4, self.digital_tab_num_cols):
        exec("self.digital_table.setColumnWidth(%d,int(self.SCALE_W*(%d)))" % (i, self.digital_and_analog_table_column_width))

    for row_index in range(self.digital_table.rowCount()):
        separator_item = self.digital_table.item(row_index, 3)
        if separator_item is None:
            separator_item = QTableWidgetItem()
            self.digital_table.setItem(row_index, 3, separator_item)
        separator_item.setFlags(Qt.NoItemFlags)
        separator_item.setBackground(self.grey)

    header_separator_item = self.digital_table.horizontalHeaderItem(3)
    if header_separator_item is None:
        header_separator_item = QTableWidgetItem()
        self.digital_table.setHorizontalHeaderItem(3, header_separator_item)
    header_separator_item.setText("")
    header_separator_item.setBackground(self.grey)
    header_separator_item.setData(Qt.ForegroundRole, self.grey)

    self.digital_header_column_separator = _create_header_column_overlay(
        self,
        self.digital_tab_widget,
        self.digital_table,
        3,
    )
    
    
    #Filling the DIGITAL table
    for index, channel in enumerate(self.experiment.sequence[0].digital):
        col = index + 4
        self.digital_table.setItem(0, col, QTableWidgetItem(channel.expression))
        if channel.value == 1:
            self.digital_table.item(0, col).setBackground(self.green)
        else:
            self.digital_table.item(0, col).setBackground(self.red)
    
    #Binding functions
    self.digital_table.itemChanged.connect(lambda item: change_handlers.handle_digital_table_changed(self, item))
    self.digital_table.horizontalHeader().sectionClicked.connect(self.digital_table_header_clicked)



    #Dummy table that will display edge number, name and time and will be fixed
    self.digital_dummy = QTableWidget(self.digital_tab_widget)
    self.digital_dummy.setGeometry(QRect(*self.scale_geom(10, 30, 330, 1050)))
    self.digital_dummy.setColumnCount(3)
    self.digital_dummy.setRowCount(1)
    self.digital_dummy.setHorizontalHeaderLabels(self.experiment.title_digital_tab[0:3])
    self.digital_dummy.verticalHeader().setVisible(False)
    self.digital_dummy.horizontalHeader().setFixedHeight(int(self.SCALE_H*60))
    self.digital_dummy.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.digital_dummy.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.digital_dummy.setFont(QFont('Arial', self.scale_font(12)))
    self.digital_dummy.setColumnWidth(0,int(self.SCALE_W*(50)))
    self.digital_dummy.setColumnWidth(1,int(self.SCALE_W*(180)))
    self.digital_dummy.setColumnWidth(2,int(self.SCALE_W*(100)))
    self.digital_dummy.setFrameStyle(QFrame.NoFrame)
    
    #Setting the left part of the DIGITAL table (edge number, name, time)
    self.digital_dummy.setItem(0, 0, QTableWidgetItem("0"))
    self.digital_dummy.setItem(0, 1, QTableWidgetItem(self.experiment.sequence[0].name))
    self.digital_dummy.setItem(0, 2, QTableWidgetItem(str(self.experiment.sequence[0].value)))
    delegate = ReadOnlyDelegate(self)
    for _ in range(3):
        exec("self.digital_dummy.setItemDelegateForColumn(%d,delegate)" %_)
        
    self.digital_dummy.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.digital_dummy.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    separator_height = max(2, int(round(self.SCALE_H)))
    digital_table_geom = self.digital_table.geometry()
    digital_header_height = self.digital_table.horizontalHeader().height()
    digital_sep_y = digital_table_geom.y() + digital_header_height - separator_height // 2
    self.digital_header_separator_right = _create_header_separator(
        self,
        self.digital_tab_widget,
        digital_table_geom.x(),
        digital_sep_y,
        digital_table_geom.width(),
    )

    digital_dummy_geom = self.digital_dummy.geometry()
    digital_dummy_header_height = self.digital_dummy.horizontalHeader().height()
    digital_dummy_sep_y = digital_dummy_geom.y() + digital_dummy_header_height - separator_height // 2
    self.digital_header_separator_left = _create_header_separator(
        self,
        self.digital_tab_widget,
        digital_dummy_geom.x(),
        digital_dummy_sep_y,
        digital_dummy_geom.width(),
    )

    self.number_of_runs_input_digital = bottom_buttons_build(self,self.digital_tab_widget)
    self.variables_table_digital, self.delete_variable_digital = variables_sidebar_build(self,self.digital_tab_widget)

# ANALOG TAB
def analog_tab_build(self):
    self.analog_tab_num_cols = config.analog_channels_number + 4    
    #ANALOG TAB WIDGET
    self.analog_tab_widget = QWidget()
    #ANALOG LABLE
    analog_lable = QLabel(self.analog_tab_widget)
    analog_lable.setText("Analog channels")
    analog_lable.setFont(QFont('Arial', self.scale_font(14)))
    analog_lable.setGeometry(*self.scale_geom(85, 0, 400, 30))


    #ANALOG TAB LAYOUT
    analog_table_w = 1920 - 2*self.sep - self.variables_table_width - self.sep
    analog_table_h = self.bottom_buttons_y_val - self.top_margin - self.sep
    self.analog_table = QTableWidget(self.analog_tab_widget)
    self.analog_table.setGeometry(QRect(*self.scale_geom(self.sep, self.top_margin, analog_table_w, analog_table_h)))  
    self.analog_table.setColumnCount(self.analog_tab_num_cols) 
    self.analog_table.setRowCount(1)
    self.analog_table.setHorizontalHeaderLabels(self.experiment.title_analog_tab)
    self.analog_table.verticalHeader().setVisible(False)
    self.analog_table.horizontalHeader().setFixedHeight(int(self.SCALE_H*60))
    self.analog_table.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.analog_table.setFont(QFont('Arial', self.scale_font(12)))
    self.analog_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.analog_table.horizontalHeader().setMinimumSectionSize(0)
    self.analog_table.setColumnWidth(0,int(self.SCALE_W*(50)))
    self.analog_table.setColumnWidth(1,int(self.SCALE_W*(180)))
    self.analog_table.setColumnWidth(2,int(self.SCALE_W*(100)))
    self.analog_table.setColumnWidth(3,int(self.SCALE_W*(5)))
    self.analog_table.setFrameStyle(QFrame.NoFrame)
    delegate = ReadOnlyDelegate(self)
    for _ in range(4):
        exec("self.analog_table.setItemDelegateForColumn(%d,delegate)" %_)
    #self.analog_table.setItemDelegateForRow(0,delegate)
    for i in range(4, self.analog_tab_num_cols):
        exec("self.analog_table.setColumnWidth(%d,int(self.SCALE_W*(%d)))" % (i,self.digital_and_analog_table_column_width))

    for row_index in range(self.analog_table.rowCount()):
        separator_item = self.analog_table.item(row_index, 3)
        if separator_item is None:
            separator_item = QTableWidgetItem()
            self.analog_table.setItem(row_index, 3, separator_item)
        separator_item.setFlags(Qt.NoItemFlags)
        separator_item.setBackground(self.grey)

    analog_header_separator_item = self.analog_table.horizontalHeaderItem(3)
    if analog_header_separator_item is None:
        analog_header_separator_item = QTableWidgetItem()
        self.analog_table.setHorizontalHeaderItem(3, analog_header_separator_item)
    analog_header_separator_item.setText("")
    analog_header_separator_item.setBackground(self.grey)
    analog_header_separator_item.setData(Qt.ForegroundRole, self.grey)

    self.analog_header_column_separator = _create_header_column_overlay(
        self,
        self.analog_tab_widget,
        self.analog_table,
        3,
    )
    #Filling the default values
    for index, channel in enumerate(self.experiment.sequence[0].analog):
        # plus 3 is because first 3 columns are used by number, name and time of edge
        col = index + 4
        self.analog_table.setItem(0, col, QTableWidgetItem(channel.expression))
        self.analog_table.item(0, col).setToolTip(str(channel.value))
        if channel.value != 0:
            self.analog_table.item(0, col).setBackground(self.green)
        else:
            self.analog_table.item(0, col).setBackground(self.red)
    
    self.analog_table.itemChanged.connect(lambda item: change_handlers.handle_analog_table_changed(self, item))
    self.analog_table.horizontalHeader().sectionClicked.connect(self.analog_table_header_clicked)

    #Dummy table that will display edge number, name and time and will be fixed
    self.analog_dummy = QTableWidget(self.analog_tab_widget)
    self.analog_dummy.setGeometry(QRect(*self.scale_geom(10, 30, 330, 1050)))
    self.analog_dummy.setColumnCount(3)
    self.analog_dummy.setRowCount(1)
    self.analog_dummy.setHorizontalHeaderLabels(self.experiment.title_analog_tab[0:3])
    self.analog_dummy.verticalHeader().setVisible(False)
    self.analog_dummy.horizontalHeader().setFixedHeight(int(self.SCALE_H*60))
    self.analog_dummy.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.analog_dummy.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.analog_dummy.setFont(QFont('Arial', self.scale_font(12)))
    self.analog_dummy.setColumnWidth(0,int(self.SCALE_W*(50)))
    self.analog_dummy.setColumnWidth(1,int(self.SCALE_W*(180)))
    self.analog_dummy.setColumnWidth(2,int(self.SCALE_W*(100)))
    self.analog_dummy.setFrameStyle(QFrame.NoFrame)
    #Setting the left part of the analog table
    self.analog_dummy.setItem(0, 0, QTableWidgetItem("0"))
    self.analog_dummy.setItem(0, 1, QTableWidgetItem(self.experiment.sequence[0].name))
    self.analog_dummy.setItem(0, 2, QTableWidgetItem(str(self.experiment.sequence[0].value)))    

    delegate = ReadOnlyDelegate(self)
    for _ in range(3):
        exec("self.analog_dummy.setItemDelegateForColumn(%d,delegate)" %_)

    self.analog_dummy.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.analog_dummy.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    separator_height = max(2, int(round(self.SCALE_H)))
    analog_table_geom = self.analog_table.geometry()
    analog_header_height = self.analog_table.horizontalHeader().height()
    analog_sep_y = analog_table_geom.y() + analog_header_height - separator_height // 2
    self.analog_header_separator_right = _create_header_separator(
        self,
        self.analog_tab_widget,
        analog_table_geom.x(),
        analog_sep_y,
        analog_table_geom.width(),
    )

    analog_dummy_geom = self.analog_dummy.geometry()
    analog_dummy_header_height = self.analog_dummy.horizontalHeader().height()
    analog_dummy_sep_y = analog_dummy_geom.y() + analog_dummy_header_height - separator_height // 2
    self.analog_header_separator_left = _create_header_separator(
        self,
        self.analog_tab_widget,
        analog_dummy_geom.x(),
        analog_dummy_sep_y,
        analog_dummy_geom.width(),
    )

    self.number_of_runs_input_analog = bottom_buttons_build(self,self.analog_tab_widget)
    self.variables_table_analog, self.delete_variable_analog = variables_sidebar_build(self,self.analog_tab_widget)

# DDS TAB
def dds_tab_build(self):
    self.dds_tab_num_cols = 6*config.dds_channels_number
    #DDS TABLE WIDGET
    self.dds_tab_widget = QWidget()
    
    dds_table_w = 1920 - 2*self.sep - self.variables_table_width - self.sep
    dds_table_h = self.bottom_buttons_y_val - self.top_margin - self.sep
    dds_header_h = 90
    dds_side_w = 335
    
    #DDS LABLE
    dds_lable = QLabel(self.dds_tab_widget)
    dds_lable.setText("DDS channels")
    dds_lable.setFont(QFont('Arial', self.scale_font(14)))
    dds_lable.setGeometry(*self.scale_geom(self.sep, 0, dds_side_w, self.top_margin))
    dds_lable.setAlignment(Qt.AlignCenter)
    self.sequence_num_rows = len(self.experiment.sequence)

    #DDS TAB LAYOUT, main table with actual numbers (bottom right)
    self.dds_table = QTableWidget(self.dds_tab_widget)

    self.dds_table.setGeometry(QRect(*self.scale_geom(self.sep + dds_side_w,self.top_margin + dds_header_h, dds_table_w - dds_side_w, dds_table_h - dds_header_h)))
    self.dds_table.setColumnCount(self.dds_tab_num_cols)

    self.dds_table.verticalHeader().setVisible(False)
    self.dds_table.horizontalHeader().setVisible(False)
    self.dds_table.setRowCount(self.sequence_num_rows)
    self.dds_table.horizontalHeader().setMinimumSectionSize(0)
    self.dds_table.setFont(QFont('Arial', self.scale_font(12)))
    self.dds_table.setFrameStyle(QFrame.NoFrame)
    

    delegate = ReadOnlyDelegate(self)
    #SHAPING THE TABLE
    for i in range(config.dds_channels_number):
        # self.dds_table.setSpan(0,1 + 6*i, 1, 5) # stretching the title of the channel
        for row_index in range(self.dds_table.rowCount()):
            separator_item = self.dds_table.item(row_index, 6*i + 0)
            if separator_item is None:
                separator_item = QTableWidgetItem()
                self.dds_table.setItem(row_index, 6*i + 0, separator_item)
            separator_item.setFlags(Qt.NoItemFlags)
            separator_item.setBackground(self.grey)
        self.dds_table.horizontalHeader().setMinimumSectionSize(0)

        self.dds_table.setColumnWidth(0 + 6*i,int(self.SCALE_W*(5))) # making separation line thin
        self.dds_table.setColumnWidth(1 + 6*i,int(self.SCALE_W*(99))) 
        self.dds_table.setColumnWidth(2 + 6*i,int(self.SCALE_W*(99))) 
        self.dds_table.setColumnWidth(3 + 6*i,int(self.SCALE_W*(99))) 
        self.dds_table.setColumnWidth(4 + 6*i,int(self.SCALE_W*(99))) 
        self.dds_table.setColumnWidth(5 + 6*i,int(self.SCALE_W*(44))) # making state column smaller
        self.dds_table.setItemDelegateForColumn(0 + 6*i,delegate) #making separation line uneditable
    

    #Filling the default values of DDS table
    for index, channel in enumerate(self.experiment.sequence[0].dds):
        #plus 4 is because first 4 columns are used by number, name, time and separator(dark grey line)
        col = 1 + index * 6  
        for setting in range(5):
            exec("self.dds_table.setItem(0, col + setting, QTableWidgetItem(str(channel.%s.expression)))" %self.setting_dict[setting])
            exec("self.dds_table.item(0, col + setting).setToolTip(str(channel.%s.value))" %self.setting_dict[setting])
            if channel.state.value == 1:
                self.dds_table.item(0, col + setting).setBackground(self.green)
            else:  
                self.dds_table.item(0, col + setting).setBackground(self.red)


    self.dds_table.itemChanged.connect(lambda item: change_handlers.handle_dds_table_changed(self, item))
    

    #Dummy table that will display edge number, name and time and will be fixed (LEFT SIDE OF THE TABLE)

    #table with times, names of edges and numbers of edges (bottom left)

    self.dds_seq = QTableWidget(self.dds_tab_widget)
    self.dds_seq.setGeometry(QRect(*self.scale_geom(self.sep,self.top_margin + dds_header_h,dds_side_w,dds_table_h - dds_header_h)))
    self.dds_seq.setColumnCount(3)
    self.dds_seq.setRowCount(self.sequence_num_rows)
    self.dds_seq.verticalHeader().setVisible(False)
    self.dds_seq.horizontalHeader().setVisible(False)
    self.dds_seq.horizontalHeader().setMinimumSectionSize(0)
    self.dds_seq.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.dds_seq.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.dds_seq.setFont(QFont('Arial', self.scale_font(12)))
    self.dds_seq.setColumnWidth(0, int(self.SCALE_W * 50))
    self.dds_seq.setColumnWidth(1, int(self.SCALE_W * 180))
    self.dds_seq.setColumnWidth(2, int(self.SCALE_W * 100))
    self.dds_seq.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    self.dds_seq.setFrameStyle(QFrame.NoFrame)

    #making first three columns vertically wider to fit with header 
    for i in range(4):
        self.dds_seq.setItemDelegateForColumn(i,delegate)

    #Filling the left part of the DDS table
    self.dds_seq.setItem(0, 0, QTableWidgetItem("0"))
    self.dds_seq.setItem(0, 1, QTableWidgetItem(self.experiment.sequence[0].name))
    self.dds_seq.setItem(0, 2, QTableWidgetItem(str(self.experiment.sequence[0].value)))


    #Dummy horizontal header (TOP SIDE OF THE TABLE)

    #table header for actual numbers (top right)

    self.dds_table_header = QTableWidget(self.dds_tab_widget)
    self.dds_table_header.setGeometry(QRect(*self.scale_geom(self.sep + dds_side_w, self.top_margin, dds_table_w - dds_side_w, dds_header_h)))
    self.dds_table_header.setColumnCount(self.dds_tab_num_cols)
    self.dds_table_header.setRowCount(2) 

    self.dds_table_header.setRowHeight(0,int(self.SCALE_H*(dds_header_h/2)))
    self.dds_table_header.setRowHeight(1,int(self.SCALE_H*(dds_header_h/2)))
    self.dds_table_header.verticalHeader().setVisible(False)
    self.dds_table_header.horizontalHeader().setVisible(False)
    self.dds_table_header.horizontalHeader().setMinimumSectionSize(0)
    self.dds_table_header.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.dds_table_header.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

    self.dds_table_header.setFont(QFont('Arial', self.scale_font(12)))
    self.dds_table_header.setFrameStyle(QFrame.NoFrame)


    self.dds_table_header.cellClicked.connect(self.dds_table_header_clicked)
    
    #SHAPING THE TABLE
    for i in range(config.dds_channels_number):
        self.dds_table_header.setSpan(0,1 + 6*i, 1, 5) # stretching the title of the channel
        self.dds_table_header.setColumnWidth(0 + 6*i,int(self.SCALE_W*(5))) # making separation line thin
        self.dds_table_header.setColumnWidth(1 + 6*i,int(self.SCALE_W*(99))) 
        self.dds_table_header.setColumnWidth(2 + 6*i,int(self.SCALE_W*(99))) 
        self.dds_table_header.setColumnWidth(3 + 6*i,int(self.SCALE_W*(99))) 
        self.dds_table_header.setColumnWidth(4 + 6*i,int(self.SCALE_W*(99))) 
        self.dds_table_header.setColumnWidth(5 + 6*i,int(self.SCALE_W*(44))) # making state column smaller
        # self.dds_table_header.horizontalHeader().setSectionResizeMode(5 + 6*i, QHeaderView.Stretch)
        self.dds_table_header.setItemDelegateForColumn(0 + 6*i,delegate) #making separation line uneditable

    self.dds_table_header.setItemDelegateForRow(1, delegate) #making row number 2 uneditable

    #populating headers and separators
    dds_titles = getattr(self.experiment, "title_dds_tab", [])
    for i in range(config.dds_channels_number):
        #separator
        self.dds_table_header.setSpan(0, 6*i + 0, 2, 1)
        separator_header_item = self.dds_table_header.item(0, 6*i + 0)
        if separator_header_item is None:
            separator_header_item = QTableWidgetItem()
            self.dds_table_header.setItem(0, 6*i + 0, separator_header_item)
        separator_header_item.setFlags(Qt.NoItemFlags)
        separator_header_item.setBackground(self.grey)
        #headers Channel
        title_index = i + 4
        title_text = str(dds_titles[title_index]) if title_index < len(dds_titles) else f"DDS{i}"
        self.dds_table_header.setItem(0,6*i+1, QTableWidgetItem(title_text))
        self.dds_table_header.item(0,6*i+1).setTextAlignment(Qt.AlignCenter)
        #headers Channel attributes (f, Amp, att, phase, state)
        self.dds_table_header.setItem(1,6*i+1, QTableWidgetItem('f (MHz)'))
        self.dds_table_header.setItem(1,6*i+2, QTableWidgetItem('Amp (%)'))
        self.dds_table_header.setItem(1,6*i+3, QTableWidgetItem('Att (dB)'))
        self.dds_table_header.setItem(1,6*i+4, QTableWidgetItem('phase (deg)'))
        self.dds_table_header.setItem(1,6*i+5, QTableWidgetItem('state'))

    # self.dds_table_header.itemChanged.connect(self.dds_table_header_changed)

    #Making fixed corner (TOP LEFT SIDE OF THE TABLE)

    self.dds_seq_header = QTableWidget(self.dds_tab_widget)
    self.dds_seq_header.setGeometry(QRect(*self.scale_geom(self.sep, self.top_margin, dds_side_w, dds_header_h)))
    self.dds_seq_header.setColumnCount(3)
    self.dds_seq_header.verticalHeader().setVisible(False)
    self.dds_seq_header.horizontalHeader().setVisible(False)
    self.dds_seq_header.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.dds_seq_header.horizontalHeader().setMinimumSectionSize(0)
    self.dds_seq_header.verticalHeader().setMinimumSectionSize(0)
    self.dds_seq_header.setRowCount(1) 
    self.dds_seq_header.setFont(QFont('Arial', self.scale_font(12)))
    self.dds_seq_header.setFrameStyle(QFrame.NoFrame)
    
    #SHAPING THE FIRST 3 COLUMNS
    self.dds_seq_header.setColumnWidth(0, int(self.SCALE_W * 50))
    self.dds_seq_header.setColumnWidth(1, int(self.SCALE_W * 180))
    self.dds_seq_header.setColumnWidth(2, int(self.SCALE_W * 100))
    self.dds_seq_header.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    self.dds_seq_header.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    self.dds_seq_header.setRowHeight(0, int(self.SCALE_H * (dds_header_h)))
    for i in range(3):
        self.dds_seq_header.setItemDelegateForColumn(i,delegate)
    
    #Separator
    # self.dds_seq_header.setItem(0,3, QTableWidgetItem())
    # self.dds_seq_header.item(0,3).setBackground(self.grey)
    # populating edge number, name and time  @ title_dds_tab
    for i in range(3):
        title_text = str(dds_titles[i]) if i < len(dds_titles) else ("#" if i == 0 else "" )
        self.dds_seq_header.setItem(0,i, QTableWidgetItem(title_text))
        self.dds_seq_header.item(0,i).setTextAlignment(Qt.AlignCenter)

    # # Always use fixed labels for the first three columns
    # fixed_labels = ["#", "NameTest", "Time (ms)"]
    # for i in range(3):
    #     item = QTableWidgetItem(fixed_labels[i])
    #     item.setTextAlignment(Qt.AlignCenter)
    #     self.dds_seq_header.setItem(0, i, item)

    #MAKING VERTICAL SCROLL BARS COMMON FOR DDS TABLE
    self.dds_tables = [self.dds_table,self.dds_seq,self.analog_table,self.analog_dummy, self.digital_table, self.digital_dummy, self.sequence_table]

    def move_other_scrollbars_vertical(idx,bar):
        scrollbars = {tbl.verticalScrollBar() for tbl in self.dds_tables}
        scrollbars.remove(bar)
        for bar in scrollbars:
            bar.setValue(idx)
        
    self.dds_seq.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.dds_seq.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    self.dds_seq_header.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
    self.dds_seq_header.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    
    for tbl in self.dds_tables:
        scrollbar = tbl.verticalScrollBar()
        scrollbar.valueChanged.connect(lambda idx,bar=scrollbar: move_other_scrollbars_vertical(idx, bar))

    #MAKING HORIZONTAL SCROLL BARS COMMON FOR DDS TABLE
    self.dds_seq_tables = [self.dds_table,self.dds_table_header]

    def move_other_scrollbars_horizontal(idx,bar):
        scrollbars = {tbl.horizontalScrollBar() for tbl in self.dds_seq_tables}
        scrollbars.remove(bar)
        for bar in scrollbars:
            bar.setValue(idx)
    
    self.dds_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) 
    self.dds_table_header.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) 
    self.dds_table_header.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    for tbl in self.dds_seq_tables:
        scrollbar = tbl.horizontalScrollBar()
        scrollbar.valueChanged.connect(lambda idx,bar=scrollbar: move_other_scrollbars_horizontal(idx, bar))

    separator_height = max(2, int(round(self.SCALE_H)))

    dds_left_geom = self.dds_seq.geometry()
    dds_left_sep_y = dds_left_geom.y() - separator_height // 2
    self.dds_header_separator_left = _create_header_separator(
        self,
        self.dds_tab_widget,
        dds_left_geom.x(),
        dds_left_sep_y,
        dds_left_geom.width(),
    )

    dds_right_geom = self.dds_table.geometry()
    dds_right_sep_y = dds_right_geom.y() - separator_height // 2
    self.dds_header_separator_right = _create_header_separator(
        self,
        self.dds_tab_widget,
        dds_right_geom.x(),
        dds_right_sep_y,
        dds_right_geom.width(),
    )

    self.number_of_runs_input_dds = bottom_buttons_build(self,self.dds_tab_widget)
    self.variables_table_dds, self.delete_variable_dds = variables_sidebar_build(self,self.dds_tab_widget)

#VARIABLES TAB
def variables_tab_build(self):
    
    derived_variables_table_w = 2*self.sep + 3*self.button_w + int(self.SCALE_W * 250) #increase width to have more space for function
    lookup_variables_table_w = 2*self.sep + 3*self.button_w
    derived_variables_table_h = self.bottom_buttons_y_val - self.top_margin - 2*self.sep - self.button_h

    self.variables_tab_widget = QWidget()
    
    #DERIVED VARIABLES LABLE
    derived_variables_lable = QLabel(self.variables_tab_widget)
    derived_variables_lable.setText("Derived variables")
    derived_variables_lable.setFont(QFont('Arial', self.scale_font(14)))
    derived_variables_lable.setGeometry(*self.scale_geom(self.sep, 0, derived_variables_table_w, self.button_h))
    derived_variables_lable.setAlignment(Qt.AlignCenter)

    #DERIVED VARIABLES TABLE LAYOUT
    self.derived_variables_table = QTableWidget(self.variables_tab_widget)
    
    self.derived_variables_table.setGeometry(QRect(*self.scale_geom(self.sep, self.top_margin, derived_variables_table_w, derived_variables_table_h)))  #size of the table
    derived_variables_num_columns = 5
    self.derived_variables_table.setColumnCount(derived_variables_num_columns)
    self.derived_variables_table.setHorizontalHeaderLabels(["Name", "Arguments", "Edge id","Function in python syntax", "Initial value"])
    self.derived_variables_table.verticalHeader().setVisible(False)
    self.derived_variables_table.horizontalHeader().setFixedHeight(int(self.SCALE_H*50))
    self.derived_variables_table.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.derived_variables_table.setFont(QFont('Arial', self.scale_font(12)))
    self.derived_variables_table.setColumnWidth(0,int(self.SCALE_W*(120)))
    self.derived_variables_table.setColumnWidth(1,int(self.SCALE_W*(90)))
    self.derived_variables_table.setColumnWidth(2,int(self.SCALE_W*(70)))
    # self.derived_variables_table.setColumnWidth(3,int(self.SCALE_W*(310)))
    self.derived_variables_table.setColumnWidth(4,int(self.SCALE_W*(88)))
    self.derived_variables_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
    self.derived_variables_table.setRowCount(1)
    prototypeItem = QTableWidgetItem()
    prototypeItem.setTextAlignment(Qt.AlignCenter)
    self.derived_variables_table.setItemPrototype(prototypeItem)
    #Disabling the first example row
    delegate = ReadOnlyDelegate(self)
    self.derived_variables_table.setItemDelegateForRow(0,delegate)
    self.derived_variables_table.setItem(0, 0, QTableWidgetItem("example_name"))
    self.derived_variables_table.item(0,0).setToolTip("Name of the derived variable")
    self.derived_variables_table.setItem(0, 1, QTableWidgetItem("x,y"))
    self.derived_variables_table.item(0,1).setToolTip("Comma separated arguments of the function to be used to derive the variable")
    self.derived_variables_table.setItem(0, 2, QTableWidgetItem("id5"))
    self.derived_variables_table.item(0,2).setToolTip("ID of the edge when user wants to request the calculation of the derived variable")
    self.derived_variables_table.setItem(0, 3, QTableWidgetItem("np.sin(x) + 5*np.sqrt(y)"))
    self.derived_variables_table.item(0,1).setToolTip("Function to be used to derive the variable. It should be python compatible with the numpy being imported as np")
    self.derived_variables_table.setItem(0, 4, QTableWidgetItem("228.32"))
    self.derived_variables_table.item(0,1).setToolTip("Initial value for dyanmic variables...")
    #when table contents are changed
    self.derived_variables_table.itemChanged.connect(lambda item: change_handlers.handle_derived_variables_table_changed(self, item))

    #button to create new derived variable
    self.create_derived_variable = QPushButton(self.variables_tab_widget)
    self.create_derived_variable.setFont(QFont('Arial', self.scale_font(14)))
    self.create_derived_variable.setGeometry(*self.scale_geom(self.sep, self.top_margin + derived_variables_table_h + self.sep, self.button_w, self.button_h))
    self.create_derived_variable.setText("Create derived var")
    self.create_derived_variable.setToolTip("Button that is used to create a new derived variable. Please input arguments and edge id before using the variable")
    self.create_derived_variable.clicked.connect(lambda: button_handlers.handle_create_derived_variable_button_clicked(self))
    #button to delete a variable
    self.delete_derived_variable = QPushButton(self.variables_tab_widget)
    self.delete_derived_variable.setFont(QFont('Arial', self.scale_font(14)))
    self.delete_derived_variable.setGeometry(*self.scale_geom(2*self.sep + self.button_w, self.top_margin + derived_variables_table_h + self.sep, self.button_w, self.button_h))
    self.delete_derived_variable.setText("Delete derived var")
    self.delete_derived_variable.setToolTip("Button that is used to delete a derived variable. First choose the derived variable by right clicking it in the derived variables table.")
    self.delete_derived_variable.clicked.connect(lambda: button_handlers.handle_delete_derived_variable_button_clicked(self))

    #LOOKUP VARIABLES LABLE
    lookup_variables_lable = QLabel(self.variables_tab_widget)
    lookup_variables_lable.setText("Lookup variables")
    lookup_variables_lable.setFont(QFont('Arial', self.scale_font(14)))
    lookup_variables_lable.setGeometry(*self.scale_geom(2*self.sep + derived_variables_table_w, 0, lookup_variables_table_w, self.button_h))
    lookup_variables_lable.setAlignment(Qt.AlignCenter)

    #LOOKUP VARIABLES TABLE LAYOUT
    self.lookup_variables_table = QTableWidget(self.variables_tab_widget)
    
    self.lookup_variables_table.setGeometry(QRect(*self.scale_geom(2*self.sep + derived_variables_table_w, self.top_margin, lookup_variables_table_w, derived_variables_table_h)))  #size of the table
    lookup_variables_num_columns = 3
    self.lookup_variables_table.setColumnCount(lookup_variables_num_columns)
    self.lookup_variables_table.setHorizontalHeaderLabels(["Name", "Argument", "Lookup list name"])
    self.lookup_variables_table.verticalHeader().setVisible(False)
    self.lookup_variables_table.horizontalHeader().setFixedHeight(int(self.SCALE_H*50))
    self.lookup_variables_table.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.lookup_variables_table.setFont(QFont('Arial', self.scale_font(12)))
    self.lookup_variables_table.setColumnWidth(0,int(self.SCALE_W*(180)))
    self.lookup_variables_table.setColumnWidth(1,int(self.SCALE_W*(150)))
    # self.lookup_variables_table.setColumnWidth(2,int(self.SCALE_W*(413)))
    self.lookup_variables_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
    self.lookup_variables_table.setRowCount(1)
    prototypeItem = QTableWidgetItem()
    prototypeItem.setTextAlignment(Qt.AlignCenter)
    self.lookup_variables_table.setItemPrototype(prototypeItem)
    #Disabling the first example row
    delegate = ReadOnlyDelegate(self)
    self.lookup_variables_table.setItemDelegateForRow(0,delegate)
    self.lookup_variables_table.setItemDelegateForColumn(2,delegate)
    self.lookup_variables_table.setItem(0, 0, QTableWidgetItem("example_name"))
    self.lookup_variables_table.item(0,0).setToolTip("Name of the lookup variable")
    self.lookup_variables_table.setItem(0, 1, QTableWidgetItem("sampled_var"))
    self.lookup_variables_table.item(0,1).setToolTip("Name of the sampled variable that is going to be used as an argument for the lookup list")
    self.lookup_variables_table.setItem(0, 2, QTableWidgetItem("gaussian_fit"))
    self.lookup_variables_table.item(0,0).setToolTip("Name of the lookup list to remind the user the purpose of the lookup variable")
    #when table contents are changed
    self.lookup_variables_table.itemChanged.connect(lambda item: change_handlers.handle_lookup_variables_table_changed(self, item))

    #button to create new lookup variable
    self.create_lookup_variable = QPushButton(self.variables_tab_widget)
    self.create_lookup_variable.setFont(QFont('Arial', self.scale_font(14)))
    self.create_lookup_variable.setGeometry(*self.scale_geom(2*self.sep + derived_variables_table_w, self.top_margin + derived_variables_table_h + self.sep, self.button_w, self.button_h))
    self.create_lookup_variable.setText("Create lookup var")
    self.create_lookup_variable.setToolTip("Button that is used to create a new lookup variable. Please input the arguments before using the variable")
    self.create_lookup_variable.clicked.connect(lambda: button_handlers.handle_create_lookup_variable_button_clicked(self))
    #button to delete a variable
    self.delete_lookup_variable = QPushButton(self.variables_tab_widget)
    self.delete_lookup_variable.setFont(QFont('Arial', self.scale_font(14)))
    self.delete_lookup_variable.setGeometry(*self.scale_geom(3*self.sep + derived_variables_table_w + self.button_w, self.top_margin + derived_variables_table_h + self.sep, self.button_w, self.button_h))
    self.delete_lookup_variable.setText("Delete lookup var")
    self.delete_lookup_variable.setToolTip("Button that is used to delete a lookup variable. First choose the lookup variable by right clikcing it in the lookup variables table.")
    self.delete_lookup_variable.clicked.connect(lambda: button_handlers.handle_delete_lookup_variable_button_clicked(self))
    #button to load the lookup table
    self.load_lookup_list = QPushButton(self.variables_tab_widget)
    self.load_lookup_list.setFont(QFont('Arial', self.scale_font(14)))
    self.load_lookup_list.setGeometry(*self.scale_geom(4*self.sep + derived_variables_table_w + 2*self.button_w, self.top_margin + derived_variables_table_h + self.sep, self.button_w, self.button_h))
    self.load_lookup_list.setText("Load lookup list")
    self.load_lookup_list.setToolTip("Button is used to load the lookup list for the variable. First choose the lookup variable by right clicking it in the lookup variables table. After that navigate and open the lookup variable list. It should be of the .mat format.")
    self.load_lookup_list.clicked.connect(lambda: button_handlers.handle_load_lookup_list_button_clicked(self))

    self.number_of_runs_input_variables = bottom_buttons_build(self,self.variables_tab_widget)
    self.variables_table_variables, self.delete_variable_variables = variables_sidebar_build(self,self.variables_tab_widget)
        
# SAMPLER TAB
def sampler_tab_build(self):
    sampler_table_w = 1920 - 2*self.sep - self.variables_table_width - self.sep
    sampler_table_h = self.bottom_buttons_y_val - self.top_margin - self.sep
    sampler_side_w = 320
    sampler_header_h = 90
    self.sampler_tab_num_cols = config.sampler_channels_number + 4    
    self.sampler_table_column_width = int((sampler_table_w - sampler_side_w)/config.sampler_channels_number)-1
    #SAMPLER TAB WIDGET
    self.sampler_tab_widget = QWidget()
    sampler_lable = QLabel(self.sampler_tab_widget)
    sampler_lable.setText("Sampler channels")
    sampler_lable.setFont(QFont('Arial', self.scale_font(14)))
    sampler_lable.setGeometry(*self.scale_geom(85, 0, 400, 30))
    
    #SAMPLER TAB LAYOUT
    self.sampler_table = QTableWidget(self.sampler_tab_widget)
    self.sampler_table.setGeometry(QRect(*self.scale_geom(self.sep, self.top_margin, sampler_table_w, sampler_table_h)))  
    self.sampler_table.setColumnCount(self.sampler_tab_num_cols)
    self.sampler_table.setRowCount(1) 
    self.sampler_table.setHorizontalHeaderLabels(self.experiment.title_sampler_tab)
    self.sampler_table.verticalHeader().setVisible(False)
    self.sampler_table.horizontalHeader().setFixedHeight(int(self.SCALE_H*sampler_header_h))
    self.sampler_table.horizontalHeader().setFont(QFont('Arial', self.scale_font(12)))
    self.sampler_table.setFont(QFont('Arial', self.scale_font(12)))
    self.sampler_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.sampler_table.horizontalHeader().setMinimumSectionSize(0)
    self.sampler_table.setColumnWidth(0,int(self.SCALE_W*(40)))
    self.sampler_table.setColumnWidth(1,int(self.SCALE_W*(180)))
    self.sampler_table.setColumnWidth(2,int(self.SCALE_W*(100)))
    self.sampler_table.setColumnWidth(3,int(self.SCALE_W*(5)))
    self.sampler_table.setFrameStyle(QFrame.NoFrame)
    for i in range(4, self.sampler_tab_num_cols):
        exec("self.sampler_table.setColumnWidth(%d,int(self.SCALE_W*(%d)))" % (i, self.sampler_table_column_width))

    for row_index in range(self.sampler_table.rowCount()):
        separator_item = self.sampler_table.item(row_index, 3)
        if separator_item is None:
            separator_item = QTableWidgetItem()
            self.sampler_table.setItem(row_index, 3, separator_item)
        separator_item.setFlags(Qt.NoItemFlags)
        separator_item.setBackground(self.grey)

    sampler_header_separator_item = self.sampler_table.horizontalHeaderItem(3)
    if sampler_header_separator_item is None:
        sampler_header_separator_item = QTableWidgetItem()
        self.sampler_table.setHorizontalHeaderItem(3, sampler_header_separator_item)
    sampler_header_separator_item.setText("")
    sampler_header_separator_item.setBackground(self.grey)
    sampler_header_separator_item.setData(Qt.ForegroundRole, self.grey)

    self.sampler_header_column_separator = _create_header_column_overlay(
        self,
        self.sampler_tab_widget,
        self.sampler_table,
        3,
    )

    for index, channel in enumerate(self.experiment.sequence[0].sampler):
        col = index + 4
        self.sampler_table.setItem(0, col, QTableWidgetItem(str(channel)))
        if channel != "0":
            self.sampler_table.item(0, col).setBackground(self.green)
        else:
            self.sampler_table.item(0, col).setBackground(self.white)
    #Binding functions
    self.sampler_table.itemChanged.connect(lambda item: change_handlers.handle_sampler_table_changed(self, item))
    self.sampler_table.horizontalHeader().sectionClicked.connect(self.sampler_table_header_clicked)

    #Setting the left part of the SAMPLER table (edge number, name, time)
    self.sampler_table.setItem(0, 0, QTableWidgetItem("0"))
    self.sampler_table.setItem(0, 1, QTableWidgetItem(self.experiment.sequence[0].name))
    self.sampler_table.setItem(0, 2, QTableWidgetItem(str(self.experiment.sequence[0].value)))
    delegate = ReadOnlyDelegate(self)
    for _ in range(3):
        exec("self.sampler_table.setItemDelegateForColumn(%d,delegate)" %_)

    separator_height = max(2, int(round(self.SCALE_H)))
    sampler_geom = self.sampler_table.geometry()
    sampler_header_height = self.sampler_table.horizontalHeader().height()
    sampler_sep_y = sampler_geom.y() + sampler_header_height - separator_height // 2
    self.sampler_header_separator = _create_header_separator(
        self,
        self.sampler_tab_widget,
        sampler_geom.x(),
        sampler_sep_y,
        sampler_geom.width(),
    )

    
    self.number_of_runs_input_sampler = bottom_buttons_build(self,self.sampler_tab_widget)
    self.variables_table_sampler, self.delete_variable_sampler = variables_sidebar_build(self,self.sampler_tab_widget)

# MIRNY TAB
def mirny_tab_build(self):
    self.mirny_tab_widget = QWidget()

    mirny_table_w = 1920 - 2*self.sep - self.variables_table_width - self.sep
    mirny_table_h = self.bottom_buttons_y_val - self.top_margin - self.sep
    mirny_header_h = 90
    mirny_side_w = 335

    mirny_label = QLabel(self.mirny_tab_widget)
    mirny_label.setText("Mirny channels")
    mirny_label.setFont(QFont('Arial', self.scale_font(14)))
    mirny_label.setGeometry(*self.scale_geom(self.sep, 0, mirny_side_w, self.top_margin))
    mirny_label.setAlignment(Qt.AlignCenter)

    self.sequence_num_rows = len(self.experiment.sequence)

    self.mirny_tab_num_cols = 6 * config.mirny_channels_number

    self.mirny_table = QTableWidget(self.mirny_tab_widget)
    self.mirny_table.setGeometry(QRect(*self.scale_geom(
        self.sep + mirny_side_w,
        self.top_margin + mirny_header_h,
        mirny_table_w - mirny_side_w,
        mirny_table_h - mirny_header_h)))
    self.mirny_table.setColumnCount(self.mirny_tab_num_cols)
    self.mirny_table.setRowCount(self.sequence_num_rows)
    self.mirny_table.verticalHeader().setVisible(False)
    self.mirny_table.horizontalHeader().setVisible(False)
    self.mirny_table.horizontalHeader().setMinimumSectionSize(0)
    self.mirny_table.setFont(QFont('Arial', self.scale_font(12)))
    self.mirny_table.setFrameStyle(QFrame.NoFrame)

    delegate = ReadOnlyDelegate(self)
    for i in range(config.mirny_channels_number):
        base_col = 6 * i
        self.mirny_table.setColumnWidth(base_col, int(self.SCALE_W * 5))
        self.mirny_table.setColumnWidth(base_col + 1, int(self.SCALE_W * 99))
        self.mirny_table.setColumnWidth(base_col + 2, int(self.SCALE_W * 99))
        self.mirny_table.setColumnWidth(base_col + 3, int(self.SCALE_W * 99))
        self.mirny_table.setColumnWidth(base_col + 4, int(self.SCALE_W * 99))
        self.mirny_table.setColumnWidth(base_col + 5, int(self.SCALE_W * 44))
        self.mirny_table.setItemDelegateForColumn(base_col, delegate)
        for row_index in range(self.sequence_num_rows):
            separator_item = self.mirny_table.item(row_index, base_col)
            if separator_item is None:
                separator_item = QTableWidgetItem()
                self.mirny_table.setItem(row_index, base_col, separator_item)
            separator_item.setFlags(Qt.NoItemFlags)
            separator_item.setBackground(self.grey)

    for row_index, edge in enumerate(self.experiment.sequence):
        for channel_index, channel in enumerate(edge.mirny):
            col = channel_index * 6 + 1
            for setting in range(5):
                attr = self.setting_dict[setting]
                item = QTableWidgetItem(str(getattr(channel, attr).expression))
                self.mirny_table.setItem(row_index, col + setting, item)
                self.mirny_table.item(row_index, col + setting).setToolTip(str(getattr(channel, attr).value))
                if channel.state.value == 1:
                    self.mirny_table.item(row_index, col + setting).setBackground(self.green)
                else:
                    self.mirny_table.item(row_index, col + setting).setBackground(self.red)

    self.mirny_table.itemChanged.connect(lambda item: change_handlers.handle_mirny_table_changed(self, item))

    self.mirny_dummy = QTableWidget(self.mirny_tab_widget)
    self.mirny_dummy.setGeometry(QRect(*self.scale_geom(
        self.sep,
        self.top_margin + mirny_header_h,
        mirny_side_w,
        mirny_table_h - mirny_header_h)))
    self.mirny_dummy.setColumnCount(3)
    self.mirny_dummy.setRowCount(self.sequence_num_rows)
    self.mirny_dummy.verticalHeader().setVisible(False)
    self.mirny_dummy.horizontalHeader().setVisible(False)
    self.mirny_dummy.horizontalHeader().setMinimumSectionSize(0)
    self.mirny_dummy.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.mirny_dummy.setFont(QFont('Arial', self.scale_font(12)))
    self.mirny_dummy.setColumnWidth(0, int(self.SCALE_W * 50))
    self.mirny_dummy.setColumnWidth(1, int(self.SCALE_W * 180))
    self.mirny_dummy.setColumnWidth(2, int(self.SCALE_W * 100))
    self.mirny_dummy.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    self.mirny_dummy.setFrameStyle(QFrame.NoFrame)
    for col in range(3):
        self.mirny_dummy.setItemDelegateForColumn(col, delegate)
    for row_index, edge in enumerate(self.experiment.sequence):
        self.mirny_dummy.setItem(row_index, 0, QTableWidgetItem(str(row_index)))
        self.mirny_dummy.setItem(row_index, 1, QTableWidgetItem(edge.name))
        self.mirny_dummy.setItem(row_index, 2, QTableWidgetItem(str(edge.value)))

    self.mirny_dummy_header = QTableWidget(self.mirny_tab_widget)
    self.mirny_dummy_header.setGeometry(QRect(*self.scale_geom(
        self.sep + mirny_side_w,
        self.top_margin,
        mirny_table_w - mirny_side_w,
        mirny_header_h)))
    self.mirny_dummy_header.setColumnCount(self.mirny_tab_num_cols)
    self.mirny_dummy_header.setRowCount(2)
    self.mirny_dummy_header.verticalHeader().setVisible(False)
    self.mirny_dummy_header.horizontalHeader().setVisible(False)
    self.mirny_dummy_header.horizontalHeader().setMinimumSectionSize(0)
    self.mirny_dummy_header.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.mirny_dummy_header.setFont(QFont('Arial', self.scale_font(12)))
    self.mirny_dummy_header.setFrameStyle(QFrame.NoFrame)
    self.mirny_dummy_header.setRowHeight(0, int(self.SCALE_H * (mirny_header_h / 2)))
    self.mirny_dummy_header.setRowHeight(1, int(self.SCALE_H * (mirny_header_h / 2)))

    mirny_titles = getattr(self.experiment, "title_mirny_tab", [])
    for i in range(config.mirny_channels_number):
        base_col = 6 * i
        self.mirny_dummy_header.setSpan(0, base_col, 2, 1)
        sep_item = QTableWidgetItem()
        sep_item.setFlags(Qt.NoItemFlags)
        sep_item.setBackground(self.grey)
        self.mirny_dummy_header.setItem(0, base_col, sep_item)
        title_index = i + 4
        title_text = str(mirny_titles[title_index]) if title_index < len(mirny_titles) else f"M{i}"
        self.mirny_dummy_header.setSpan(0, base_col + 1, 1, 5)
        title_item = QTableWidgetItem(title_text)
        title_item.setTextAlignment(Qt.AlignCenter)
        self.mirny_dummy_header.setItem(0, base_col + 1, title_item)
        labels = ['f (MHz)', 'Amp (dBm)', 'Att (dB)', 'phase (deg)', 'state']
        for offset, label in enumerate(labels):
            attr_item = QTableWidgetItem(label)
            attr_item.setTextAlignment(Qt.AlignCenter)
            self.mirny_dummy_header.setItem(1, base_col + 1 + offset, attr_item)
        self.mirny_dummy_header.setColumnWidth(base_col, int(self.SCALE_W * 5))
        self.mirny_dummy_header.setColumnWidth(base_col + 1, int(self.SCALE_W * 99))
        self.mirny_dummy_header.setColumnWidth(base_col + 2, int(self.SCALE_W * 99))
        self.mirny_dummy_header.setColumnWidth(base_col + 3, int(self.SCALE_W * 99))
        self.mirny_dummy_header.setColumnWidth(base_col + 4, int(self.SCALE_W * 99))
        self.mirny_dummy_header.setColumnWidth(base_col + 5, int(self.SCALE_W * 44))
        self.mirny_dummy_header.setItemDelegateForColumn(base_col, delegate)

    self.mirny_dummy_header.setItemDelegateForRow(1, delegate)
    self.mirny_dummy_header.itemChanged.connect(lambda item: change_handlers.handle_mirny_dummy_header_changed(self, item))

    self.mirny_fixed = QTableWidget(self.mirny_tab_widget)
    self.mirny_fixed.setGeometry(QRect(*self.scale_geom(self.sep, self.top_margin, mirny_side_w, mirny_header_h)))
    self.mirny_fixed.setColumnCount(3)
    self.mirny_fixed.setRowCount(1)
    self.mirny_fixed.verticalHeader().setVisible(False)
    self.mirny_fixed.horizontalHeader().setVisible(False)
    self.mirny_fixed.horizontalHeader().setMinimumSectionSize(0)
    self.mirny_fixed.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.mirny_fixed.setFont(QFont('Arial', self.scale_font(12)))
    self.mirny_fixed.setFrameStyle(QFrame.NoFrame)
    self.mirny_fixed.setColumnWidth(0, int(self.SCALE_W * 50))
    self.mirny_fixed.setColumnWidth(1, int(self.SCALE_W * 180))
    self.mirny_fixed.setColumnWidth(2, int(self.SCALE_W * 100))
    self.mirny_fixed.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    self.mirny_fixed.setRowHeight(0, int(self.SCALE_H * mirny_header_h))
    for col in range(3):
        self.mirny_fixed.setItemDelegateForColumn(col, delegate)
        header_text = ""
        if col < len(mirny_titles):
            header_text = str(mirny_titles[col])
        elif col == 0:
            header_text = "#"
        elif col == 1:
            header_text = "Name"
        elif col == 2:
            header_text = "Time (ms)"
        item = QTableWidgetItem(header_text)
        item.setTextAlignment(Qt.AlignCenter)
        self.mirny_fixed.setItem(0, col, item)

    self.mirny_tables = [self.mirny_table, self.mirny_dummy, self.analog_table, self.analog_dummy, self.digital_table, self.digital_dummy, self.sequence_table]

    def move_other_scrollbars_vertical(idx, bar):
        scrollbars = {tbl.verticalScrollBar() for tbl in self.mirny_tables}
        scrollbars.discard(bar)
        for other in scrollbars:
            other.setValue(idx)

    self.mirny_dummy.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.mirny_dummy.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.mirny_fixed.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.mirny_fixed.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    for tbl in self.mirny_tables:
        scrollbar = tbl.verticalScrollBar()
        scrollbar.valueChanged.connect(lambda idx, bar=scrollbar: move_other_scrollbars_vertical(idx, bar))

    self.mirny_dummy_tables = [self.mirny_table, self.mirny_dummy_header]

    def move_other_scrollbars_horizontal(idx, bar):
        scrollbars = {tbl.horizontalScrollBar() for tbl in self.mirny_dummy_tables}
        scrollbars.discard(bar)
        for other in scrollbars:
            other.setValue(idx)

    self.mirny_dummy_header.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.mirny_dummy_header.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    for tbl in self.mirny_dummy_tables:
        scrollbar = tbl.horizontalScrollBar()
        scrollbar.valueChanged.connect(lambda idx, bar=scrollbar: move_other_scrollbars_horizontal(idx, bar))

    separator_height = max(2, int(round(self.SCALE_H)))

    mirny_left_geom = self.mirny_dummy.geometry()
    mirny_left_sep_y = mirny_left_geom.y() - separator_height // 2
    self.mirny_header_separator_left = _create_header_separator(
        self,
        self.mirny_tab_widget,
        mirny_left_geom.x(),
        mirny_left_sep_y,
        mirny_left_geom.width(),
    )

    mirny_right_geom = self.mirny_table.geometry()
    mirny_right_sep_y = mirny_right_geom.y() - separator_height // 2
    self.mirny_header_separator_right = _create_header_separator(
        self,
        self.mirny_tab_widget,
        mirny_right_geom.x(),
        mirny_right_sep_y,
        mirny_right_geom.width(),
    )

    self.number_of_runs_input_mirny = bottom_buttons_build(self, self.mirny_tab_widget)
    self.variables_table_mirny, self.delete_variable_mirny = variables_sidebar_build(self, self.mirny_tab_widget)

# SLOW DDS TAB
def slow_dds_tab_build(self):
    self.slow_dds_tab_num_cols = 6*config.slow_dds_channels_number
    #SLOW_DDS TABLE WIDGET
    self.slow_dds_tab_widget = QWidget()
    #SLOW_DDS LABLE
    slow_dds_lable = QLabel(self.slow_dds_tab_widget)
    slow_dds_lable.setText("Slow_dds channels")
    slow_dds_lable.setFont(QFont('Arial', self.scale_font(14)))
    slow_dds_lable.setGeometry(*self.scale_geom(85, 0, 400, 30))
    self.sequence_num_rows = len(self.experiment.sequence)
    
    #SLOW_DDS TAB LAYOUT
    self.slow_dds_table = QTableWidget(self.slow_dds_tab_widget)
    self.slow_dds_table.setGeometry(QRect(*self.scale_geom(10, 30, 1905, 1020)))
    self.slow_dds_table.setColumnCount(self.slow_dds_tab_num_cols)
    self.slow_dds_table.horizontalHeader().setMinimumHeight(int(self.SCALE_H*50))
    self.slow_dds_table.verticalHeader().setVisible(False)
    self.slow_dds_table.horizontalHeader().setVisible(False)
    self.slow_dds_table.setRowCount(3) 
    self.slow_dds_table.horizontalHeader().setMinimumSectionSize(0)
    self.slow_dds_table.setFont(QFont('Arial', self.scale_font(12)))
    self.slow_dds_table.setFrameStyle(QFrame.NoFrame)

    delegate = ReadOnlyDelegate(self)
    #SHAPING THE TABLE
    for i in range(config.slow_dds_channels_number):
        self.slow_dds_table.setSpan(0,1 + 6*i, 1, 5) # stretching the title of the channel
        self.slow_dds_table.setColumnWidth(6*i,int(self.SCALE_W*( 5))) # making separation line thin
        self.slow_dds_table.setColumnWidth(5 + 6*i,int(self.SCALE_W*( 45))) # making state column smaller
        self.slow_dds_table.setItemDelegateForColumn(6*i,delegate) #making separation line uneditable
    
    for index, channel in enumerate(self.experiment.slow_dds):
        col = index * 6 + 1 # there is a separator in the very beginning
        for setting in range(5):
            exec("self.slow_dds_table.setItem(2, col + setting, QTableWidgetItem(str(channel.%s)))" %self.setting_dict[setting])
            exec("self.slow_dds_table.item(2, col + setting).setToolTip(str(channel.%s))" %self.setting_dict[setting])
            if channel.state == 1:
                self.slow_dds_table.item(2, col + setting).setBackground(self.green)
            else:  
                self.slow_dds_table.item(2, col + setting).setBackground(self.red)
                
    self.slow_dds_table.setItemDelegateForRow(1, delegate) #making row number 2 uneditable
    self.slow_dds_table.itemChanged.connect(lambda item: change_handlers.handle_slow_dds_table_changed(self, item))

    #populating headers and separators
    slow_titles = getattr(self.experiment, "title_slow_dds_tab", [])
    for i in range(config.slow_dds_channels_number):
        #separator
        self.slow_dds_table.setSpan(0, 6*i, self.sequence_num_rows+2, 1)
        self.slow_dds_table.setItem(0, 6*i, QTableWidgetItem())
        self.slow_dds_table.item(0, 6*i).setBackground(self.grey)
        #headers Channel
        title_index = i + 4
        title_text = str(slow_titles[title_index]) if title_index < len(slow_titles) else f"slow DDS{i}"
        self.slow_dds_table.setItem(0,6*i + 1, QTableWidgetItem(title_text))
        self.slow_dds_table.item(0,6*i + 1).setTextAlignment(Qt.AlignCenter)
        #headers Channel attributes (f, Amp, att, phase, state)
        self.slow_dds_table.setItem(1,6*i + 1, QTableWidgetItem('f (MHz)'))
        self.slow_dds_table.setItem(1,6*i + 2, QTableWidgetItem('Amp (dBm)'))
        self.slow_dds_table.setItem(1,6*i + 3, QTableWidgetItem('Att (dB)'))
        self.slow_dds_table.setItem(1,6*i + 4, QTableWidgetItem('phase (deg)'))
        self.slow_dds_table.setItem(1,6*i + 5, QTableWidgetItem('state'))

    separator_height = max(2, int(round(self.SCALE_H)))
    slow_dds_geom = self.slow_dds_table.geometry()
    slow_header_height = self.slow_dds_table.rowHeight(0) + self.slow_dds_table.rowHeight(1)
    slow_sep_y = slow_dds_geom.y() + slow_header_height - separator_height // 2
    self.slow_dds_header_separator = _create_header_separator(
        self,
        self.slow_dds_tab_widget,
        slow_dds_geom.x(),
        slow_sep_y,
        slow_dds_geom.width(),
    )

    #button to set slow dds states
    self.set_slow_dds_states = QPushButton(self.slow_dds_tab_widget)
    self.set_slow_dds_states.setFont(QFont('Arial', self.scale_font(14)))
    self.set_slow_dds_states.setGeometry(*self.scale_geom(10, 1200-40-60-5, 200, 30))
    self.set_slow_dds_states.setText("Set slow DDS states")
    self.set_slow_dds_states.clicked.connect(lambda: button_handlers.handle_set_slow_dds_states_button_clicked(self))
    self.set_slow_dds_states.setToolTip("Set slow dds states button is used to prepare the experimental description and run it to set the states of only the slow dds channels. Any experiment that has been running at the time of pressing this button will be interrupted and might leave the experiment in a random state that might be not safe. It is a user responsibility to make sure that this button is clicked only when there is no experiment running. This should be fine since this DDSs should be used permanently and only changed quite rarely.")

    self.number_of_runs_input_slow_dds = bottom_buttons_build(self,self.slow_dds_tab_widget)
    self.variables_table_slow_dds, self.delete_variable_slow_dds = variables_sidebar_build(self,self.slow_dds_tab_widget)

# ACQUISITION TAB
def acquisition_tab_build(self):
    self.acquisition_tab_widget = QWidget()

    #exposure time
    #gain
    #format
    #path to save
    #experiment list
    #main camera
    self.experiment_list_box = QWidget(self.acquisition_tab_widget)
    self.experiment_list_box.setGeometry(*self.scale_geom(self.sep,
                                                      self.top_margin,
                                                    #   1.5*self.button_w + self.sep,
                                                      self.button_w,
                                                      self.bottom_buttons_y_val - self.top_margin - self.sep))
    self.experiment_list_box_layout = QVBoxLayout(self.experiment_list_box)
    self.experiment_list_box_layout.setContentsMargins(0, 0, 0, 0)


    # Top: chosen element line
    self.experiment_list_chosen_label = QLabel(parent = self.acquisition_tab_widget, text = "Choose experiment")
    self.experiment_list_chosen_label.setFont(QFont('Arial', self.scale_font(14)))
    self.experiment_list_chosen_label.setAlignment(Qt.AlignCenter)
    self.experiment_list_chosen_label.setGeometry(*self.scale_geom(self.sep,
                                                                0,
                                                                #   1.5*self.button_w + self.sep,
                                                                self.button_w,
                                                                self.top_margin))


    self.experiment_list_chosen_line = QLineEdit(self.experiment_list_box)
    self.experiment_list_chosen_line.setReadOnly(True)
    self.experiment_list_chosen_line.setToolTip("Experiment name")
    self.experiment_list_chosen_line.setFont(QFont('Arial', self.scale_font(12)))

    self.experiment_list_chosen_line_caption = QLineEdit(self.experiment_list_box)
    self.experiment_list_chosen_line_caption.setToolTip("Experiment caption")
    self.experiment_list_chosen_line_caption.editingFinished.connect(lambda : self.update_experiment_names_list(caption = self.experiment_list_chosen_line_caption.text(),last = False))
    self.experiment_list_chosen_line_caption.setFont(QFont('Arial', self.scale_font(12)))

    # Center: list of items
    self.experiment_list_list_widget = QListWidget(self.experiment_list_box)
    self.experiment_list_list_widget.setSelectionMode(QListWidget.SingleSelection)
    self.experiment_list_list_widget.setFont(QFont('Arial', self.scale_font(12)))
    self.experiment_list_list_widget.itemSelectionChanged.connect(lambda: change_handlers.handle_chosen_experiment_changed(self))
    
    with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json") as f:
        experiment_names_dict = json.load(f)
        
    for key in list(experiment_names_dict.keys()):
        name = experiment_names_dict[key]["name"]
        self.experiment_list_list_widget.addItem(name)

    # Bottom: add-new line and buttons
    # self.experiment_list_new_label = QLabel(parent = self.experiment_list_box, text = "Add new element")

    # self.experiment_list_new_line = QLineEdit(self.experiment_list_box)
    # self.experiment_list_new_line.setPlaceholderText("Type new element and press Enter or click Add")


    # self.new_line.returnPressed.connect(self.add_element)

    self.experiment_list_btn_add = QPushButton(parent = self.experiment_list_box, text = "Add experiment name")
    self.experiment_list_btn_add.setFixedHeight(int(self.SCALE_H*self.button_h))
    self.experiment_list_btn_add.setFont(QFont('Arial', self.scale_font(14)))
    self.experiment_list_btn_add.clicked.connect(lambda: button_handlers.handle_add_element_experiment_list_button_clicked(self))

    self.experiment_list_btn_delete = QPushButton(parent = self.experiment_list_box, text = "Delete experiment name")
    self.experiment_list_btn_delete.setFixedHeight(int(self.SCALE_H*self.button_h))
    self.experiment_list_btn_delete.setFont(QFont('Arial', self.scale_font(14)))
    self.experiment_list_btn_delete.setEnabled(False)

    self.experiment_list_btn_delete.clicked.connect(lambda: button_handlers.handle_delete_element_experiment_list_button_clicked(self))

    # self.experiment_list_bottom_row = QHBoxLayout()
    # self.bottom_row.addWidget(self.new_line)
    # self.experiment_list_bottom_row.addWidget(self.experiment_list_btn_add)
    # self.experiment_list_bottom_row.addWidget(self.experiment_list_btn_delete)

    # self.experiment_list_box_layout.addWidget(self.experiment_list_chosen_label)
    self.experiment_list_box_layout.addWidget(self.experiment_list_chosen_line)
    self.experiment_list_box_layout.addWidget(self.experiment_list_chosen_line_caption)
    self.experiment_list_box_layout.addWidget(self.experiment_list_list_widget)
    self.experiment_list_box_layout.addWidget(self.experiment_list_btn_add)
    self.experiment_list_box_layout.addWidget(self.experiment_list_btn_delete)
    # self.experiment_list_box_layout.addLayout(self.experiment_list_bottom_row)
    
    # self.experiment_list_box_layout.addWidget()

    self.camera_box = QGroupBox(self.acquisition_tab_widget)
    self.camera_box.setTitle("Camera")
    self.camera_box.setCheckable(True)
    self.camera_box.setChecked(False)
    self.camera_box.setFont(QFont('Arial', self.scale_font(14)))
    self.camera_box.move(int(self.SCALE_W*(self.button_w + 2*self.sep)), int(self.SCALE_H*self.top_margin))
    self.camera_box.setFixedSize(int(self.SCALE_W*(2*self.button_w + self.sep)), int(self.SCALE_H*(300)))
    
    # self.camera_box.toggled.connect(self.camera_box_checked)
    form = QFormLayout(self.camera_box)

    self.live_cameras_box = QGroupBox(self.acquisition_tab_widget)
    self.live_cameras_box.setTitle("Live cameras")
    self.live_cameras_box.setFont(QFont('Arial', self.scale_font(14)))
    self.live_cameras_box.move(int(self.SCALE_W*(3*self.button_w + 4*self.sep)), int(self.SCALE_H*self.top_margin))
    live_panel_width = int(self.SCALE_W*(2.2*self.button_w + self.sep))
    live_panel_height = int(self.SCALE_H*(580))
    live_group_width = int(self.SCALE_W*(4.5*self.button_w + 3*self.sep))
    live_group_height = live_panel_height + int(self.SCALE_H*(90))
    self.live_cameras_box.setFixedSize(live_group_width, live_group_height)

    live_container = QWidget(self.live_cameras_box)
    live_container.move(int(self.SCALE_W*10), int(self.SCALE_H*28))
    live_container.setFixedSize(live_group_width - int(self.SCALE_W*20), live_group_height - int(self.SCALE_H*36))

    self.live_camera_box_1 = _build_live_camera_panel(self, live_container, 0, 0, 0, live_panel_width, live_panel_height)
    self.live_camera_box = self.live_camera_box_1
    self.live_camera_box_2 = _build_live_camera_panel(self, live_container, 1, live_panel_width + int(self.SCALE_W*self.sep), 0, live_panel_width, live_panel_height)

    buttons_y = live_panel_height + int(self.SCALE_H*18)
    button_width = int(self.SCALE_W*(self.button_w + 20))
    button_height = int(self.SCALE_H*34)
    button_spacing = int(self.SCALE_W*self.sep)
    buttons_total_width = 2*button_width + button_spacing
    buttons_x = max(0, (live_container.width() - buttons_total_width) // 2)

    self.live_reset_button = QPushButton("Reset acquisition", live_container)
    self.live_reset_button.setFont(QFont('Arial', self.scale_font(12)))
    self.live_reset_button.setGeometry(buttons_x, buttons_y, button_width, button_height)
    self.live_reset_button.clicked.connect(lambda _checked=False: self.handle_live_cameras_reset_clicked())

    self.live_start_button = QPushButton("Start acquisition", live_container)
    self.live_start_button.setFont(QFont('Arial', self.scale_font(12)))
    self.live_start_button.setGeometry(buttons_x + button_width + button_spacing, buttons_y, button_width, button_height)
    self.live_start_button.clicked.connect(lambda _checked=False: self.handle_live_cameras_start_clicked())

    self.handle_live_gaussian_toggled(self.live_gaussian_checkbox.isChecked(), 0)
    self.handle_live_fps_limit_toggled(self.live_fps_limit_checkbox.isChecked(), 0)

    live_defaults = getattr(self.experiment.experimental_data, "live_cameras", None)
    if not isinstance(live_defaults, list) or len(live_defaults) < 2:
        live_defaults = [getattr(self.experiment.experimental_data, "live_camera", None), None]

    for slot_index in range(2):
        live_defaults_slot = live_defaults[slot_index] if slot_index < len(live_defaults) else None
        suffix = "" if slot_index == 0 else f"_{slot_index}"
        camera_box = getattr(self, f"live_camera_box{suffix}")
        camera_box.blockSignals(True)
        camera_box.setChecked(bool(getattr(live_defaults_slot, "enabled", False)))

        camera_combo = getattr(self, f"live_which_cam_combo{suffix}")
        gain_edit = getattr(self, f"live_gain_edit{suffix}")
        exposure_edit = getattr(self, f"live_exposure_edit{suffix}")
        format_combo = getattr(self, f"live_format_combo{suffix}")
        hardware_trigger_checkbox = getattr(self, f"live_hardware_trigger_checkbox{suffix}")
        subtract_checkbox = getattr(self, f"live_subtract_checkbox{suffix}")
        dynamic_subtract_checkbox = getattr(self, f"live_dynamic_subtract_checkbox{suffix}")
        gaussian_checkbox = getattr(self, f"live_gaussian_checkbox{suffix}")
        gaussian_sigma_edit = getattr(self, f"live_gaussian_sigma_edit{suffix}")
        gaussian_kernel_edit = getattr(self, f"live_gaussian_kernel_edit{suffix}")
        display_gain_edit = getattr(self, f"live_display_gain_edit{suffix}")
        downsample_factor_edit = getattr(self, f"live_downsample_factor_edit{suffix}")
        fps_limit_checkbox = getattr(self, f"live_fps_limit_checkbox{suffix}")
        target_fps_edit = getattr(self, f"live_target_fps_edit{suffix}")

        if getattr(live_defaults_slot, "camera_name", ""):
            live_index = camera_combo.findText(live_defaults_slot.camera_name)
            if live_index >= 0:
                camera_combo.setCurrentIndex(live_index)
        if getattr(live_defaults_slot, "gain_db", None) is not None:
            gain_edit.setText(str(live_defaults_slot.gain_db))
        if getattr(live_defaults_slot, "exposure_time_ms", None) is not None:
            exposure_edit.setText(str(live_defaults_slot.exposure_time_ms))
        if getattr(live_defaults_slot, "format_name", ""):
            live_index = format_combo.findText(live_defaults_slot.format_name)
            if live_index >= 0:
                format_combo.setCurrentIndex(live_index)
        if hasattr(live_defaults_slot, "hardware_trigger"):
            hardware_trigger_checkbox.setChecked(bool(live_defaults_slot.hardware_trigger))
        if hasattr(live_defaults_slot, "subtraction_enabled"):
            subtract_checkbox.setChecked(bool(live_defaults_slot.subtraction_enabled))
        if hasattr(live_defaults_slot, "dynamic_subtraction_enabled"):
            dynamic_subtract_checkbox.setChecked(bool(live_defaults_slot.dynamic_subtraction_enabled))
        if hasattr(live_defaults_slot, "gaussian_enabled"):
            gaussian_checkbox.setChecked(bool(live_defaults_slot.gaussian_enabled))
        if hasattr(live_defaults_slot, "gaussian_sigma") and live_defaults_slot.gaussian_sigma is not None:
            gaussian_sigma_edit.setText(str(live_defaults_slot.gaussian_sigma))
        if hasattr(live_defaults_slot, "gaussian_kernel") and live_defaults_slot.gaussian_kernel is not None:
            gaussian_kernel_edit.setText(str(live_defaults_slot.gaussian_kernel))
        if hasattr(live_defaults_slot, "display_gain") and live_defaults_slot.display_gain is not None:
            display_gain_edit.setText(str(live_defaults_slot.display_gain))
        if hasattr(live_defaults_slot, "downsample_factor") and live_defaults_slot.downsample_factor is not None:
            downsample_factor_edit.setText(str(live_defaults_slot.downsample_factor))
        if hasattr(live_defaults_slot, "fps_limit_enabled"):
            fps_limit_checkbox.setChecked(bool(live_defaults_slot.fps_limit_enabled))
        if hasattr(live_defaults_slot, "target_fps") and live_defaults_slot.target_fps is not None:
            target_fps_edit.setText(str(live_defaults_slot.target_fps))

        camera_box.blockSignals(False)
        self.handle_live_camera_toggled(camera_box.isChecked(), slot_index)
        self.handle_live_gaussian_toggled(gaussian_checkbox.isChecked(), slot_index)
        self.handle_live_fps_limit_toggled(fps_limit_checkbox.isChecked(), slot_index)

    self._update_live_camera_action_buttons()

    self.which_cam_combo = QComboBox(self.camera_box)
    self.which_cam_combo.addItems(list(config.camera_serial_numbers_dict.keys()))
    self.which_cam_combo.setEditable(True)
    self.which_cam_combo.lineEdit().setReadOnly(True)
    self.which_cam_combo.lineEdit().setPlaceholderText("Select camera...")  # shown until user picks
    self.which_cam_combo.setCurrentIndex(-1) 
    self.which_cam_combo.currentTextChanged.connect(lambda: change_handlers.handle_camera_which_cam_changed(self))
    form.addRow("Which camera", self.which_cam_combo)


    self.gain_edit = QLineEdit(self.camera_box)
    self.gain_edit.setPlaceholderText("e.g. 20")
    self.gain_edit.editingFinished.connect(lambda: change_handlers.handle_camera_gain_changed(self))
    form.addRow("Gain, dB", self.gain_edit)

    self.roi_checkbox = QCheckBox("Enable ROI", self.camera_box)
    self.roi_checkbox.setFont(QFont('Arial', self.scale_font(12)))
    self.roi_checkbox.setChecked(False)
    self.roi_checkbox.toggled.connect(lambda enabled: change_handlers.handle_camera_roi_toggled(self, enabled))
    form.addRow("", self.roi_checkbox)

    self.roi_x_center_edit = QLineEdit(self.camera_box)
    self.roi_x_center_edit.setPlaceholderText("e.g. 512")
    self.roi_x_center_edit.editingFinished.connect(lambda: change_handlers.handle_camera_roi_changed(self))
    form.addRow("ROI X center", self.roi_x_center_edit)

    self.roi_y_center_edit = QLineEdit(self.camera_box)
    self.roi_y_center_edit.setPlaceholderText("e.g. 384")
    self.roi_y_center_edit.editingFinished.connect(lambda: change_handlers.handle_camera_roi_changed(self))
    form.addRow("ROI Y center", self.roi_y_center_edit)

    self.roi_width_edit = QLineEdit(self.camera_box)
    self.roi_width_edit.setPlaceholderText("e.g. 200")
    self.roi_width_edit.editingFinished.connect(lambda: change_handlers.handle_camera_roi_changed(self))
    form.addRow("ROI X width", self.roi_width_edit)

    self.roi_height_edit = QLineEdit(self.camera_box)
    self.roi_height_edit.setPlaceholderText("e.g. 200")
    self.roi_height_edit.editingFinished.connect(lambda: change_handlers.handle_camera_roi_changed(self))
    form.addRow("ROI Y height", self.roi_height_edit)


    exp_row = QWidget(self.camera_box)
    h = QHBoxLayout(exp_row)
    h.setContentsMargins(0, 0, 0, 0)

    self.exposure_edit = QLineEdit(exp_row)
    self.exposure_edit.setPlaceholderText("e.g. 0.35")
    self.exposure_edit.editingFinished.connect(lambda: change_handlers.handle_camera_exposure_changed(self))

    self.exposure_hint_label = QLabel("Var: T_exp_", exp_row)
    self.exposure_hint_label.setStyleSheet("color: gray; font-style: italic;")
    self.exposure_hint_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    self.lock_cb = QCheckBox("Lock", exp_row)
    self.lock_cb.toggled.connect(self.handle_texp_lock_toggled)

    h.addWidget(self.exposure_edit, 1)
    h.addWidget(self.exposure_hint_label, 0)
    h.addWidget(self.lock_cb, 0)
    form.addRow("Exposure time, ms", exp_row)

    # Image format
    self.format_combo = QComboBox(self.camera_box)
    self.format_combo.setEditable(True)
    self.format_combo.lineEdit().setReadOnly(True)
    self.format_combo.lineEdit().setPlaceholderText("Select image format...")  # shown until user picks
    self.format_combo.addItems(["Mono8", "Mono16"])
    self.format_combo.setCurrentIndex(-1) 
    self.format_combo.currentTextChanged.connect(lambda: change_handlers.handle_camera_image_format_changed(self))
    form.addRow("Image format", self.format_combo)


    # Save sampled variables group (checkable QGroupBox similar to Camera)
    self.save_sampled_box = QGroupBox(self.acquisition_tab_widget)
    self.save_sampled_box.setTitle("Save sampled variables")
    self.save_sampled_box.setCheckable(True)
    self.save_sampled_box.setChecked(False)
    self.save_sampled_box.setFont(QFont('Arial', self.scale_font(14)))
    # Place it next to camera_box (below it)
    self.save_sampled_box.move(int(self.SCALE_W*(self.button_w + 2*self.sep)), int(self.SCALE_H*(self.top_margin + 310)))
    self.save_sampled_box.setFixedSize(int(self.SCALE_W*(2*self.button_w + self.sep)), int(self.SCALE_H*(120)))
    form_ss = QFormLayout(self.save_sampled_box)
    # Small descriptive label inside the group
    label_desc = QLabel("Save sampled-variable dataset copy into the  - only if there is a sampled variable", self.save_sampled_box)
    label_desc.setWordWrap(True)
    form_ss.addRow(label_desc)





    self.number_of_runs_input_acquisition = bottom_buttons_build(self,self.acquisition_tab_widget)
    self.variables_table_acquisition, self.delete_variable_acquisition = variables_sidebar_build(self,self.acquisition_tab_widget)

    # initialise exposure lock state
    self.handle_texp_lock_toggled(self.lock_cb.isChecked())

    texp_var = self.experiment.variables.get("T_exp_")
    if texp_var is not None:
        self._set_camera_exposure_line(texp_var.value)
    else:
        self.exposure_edit.clear()




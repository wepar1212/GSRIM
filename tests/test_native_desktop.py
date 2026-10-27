import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
try:
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from gsrim.desktop import MainWindow, reference_project
    from gsrim.output import PLOT_NAMES, reference_plots
    from gsrim.project import DEFAULT
    from gsrim.simulation import Simulation
    HAS_QT=True
except ImportError:
    HAS_QT=False


@unittest.skipUnless(HAS_QT,"Optional native Qt dependencies are not installed")
class NativeDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        settings=QSettings(str(Path(self.temp.name)/"ui.ini"),QSettings.Format.IniFormat)
        settings.setValue("language","zh")
        self.window=MainWindow(settings=settings)
        self.window.timer.stop()

    def tearDown(self):
        self.window.close();self.window.deleteLater();self.app.processEvents();self.temp.cleanup()

    def test_language_switch_keeps_even_incomplete_edits_and_selections(self):
        w=self.window;w.name.setText("自定义输入");w.ion_energy.setText("1e")
        w.output_checks["RANGE.txt"].setChecked(False)
        w.language_combo.setCurrentIndex(1)
        self.assertEqual(w.name.text(),"自定义输入");self.assertEqual(w.ion_energy.text(),"1e")
        self.assertEqual(w.start_button.text(),"Save input & run")
        self.assertFalse(w.output_checks["RANGE.txt"].isChecked())
        w.language_combo.setCurrentIndex(0)
        self.assertIn("开始计算",w.start_button.text())

    def test_layers_units_and_species_edit_survive_selection(self):
        w=self.window;w.add_layer();self.assertEqual(w.layers.rowCount(),2)
        w.species.item(0,5).setText("30")
        w.layers.setCurrentCell(0,0);w.layers.setCurrentCell(1,0)
        self.assertEqual(w.species.item(0,5).text(),"30.0")
        w.layers.item(1,1).setText("100");w.layers.cellWidget(1,2).setCurrentIndex(1)
        self.assertEqual(w.collect()["layers"][1]["thickness_a"],1000)
        w.remove_layer();self.assertEqual(w.layers.rowCount(),1)

    def test_reference_setup_and_all_chart_modes_render(self):
        w=self.window;p=reference_project();w.fill_project(p)
        self.assertEqual(w.collect(check=True)["ion"]["symbol"],"H")
        self.assertEqual(w.species.item(0,4).text(),"60.000")
        sim=Simulation(p);w.state=sim.snapshot()
        for index in range(len(PLOT_NAMES)):
            w.plot_list.setCurrentRow(index);w.refresh_result()
            self.assertFalse(w.chart.image(800,600).isNull())

    def test_no_server_or_webview_used(self):
        with patch("webbrowser.open",side_effect=AssertionError("browser used")), \
             patch("http.server.ThreadingHTTPServer",side_effect=AssertionError("server used")):
            self.window.show();self.app.processEvents()
            QTest.mouseClick(self.window.tabs.tabBar(),Qt.MouseButton.LeftButton,pos=self.window.tabs.tabBar().tabRect(1).center())
            self.assertEqual(self.window.tabs.currentIndex(),1)

    def test_reference_display_never_enables_simulation_export_or_dose(self):
        w=self.window
        path=Path(self.temp.name)/"RANGE.txt";path.write_text(" DEPTH H Si\n10 1 2\n20 3 4\n")
        w.reference_folder=self.temp.name;w.references=reference_plots(self.temp.name)
        w.source.setCurrentIndex(1)
        self.assertFalse(w.export_button.isEnabled())
        self.assertIn("参考数据",w.dose_text.text())

    def test_invalid_run_does_not_replace_existing_simulation(self):
        w=self.window;sim=Simulation(copy.deepcopy(DEFAULT));w.simulation=sim
        w.ion_energy.setText("nan")
        with patch.object(w,"error") as error:w.start_run()
        error.assert_called_once();self.assertIs(w.simulation,sim)

    def test_reference_curve_toggle_never_discards_original_columns(self):
        w=self.window
        path=Path(self.temp.name)/"RANGE.txt";path.write_text(" DEPTH H Si\n10 1 2\n20 3 4\n")
        w.reference_folder=self.temp.name;w.references=reference_plots(self.temp.name)
        w.source.setCurrentIndex(1)
        self.assertEqual(len(w.chart.data.series),1)
        w.show_targets.setChecked(True)
        self.assertEqual(len(w.chart.data.series),2)
        w.show_targets.setChecked(False);w.show_targets.setChecked(True)
        self.assertEqual(len(w.references["range"].series),2)

    def test_project_roundtrip_uses_native_file_actions(self):
        w=self.window;path=Path(self.temp.name)/"project.json"
        w.ion_energy.setText("40")
        with patch.object(w,"dialog",return_value=str(path)):w.save_project()
        w.ion_energy.setText("5")
        with patch.object(w,"dialog",return_value=str(path)):w.open_project()
        self.assertEqual(float(w.ion_energy.text()),40.)

    def test_added_elements_have_individual_defaults_and_unknowns(self):
        w=self.window
        w.species.item(0,5).setText('32')
        w.add_species()
        self.assertEqual(w.species.cellWidget(1,0).currentText(),'H')
        self.assertEqual([float(w.species.item(1,c).text()) for c in (5,6,7)],[10,3,2])
        self.assertEqual(float(w.species.item(0,5).text()),32)
        w.add_species()
        self.assertEqual(w.species.cellWidget(2,0).currentText(),'He')
        self.assertEqual(w.species.item(2,5).text(),'')
        self.assertEqual(w.species.item(2,7).text(),'')
        self.assertIn('待填写',w.species.item(2,7).toolTip())
        self.assertIsNone(w.collect()['layers'][0]['species'][2]['surface_ev'])
        with self.assertRaisesRegex(ValueError,'He.*displacement_ev'):w.collect(check=True)
        w.species.item(2,5).setText('10');w.species.item(2,7).setText('1')
        w.collect(check=True)

    def test_switching_target_refreshes_binding_without_changing_amount(self):
        w=self.window;w.species.item(0,3).setText('3')
        w.species.cellWidget(0,0).setCurrentText('W')
        self.assertEqual([float(w.species.item(0,c).text()) for c in (5,6,7)],[90,3,8.68])
        self.assertEqual(float(w.species.item(0,3).text()),3)
        w.species.cellWidget(0,0).setCurrentText('Si')
        self.assertEqual([float(w.species.item(0,c).text()) for c in (5,6,7)],[15,2,4.7])
        w.species.item(0,5).setText('19')
        w.language_combo.setCurrentIndex(1)
        self.assertEqual(w.species.item(0,5).text(),'19')
        self.assertIn('official SRIM',w.species.item(0,5).toolTip())

    def test_loading_existing_project_preserves_old_explicit_values(self):
        p=copy.deepcopy(DEFAULT)
        p['layers'][0]['species'][0].update(displacement_ev=25,lattice_ev=3,surface_ev=4.9)
        self.window.fill_project(p)
        self.assertEqual(self.window.collect(check=True)['layers'][0]['species'][0],p['layers'][0]['species'][0])

    def test_range_chart_has_four_moments_in_both_languages_and_exports(self):
        import numpy as np
        from gsrim.simulation import NREC
        w=self.window;sim=Simulation(copy.deepcopy(DEFAULT))
        r=np.zeros((4,NREC));r[:,3]=[100,100,100,300]
        sim.records=[r];sim.completed=4;sim.status='completed';sim.hist[0,8]=4
        w.state=sim.snapshot();w.refresh_result()
        self.assertEqual([x[0] for x in w.chart.data.statistics],['平均射程','射程展宽','偏度','峰度'])
        w.show_targets.setChecked(True)
        self.assertEqual(len(w.chart.data.statistics),4)
        w.language_combo.setCurrentIndex(1)
        self.assertEqual([x[0] for x in w.chart.data.statistics],['Ion Range','Straggle','Skewness','Kurtosis'])
        for width,height in [(480,380),(800,620),(1500,1050)]:
            image=w.chart.image(width,height)
            self.assertFalse(image.isNull())
            self.assertTrue(image.save(str(Path(self.temp.name)/f'moments-{width}.png')))

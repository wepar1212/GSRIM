import copy
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import numpy as np
from gsrim.server import App,make_handler
from gsrim.project import DEFAULT
from gsrim.simulation import Simulation,NREC


class ServerRegressions(unittest.TestCase):
    def setUp(self):
        self.app=App()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.app))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.folder=tempfile.TemporaryDirectory(prefix='gsrim-http-test-')
        self.path=Path(self.folder.name)/'checkpoint.npz'
        self.patch=patch('gsrim.server.AUTOSAVE_PATH',self.path);self.patch.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2)
        self.patch.stop();self.folder.cleanup()

    def populated(self,failed=False,sputtered=False):
        p=copy.deepcopy(DEFAULT);p['run']['ions']=1;p['ion']['energy_kev']=40
        s=Simulation(p);s.completed=1;s.status='completed'
        r=np.zeros((1,NREC));r[0,13]=int(sputtered);r[0,16]=int(failed)
        s.records=[r];s.hist[0,0]=1
        return s

    def post(self,route,authorized=True):
        req=Request(self.url+'/api/'+route,data=b'{}',headers={'X-GSRIM-Token':self.app.token if authorized else 'wrong'})
        with urlopen(req,timeout=5) as response:return json.load(response)

    def test_restore_sputtering_not_failure(self):
        self.populated(sputtered=True).save_checkpoint(self.path)
        result=self.post('restore')
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['stats']['failed_histories'],0)
        self.assertFalse(result['diagnostic_only'])

    def test_restore_failure_not_missed(self):
        self.populated(failed=True).save_checkpoint(self.path)
        result=self.post('restore')
        self.assertEqual(result['status'],'error')
        self.assertTrue(result['diagnostic_only'])

    def test_csv_separate_energy_axes(self):
        self.app.simulation=self.populated()
        with urlopen(self.url+'/api/csv',timeout=5) as response:text=response.read().decode('utf-8-sig')
        self.assertIn('ion_energy_ev,backscattered,transmitted,sputter_energy_ev',text)
        self.assertIn('312.5,0.0,0.0,7.8125,0.0',text)

    def test_failed_csv_disabled(self):
        self.app.simulation=self.populated(failed=True)
        with self.assertRaises(HTTPError) as caught:urlopen(self.url+'/api/csv',timeout=5)
        self.assertEqual(caught.exception.code,400)

    def test_write_requires_token(self):
        with self.assertRaises(HTTPError) as caught:self.post('restore',authorized=False)
        self.assertEqual(caught.exception.code,403)

    def test_engine_identity_is_independent_of_loaded_result(self):
        self.app.simulation=self.populated();self.app.simulation.engine_revision=1
        with urlopen(self.url+'/api/info',timeout=5) as response:info=json.load(response)
        self.assertEqual(info['engine_revision'],2)
        self.assertEqual(info['app'],'GSRIM')

"""Internal software fixtures only; these are not experimental/manuscript data."""
from pathlib import Path
import json,tempfile,unittest
from core import digest,atomic
from sizes import config,requested,sample,counts,cell_sizes,panel_target
from prepare_panels import prepare,sha
from render_results import report


def fixture_row(c,s,i):return dict(record_id=f'{c}-{s}-{i}',text=f'Internal fixture {c} {s} {i}',target=[i%2])


class SizesTests(unittest.TestCase):
    def settings(self,path,default=8,overrides=None):
        value=dict(schema_version=1,sampling_seed=42,defaults=dict(train=8,dev=6,test=default),overrides=overrides or {})
        path.write_text(json.dumps(value));return value

    def test_override_and_full(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'config.json';self.settings(p,overrides={'goemotions':{'test':'all'}})
            value=config(p);self.assertEqual(requested(value,'goemotions'),dict(train=8,dev=6,test='all'))
            self.assertEqual(requested(value,'dreaddit')['test'],8)
            self.assertEqual(len(sample([fixture_row('x','test',i) for i in range(13)],'all',42,'x','test')),13)

    def test_samples_are_deterministic_nested_and_no_silent_shortfall(self):
        data=[fixture_row('x','test',i) for i in range(40)]
        a=sample(data,8,42,'x','test');b=sample(list(reversed(data)),16,42,'x','test')
        self.assertEqual(a,b[:8]);self.assertNotEqual(a,sample(data,8,43,'x','test'))
        with self.assertRaises(ValueError):sample(data,41,42,'x','test')
        with self.assertRaises(ValueError):sample(data+data[:1],8,42,'x','test')

    def test_materialization_drives_counts_and_report_denominators(self):
        from sizes import CORPORA,SPLITS
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);p=d/'config.json';self.settings(p,default=12,overrides={'cache':{'test':'all'}})
            pool=d/'pool';pool.mkdir();hashes={}
            for c in CORPORA:
                for split in SPLITS:
                    f=pool/c/(split+'.jsonl');f.parent.mkdir(parents=True,exist_ok=True)
                    f.write_text(''.join(json.dumps(fixture_row(c,split,i))+'\n' for i in range(17)))
                    hashes[str(f.relative_to(pool))]=sha(f)
            atomic(pool/'pool_manifest.json',dict(status='validated',cross_split_checks_passed=True,files=hashes))
            out=d/'run';result=prepare(p,pool,out)
            self.assertEqual(counts(out,'cache')['test'],17)
            self.assertEqual(cell_sizes(out,'cache','offline','ace')['update_n'],8)
            self.assertEqual(cell_sizes(out,'cache','online','ace')['update_n'],17)
            self.assertEqual(panel_target(out),3*(10*12+10*12+4*17+4*12))
            protocol=dict(seeds=[42,43,44],conditions=[dict(dataset=c,phase='baseline',method='base',adaptation_gt='not_applicable') for c in CORPORA])
            text,data=report(out,protocol)
            self.assertIn('0/51',text);self.assertIn('0/0/17',text)
            with self.assertRaises(ValueError):prepare(p,pool,out)
            sampling=json.loads((out/'sampling_manifest.json').read_text());sampling['counts']['cache']['test']=100
            (out/'sampling_manifest.json').write_text(json.dumps(sampling))
            with self.assertRaises(ValueError):counts(out,'cache')

    def test_config_rejects_typos_zero_boolean_and_invalid_full(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'config.json'
            for bad in [0,-1,True,'ALL',1.5]:
                value=self.settings(p);value['defaults']['test']=bad;p.write_text(json.dumps(value))
                with self.assertRaises(ValueError):config(p)

    def test_accuracy_uses_actual_frozen_panel_not_100(self):
        from report_predictions import scores
        task={'labels':[0,1],'single_label':True}
        gold={str(i):{'target':[i%2]} for i in range(20)}
        pred=[{'record_id':str(i),'valid':False,'output':None} for i in range(20)]
        for i in range(10):pred[i].update(valid=True,output={'label_ids':[i%2]})
        result=scores(pred,gold,task)
        self.assertEqual(result['accuracy'],50.0);self.assertEqual(result['accuracy_status'],'complete')
        self.assertIsNone(scores(pred[:-1],gold,task)['accuracy'])
        with self.assertRaises(ValueError):scores(pred+pred[:1],gold,task)


if __name__=='__main__':unittest.main()

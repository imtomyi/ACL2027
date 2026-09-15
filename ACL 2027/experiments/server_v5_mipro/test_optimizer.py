"""Internal software cases for objective correctness, not experiment observations."""
from pathlib import Path
import tempfile, unittest
import dspy
from sklearn.metrics import f1_score
from optimizer import corpus_f1, evaluator_type


class Predictions(dspy.Module):
    def __init__(self, labels): super().__init__(); self.labels=labels
    def forward(self, index): return dspy.Prediction(label_ids=self.labels[index])


class ObjectiveTests(unittest.TestCase):
    def evaluate(self, gold, predictions, dataset, labels):
        examples=[dspy.Example(index=i,label_ids=x).with_inputs('index') for i,x in enumerate(gold)]
        with tempfile.TemporaryDirectory() as temp:
            evaluator=evaluator_type(dict(dataset=dataset,labels=labels),Path(temp))(
                devset=examples,metric=lambda g,p:float(g.label_ids==p.label_ids),num_threads=1,
                display_progress=False,display_table=False)
            return evaluator(Predictions(predictions)).score

    def test_macro_matches_sklearn_and_selects_against_accuracy(self):
        gold=[0]*90+[1]*10;majority=[0]*100;balanced=[0]*80+[1]*18+[0]*2
        g=[[x] for x in gold];a=[[x] for x in majority];b=[[x] for x in balanced]
        self.assertAlmostEqual(corpus_f1(g,b,[0,1],'macro'),f1_score(gold,balanced,labels=[0,1],average='macro'))
        self.assertGreater(sum(x==y for x,y in zip(gold,majority)),sum(x==y for x,y in zip(gold,balanced)))
        self.assertGreater(self.evaluate(g,b,'dreaddit',[0,1]),self.evaluate(g,a,'dreaddit',[0,1]))

    def test_multilabel_objective_is_not_mean_item_f1(self):
        gold=[[1],[1,2,3,4]];a=[[1],[5]];b=[[5],[1,2]]
        item_average=lambda p:sum(2*len(set(g)&set(x))/(len(g)+len(x)) for g,x in zip(gold,p))/2
        self.assertGreater(item_average(a),item_average(b))
        self.assertGreater(self.evaluate(gold,b,'goemotions',[1,2,3,4,5]),
                           self.evaluate(gold,a,'goemotions',[1,2,3,4,5]))
        self.assertAlmostEqual(corpus_f1(gold,b,[1,2,3,4,5],'micro'),0.5)

    def test_invalid_candidate_cannot_gain_by_abstaining(self):
        self.assertEqual(self.evaluate([[0],[1]],[[0],[]],'dreaddit',[0,1]),0)

    def test_unknown_labels_and_misalignment_fail(self):
        with self.assertRaises(ValueError):corpus_f1([[0]],[[2]],[0,1],'macro')
        with self.assertRaises(ValueError):corpus_f1([[0]],[],[0,1],'macro')


if __name__=='__main__': unittest.main()

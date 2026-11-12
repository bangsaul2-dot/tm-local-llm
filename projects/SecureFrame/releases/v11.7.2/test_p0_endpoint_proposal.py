import copy
import unittest
from p0_endpoint_proposal import propose_endpoint_correction as propose

A={"name":"A","kind":"leaf","bbox":[0,0,30,40]}
B={"name":"B","kind":"leaf","bbox":[100,0,130,40]}
def wire(points, verified=True):
    return {"id":"synthetic","points":points,"trace_verified":verified}

class EndpointP0Tests(unittest.TestCase):
    def test_safe_two_face_extension(self):
        w=wire([[40,20],[90,20]])
        original=copy.deepcopy(w)
        out=propose(w,[A,B])
        self.assertEqual(out["proposed_points"],[[30,20],[100,20]])
        self.assertEqual(out["_source_points"],original["points"])
        self.assertEqual(w,original)
        self.assertEqual(len(out["corrections"]),2)
        self.assertFalse(out["source_verified"])
    def test_floating_parallel_no_intersection(self):
        out=propose(wire([[40,-12],[90,-12]]),[A,B])
        self.assertEqual(out["corrections"],[])
        self.assertEqual(out["proposed_points"],[[40,-12],[90,-12]])
    def test_true_tangent_no_intersection(self):
        out=propose(wire([[40,20],[90,20]]),[{"name":"C","kind":"leaf","bbox":[40,50,90,80]}])
        self.assertEqual(out["corrections"],[])
    def test_competing_leaf_abstain(self):
        dup={"name":"D","kind":"leaf","bbox":[0,0,30,40]}
        out=propose(wire([[40,20],[90,20]]),[A,dup,B])
        self.assertNotIn("start",[x["endpoint"] for x in out["corrections"]])
        self.assertIn("ambiguous_face_or_competitor",out["reasons"])
    def test_corner_two_faces_abstain(self):
        out=propose(wire([[40,50],[50,60]]),[A])
        self.assertEqual(out["corrections"],[])
    def test_zero_length_abstain(self):
        out=propose(wire([[40,20],[40,20]]),[A])
        self.assertEqual(out["corrections"],[])
    def test_too_far_no_correction(self):
        out=propose(wire([[48,20],[90,20]]),[A,B],max_extension=12)
        self.assertNotIn("start",[x["endpoint"] for x in out["corrections"]])
    def test_unverified_trace_abstain(self):
        out=propose(wire([[40,20],[90,20]],False),[A,B])
        self.assertEqual(out["corrections"],[])
    def test_no_auto_approval(self):
        out=propose(wire([[40,20],[90,20]]),[A,B])
        self.assertEqual(out["status"],"needs_review")
        self.assertFalse(out["auto_approval"])

if __name__=="__main__":unittest.main()

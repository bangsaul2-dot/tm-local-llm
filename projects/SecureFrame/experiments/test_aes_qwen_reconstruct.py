import unittest
from aes_qwen_reconstruct import validate,svg

def block(i,kind="leaf",parent=None):
    return {"id":i,"label":"<AES & Key>","kind":kind,"parent":parent,
            "x":0.1,"y":0.1,"w":0.2,"h":0.1}

class Tests(unittest.TestCase):
    def test_valid_svg(self):
        data={"blocks":[block("a"),block("b")],
              "connections":[{"from":"a","to":"b","direction":"forward","label":""}]}
        result=svg(validate(data))
        self.assertIn("&lt;AES &amp; Key&gt;",result)
        self.assertIn("marker-end",result)
    def test_reject_container_endpoint(self):
        data={"blocks":[block("a","container"),block("b")],
              "connections":[{"from":"a","to":"b","direction":"forward","label":""}]}
        with self.assertRaises(ValueError):validate(data)
    def test_reject_coordinates_out_of_bounds(self):
        b=block("a");b["x"]=1.1
        with self.assertRaises(ValueError):validate({"blocks":[b],"connections":[]})
    def test_reject_extra_fields(self):
        b=block("a");b["confidence"]=0.9
        with self.assertRaises(ValueError):validate({"blocks":[b],"connections":[]})
    def test_reject_unknown_edge(self):
        with self.assertRaises(ValueError):
            validate({"blocks":[block("a")],"connections":[
                {"from":"a","to":"missing","direction":"forward","label":""}]})
    def test_reject_parent_cycle(self):
        a=block("a","container","b");b=block("b","container","a")
        with self.assertRaises(ValueError):validate({"blocks":[a,b],"connections":[]})
if __name__=="__main__":unittest.main()

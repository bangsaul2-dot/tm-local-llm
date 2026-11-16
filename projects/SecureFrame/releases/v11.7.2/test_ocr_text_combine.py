"""Synthetic tests; never use customer labels, images or geometry."""
import unittest
from copy import deepcopy
from ocr_text_combine import combine_ocr_tokens

def tok(text,x,y=2,w=8,h=8):
    return {"text":text,"bbox":[x,y,x+w,y+h]}
def geom(tokens,boxes=None):
    return {"boxes":boxes if boxes is not None else [{"bbox":[0,0,100,40]}],
            "ocr":tokens,"wires":[{"id":"synthetic"}]}

class Tests(unittest.TestCase):
    def test_adjacent_fragments_join(self):
        g=geom([tok("AB",2),tok("-12",11)])
        r=combine_ocr_tokens(g)
        self.assertEqual([x["text"] for x in r["ocr"]],["AB-12"])
        self.assertEqual(r["ocr"][0]["bbox"],[2,2,19,10])
    def test_no_mutation(self):
        g=geom([tok("A",2),tok("B",11)])
        before=deepcopy(g)
        combine_ocr_tokens(g)
        self.assertEqual(g,before)
    def test_different_boxes_never_join(self):
        g=geom([tok("A",2),tok("B",15)],
               [{"bbox":[0,0,12,40]},{"bbox":[13,0,40,40]}])
        self.assertEqual(len(combine_ocr_tokens(g)["ocr"]),2)
    def test_far_gap_no_join(self):
        self.assertEqual(len(combine_ocr_tokens(geom([tok("A",2),tok("B",60)]))["ocr"]),2)
    def test_different_line_no_join(self):
        self.assertEqual(len(combine_ocr_tokens(geom([tok("A",2),tok("B",11,y=22)]))["ocr"]),2)
    def test_punctuation_not_joined(self):
        self.assertEqual(len(combine_ocr_tokens(geom([tok("A",2),tok("|",11)]))["ocr"]),2)
    def test_unicode_nfkc(self):
        self.assertEqual(combine_ocr_tokens(geom([tok("ＡＢ",2)]))["ocr"][0]["text"],"AB")
    def test_box_wire_counts_unchanged(self):
        g=geom([tok("A",2),tok("B",11)])
        r=combine_ocr_tokens(g)
        self.assertEqual(len(r["boxes"]),len(g["boxes"]))
        self.assertEqual(len(r["wires"]),len(g["wires"]))
    def test_overlap_box_ambiguous_no_merge(self):
        g=geom([tok("A",2),tok("B",11)],
               [{"bbox":[0,0,100,40]},{"bbox":[0,0,100,40]}])
        self.assertEqual(len(combine_ocr_tokens(g)["ocr"]),2)
    def test_invalid_token_rejected(self):
        with self.assertRaises(ValueError):
            combine_ocr_tokens(geom([{"text":"A","bbox":[1,1,1,2]}]))
    def test_group_limit(self):
        g=geom([tok("A",2,w=2),tok("B",5,w=2),tok("C",8,w=2)])
        self.assertEqual(len(combine_ocr_tokens(g,max_group=2)["ocr"]),2)

if __name__=="__main__":
    unittest.main()

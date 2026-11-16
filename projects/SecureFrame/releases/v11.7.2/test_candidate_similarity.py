"""Synthetic-only deterministic checks; no confidential samples."""
import copy
import json
import unittest
from candidate_similarity import normalize, similarity, rank_candidates, aggregate

def node(name,kind="leaf"):
    return {"name":name,"kind":kind,"parent":None}
def token(text,x=2,y=2,w=12,h=8):
    return {"text":text,"bbox":[x,y,x+w,y+h]}
def geo(texts,boxes=None):
    return {"boxes":boxes if boxes is not None else [{"bbox":[0,0,120,40]}],
            "ocr":[token(t,2+20*i) for i,t in enumerate(texts)],"wires":[]}
def rank(names,geom):
    return rank_candidates({"nodes":[node(n) for n in names],"edges":[]},geom)

class SimilarityTests(unittest.TestCase):
    def test_nfkc(self): self.assertEqual(normalize("ＡＢ－１２"),"ab12")
    def test_punctuation(self): self.assertEqual(similarity("1ch'256b","1ch256b")[0],1)
    def test_case(self): self.assertEqual(similarity("Host","HOST")[0],1)
    def test_numeric_conflict(self): self.assertEqual(similarity("1ch256b","1ch128b"),(0.0,"numeric_conflict"))
    def test_numeric_zero_conflict(self): self.assertEqual(similarity("AB01","AB1")[0],0)
    def test_numeric_order(self): self.assertEqual(similarity("A12B34","A34B12")[0],0)
    def test_short_substring(self): self.assertNotEqual(similarity("CLK","CLK_RESET")[1],"substring")
    def test_long_substring(self): self.assertEqual(similarity("enable","enable_control")[1],"substring")
    def test_empty(self): self.assertEqual(similarity("","abc")[0],0)
    def test_unicode_mixed(self): self.assertEqual(normalize("漢字 Ａ1"),"漢字a1")
    def test_exact_box(self):
        p=rank(["Alpha"],geo(["Alpha"]))[0]
        self.assertEqual(p["box_index"],0)
        self.assertEqual(p["review_state"],"needs_review")
    def test_competing_boxes_abstain(self):
        g={"boxes":[{"bbox":[0,0,30,40]},{"bbox":[40,0,70,40]}],
           "ocr":[token("Alpha",2),token("Alpha",42)],"wires":[]}
        self.assertIsNone(rank(["Alpha"],g)[0]["box_index"])
    def test_duplicate_nodes_same_box_abstain(self):
        p=rank(["Alpha","alpha"],geo(["Alpha"]))
        self.assertTrue(all(x["box_index"] is None for x in p))
    def test_wrong_digits_abstain(self):
        self.assertIsNone(rank(["AB128"],geo(["AB256"]))[0]["box_index"])
    def test_no_ocr_abstain(self):
        self.assertIsNone(rank(["Alpha"],geo([]))[0]["box_index"])
    def test_no_mutation(self):
        g=geo(["Alpha"]);s={"nodes":[node("Alpha")],"edges":[]}
        old=copy.deepcopy((s,g))
        rank_candidates(s,g)
        self.assertEqual((s,g),old)
    def test_aggregate_sanitized(self):
        p=rank(["SecretAlpha"],geo(["SecretAlpha"]))
        a=aggregate(p)
        self.assertNotIn("SecretAlpha",json.dumps(a))
        self.assertFalse(a["auto_approval"])
        self.assertEqual(a["pass_90"],"NOT_EVALUABLE")
    def test_invalid_bbox(self):
        with self.assertRaises(ValueError):
            rank(["Alpha"],{"boxes":[{"bbox":[1,2,1,3]}],"ocr":[]})
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            rank_candidates({"nodes":[],"edges":[]},geo([]),min_score=2)
    def test_container_not_approved(self):
        p=rank_candidates({"nodes":[node("Group","container")],"edges":[]},geo(["Group"]))[0]
        self.assertFalse(p["auto_approval"])
        self.assertEqual(p["kind"],"container")
    def test_no_fuzzy_character_substitution(self):
        self.assertLess(similarity("HOST","H0ST")[0],0.84)
    def test_ocr_fragments(self):
        p=rank(["ABCD"],geo(["AB","CD"]))[0]
        self.assertEqual(p["box_index"],0)

if __name__=="__main__":unittest.main()

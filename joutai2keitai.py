"""
Converts Japanese sentences from written language style (`joutai`) to spoken language style (`keitai`).
"""
import os
import argparse
import unicodedata
import MeCab
import re

conjugation_dict = { # "活用型": "基本形,未然形,連用形,終止形,連体形,仮定形,命令形" 
    "カ行": "く,かこ,きい,く,く,け,け", 
    "ガ行": "ぐ,がご,ぎい,ぐ,ぐ,げ,げ",
    "サ行": "す,さそ,し,す,す,せ,せ",
    "タ行": "つ,たと,ちっ,つ,つ,て,て",
    "ナ行": "ぬ,なの,にん,ぬ,ぬ,ね,ね",
    "バ行": "ぶ,ばぼ,びん,ぶ,ぶ,べ,べ",
    "マ行": "む,まも,みん,む,む,め,め",
    "ラ行": "る,らろ,りっ,る,る,れ,れ",
    "ワ行": "う,わお,いっ,う,う,え,え"
}


def get_args():
    parser = argparse.ArgumentParser(description="joutai2keitai.py")
    # for debugging
    parser.add_argument("-t", "--test_file", default=None)
    if not parser.parse_known_args()[0].test_file:
        parser.add_argument("-i", "--in_file", required=True,
                                        help="Input file path")
        parser.add_argument("-o", "--out_file", required=True,
                                        help="Output file path")
    parser.add_argument("--nfkc", action="store_true",
                                    help="Adapt Unicode normalization")
    return parser.parse_args()


class Transfer:
    def __init__(self, nfkc=False):
        self.tagger = MeCab.Tagger("")
        self.tagger.parse("")
        self.nfkc = nfkc

    def exec_sentence(self, sentence) -> str:
        if self.nfkc:
            sentence = unicodedata.normalize("NFKC", sentence)
        self.node = self.tagger.parseToNode(sentence)
        sent_l = []
        while self.node:
            sent_l.append(self.joutai2keitai())
            self.node = self.node.next
        return "".join(sent_l)

    def joutai2keitai(self) -> str:
        node2 = self.node.next
        if node2: node3 = node2.next
        surface = self.node.surface
        features = self.node.feature.split(",")
        pos = features[0] 
        conjugations = features[4]
        conjugated = features[5]
        if features[6] == "*":
            infinitive = None
        else:
            infinitive = features[6]

        word = ""
        if pos == "動詞" and conjugated in {"基本形", "連用タ接続", "連用形", "未然形"}:

            # 動詞基本形 -> 動詞連用形
            if "五段" in conjugations:
                ptn = ".*([カ|ガ|サ|タ|ナ|バ|マ|ラ|ワ]行).*"
                con_type = re.match(ptn, conjugations).group(1)
                suffix = conjugation_dict[con_type].split(",")[2][0]
                word = infinitive[:-1] + suffix
            elif "一段" in conjugations:
                word = infinitive[:-1]
            elif "サ変" in conjugations:
                word = "し"
            elif "カ変・来ル" in conjugations:
                word = "来"
            elif "カ変・クル" in conjugations:
                word = "き"
            else:
                raise Exception("{} is not expected".format(surface))

            # rule 1: 動詞基本形 -> 動詞連用形+"ます"
            if conjugated=="基本形":
                if node2.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                    word += "ます"
                else: word = surface

            # rule 2: 動詞連用形/連用タ接続+"た" -> 動詞連用形+"ました"
            elif conjugated in {"連用タ接続", "連用形"} \
                    and node2.feature.split(",")[6] in {"た", "だ"}:
                if node3.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                    word += "ました"
                    self.node = self.node.next
                else: word = surface

            elif conjugated == "未然形" and node2.feature.split(",")[6] == "ない":
                # rule 3: 動詞未然形+"ない" -> 動詞連用形+"ません"
                if node2.feature.split(",")[5] == "基本形":
                    if node3.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                        word += "ません"
                        self.node = self.node.next
                    else: word = surface

                # rule 4: 動詞未然形+"ない"連用タ接続+"た" -> 動詞連用形+"ませんでした"
                elif node2.feature.split(",")[5] == "連用タ接続" \
                        and node3.surface == "た":
                    if node3.next.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                        word += "ませんでした"
                        self.node = self.node.next
                        self.node = self.node.next
                    else: word = surface
                else: word = surface
            else: word = surface

        elif pos == "助動詞" and infinitive == "だ" and \
                conjugated in {"基本形", "連用タ接続", "連用形", "未然形"}:

            # rule 5: 助動詞"だ" -> "です"
            if conjugated == "基本形":
                if node2.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                    word += "です"
                else: word = surface

            # rule 6: 助動詞"だ"連用タ接続+助動詞"た"基本形 -> "でした"
            elif conjugated == "連用タ接続" and node2.feature.split(",")[6] == "た" \
                    and node2.feature.split(",")[5] == "基本形":
                if node3.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                    word += "でした"
                    self.node = self.node.next
                else: word = surface

            # rule 8: 助動詞"だ"連用形+助動詞"ある"基本形 -> "です"
            elif conjugated == "連用形" and node2.feature.split(",")[6] == "ある" \
                    and node2.feature.split(",")[5] == "基本形":
                if node3.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                    word += "です"
                    self.node = self.node.next
                else: word = surface

            # rule 9: 助動詞"だ"連用形+助動詞"ある"連用タ接続
            #           +助動詞"た"基本形 -> "でした"
            elif conjugated == "連用形" and node2.feature.split(",")[6] == "ある" \
                    and node2.feature.split(",")[5] == "連用タ接続" \
                    and node3.feature.split(",")[6] == "た" \
                    and node3.feature.split(",")[5] == "基本形" :
                if node3.next.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                    word += "でした"
                    self.node = self.node.next
                    self.node = self.node.next
                else: word = surface

            # rule 10: 助動詞"だ"連用形+助動詞"ある"未然ウ接続
            #           +助動詞"う"基本形 -> "でしょう"
            elif conjugated == "連用形" and node2.feature.split(",")[6] == "ある" \
                    and node2.feature.split(",")[5] == "未然ウ接続" \
                    and node3.feature.split(",")[6] == "う" \
                    and node3.feature.split(",")[5] == "基本形" :
                if node3.next.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                    word += "でしょう"
                    self.node = self.node.next
                    self.node = self.node.next
                else: word = surface

            # rule 11: 助動詞"だ"未然形+助動詞"う"基本形 -> "でしょう"
            elif conjugated == "未然形" and node2.feature.split(",")[6] == "う" \
                    and node2.feature.split(",")[5] == "基本形":
                if node3.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                    word += "でしょう"
                    self.node = self.node.next
                else: word = surface

            else: word = surface

        # rule 7: 助動詞"ない"基本形 -> "ありません"
        # rule 13: 形容詞"ない"基本形 -> "ありません"
        elif pos in {"助動詞", "形容詞"}  and infinitive == "ない" \
                and conjugated == "基本形":
            if node2.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                word += "ありません"
            else: word = surface

        # rule 12: 接続詞"だが","が" -> "ですが"
        elif pos == "接続詞" and infinitive in {"だが", "が"}:
            word += "ですが"

        # rule 14: 形容詞"ない"連用タ接続+助動詞"た"基本形 -> "ありませんでした"
        elif pos == "形容詞" and infinitive == "ない" and conjugated == "連用タ接続" \
            and node2.feature.split(",")[6] == "た" \
            and node2.feature.split(",")[5] == "基本形":
            if node3.feature.split(",")[0] in {"記号", "BOS/EOS"}:
                word += "ありませんでした"
                self.node = self.node.next
            else: word = surface
            
        else: word = surface
        return word


def main():
    transfer = Transfer(args.nfkc)

    if args.test_file is not None: # debug mode
        src, ref = [], []
        with open(args.test_file) as f:
            lines = f.readlines()
        print("written->spoken")
        for line in lines:
            src, ref = line.rstrip("\r\n").split("\t")
            hyp = transfer.exec_sentence(src)
            assert hyp==ref, (hyp, ref)
            print("{}->{}".format(src, hyp))
        print("done!")
    else:
        with open(args.in_file) as f:
            lines = f.readlines()
        with open(args.out_file, mode="w") as f:
            for line in lines:
                hyp = transfer.exec_sentence(line.rstrip("\r\n"))
                f.write(hyp+"\n")


if __name__ == "__main__":
    args = get_args()
    main()

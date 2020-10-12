# joutai2keitai
Converts Japanese sentences from written language style (常体) to spoken language style (敬体).

## requirements
- Python 3
- mecab-python3

## get started
### inference
Convert input sentences into spoken language and output
```
python joutai2keitai.py -i src.txt -o hyp.txt
```
- `-i, --in_file`: input file path
- `-o, --out_file`: output file path
- `--nfkc`: (optional) adapt Unicode normalization (NFKC)

### test
A mode to check if the conversion is correct.
```
python joutai2keitai.py -t test.txt
```
- `-t, --test_file`: a file in which written and spoken languages are separated by tabs

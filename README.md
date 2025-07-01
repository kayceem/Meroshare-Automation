### Setup Instructions
1. Install uv:
```bash
pip install uv
```
2. Install dependencies:
```bash
uv sync
``` 
3. Add users
```bash
python -m scripts.generator
```

### IPO

```bash
python main.py ipo
```
*--noheadless* option can be used to run the script without a headless browser.
### IPO Results

```bash
python main.py ipo-results
```
### EDIS

```bash
python main.py edis <user>
```

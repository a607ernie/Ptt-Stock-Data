# Ptt-Stock-Data




## Read the json file

```python
with open('ptt_stock.json', encoding='utf-8') as fh:
    data = json.load(fh)

df = pd.DataFrame(data)
df.T

```

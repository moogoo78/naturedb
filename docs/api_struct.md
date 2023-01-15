# API

- no tailing slash

```python
args: {
  align: '{right|left}', # default: left
  type: '{text|checkbox}' # default: text
}
```

```python
    data = {
        'header': (
            ('pk', 'pk', {'align':'right'}),
            ('full_name', '全名', {'align': 'right'}),
            ('is_collector', '採集者', {'align': 'right'}),
            ('is_identifier', '鑒定者', {'align': 'right'}),
        ),
        'rows': [],
}
```

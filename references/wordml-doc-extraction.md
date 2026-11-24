# WordML .doc Extraction

When `prepare_work_materials.py` extracts fewer students than the mark-list shows, the missing students likely have WordML flat XML `.doc` files. These are not binary OLE2 `.doc` files — they start with `<?xml version="1.0"?>` and use the `xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"` namespace.

## The Problem

Standard WordML parsing (extracting all `w:t` elements via ElementTree) returns only ~190 chars because:

1. The essay text is inside ONE giant `<w:t>` element after `学生答案：`
2. Line breaks are `<w:br />` tags embedded INSIDE the `<w:t>` element
3. ElementTree's `iter()` for `w:t` tags picks up the text node but the `<w:br/>` children are lost
4. The result is the header metadata ("答题人：XXX 提交时间：XXX") without the actual essay

## Detection

```python
with open(path, 'rb') as f:
    header = f.read(10)
# Binary OLE2 .doc: header[:4] == b'\xd0\xcf\x11\xe0'
# WordML XML .doc: starts with b'\xef\xbb\xbf<?xml' or contains 'w:wordDocument'
```

Also check file size: WordML `.doc` files are typically 60-80KB but contain only ~190 chars of extractable `w:t` text via standard parsing.

## Correct Extraction Recipe

```python
import re

def read_wordml_doc(path):
    with open(path, 'r', errors='replace') as f:
        content = f.read()
    
    # Find the student answer section
    answer_idx = content.find('学生答案')
    if answer_idx >= 0:
        end_idx = content.find('正确答案', answer_idx)
        if end_idx < 0:
            end_idx = len(content)
        answer_section = content[answer_idx:end_idx]
    else:
        answer_section = content
    
    # Replace <w:br /> with newlines BEFORE extracting text
    answer_section = re.sub(r'<w:br\s*/?>', '\n', answer_section)
    
    # Extract text from <w:t> elements (non-greedy, DOTALL)
    texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', answer_section, re.S)
    full_text = ''.join(texts)
    
    # Clean any remaining tags
    full_text = re.sub(r'<[^>]+>', '', full_text)
    return full_text.strip()
```

## Binary .doc Fallback

For true binary OLE2 `.doc` files (e.g. 张吟晨's submission), install and use `antiword`:

```bash
sudo apt-get install -y antiword
antiword path/to/file.doc
```

`catdoc` is an alternative. `libreoffice --headless --convert-to txt` works but is slower.

## Case-Insensitive .DOCX Matching

Some students upload files with uppercase `.DOCX` extension. Always match case-insensitively:

```python
docx_files = sorted([f for f in all_files if f.lower().endswith('.docx')])
doc_files = sorted([f for f in all_files if f.lower().endswith('.doc') and not f.lower().endswith('.docx')])
```

## Full Student File Reader (Production Pattern)

```python
def read_student_file(folder_path):
    if not os.path.isdir(folder_path):
        return ''
    all_files = os.listdir(folder_path)
    docx_files = sorted([f for f in all_files if f.lower().endswith('.docx')])
    doc_files = sorted([f for f in all_files if f.lower().endswith('.doc') and not f.lower().endswith('.docx')])
    
    # Prefer .docx
    if docx_files:
        return read_docx_text(os.path.join(folder_path, docx_files[0]))
    
    # Try .doc files
    for f in doc_files:
        path = os.path.join(folder_path, f)
        with open(path, 'rb') as fh:
            header = fh.read(10)
        if header[:4] == b'\xd0\xcf\x11\xe0':
            text = read_binary_doc(path)  # antiword
            if len(text) > 100:
                return text
        else:
            text = read_wordml_doc(path)  # XML extraction
            if len(text) > 100:
                return text
    return ''
```

## Fallback: Files Not in Individual Folders

Some WordML `.doc` files appear directly in the `extracted/` directory (not in a per-student subfolder), named like `电子信息学院-物联网工程-物联网2303班-233080348-叶为.doc`. Always scan both the per-student folders AND the extracted root directory for orphans.

import csv
import json
from typing import List


def load_texts(file_path: str) -> List[str]:
    """Load a dataset file and return a list of text strings."""
    ext = file_path.rsplit(".", 1)[-1].lower()

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    if ext == "txt":
        return [line.strip() for line in raw.splitlines() if line.strip()]

    elif ext == "json":
        data = json.loads(raw)
        if isinstance(data, list):
            texts = []
            for item in data:
                if isinstance(item, str):
                    texts.append(item)
                elif isinstance(item, dict):
                    # Try common text field names
                    for key in ("text", "content", "output", "response", "value", "data"):
                        if key in item:
                            texts.append(str(item[key]))
                            break
                    else:
                        texts.append(json.dumps(item))
            return texts
        elif isinstance(data, dict):
            return [json.dumps(data)]
        return [raw]

    elif ext == "csv":
        texts = []
        reader = csv.DictReader(raw.splitlines())
        for row in reader:
            # Try common column names, fallback to joining all values
            for key in ("text", "content", "output", "response", "value"):
                if key in row:
                    texts.append(row[key])
                    break
            else:
                texts.append(" ".join(str(v) for v in row.values()))
        return texts

    return [raw]

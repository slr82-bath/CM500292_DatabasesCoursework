from dataclasses import fields
from typing import List, Optional

def print_table(objects: List, columns: Optional[List[str]]):
    if not objects:
        return

    # Right padding for each column
    padding = 4

    # Get headers from object properties
    headers = list(objects[0].__dict__.keys())

    # Filter headers if columns are present and not empty
    if columns is not None and len(columns):
        headers = list(filter(lambda item: item in columns, headers))

    max_len = {h: len(h) + padding for h in headers}

    # Calculate width for each column
    for obj in objects:
        for h in headers:
            current_max_len = max_len[h]
            field_value_len_with_padding = len(str(getattr(obj, h))) + padding
            if current_max_len < field_value_len_with_padding:
                max_len[h] = field_value_len_with_padding

    # Print headers
    for h in headers:
        print(f"{h:<{max_len[h]}}", end="")
    print()
    
    print("-" * (sum(list(max_len.values())) - padding))

    # Print rows
    for obj in objects:
        for h in headers:
            print(f"{str(getattr(obj, h)):<{max_len[h]}}", end="")
        print()

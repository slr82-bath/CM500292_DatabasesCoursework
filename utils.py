import sqlparse
from typing import List, Optional


def print_table(objects: List, columns: Optional[List[str]]):
    """
    Print a collection of objects as a formatted table.

    Args:
        objects: List of objects whose attributes will be displayed.
        columns: Optional list of attribute names to include. If None or empty,
                 all attributes from the first object are displayed.

    Notes:
        - Column widths are calculated dynamically based on the longest value
          in each column.
        - Object attributes are read from __dict__, so this function works
          best with simple data objects/classes.
    """
    # Nothing to print if the collection is empty.
    if not objects:
        return

    # Extra spaces added to each column to improve readability.
    padding = 4

    # Use the attributes of the first object as table headers.
    # Assumes all objects have the same structure.
    headers = list(objects[0].__dict__.keys())

    # If specific columns were requested, keep only those headers.
    if columns is not None and len(columns):
        headers = list(filter(lambda item: item in columns, headers))

    # Initialize each column width using the header length.
    # Padding is included so columns do not touch each other.
    max_len = {h: len(h) + padding for h in headers}

    # Determine the maximum width required for each column by
    # comparing header length with the length of every field value.
    for obj in objects:
        for h in headers:
            current_max_len = max_len[h]
            field_value_len_with_padding = len(str(getattr(obj, h))) + padding

            if current_max_len < field_value_len_with_padding:
                max_len[h] = field_value_len_with_padding

    # Print table header row.
    for h in headers:
        print(f"{h:<{max_len[h]}}", end="")
    print()

    # Print a separator line spanning the full table width.
    print("-" * (sum(max_len.values()) - padding))

    # Print each object as a table row.
    # Values are left-aligned according to the calculated column width.
    for obj in objects:
        for h in headers:
            print(f"{str(getattr(obj, h)):<{max_len[h]}}", end="")
        print()


def optional_input(prompt: str) -> Optional[str]:
    """
    Prompt the user for input and return None when the input is empty.

    Args:
        prompt: Text displayed to the user.

    Returns:
        The trimmed input string, or None if the user entered only
        whitespace or pressed Enter without providing a value.
    """
    value = input(prompt).strip()
    return value if value else None


def print_sql_script(sql_script: str):
    """
    Print a SQL script using a standardized, readable format.

    The SQL is:
        - Reindented for consistent formatting.
        - Converted to uppercase SQL keywords.

    Args:
        sql_script: Raw SQL script as a string.

    Raises:
        TypeError: If sql_script is not a string.
    """
    # Validate input early to prevent unexpected formatting errors.
    if not isinstance(sql_script, str):
        raise TypeError("SQL script must be a string.")

    # Format and print the SQL statement(s).
    print(sqlparse.format(sql_script, reindent=True, keyword_case="upper"))

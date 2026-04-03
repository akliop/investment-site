import ast
try:
    with open('app.py', encoding='utf-8') as f:
        ast.parse(f.read())
    print("No Syntax Errors found.")
except SyntaxError as e:
    print(f"SyntaxError: {e.msg} at line {e.lineno}")
except Exception as e:
    print(f"Error: {e}")

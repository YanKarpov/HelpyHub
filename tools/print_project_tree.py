import os

IGNORED_DIRS = {"__pycache__", ".git", "venv", ".venv", ".idea", ".mypy_cache"}

def print_project_tree(root, prefix=""):
    items = sorted(os.listdir(root))
    for i, item in enumerate(items):
        path = os.path.join(root, item)
        if os.path.basename(path) in IGNORED_DIRS:
            continue
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        print(prefix + connector + item)

        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            print_project_tree(path, prefix + extension)

print_project_tree(".")

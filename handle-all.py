import os


def gather_py_files(root_dir):
    py_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.endswith(".py"):
                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, root_dir)
                py_files.append((rel_path, full_path))
    return py_files


def combine_py_files(root_dir, output_file):
    py_files = gather_py_files(root_dir)
    with open(output_file, "w", encoding="utf-8") as out_f:
        for rel_path, full_path in py_files:
            out_f.write(f"# === File: {rel_path} ===\n")
            with open(full_path, encoding="utf-8") as in_f:
                out_f.write(in_f.read())
                out_f.write("\n\n")
    print(f"Combined {len(py_files)} files into {output_file}")


if __name__ == "__main__":
    import sys

    # Usage: python combine_py_files.py [source_dir] [output_file]
    source_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    output_file = sys.argv[2] if len(sys.argv) > 2 else "combined_output.py"
    combine_py_files(source_dir, output_file)

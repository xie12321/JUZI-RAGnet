import frontmatter
from pathlib import Path
from config import WIKI_ROOT

def check_missing_frontmatter(directory: Path):
    missing = []
    incomplete = []
    for md_file in directory.rglob("*.md"):
        if '.obsidian' in md_file.parts:
            continue
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            metadata = post.metadata
            # 检查是否有 frontmatter（即 metadata 非空且至少有一个字段）
            if not metadata:
                missing.append(md_file)
            else:
                # 检查必要字段
                required = ['title', 'summary', 'tags']
                for field in required:
                    if field not in metadata or not metadata[field]:
                        incomplete.append((md_file, field))
        except Exception as e:
            print(f"Error reading {md_file}: {e}")
    return missing, incomplete

if __name__ == "__main__":
    missing, incomplete = check_missing_frontmatter(WIKI_ROOT)
    if missing:
        print("=== 缺少 Frontmatter 的文件 ===")
        for f in missing:
            print(f)
    if incomplete:
        print("\n=== 缺少必要字段的文件 ===")
        for f, field in incomplete:
            print(f"{f}: 缺少字段 '{field}'")
    if not missing and not incomplete:
        print("所有文件 Frontmatter 完整。")
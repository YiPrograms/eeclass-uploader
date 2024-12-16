import markdown

FILENAME = "score.tsv"

# (sid, score, comment)
def parse(line: list[str]) -> tuple[str, float, str]:
    sid, name, section1, section2, section3, total, note = line
    
    comment_md = f"""
- Section 1: **{section1}** / 50
- Section 2: **{section2}** / 30
- Section 3: **{section3}** / 20
<br>
{f"- Note: {note}" if note else ""}
- Total: **{total}**
    """
    
    comment_md = comment_md.strip()
    comment_html = markdown.markdown(comment_md)
    
    if len(total) == 0 or total == "#N/A":
        total = None
    else:
        total = float(total)

    return sid, total, comment_html

# list[(sid, score, comment)]
def get_data() -> list[tuple[str, float, str]]:
    with open(FILENAME) as f:
        lines = f.read().splitlines()
    
    lines = list(map(lambda x: x.split("\t"), lines))
    lines = lines[1:]
    lines = list(map(parse, lines))
    return lines

if __name__ == "__main__":
    print(get_data()[0])
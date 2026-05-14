from rich.console import Console
from rich.markdown import Markdown

console = Console()
md = Markdown("[Example](http://example.com)")
console.print(md)

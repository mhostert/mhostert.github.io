from inspyhep import Author
import os
import glob

files = glob.glob("../_publications/*.md")

for f in files:
    os.remove(f)

mh = Author("Matheus.Hostert.1")
mh.get_markdown_descriptor(max_nauthors=9, path="../_publications/")

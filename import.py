import gedcom7


def importer(s: str):
    """Import a Gedcom 7 string."""
    records = gedcom7.loads(s)
    print(records)


if __name__ == "__main__":
    with open("maximal70.ged", encoding="utf-8") as f:
        s = f.read()
    importer(s)

"""Produire un CSV sans doublons à partir d’un fichier déjà validé."""
import csv
from io import StringIO


def correct_csv(content: bytes, delimiter: str = ",") -> bytes:
    """Conserver les valeurs, l’ordre et l’en-tête ; ignorer les lignes vierges."""
    reader = csv.reader(StringIO(content.decode("utf-8-sig"), newline=""), delimiter=delimiter, strict=True)
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=delimiter, lineterminator="\r\n")
    writer.writerow(next(reader))
    seen = set()
    for row in reader:
        if not row or tuple(row) in seen:
            continue
        seen.add(tuple(row))
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")

"""
Data model definitions for the Study Bible Compendium.

For now we define:
- VerseRef: a normalized reference (book_num, chapter, verse)
- Verse   : a verse row as it appears in the DB
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerseRef:
    """
    A normalized reference to a single verse.

    book_num: 1–66 (Protestant canon order)
    chapter : 1..N
    verse   : 1..N
    """
    book_num: int
    chapter: int
    verse: int

    def to_normalized(self, book_code: str) -> str:
        """
        Compute the normalized_ref string (e.g. 'GEN.1.1').

        Parameters
        ----------
        book_code:
            Canonical 3-letter code for the book (e.g. 'GEN').

        Returns
        -------
        str
            Normalized reference string.
        """
        return f"{book_code.upper()}.{self.chapter}.{self.verse}"


@dataclass
class Verse:
    """
    Representation of a verse row as stored in the `verses` table.
    """
    id: int | None
    translation_code: str
    book_num: int
    book_code: str
    chapter: int
    verse: int
    normalized_ref: str
    text: str
    word_count: int

    @classmethod
    def from_db_row(cls, row: tuple) -> "Verse":
        """
        Construct from a SELECT row in the order of the `verses` table.
        """
        (
            id_,
            translation_code,
            book_num,
            book_code,
            chapter,
            verse,
            normalized_ref,
            text,
            word_count,
            _created_utc,
        ) = row
        return cls(
            id=id_,
            translation_code=translation_code,
            book_num=book_num,
            book_code=book_code,
            chapter=chapter,
            verse=verse,
            normalized_ref=normalized_ref,
            text=text,
            word_count=word_count,
        )

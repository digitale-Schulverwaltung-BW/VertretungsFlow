"""
WebUntis Parser
Pure parsing and transformation functions for WebUntis timetable data
"""

import logging
from datetime import datetime
from typing import List, Dict

from app.schemas.schemas import WebUntisLesson

logger = logging.getLogger(__name__)


def parse_timetable(
    timetable_data: List[dict],
    teacher_id: int,
    subjects: Dict,
    classes: Dict,
    rooms: Dict,
    timegrid: Dict,
) -> List[WebUntisLesson]:
    """
    Parsed Stundenplan-Daten von WebUntis

    Args:
        timetable_data: Rohdaten von WebUntis
        teacher_id: ID des Lehrers (zum Filtern bei Team-Teaching)
        subjects: Fächer-Mapping {id: name}
        classes: Klassen-Mapping {id: name}
        rooms: Raum-Mapping {id: name}
        timegrid: Stundenraster-Mapping {startTime: period}

    Returns:
        Liste von WebUntisLesson Objekten
    """
    logger.debug(f"Parse Timetable: {len(timetable_data)} Einträge")

    lessons = []

    for i, entry in enumerate(timetable_data):
        try:
            logger.info(f"📝 Parse Entry {i+1}/{len(timetable_data)}: {entry}")

            # Filter: Nur Stunden wo der Lehrer tatsächlich dabei ist
            teacher_ids = [t.get("id") for t in entry.get("te", [])]
            if teacher_id not in teacher_ids:
                logger.info(
                    f"⏭️ Überspringe Entry {i+1}: Lehrer {teacher_id} nicht in {teacher_ids}"
                )
                continue

            # Datum parsen (Format: YYYYMMDD)
            date_str = str(entry.get("date", ""))
            date = datetime.strptime(date_str, "%Y%m%d")

            # IDs auflösen
            # WICHTIG: JSONB speichert numerische Keys als Strings, daher beide Varianten probieren
            subject_ids = [s.get("id") for s in entry.get("su", [])]
            if subject_ids:
                subject_id = subject_ids[0]
                subject = subjects.get(subject_id) or subjects.get(
                    str(subject_id), "Unbekannt"
                )
            else:
                subject = "Unbekannt"

            class_ids = [c.get("id") for c in entry.get("kl", [])]
            if class_ids:
                class_id = class_ids[0]
                class_name = classes.get(class_id) or classes.get(
                    str(class_id), "Unbekannt"
                )
            else:
                class_name = "Unbekannt"

            room_ids = [r.get("id") for r in entry.get("ro", [])]
            if room_ids:
                room_id = room_ids[0]
                room = rooms.get(room_id) or rooms.get(str(room_id))
            else:
                room = None

            # Stundennummer aus Timegrid ermitteln
            start_time = entry.get("startTime", 0)
            end_time = entry.get("endTime", 0)
            # JSONB konvertiert auch hier Keys zu Strings
            period = timegrid.get(start_time) or timegrid.get(
                str(start_time), start_time // 100
            )

            lesson = WebUntisLesson(
                date=date,
                period=period,
                start_time=start_time if start_time else None,
                end_time=end_time if end_time else None,
                subject=subject,
                class_name=class_name,
                room=room,
            )

            logger.info(
                f"✅ Stunde geparst: {date.date()} #{period} - {subject} ({class_name}) in {room}"
            )
            lessons.append(lesson)

        except Exception as e:
            logger.error(f"❌ Parse Lesson Error bei Entry {i+1}: {e}", exc_info=True)
            logger.error(f"Problematischer Entry: {entry}")
            continue

    logger.info(
        f"Parsing abgeschlossen: {len(lessons)}/{len(timetable_data)} Stunden erfolgreich geparst"
    )

    # Doppelstunden zusammenfassen
    merged_lessons = merge_consecutive_lessons(lessons)
    logger.info(f"🔗 Nach Zusammenfassung: {len(merged_lessons)} Stundenblöcke")

    return merged_lessons


def merge_consecutive_lessons(lessons: List[WebUntisLesson]) -> List[WebUntisLesson]:
    """
    Fasst aufeinanderfolgende Stunden mit gleicher Klasse und gleichem Fach zusammen

    Args:
        lessons: Liste von einzelnen Stunden

    Returns:
        Liste mit zusammengefassten Stundenblöcken
    """
    if not lessons:
        return lessons

    # Sortieren nach Datum und Periode
    sorted_lessons = sorted(lessons, key=lambda lesson: (lesson.date, lesson.period))

    merged = []
    current_block = None

    for lesson in sorted_lessons:
        if current_block is None:
            # Erster Block
            current_block = {
                "lesson": lesson,
                "start_period": lesson.period,
                "end_period": lesson.period,
            }
        elif (
            lesson.date == current_block["lesson"].date
            and lesson.class_name == current_block["lesson"].class_name
            and lesson.subject == current_block["lesson"].subject
            and lesson.room == current_block["lesson"].room
            and lesson.period == current_block["end_period"] + 1
        ):
            # Aufeinanderfolgende Stunde mit gleicher Klasse/Fach -> erweitern
            current_block["end_period"] = lesson.period
            logger.debug(
                f"🔗 Erweitere Block: {lesson.class_name} {lesson.subject} "
                f"({current_block['start_period']}-{current_block['end_period']})"
            )
        else:
            # Neuer Block beginnt
            merged.append(current_block)
            current_block = {
                "lesson": lesson,
                "start_period": lesson.period,
                "end_period": lesson.period,
            }

    # Letzten Block hinzufügen
    if current_block:
        merged.append(current_block)

    # Konvertiere Blöcke zurück zu WebUntisLesson mit end_period
    result = []
    for block in merged:
        lesson = block["lesson"]
        # Setze end_period für Doppelstunden
        if block["start_period"] != block["end_period"]:
            # Erstelle neue WebUntisLesson mit end_period
            merged_lesson = WebUntisLesson(
                date=lesson.date,
                period=block["start_period"],
                end_period=block["end_period"],
                subject=lesson.subject,
                class_name=lesson.class_name,
                room=lesson.room,
            )
            logger.info(
                f"📚 Stundenblock: {block['start_period']}.{block['end_period']}. Stunde - "
                f"{lesson.subject} ({lesson.class_name})"
            )
            result.append(merged_lesson)
        else:
            # Einzelstunde
            result.append(lesson)

    return result

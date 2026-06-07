
def initialize_world_state(compiled_context: dict):

    context = compiled_context["retrieved_context"]

    return {
        "characters": context.get("character_states", []),
        "relationships": context.get("relationship_summary", []),
        "events": [],
        "chapter_memory": [],
    }


def update_world_state(
    world_state: dict,
    outline: dict,
):

    changes = outline.get(
        "world_state_changes",
        [],
    )

    world_state["events"].extend(changes)

    summary = summarize_chapter(outline)

    world_state["chapter_memory"].append(summary)

    world_state["chapter_memory"] = (
        world_state["chapter_memory"][-5:]
    )

    return world_state


def summarize_chapter(outline: dict):

    scene_text = " ".join(
        scene["summary"]
        for scene in outline.get("scenes", [])
    )

    return (
        f"Chapter {outline['chapter_number']} - "
        f"{outline['chapter_title']}: "
        f"{scene_text}"
    )


def validate_scene(
    prose: str,
    world_state: dict,
    outline: dict,
    genre: str | None,
):

    warnings = []

    pov = outline.get("pov_character", "")

    if pov and pov.lower() not in prose.lower():
        warnings.append(
            f"POV character '{pov}' missing from prose."
        )

    known_names = [
        character.get("name", "").lower()
        for character in world_state.get("characters", [])
    ]

    for word in prose.split():

        clean_word = word.strip(".,!?").lower()

        if clean_word.istitle():
            if (
                clean_word not in known_names
                and len(clean_word) > 3
            ):
                pass

    if genre == "psychological_thriller":

        thriller_words = [
            "fear",
            "secret",
            "suspicion",
            "paranoia",
        ]

        if not any(
            word in prose.lower()
            for word in thriller_words
        ):
            warnings.append(
                "Thriller tone appears weak."
            )

    return warnings

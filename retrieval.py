# retrieval.py - Loads data from saga_contract.json instead of Neo4j

import json
from pathlib import Path
from collections import Counter

# Path to your contract file
CONTRACT_PATH = Path("saga_contract.json")

def load_retrieval_data(book_title: str) -> dict:
    """
    Load data from saga_contract.json file instead of Neo4j
    """
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(f"Contract file not found at {CONTRACT_PATH}")
    
    with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
        contract = json.load(f)
    
    print(f"[INFO] Loaded data from {CONTRACT_PATH}")
    
    # Extract data from the contract
    outputs = contract.get("outputs", {})
    
    # Extract characters from entity registry
    characters = []
    entity_registry = outputs.get("entity_registry", [])
    for entity in entity_registry:
        if entity.get("entity_type") == "character":
            characters.append({
                "name": entity.get("name"),
                "mention_count": entity.get("mention_count", 0),
                "first_seen_chapter": entity.get("first_seen", {}).get("chapter_index", 1),
                "descriptions": [d.get("description") for d in entity.get("descriptions", [])],
                "aliases": [],
                "personality_traits": _extract_personality_traits(entity),
            })
    
    # Extract original chapter content
    chapters = []
    resolved_scenes = outputs.get("resolved_scene_analyses", [])
    for scene in resolved_scenes:
        chapter_idx = scene.get("chapter_index", 1)
        # Group scenes by chapter
        chapters.append({
            "number": chapter_idx,
            "title": f"Chapter {chapter_idx}",
            "content": scene.get("text", ""),
            "pov_character": scene.get("canonical_characters", [{}])[0].get("name", "Feyre") if scene.get("canonical_characters") else "Feyre",
            "scenes": [scene]
        })
    
    # Extract relationships from state transitions
    relationships = []
    state_result = outputs.get("state_result", {})
    transitions = state_result.get("transitions", [])
    
    for trans in transitions:
        if trans.get("change_type") == "relationship":
            relationships.append({
                "entity_a": trans.get("source_entity"),
                "entity_b": trans.get("target_entity"),
                "relationship_type": trans.get("relationship", "unknown"),
                "evidence": trans.get("evidence", ""),
                "last_seen_chapter": trans.get("chapter_index", 1)
            })
    
    # Extract events from timeline
    events = []
    timeline = outputs.get("timeline", [])
    for event in timeline:
        events.append({
            "id": event.get("event_id", f"evt_{event.get('time_index', 0)}"),
            "description": event.get("summary", ""),
            "chapter_index": event.get("chapter_index", 1),
            "is_critical": event.get("event_id") in [e.get("event_id") for e in outputs.get("causal_graph_result", {}).get("critical_path", [])],
            "criticality_score": 8 if event.get("event_id") in [e.get("event_id") for e in outputs.get("causal_graph_result", {}).get("critical_path", [])] else 5,
            "story_impact": event.get("summary", "")[:100],
            "characters": event.get("characters", [])
        })
    
    # Extract unresolved threads from divergence points
    unresolved_threads = []
    causal_graph = outputs.get("causal_graph_result", {})
    divergence_points = causal_graph.get("divergence_points", [])
    for dp in divergence_points:
        unresolved_threads.append({
            "event_id": dp.get("event_id"),
            "event_description": f"Divergence point at event {dp.get('event_id')}",
            "chapter_index": 1,
            "is_critical": True,
            "decision_made": dp.get("decision_made", ""),
            "alternatives": dp.get("alternatives", []),
            "divergence_potential": dp.get("divergence_potential", 5),
            "alternate_timeline": dp.get("alternate_timeline", "")
        })
    
    # Extract causal chains
    causal_chains = causal_graph.get("causal_chains", [])
    
    # Extract flexible events
    flexible_events = []
    flexible = causal_graph.get("flexible_events", [])
    for fe in flexible:
        flexible_events.append({
            "event_id": fe.get("event_id"),
            "description": fe.get("why_flexible", ""),
            "chapter_index": 1,
            "flexibility_score": fe.get("flexibility_score", 5),
            "why_flexible": fe.get("why_flexible", "")
        })
    
    # Extract character trajectories
    character_timelines = outputs.get("character_timelines", [])
    character_trajectories = []
    for ct in character_timelines:
        character_trajectories.append({
            "character": ct.get("character"),
            "last_events": ct.get("events", [])[:5]
        })
    
    print(f"[INFO] Extracted {len(characters)} characters")
    print(f"[INFO] Extracted {len(relationships)} relationships")
    print(f"[INFO] Extracted {len(events)} events")
    print(f"[INFO] Extracted {len(unresolved_threads)} unresolved threads")
    print(f"[INFO] Extracted {len(causal_chains)} causal chains")
    print(f"[INFO] Extracted {len(chapters)} chapters for perspective swap")
    
    return {
        # sequel
        "story_ending": {
            "last_scene": outputs.get("resolved_scene_analyses", [{}])[-1] if outputs.get("resolved_scene_analyses") else {},
            "critical_path_tail": events[-5:] if events else []
        },
        "character_states": characters,
        "relationship_summary": relationships,
        "unresolved_threads": unresolved_threads,
        "causal_chains": causal_chains,
        "character_trajectories": character_trajectories,
        # what_if
        "critical_events": events[:10] if events else [],
        # genre_swap
        "events": flexible_events if flexible_events else events[:20],
        # perspective_swap
        "original_chapters": chapters,
        "world_lore": [],
    }


def _extract_personality_traits(entity: dict) -> list:
    """Extract personality traits from entity descriptions"""
    traits = []
    descriptions = entity.get("descriptions", [])
    for desc in descriptions:
        desc_text = desc.get("description", "").lower()
        trait_keywords = ["proud", "stubborn", "brave", "loyal", "cold", "warm", "sharp", "kind", "fierce", "calculated"]
        for trait in trait_keywords:
            if trait in desc_text and trait not in traits:
                traits.append(trait)
    return traits


def get_all_books() -> list:
    """Get all book titles from the contract (just one)"""
    try:
        with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
            contract = json.load(f)
        inputs = contract.get("inputs", {})
        books = inputs.get("books", [])
        return [book.get("title", "Unknown") for book in books]
    except:
        return ["A Court of Frost and Starlight"]


# ===========================================================================
# CONTEXT SLICING — use-case routing
# ===========================================================================

def retrieve_context(
    use_case: str,
    retrieval_data: dict,
    user_prompt: str,
    genre: str | None = None,
    target_pov: str | None = None,
) -> dict:

    if use_case == "sequel":
        return _retrieve_sequel_context(retrieval_data)

    if use_case == "what_if":
        return _retrieve_what_if_context(retrieval_data, user_prompt)

    if use_case == "genre_swap":
        return _retrieve_genre_context(retrieval_data, genre)
    
    if use_case == "perspective_swap":
        return _retrieve_perspective_swap_context(retrieval_data, target_pov, user_prompt)

    raise ValueError(f"Unsupported use case: {use_case}")


def _retrieve_sequel_context(data: dict) -> dict:
    return {
        "mode": "sequel",
        "story_ending": data.get("story_ending", {}),
        "character_states": data.get("character_states", [])[:10],
        "relationship_summary": data.get("relationship_summary", [])[:15],
        "unresolved_threads": sorted(
            data.get("unresolved_threads", []),
            key=lambda x: x.get("divergence_potential", 0),
            reverse=True,
        )[:8],
        "character_trajectories": data.get("character_trajectories", [])[:10],
    }


def _retrieve_what_if_context(data: dict, user_prompt: str) -> dict:
    """Enhanced what-if retrieval that prioritizes user prompt"""
    
    causal_chains = data.get("causal_chains", [])

    ranked_chains = sorted(
        causal_chains,
        key=lambda chain: _keyword_overlap(user_prompt, chain.get("description", "")),
        reverse=True,
    )

    return {
        "mode": "what_if",
        "what_if_premise": {
            "divergence_point": user_prompt[:200],
            "full_prompt": user_prompt
        },
        "causal_chains": ranked_chains[:5],
        "critical_events": data.get("critical_events", [])[:10],
        "character_states": data.get("character_states", [])[:10],
        "relationship_summary": data.get("relationship_summary", [])[:10],
        "override_instruction": "IGNORE CANON RELATIONSHIPS if they contradict the prompt",
    }


def _retrieve_genre_context(data: dict, genre: str) -> dict:
    events = data.get("events", [])
    
    if not events:
        events = data.get("critical_events", [])[:15]

    ranked = sorted(
        events,
        key=lambda e: _genre_score(genre, e.get("description", "")),
        reverse=True,
    )

    return {
        "mode": "genre_swap",
        "genre": genre,
        "genre_events": ranked[:15],
        "character_states": data.get("character_states", [])[:10],
        "relationship_summary": data.get("relationship_summary", [])[:15],
        "world_lore": data.get("world_lore", [])[:10],
    }


def _retrieve_perspective_swap_context(data: dict, target_pov: str, user_prompt: str) -> dict:
    """Retrieve context for perspective swap use case"""
    
    # Get all chapters
    original_chapters = data.get("original_chapters", [])
    
    # Find character info for target POV
    character_info = None
    for char in data.get("character_states", []):
        if char.get("name", "").lower() == target_pov.lower():
            character_info = char
            break
    
    # If character not found, try partial match
    if not character_info:
        for char in data.get("character_states", []):
            if target_pov.lower() in char.get("name", "").lower():
                character_info = char
                break
    
    return {
        "mode": "perspective_swap",
        "target_pov": target_pov,
        "character_info": character_info or {"name": target_pov, "descriptions": []},
        "original_chapters": original_chapters,
        "user_direction": user_prompt,
        "all_characters": data.get("character_states", [])[:15],
        "relationships": data.get("relationship_summary", [])[:20],
    }


# ===========================================================================
# SCORING HELPERS
# ===========================================================================

def _keyword_overlap(a: str, b: str) -> int:
    return len(set(a.lower().split()) & set(b.lower().split()))


def _genre_score(genre: str, text: str) -> int:
    genre_keywords = {
        "romcom": ["love", "relationship", "kiss", "awkward", "funny", "banter", "romance", "date", "heart", "smile", "laugh", "witty", "charm"],
        "fantasy": ["magic", "kingdom", "war", "dragon", "curse", "prophecy", "spell", "sword", "throne", "fae", "prythian", "cauldron", "power"],
        "psychological_thriller": [
            "fear", "secret", "suspicion", "paranoia", "murder", "dark", "twist", "mind", 
            "betrayal", "hunt", "stalk", "watch", "hide", "truth", "lied", "shadow", "whisper"
        ],
    }
    counter = Counter(text.lower().split())
    return sum(counter.get(kw, 0) for kw in genre_keywords.get(genre, []))


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAGA Retrieval Layer (JSON Mode)")
    parser.add_argument("--book", default="A Court of Frost and Starlight")
    parser.add_argument(
        "--use-case", default="sequel", choices=["sequel", "what_if", "genre_swap", "perspective_swap"]
    )
    parser.add_argument("--prompt", default="")
    parser.add_argument("--genre", default=None)
    parser.add_argument("--target-pov", default=None)
    parser.add_argument("--out", default="retrieval_context.json")
    args = parser.parse_args()

    data = load_retrieval_data(args.book)
    context = retrieve_context(
        use_case=args.use_case,
        retrieval_data=data,
        user_prompt=args.prompt,
        genre=args.genre,
        target_pov=args.target_pov,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(context, f, indent=2, ensure_ascii=False, default=str)

    print(f"[SAGA] Context saved to: {args.out}")
    print(f"[SAGA] Mode: {context.get('mode')}")
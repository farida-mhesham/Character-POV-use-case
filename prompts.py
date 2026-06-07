import json


BLUEPRINT_SYSTEM = """
You are a master narrative architect specializing in story structure.

Create a detailed, comprehensive story blueprint based on the provided context.

Your blueprint MUST include:
- A compelling title
- A clear premise
- Total chapters (between 5-30 depending on story complexity)
- Central conflict
- Character arcs for main characters (with start state, end state, and key turning points)
- Acts with chapter ranges and narrative goals

IMPORTANT: For WHAT-IF scenarios, completely ignore canon relationships and character states.
The user prompt defines the alternative reality - follow it strictly.

Return ONLY valid JSON. No other text.
"""


OUTLINE_SYSTEM = """
You are a narrative planner.

Create a detailed chapter outline with specific scenes.

For WHAT-IF scenarios: Follow the alternative premise strictly.
For SEQUEL: Continue naturally from where the story ended.
For GENRE_SWAP: Maintain plot points but adjust tone.

Return ONLY valid JSON with this exact structure:
{
    "chapter_number": number,
    "chapter_title": "string",
    "scenes": [
        {
            "title": "string",
            "summary": "string",
            "pov_character": "string",
            "key_beats": ["beat1", "beat2"]
        }
    ],
    "world_state_changes": []
}
"""


PROSE_SYSTEM = """
You are a professional fiction writer.

Write immersive, vivid scene prose that:
- Maintains consistent character voices
- Shows, doesn't tell
- Includes sensory details
- Advances the plot
- Maintains continuity

For WHAT-IF scenarios: Write as if the alternative reality is the ONLY reality.
Do not reference canon events that didn't happen in this timeline.

Write 500-1000 words per scene.
"""


PERSPECTIVE_SWAP_SYSTEM = """
You are a master of character voice and psychological depth.

Your task is to rewrite existing scenes from a NEW character's point of view while preserving all events and dialogue.

CRITICAL RULES:
1. ALL external events, actions, and dialogue must remain EXACTLY as in the original
2. ONLY change whose thoughts, feelings, and internal experiences we see
3. The new POV character cannot know information they wouldn't have access to
4. The new POV character's interpretations may be biased or incomplete
5. Show how the same events look different through their eyes

For the new POV character, you must capture:
- Their unique voice and vocabulary
- Their emotional reactions to events
- Their observations of other characters (what they notice vs. miss)
- Their internal assumptions and biases
- Their memories and associations triggered by events
- Their physical sensations and experiences

Write in consistent tense and person with the original (usually first-person or close third-person).
The goal is to reveal NEW meaning from the same events by changing the lens through which we see them.
"""


ROMCOM_STYLE = """
Tone:
- witty and playful dialogue
- emotionally warm
- comedic misunderstandings
- romantic tension with humor
- banter between characters
- lighthearted even during conflict
"""


FANTASY_STYLE = """
Tone:
- mythic and epic
- immersive worldbuilding
- lyrical prose
- high emotional stakes
- magical elements woven naturally
"""


THRILLER_STYLE = """
Tone:
- tense and suspenseful
- psychologically intense
- paranoid atmosphere
- quick pacing
- unexpected revelations
- dark and brooding
"""


def get_genre_modifier(genre: str | None):
    """Get genre-specific tone modifiers"""
    if genre == "romcom":
        return ROMCOM_STYLE
    if genre == "fantasy":
        return FANTASY_STYLE
    if genre == "psychological_thriller":
        return THRILLER_STYLE
    return ""


def parse_what_if_prompt(user_prompt: str) -> dict:
    """Extract key elements from a what-if prompt"""
    elements = {
        "divergence_point": "",
        "changed_character_status": {},
        "new_relationships": [],
        "key_events": [],
        "time_skip": None
    }
    
    # Look for common patterns
    if "never" in user_prompt.lower() or "didn't" in user_prompt.lower():
        lines = user_prompt.split("\n")
        for line in lines:
            if "what if" in line.lower() or "chose to" in line.lower():
                elements["divergence_point"] = line.strip()
    
    # Look for time references
    import re
    time_match = re.search(r'(\d+)\s*(year|month|week)s?', user_prompt.lower())
    if time_match:
        elements["time_skip"] = int(time_match.group(1))
    
    return elements


def build_blueprint_prompt(
    compiled_context: dict,
    genre_modifier: str,
) -> str:
    """Build prompt for blueprint generation with enhanced what-if handling"""
    
    use_case = compiled_context.get("use_case", "sequel")
    user_prompt = compiled_context.get("user_prompt", "")
    genre = compiled_context.get("genre")
    retrieved_context = compiled_context.get("retrieved_context", {})
    
    # Special handling for what-if scenarios
    what_if_override = ""
    if use_case == "what_if":
        what_if_override = f"""
⚠️ IMPORTANT - THIS IS A WHAT-IF SCENARIO ⚠️

The user has specified an alternative reality. IGNORE the retrieved context if it contradicts this premise.

ALTERNATIVE REALITY PREMISE:
{user_prompt}

Follow this premise EXACTLY. Do not use canon relationships or character states.
Create a completely new story where:
1. The divergence point is strictly followed
2. Character statuses are as described in the prompt
3. Relationships are as described in the prompt
4. Canon events that wouldn't happen in this timeline are ignored

GENERATE A BLUEPRINT FOR THIS ALTERNATIVE REALITY ONLY.
"""
    
    # Normal context for sequel/genre_swap
    normal_context = f"""
RETRIEVED CONTEXT (for reference only - use as source material):
{json.dumps(retrieved_context, indent=2)[:4000]}

USER PROMPT/DIRECTION:
{user_prompt}

USE CASE: {use_case}
{"" if not genre else f"TARGET GENRE: {genre}"}

GENRE MODIFIER:
{genre_modifier}
"""
    
    # Combine based on use case
    if use_case == "what_if":
        context_section = what_if_override
    else:
        context_section = normal_context
    
    return f"""
{context_section}

Based on this information, create a complete story blueprint.
The blueprint should be detailed and structured.
Include character arcs, acts, and total chapters.

For SEQUEL: Continue naturally from where the story left off.
For WHAT-IF: Create an entirely new timeline based on the premise.
For GENRE_SWAP: Keep plot points, change tone.

Return ONLY valid JSON.
"""


def build_outline_prompt(
    blueprint: dict,
    world_state: dict,
    previous_summaries: list[str],
    chapter_number: int,
) -> str:
    """Build prompt for chapter outline generation"""
    
    # Extract what-if context if present
    what_if_note = ""
    if "what_if_premise" in blueprint:
        what_if_note = f"""
WHAT-IF NOTE: This chapter MUST follow the alternative reality premise:
{blueprint.get('what_if_premise', '')}

Ignore canon. Write for the alternative timeline only.
"""
    
    return f"""
{what_if_note}

BLUEPRINT:
{json.dumps(blueprint, indent=2)[:3000]}

CURRENT WORLD STATE:
{json.dumps(world_state, indent=2)[:1500]}

PREVIOUS CHAPTER SUMMARIES:
{json.dumps(previous_summaries, indent=2)}

Generate a detailed outline for chapter {chapter_number}.
Include 2-4 scenes that advance the story according to the blueprint.

For WHAT-IF: Ensure the chapter reflects the alternative reality described in the blueprint.
For SEQUEL: Maintain continuity with previous events.
For GENRE_SWAP: Keep plot progression, adjust tone.

Return ONLY valid JSON with the specified structure.
"""


def build_scene_prompt(
    scene_outline: dict,
    chapter_outline: dict,
    world_state: dict,
    previous_scene_ending: str,
    genre_modifier: str,
) -> str:
    """Build prompt for scene prose generation"""
    
    pov_character = scene_outline.get("pov_character", "Feyre")
    scene_title = scene_outline.get("title", "Untitled Scene")
    scene_summary = scene_outline.get("summary", "No summary provided")
    
    # Extract what-if override if present in world_state
    what_if_note = ""
    if world_state.get("what_if_mode"):
        what_if_note = f"""
⚠️ WHAT-IF MODE ACTIVE ⚠️
This scene takes place in an alternative reality.
Do not reference canon events that didn't happen in this timeline.
Write as if the what-if premise is the ONLY true history.
POV Character Status: {world_state.get('what_if_character_status', {}).get(pov_character, 'As defined in premise')}
"""
    
    return f"""
{what_if_note}

CHAPTER CONTEXT:
Title: {chapter_outline.get('chapter_title', 'Unknown')}
Number: {chapter_outline.get('chapter_number', 'Unknown')}

SCENE TO WRITE:
Title: {scene_title}
Summary: {scene_summary}
POV Character: {pov_character}
Key Beats: {json.dumps(scene_outline.get('key_beats', []), indent=2)}

WORLD STATE (current):
{json.dumps(world_state, indent=2)[:1000]}

WHERE THE PREVIOUS SCENE ENDED:
{previous_scene_ending}

GENRE MODIFIER:
{genre_modifier}

Write this scene as immersive prose. Start where the previous scene ended.
Include:
- Dialogue that reveals character
- Sensory details (sights, sounds, smells, textures)
- Emotional beats
- Physical descriptions

Write approximately 500-800 words.
Maintain consistency with the world state and previous events.
{ "Follow the what-if premise strictly." if world_state.get("what_if_mode") else "Stay true to established characters." }
"""


def build_what_if_divergence_prompt(
    user_prompt: str,
    retrieved_context: dict,
) -> str:
    """Special prompt for establishing what-if divergence points"""
    
    elements = parse_what_if_prompt(user_prompt)
    
    return f"""
WHAT-IF SCENARIO ANALYSIS

USER'S ALTERNATIVE REALITY:
{user_prompt}

IDENTIFIED ELEMENTS:
- Divergence Point: {elements['divergence_point']}
- Time Skip: {elements['time_skip'] if elements['time_skip'] else 'Not specified'} years
- Character Changes: {json.dumps(elements['changed_character_status'], indent=2)}

ORIGINAL CANON (TO BE OVERRIDDEN):
Key characters from source material but their relationships and statuses may change.

YOUR TASK:
Create a divergence analysis that:
1. Identifies the exact point where history changed
2. Maps out the ripple effects of that change
3. Defines new character statuses and relationships
4. Establishes the new "canon" for this timeline

Return JSON with:
{{
    "divergence_point": "description of when/where things changed",
    "causal_ripples": ["effect1", "effect2"],
    "character_changes": {{
        "character_name": {{
            "original_status": "what they were",
            "new_status": "what they are in this timeline",
            "reason_for_change": "why"
        }}
    }},
    "relationship_changes": [
        {{
            "relationship": "description",
            "original_state": "canon state",
            "new_state": "what-if state"
        }}
    ],
    "new_timeline_premise": "one sentence summary of the alternative reality"
}}
"""


def build_causal_chain_prompt(
    divergence_point: str,
    user_prompt: str,
) -> str:
    """Build prompt for generating causal chains from a divergence point"""
    
    return f"""
CAUSAL CHAIN GENERATION

DIVERGENCE POINT:
{divergence_point}

USER PROMPT:
{user_prompt}

Generate a causal chain showing how this single change ripples through the story.

For each major event that would change, explain:
1. What originally happened (canon)
2. What happens instead (what-if)
3. Why this change occurs

Return JSON array of causal links:
[
    {{
        "event_name": "name",
        "canon_version": "what happened originally",
        "what_if_version": "what happens in alternative timeline",
        "causal_reason": "why this change occurs",
        "affected_characters": ["character1", "character2"]
    }}
]
"""


# ===========================================================================
# PERSPECTIVE SWAP PROMPTS
# ===========================================================================

def build_perspective_swap_system_prompt(target_pov: str, character_info: dict) -> str:
    """
    Build the system prompt for perspective swap generation.
    This provides detailed instructions for capturing the character's unique voice.
    """
    
    # Build character profile from available info
    character_profile = f"""
CHARACTER: {target_pov}

PERSONALITY TRAITS: {', '.join(character_info.get('personality_traits', ['To be inferred from the text'])) if character_info.get('personality_traits') else 'To be inferred from the original story'}

KNOWN DESCRIPTIONS:
{json.dumps(character_info.get('descriptions', []), indent=2) if character_info.get('descriptions') else 'Analyze from original text'}

VOICE CHARACTERISTICS:
- Vocabulary level: (educated/formal/colloquial/rough)
- Speech patterns: (direct/indirect/sarcastic/earnest)
- Internal thought style: (analytical/emotional/strategic/impulsive)
- Emotional expression: (open/guarded/intense/detached)

RELATIONSHIPS TO NOTE:
{json.dumps(character_info.get('relationships', []), indent=2) if character_info.get('relationships') else 'Extract from the story'}
"""
    
    return f"""
{PERSPECTIVE_SWAP_SYSTEM}

{character_profile}

Before writing each chapter, consider:
1. What does {target_pov} notice that others might miss?
2. What biases or blind spots does {target_pov} have?
3. How does {target_pov}'s history color their interpretation of events?
4. What physical sensations does {target_pov} experience in each moment?
5. What memories or associations do events trigger for {target_pov}?

Remember: The external events never change. Only the lens through which we see them changes.
"""


def build_perspective_swap_chapter_prompt(
    target_pov: str,
    original_chapter_content: str,
    chapter_number: int,
    original_pov: str,
    user_direction: str,
    character_context: dict,
) -> str:
    """
    Build the user prompt for rewriting a single chapter from a new perspective.
    """
    
    # Extract key relationships for this character
    relationships_note = ""
    if character_context.get("relationships"):
        relevant_rels = []
        for rel in character_context.get("relationships", []):
            if rel.get("entity_a", "").lower() == target_pov.lower() or rel.get("entity_b", "").lower() == target_pov.lower():
                relevant_rels.append(rel)
        if relevant_rels:
            relationships_note = f"""
KEY RELATIONSHIPS FOR {target_pov}:
{json.dumps(relevant_rels, indent=2)}

When writing scenes involving these characters, show {target_pov}'s unique history and feelings about them.
"""
    
    # Add character voice guidance
    voice_guidance = f"""
VOICE GUIDANCE FOR {target_pov}:

When writing from {target_pov}'s perspective, consider:
- How does {target_pov} refer to other characters? (nicknames? titles? formal names?)
- What kind of language does {target_pov} use? (military terms? courtly language? casual speech?)
- How does {target_pov} express emotion? (internally? outwardly? through action?)
- What does {target_pov} value most? (power? loyalty? love? honor? freedom?)
- What is {target_pov}'s greatest fear or vulnerability?

Use the original text as a source to infer these characteristics.
"""
    
    return f"""
{voice_guidance}

{relationships_note}

========================================
ORIGINAL CHAPTER {chapter_number}
Original POV: {original_pov}
========================================

{original_chapter_content}

========================================
YOUR TASK
========================================

Rewrite the ENTIRE chapter above from {target_pov}'s perspective.

CRITICAL INSTRUCTIONS:
1. Keep ALL dialogue EXACTLY the same - word for word
2. Keep ALL external actions EXACTLY the same
3. Change ONLY the internal experience, thoughts, and observations
4. Show what {target_pov} is thinking, feeling, and noticing
5. Reveal {target_pov}'s interpretations of other characters' actions and words
6. Include {target_pov}'s physical sensations and environment perception
7. Add internal reactions to dialogue and events
8. Show {target_pov}'s memories or associations triggered by events

What changes: WHO is telling us the story
What stays the same: WHAT happens in the story

ADDITIONAL DIRECTIONS FROM USER:
{user_direction if user_direction else "Focus on authenticity to the character's voice and perspective."}

Write the complete rewritten chapter. Start from the beginning of the chapter and rewrite every scene.
Use the same tense and person as the original (first-person or third-person).
Make us feel like we're inside {target_pov}'s head, experiencing the story through their eyes.
"""


def build_perspective_swap_summary_prompt(
    target_pov: str,
    chapters_rewritten: list,
) -> str:
    """
    Build prompt for generating a summary of insights from the perspective swap.
    """
    
    chapter_summaries = []
    for ch in chapters_rewritten[:3]:  # First 3 chapters for context
        chapter_summaries.append(f"Chapter {ch.get('number', '?')}: {ch.get('content', '')[:300]}...")
    
    return f"""
PERSPECTIVE SWAP ANALYSIS

Story has been rewritten from {target_pov}'s perspective.

Based on the rewritten chapters, provide a brief literary analysis covering:

1. What new insights do we gain about {target_pov} from seeing events through their eyes?
2. How does {target_pov}'s perspective change our understanding of other characters?
3. What emotional depth or hidden aspects of {target_pov} are revealed?
4. What does {target_pov} notice that the original POV character missed?

SAMPLE FROM REWRITTEN CHAPTERS:
{chr(10).join(chapter_summaries)}

Keep your analysis concise (200-300 words) and focused on specific insights revealed by the perspective shift.
"""


def build_perspective_swap_character_analysis_prompt(
    target_pov: str,
    original_chapters: list,
) -> str:
    """
    Build prompt for analyzing a character's voice before perspective swap.
    This helps the system understand the character before rewriting.
    """
    
    # Gather sample dialogue from the target character in the original text
    sample_lines = []
    for chapter in original_chapters[:3]:
        content = chapter.get("content", "")
        # Look for lines where the target character speaks
        lines = content.split('\n')
        for line in lines:
            if f'"{target_pov}' in line or f'{target_pov} said' in line or f'{target_pov} murmured' in line:
                sample_lines.append(line[:200])
    
    sample_dialogue = "\n".join(sample_lines[:10]) if sample_lines else "No direct dialogue found - analyze from context."
    
    return f"""
CHARACTER VOICE ANALYSIS

Target Character: {target_pov}

SAMPLE DIALOGUE/ACTIONS FROM ORIGINAL TEXT:
{sample_dialogue}

Based on this sample and your knowledge of the character, analyze:

1. VOCABULARY & SPEECH PATTERNS:
   - What words or phrases does {target_pov} favor?
   - Is their speech formal, casual, rough, or polished?
   - Do they use humor, sarcasm, or directness?

2. EMOTIONAL EXPRESSION:
   - How does {target_pov} express anger, fear, joy, or love?
   - Are they outwardly emotional or internally reserved?

3. OBSERVATION STYLE:
   - What does {target_pov} notice about others?
   - What details would they focus on in a scene?

4. INTERNAL WORLD:
   - What motivates {target_pov}?
   - What are their fears or insecurities?
   - How do they process stressful situations?

5. RELATIONSHIP DYNAMICS:
   - How does {target_pov} view other main characters?
   - What history influences their interactions?

Return a concise character profile that will guide the perspective rewrite.
"""


def get_character_pov_guidelines(character_name: str) -> str:
    """
    Get POV-specific writing guidelines for major characters.
    This helps maintain consistency in perspective swaps.
    """
    guidelines = {
        "Rhysand": """
Rhysand's POV Guidelines:
- Voice: Witty, layered, often hiding deeper meaning behind charm
- Internal: Constantly calculating, protective, burdened by leadership
- Observations: Notices everything, plays the long game
- Emotions: Guards vulnerabilities behind humor and deflection
- Focus: Feyre's safety, court politics, maintaining control
- Inner vocabulary: Strategic, analytical, occasionally vulnerable
""",
        "Cassian": """
Cassian's POV Guidelines:
- Voice: Direct, warm, with Illyrian bluntness
- Internal: Protective, loyal to a fault, struggles with self-worth
- Observations: Notices combat readiness, body language, threats
- Emotions: Expresses openly, wears heart on sleeve
- Focus: Brothers' safety, proving himself, Nesta's walls
- Inner vocabulary: Practical, earthy, occasionally self-deprecating
""",
        "Nesta": """
Nesta's POV Guidelines:
- Voice: Sharp, precise, cutting, uses words as weapons
- Internal: Deeply wounded, building walls, terrified of vulnerability
- Observations: Notices weaknesses, slights, and hidden agendas
- Emotions: Bottled beneath ice, explosive when triggered
- Focus: Protecting herself, pushing others away, numbing pain
- Inner vocabulary: Bitter, intelligent, self-loathing beneath pride
""",
        "Mor": """
Mor's POV Guidelines:
- Voice: Warm, bright, uses humor as armor
- Internal: Haunted by past, loyal to chosen family, hiding truth
- Observations: Notices social dynamics, reads people's true intentions
- Emotions: Expresses joy freely, hides pain behind brightness
- Focus: Protecting friends, avoiding the Hewn City, freedom
- Inner vocabulary: Honest, sometimes world-weary, resilient
""",
        "Amren": """
Amren's POV Guidelines:
- Voice: Ancient, cutting, dismissive of mortal concerns
- Internal: Calculating, assessing value and threat levels
- Observations: Notices power dynamics, magical residue, lies
- Emotions: Rarely expressed, shown through actions not words
- Focus: Puzzles, power, understanding the new world
- Inner vocabulary: Clinical, precise, alien in perspective
""",
        "Lucien": """
Lucien's POV Guidelines:
- Voice: Diplomatic, careful, with hints of buried anger
- Internal: Torn between loyalties, mourning lost loves
- Observations: Notices court politics, subtle manipulations
- Emotions: Guarded, expresses through sarcasm and deflection
- Focus: Survival, finding belonging, Elain's indifference
- Inner vocabulary: Wry, intelligent, weary
""",
        "Azriel": """
Azriel's POV Guidelines:
- Voice: Quiet, measured, speaks when necessary
- Internal: Haunted, protective, feels deeply but silently
- Observations: Notices threats, exits, shadows, secrets
- Emotions: Suppressed, shown through actions and shadows
- Focus: Mission success, protecting the vulnerable, Elain
- Inner vocabulary: Sparse, precise, occasionally unexpectedly tender
""",
        "Elain": """
Elain's POV Guidelines:
- Voice: Gentle, soft, chooses words carefully
- Internal: Quietly observant, seeing more than she shows
- Observations: Notices beauty, growth, potential for peace
- Emotions: Quiet, expressed through gardening and small kindnesses
- Focus: Creating beauty, avoiding conflict, finding her place
- Inner vocabulary: Poetic, gentle, sometimes unexpectedly strong
""",
    }
    
    # Try exact match, then partial match
    for name, guideline in guidelines.items():
        if name.lower() in character_name.lower() or character_name.lower() in name.lower():
            return guideline
    
    # Default guidelines for unknown characters
    return f"""
{character_name}'s POV Guidelines:
- Voice: Consistent with how they speak in the original text
- Internal: Driven by their stated goals and hidden fears
- Observations: Focuses on what matters to their role in the story
- Emotions: Expressed in character-appropriate ways
- Focus: Their personal stakes and relationships
- Inner vocabulary: Drawn from their dialogue patterns
"""
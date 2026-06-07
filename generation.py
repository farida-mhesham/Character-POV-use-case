import json
import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from prompts import (
    BLUEPRINT_SYSTEM,
    OUTLINE_SYSTEM,
    PROSE_SYSTEM,
    build_blueprint_prompt,
    build_outline_prompt,
    build_scene_prompt,
    get_genre_modifier,
)


MISTRAL_API_KEY = "jXOD1ZX2TXyI9qGJtyXeEQ9k5s3YhL6I"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "mistral-large-latest"


def create_session_with_retries():
    """Create a requests session with retry strategy"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
    retry_count: int = 3,
):
    """Call LLM with retry logic and better error handling"""
    
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    session = create_session_with_retries()
    last_error = None
    
    for attempt in range(retry_count):
        try:
            print(f"[DEBUG] API call attempt {attempt + 1}/{retry_count}")
            
            response = session.post(
                MISTRAL_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )
            
            response.raise_for_status()
            
            result = response.json()["choices"][0]["message"]["content"]
            print(f"[DEBUG] API call successful, response length: {len(result)}")
            return result
            
        except requests.exceptions.Timeout as e:
            last_error = e
            print(f"[DEBUG] Timeout error on attempt {attempt + 1}: {e}")
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 10
                print(f"[DEBUG] Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                
        except requests.exceptions.ConnectionError as e:
            last_error = e
            print(f"[DEBUG] Connection error on attempt {attempt + 1}: {e}")
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 15
                time.sleep(wait_time)
                
        except Exception as e:
            last_error = e
            print(f"[DEBUG] Error on attempt {attempt + 1}: {e}")
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 10
                time.sleep(wait_time)
    
    raise Exception(f"LLM call failed after {retry_count} attempts. Last error: {last_error}")


def parse_json(raw: str):
    """More robust JSON parsing that handles common LLM output issues"""
    
    print(f"[DEBUG] Attempting to parse JSON...")
    
    # Remove markdown code blocks
    cleaned = re.sub(r'```json\s*', '', raw)
    cleaned = re.sub(r'```\s*', '', cleaned)
    cleaned = cleaned.strip()
    
    # Try to find JSON object in the text
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        cleaned = json_match.group(0)
    
    # Fix common JSON issues
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)
    cleaned = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', cleaned)
    cleaned = re.sub(r':\s*\'([^\']*)\'', r': "\1"', cleaned)
    cleaned = re.sub(r':\s*([^"\[\]{}\s,][^,]*[^"\[\]{}\s,])', r': "\1"', cleaned)
    cleaned = re.sub(r'//.*?(\n|$)', '\n', cleaned)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'}\s*{', '},{', cleaned)
    cleaned = re.sub(r'(?<!")\n(?!")', ' ', cleaned)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse error: {e}")
        print(f"[ERROR] Raw text (first 500 chars): {raw[:500]}")
        return get_default_blueprint()


def get_default_blueprint():
    """Return a rich default blueprint structure"""
    return {
        "title": "A Court of Frost and Starlight - Continued",
        "premise": "Continue the story from where it left off, following the characters through new challenges and revelations.",
        "structure_type": "linear",
        "total_chapters": 5,
        "central_conflict": "The characters must face the consequences of their past actions while navigating new threats and relationships.",
        "primary_arcs": [
            {
                "arc_name": "Main Character Arc",
                "character": "Protagonist",
                "starts_at": "At a crossroads, uncertain of the future",
                "ends_at": "Having grown through challenges, ready for what comes next",
                "key_turning_point": "A crucial decision that changes everything"
            }
        ],
        "acts": [
            {
                "label": "Act One",
                "chapter_range": "1-2",
                "narrative_goal": "Establish the new status quo and inciting incident",
                "ends_with": "The protagonist makes a choice that sets events in motion"
            },
            {
                "label": "Act Two",
                "chapter_range": "3-4",
                "narrative_goal": "Complications arise and relationships are tested",
                "ends_with": "The situation reaches a critical point"
            },
            {
                "label": "Act Three",
                "chapter_range": "5",
                "narrative_goal": "Climax and resolution",
                "ends_with": "The story concludes with new understanding"
            }
        ],
        "world_threads_activated": [],
        "tone": "Dramatic and immersive, with emotional depth and tension"
    }


def compile_context(
    retrieved_context: dict,
    user_prompt: str,
    use_case: str,
    genre: str | None,
) -> dict:
    """Compile context for blueprint generation"""
    return {
        "use_case": use_case,
        "genre": genre,
        "user_prompt": user_prompt,
        "retrieved_context": retrieved_context,
    }


def generate_blueprint(compiled_context: dict):
    """Generate blueprint with error handling"""
    
    genre_modifier = get_genre_modifier(compiled_context.get("genre"))

    prompt = build_blueprint_prompt(
        compiled_context,
        genre_modifier,
    )
    
    print(f"[DEBUG] Generating blueprint with prompt length: {len(prompt)}")
    
    try:
        raw = call_llm(
            BLUEPRINT_SYSTEM,
            prompt,
            temperature=0.7,
            max_tokens=4000,
        )
        
        blueprint = parse_json(raw)
        
        if not blueprint.get("title"):
            blueprint["title"] = "Generated Story"
        if not blueprint.get("total_chapters"):
            blueprint["total_chapters"] = 5
        if not blueprint.get("acts"):
            blueprint["acts"] = get_default_blueprint()["acts"]
        if not blueprint.get("primary_arcs"):
            blueprint["primary_arcs"] = get_default_blueprint()["primary_arcs"]
            
        return blueprint
        
    except Exception as e:
        print(f"[ERROR] Blueprint generation failed: {e}")
        raise Exception(f"Failed to generate blueprint: {str(e)}")


def generate_outline(
    blueprint: dict,
    world_state: dict,
    previous_summaries: list[str],
    chapter_number: int,
):
    """Generate outline with error handling"""
    
    prompt = build_outline_prompt(
        blueprint,
        world_state,
        previous_summaries,
        chapter_number,
    )

    print(f"[DEBUG] Generating outline for chapter {chapter_number}")
    
    try:
        raw = call_llm(
            OUTLINE_SYSTEM,
            prompt,
            temperature=0.7,
            max_tokens=3000,
        )
        
        outline = parse_json(raw)
        
        if "chapter_number" not in outline:
            outline["chapter_number"] = chapter_number
        if "chapter_title" not in outline:
            outline["chapter_title"] = f"Chapter {chapter_number}"
        if "scenes" not in outline:
            outline["scenes"] = [
                {
                    "title": f"Scene 1",
                    "summary": f"Continue the story from chapter {chapter_number-1}",
                    "pov_character": "",
                    "key_beats": []
                }
            ]
        if "world_state_changes" not in outline:
            outline["world_state_changes"] = []
            
        return outline
        
    except Exception as e:
        print(f"[ERROR] Outline generation failed for chapter {chapter_number}: {e}")
        return {
            "chapter_number": chapter_number,
            "chapter_title": f"Chapter {chapter_number}",
            "scenes": [
                {
                    "title": f"Chapter {chapter_number} - Main Scene",
                    "summary": f"Continue the narrative, advancing the plot and character development.",
                    "pov_character": "",
                    "key_beats": []
                }
            ],
            "world_state_changes": []
        }


def generate_scene(
    scene_outline: dict,
    chapter_outline: dict,
    world_state: dict,
    previous_scene_ending: str,
    genre: str | None,
):
    """Generate scene prose with error handling"""
    
    genre_modifier = get_genre_modifier(genre)

    prompt = build_scene_prompt(
        scene_outline,
        chapter_outline,
        world_state,
        previous_scene_ending,
        genre_modifier,
    )

    print(f"[DEBUG] Generating scene: {scene_outline.get('title', 'Untitled')}")
    
    try:
        prose = call_llm(
            PROSE_SYSTEM,
            prompt,
            temperature=0.9,
            max_tokens=2000,
        )
        return prose
        
    except Exception as e:
        print(f"[ERROR] Scene generation failed: {e}")
        return f"[Scene generation failed: {str(e)}]"


# ===========================================================================
# PERSPECTIVE SWAP FUNCTION
# ===========================================================================

def generate_perspective_swap(
    retrieved_context: dict,
    target_pov: str,
    user_prompt: str,
    chapter_range: str | None = None,
) -> dict:
    """
    Generate a perspective swap of the original story from a new character's POV.
    
    Args:
        retrieved_context: The retrieved context with original chapters
        target_pov: The character whose perspective to use (e.g., "Rhysand", "Cassian")
        user_prompt: Additional directions for the rewrite
        chapter_range: Optional chapter range (e.g., "1-5")
    
    Returns:
        Dictionary with rewritten chapters from the new POV
    """
    
    original_chapters = retrieved_context.get("original_chapters", [])
    character_info = retrieved_context.get("character_info", {})
    
    print(f"[DEBUG] Perspective Swap: {target_pov}")
    print(f"[DEBUG] Found {len(original_chapters)} original chapters")
    
    # Parse chapter range if provided
    start_chapter = 1
    end_chapter = len(original_chapters)
    
    if chapter_range:
        import re
        match = re.match(r'(\d+)-(\d+)', chapter_range)
        if match:
            start_chapter = int(match.group(1))
            end_chapter = min(int(match.group(2)), len(original_chapters))
    
    # Filter chapters by range
    chapters_to_rewrite = [c for c in original_chapters if start_chapter <= c.get("number", 0) <= end_chapter]
    
    print(f"[DEBUG] Rewriting chapters {start_chapter}-{end_chapter} ({len(chapters_to_rewrite)} chapters)")
    
    # Build the system prompt for perspective swap
    system_prompt = f"""You are a master of character voice and perspective.

Your task is to rewrite the provided scenes from {target_pov}'s point of view.

IMPORTANT RULES:
1. Preserve ALL events, dialogue, and plot points exactly as they occur
2. Change ONLY whose thoughts and internal experiences we see
3. Show {target_pov}'s unique perspective on the same events
4. Maintain {target_pov}'s voice, personality, and thought patterns
5. Include {target_pov}'s internal reactions, observations, and interpretations
6. Keep all external actions and dialogue IDENTICAL to the original

Character Profile for {target_pov}:
{json.dumps(character_info, indent=2) if character_info else f"Character: {target_pov} - Write from their perspective, showing their unique voice and viewpoint."}

Write in first-person or close third-person consistent with {target_pov}'s perspective.
Return the complete rewritten chapter as prose.
"""
    
    rewritten_chapters = []
    
    for chapter in chapters_to_rewrite:
        chapter_num = chapter.get("number", 1)
        original_content = chapter.get("content", "")
        original_title = chapter.get("title", f"Chapter {chapter_num}")
        original_pov = chapter.get("pov_character", "Unknown")
        
        print(f"[DEBUG] Rewriting Chapter {chapter_num} from {original_pov}'s POV to {target_pov}'s POV...")
        
        # Build user prompt for this chapter
        chapter_prompt = f"""
ORIGINAL CHAPTER {chapter_num} (from {original_pov}'s POV):
{original_content}

ADDITIONAL DIRECTIONS:
{user_prompt if user_prompt else f"Focus on {target_pov}'s internal experience and unique perspective on these events."}

Rewrite this chapter from {target_pov}'s perspective.
Keep all dialogue and external actions exactly the same.
Show us what {target_pov} thinks, feels, notices, and how they interpret the events.

Write the complete rewritten chapter. Start from the beginning and rewrite everything.
"""
        
        try:
            # Call LLM for this chapter
            raw_response = call_llm(
                system_prompt,
                chapter_prompt,
                temperature=0.7,
                max_tokens=4000,
            )
            
            rewritten_chapters.append({
                "number": chapter_num,
                "original_title": original_title,
                "original_pov": original_pov,
                "content": raw_response,
                "length": len(raw_response)
            })
            
            print(f"[DEBUG] Successfully rewrote Chapter {chapter_num}")
            
        except Exception as e:
            print(f"[ERROR] Failed to rewrite chapter {chapter_num}: {e}")
            rewritten_chapters.append({
                "number": chapter_num,
                "original_title": original_title,
                "original_pov": original_pov,
                "content": f"[Failed to rewrite chapter {chapter_num} from {target_pov}'s perspective: {str(e)}]",
                "error": str(e)
            })
    
    # Generate a summary of the perspective swap
    summary_prompt = f"""
Based on rewriting the story from {target_pov}'s perspective, provide a brief summary of:
1. How {target_pov}'s viewpoint changes our understanding of the events
2. Key insights we gain from seeing through {target_pov}'s eyes
3. Any new emotional depth or understanding revealed

Keep the summary under 300 words.
"""
    
    try:
        summary = call_llm(
            "You are a literary analyst. Provide a concise summary.",
            summary_prompt,
            temperature=0.5,
            max_tokens=500,
        )
    except Exception as e:
        print(f"[ERROR] Failed to generate summary: {e}")
        summary = f"The story rewritten from {target_pov}'s perspective, preserving all events while revealing their unique viewpoint and internal experience."
    
    return {
        "mode": "perspective_swap",
        "target_pov": target_pov,
        "chapters_rewritten": len(rewritten_chapters),
        "total_chapters": len(original_chapters),
        "chapter_range": f"{start_chapter}-{end_chapter}" if chapter_range else "all",
        "summary": summary,
        "chapters": rewritten_chapters
    }

